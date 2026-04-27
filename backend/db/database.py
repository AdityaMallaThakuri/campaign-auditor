from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event
from typing import Generator

DATABASE_URL = "sqlite:///./smartlead_audit.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)


@event.listens_for(engine.sync_engine if hasattr(engine, "sync_engine") else engine, "connect")
def set_wal_mode(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA busy_timeout=30000")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def init_db() -> None:
    # Import all table models so SQLModel registers them before create_all
    import models.tables  # noqa: F401
    SQLModel.metadata.create_all(engine)
