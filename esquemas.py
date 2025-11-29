from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(SQLModel):
    name: str
    email: str
    password: str


class UserOut(SQLModel):
    id: int
    name: str
    email: str


class PatientCreate(SQLModel):
    name: str
    birth_date: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes_summary: Optional[str] = None
    photo_url: Optional[str] = None


class PatientOut(PatientCreate):
    id: int
    user_id: int


class AppointmentCreate(SQLModel):
    datetime: datetime
    reason: str
    doctor: str
    status: Optional[str] = "programada"


class AppointmentOut(AppointmentCreate):
    id: int
    patient_id: int


class MedicalNoteCreate(SQLModel):
    text: str


class MedicalNoteOut(MedicalNoteCreate):
    id: int
    patient_id: int
    created_at: datetime


class VitalSignCreate(SQLModel):
    weight: Optional[float] = None
    systolic: Optional[int] = None
    diastolic: Optional[int] = None
    heart_rate: Optional[int] = None


class VitalSignOut(VitalSignCreate):
    id: int
    patient_id: int
    recorded_at: datetime


class PhotoCreate(SQLModel):
    url: str
    caption: Optional[str] = None

class PhotoOut(PhotoCreate):
    id: int
    patient_id: int
    taken_at: datetime

