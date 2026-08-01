import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

# Falls back to a local SQLite file for local dev; set DATABASE_URL (e.g.
# to a Neon Postgres connection string) in production. SQLAlchemy is an
# ORM specifically so this swap doesn't touch any other code.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./workspaces.db")

# check_same_thread=False is SQLite-specific: SQLite refuses to be touched
# from a thread other than the one that opened the connection, and FastAPI
# can serve requests from different threads. Postgres has no such
# restriction and doesn't accept this argument, so only apply it for SQLite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


class Base(DeclarativeBase):
    pass


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
