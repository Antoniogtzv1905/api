from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
from sqlalchemy import func
import os
import uuid
import shutil
from base_datos import inicializar_bd, obtener_sesion
from models import User, Patient, Appointment, MedicalNote, VitalSign, Photo
from esquemas import (
    Token, UserCreate, UserOut,
    PatientCreate, PatientOut,
    AppointmentCreate, AppointmentOut,
    MedicalNoteCreate, MedicalNoteOut,
    VitalSignCreate, VitalSignOut,
    PhotoOut
)

from auth import (
    hash_password, verify_password, create_access_token, get_current_user
)
openapi_tags = [
    {"name": "Sistema"},
    {"name": "Autenticación"},
    {"name": "Pacientes"},
    {"name": "Citas"},
    {"name": "Notas médicas"},
    {"name": "Signos vitales"},
    {"name": "Fotografías"},
]

app = FastAPI(
    title="MedApp API",
    version="1.0.0",
    openapi_tags=openapi_tags,
    docs_url="/docs",
    redoc_url=None,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.on_event("startup")
def on_startup():
    inicializar_bd()


@app.get("/health", tags=["Sistema"])
def health():
    return {"estado": "activo"}


@app.post("/auth/register", response_model=UserOut, status_code=201, tags=["Autenticación"])
def register(user_in: UserCreate, session: Session = Depends(obtener_sesion)):
    # Validar longitud de contraseña (bcrypt máximo 72 bytes)
    if len(user_in.password.encode('utf-8')) > 72:
        raise HTTPException(
            status_code=400,
            detail="La contraseña es demasiado larga (máximo 72 caracteres UTF-8)"
        )
    if session.exec(select(User).where(User.email == user_in.email)).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    user = User(name=user_in.name, email=user_in.email, password_hash=hash_password(user_in.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.post("/auth/login", response_model=Token, tags=["Autenticación"])
def login(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(obtener_sesion)):
    user = session.exec(select(User).where(User.email == form.username)).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)

@app.get("/users", response_model=List[UserOut], tags=["Autenticación"])
def list_users(session: Session = Depends(obtener_sesion)):
    """
    Endpoitn para mostrar todos los usurios disponibles
    """
    users = session.exec(select(User)).all()
    return users

# ---------------- PACIENTES ----------------
@app.get("/patients", response_model=List[PatientOut], tags=["Pacientes"])
def list_patients(
    search: Optional[str] = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion)
):
    query = select(Patient).where(Patient.user_id == user.id)
    if search:
        query = query.where(func.lower(Patient.name).like(f"%{search.lower()}%"))
    return session.exec(query).all()

@app.post("/patients", response_model=PatientOut, status_code=201, tags=["Pacientes"])
def create_patient(
    p: PatientCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = Patient(**p.dict(), user_id=user.id)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient

@app.get("/patients/{pid}", response_model=PatientOut, tags=["Pacientes"])
def get_patient(
    pid: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient

@app.put("/patients/{pid}", response_model=PatientOut, tags=["Pacientes"])
def update_patient(
    pid: int,
    p: PatientCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    for k, v in p.dict().items():
        setattr(patient, k, v)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient

@app.delete("/patients/{pid}", tags=["Pacientes"])
def delete_patient(
    pid: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    session.delete(patient)
    session.commit()
    return {"ok": True}

# ---------------- CITAS ----------------
@app.get("/patients/{pid}/appointments", response_model=List[AppointmentOut], tags=["Citas"])
def list_appointments(
    pid: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    return session.exec(select(Appointment).where(Appointment.patient_id == pid)).all()

@app.post("/patients/{pid}/appointments", response_model=AppointmentOut, status_code=201, tags=["Citas"])
def create_appointment(
    pid: int,
    ap: AppointmentCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    appt = Appointment(patient_id=pid, **ap.dict())
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt

@app.put("/appointments/{aid}", response_model=AppointmentOut, tags=["Citas"])
def update_appointment(
    aid: int,
    ap: AppointmentCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    appt = session.get(Appointment, aid)
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    patient = session.exec(
        select(Patient).where(Patient.id == appt.patient_id, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta cita")

    for k, v in ap.dict().items():
        setattr(appt, k, v)
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt

@app.delete("/appointments/{aid}", tags=["Citas"])
def delete_appointment(
    aid: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    appt = session.get(Appointment, aid)
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    patient = session.exec(
        select(Patient).where(Patient.id == appt.patient_id, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta cita")

    session.delete(appt)
    session.commit()
    return {"ok": True}

# ---------------- NOTAS MÉDICAS ----------------
@app.get("/patients/{pid}/notes", response_model=List[MedicalNoteOut], tags=["Notas médicas"])
def list_notes(
    pid: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    return session.exec(select(MedicalNote).where(MedicalNote.patient_id == pid)).all()

@app.post("/patients/{pid}/notes", response_model=MedicalNoteOut, status_code=201, tags=["Notas médicas"])
def create_note(
    pid: int,
    note: MedicalNoteCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    n = MedicalNote(patient_id=pid, text=note.text)
    session.add(n)
    session.commit()
    session.refresh(n)
    return n

@app.put("/notes/{note_id}", response_model=MedicalNoteOut, tags=["Notas médicas"])
def update_note(
    note_id: int,
    note: MedicalNoteCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    medical_note = session.get(MedicalNote, note_id)
    if not medical_note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    patient = session.exec(
        select(Patient).where(Patient.id == medical_note.patient_id, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta nota")

    medical_note.text = note.text
    session.add(medical_note)
    session.commit()
    session.refresh(medical_note)
    return medical_note

@app.delete("/notes/{note_id}", tags=["Notas médicas"])
def delete_note(
    note_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    medical_note = session.get(MedicalNote, note_id)
    if not medical_note:
        raise HTTPException(status_code=404, detail="Nota no encontrada")

    patient = session.exec(
        select(Patient).where(Patient.id == medical_note.patient_id, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta nota")

    session.delete(medical_note)
    session.commit()
    return {"ok": True}

# ---------------- SIGNOS VITALES ----------------
@app.get("/patients/{pid}/vitals", response_model=List[VitalSignOut], tags=["Signos vitales"])
def list_vitals(
    pid: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    return session.exec(select(VitalSign).where(VitalSign.patient_id == pid)).all()

@app.post("/patients/{pid}/vitals", response_model=VitalSignOut, status_code=201, tags=["Signos vitales"])
def create_vital(
    pid: int,
    vs: VitalSignCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    v = VitalSign(patient_id=pid, **vs.dict())
    session.add(v)
    session.commit()
    session.refresh(v)
    return v

@app.put("/vitals/{vital_id}", response_model=VitalSignOut, tags=["Signos vitales"])
def update_vital(
    vital_id: int,
    vs: VitalSignCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    vital_sign = session.get(VitalSign, vital_id)
    if not vital_sign:
        raise HTTPException(status_code=404, detail="Signo vital no encontrado")

    patient = session.exec(
        select(Patient).where(Patient.id == vital_sign.patient_id, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este registro")

    for k, v in vs.dict().items():
        setattr(vital_sign, k, v)
    session.add(vital_sign)
    session.commit()
    session.refresh(vital_sign)
    return vital_sign

@app.delete("/vitals/{vital_id}", tags=["Signos vitales"])
def delete_vital(
    vital_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    vital_sign = session.get(VitalSign, vital_id)
    if not vital_sign:
        raise HTTPException(status_code=404, detail="Signo vital no encontrado")

    patient = session.exec(
        select(Patient).where(Patient.id == vital_sign.patient_id, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este registro")

    session.delete(vital_sign)
    session.commit()
    return {"ok": True}

# ---------------- FOTOGRAFÍAS ----------------
@app.get("/patients/{pid}/photos", response_model=List[PhotoOut], tags=["Fotografías"])
def list_photos(
    pid: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    return session.exec(select(Photo).where(Photo.patient_id == pid)).all()

@app.post("/patients/{pid}/photos", response_model=PhotoOut, status_code=201, tags=["Fotografías"])
async def upload_photo(
    pid: int,
    file: UploadFile = File(...),
    caption: Optional[str] = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    """
    Subir una foto/imagen para un paciente.
    Soporta formatos comunes: JPG, PNG, GIF, etc.
    """
    patient = session.exec(
        select(Patient).where(Patient.id == pid, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    p = Photo(
        patient_id=pid,
        url=f"/uploads/{unique_filename}",
        caption=caption
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p

@app.delete("/photos/{photo_id}", tags=["Fotografías"])
def delete_photo(
    photo_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(obtener_sesion),
):
    """
    Eliminar una foto.
    También elimina el archivo físico del servidor.
    """
    photo = session.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    patient = session.exec(
        select(Patient).where(Patient.id == photo.patient_id, Patient.user_id == user.id)
    ).first()
    if not patient:
        raise HTTPException(status_code=403, detail="No tienes permiso para eliminar esta foto")

    if photo.url.startswith("/uploads/"):
        file_path = photo.url.lstrip("/")
        if os.path.exists(file_path):
            os.remove(file_path)

    session.delete(photo)
    session.commit()
    return {"ok": True, "message": "Foto eliminada exitosamente"}
