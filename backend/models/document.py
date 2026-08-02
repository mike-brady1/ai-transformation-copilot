from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
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
    # The raw extracted text, persisted so a document can be re-embedded
    # into Chroma automatically if that data is ever lost (e.g. an
    # ephemeral-disk host wiping it on redeploy) — Chroma was previously
    # the ONLY place the actual content lived, which is why that was
    # unrecoverable. Nullable: rows from before this column existed have
    # no stored text to recover from — an honest reflection of their
    # state, not something to backfill with a guess.
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
