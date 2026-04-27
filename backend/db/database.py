from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

DATABASE_URL = "sqlite:///./smartlead_audit.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def init_db() -> None:
    # Import all table models so SQLModel registers them before create_all
    import models.tables  # noqa: F401
    SQLModel.metadata.create_all(engine)
