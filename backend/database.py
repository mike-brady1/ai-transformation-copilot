from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

DATABASE_URL = "sqlite:///./workspaces.db"

# check_same_thread=False: SQLite normally refuses to be touched from a
# thread other than the one that opened the connection. FastAPI can serve
# requests from different threads, so we relax that for local dev.
# (Not needed once we point this at Postgres later.)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()
