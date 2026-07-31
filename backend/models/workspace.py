from typing import Optional

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str] = mapped_column(String)
    industry: Mapped[str] = mapped_column(String)
    employees: Mapped[int] = mapped_column(Integer)
    countries: Mapped[list] = mapped_column(JSON)
    current_erp: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    current_mes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
