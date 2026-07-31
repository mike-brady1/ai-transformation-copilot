from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ForeignKey ties every document row to exactly one workspace row.
    # The database itself now enforces "a document always belongs to a
    # real workspace" — it's not just a convention we hope the code follows.
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    filename: Mapped[str] = mapped_column(String)
    chunk_count: Mapped[int] = mapped_column(Integer)
