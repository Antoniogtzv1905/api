from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "sqlite:///db.sqlite3"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)


def inicializar_bd() -> None:
    from models import User, Patient, Appointment, MedicalNote, VitalSign, Photo
    SQLModel.metadata.create_all(engine)


def obtener_sesion():
    with Session(engine) as session:
        yield session
