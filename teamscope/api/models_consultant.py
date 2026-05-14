"""
Consultant model — represents a team member who can be assigned to deliverables.
weekly_capacity is the total hours/week available (default 40).
float_name is how their name appears in Float CSV exports (may differ from display name).
color is a hex code used for color-coding in the grid.
"""
from sqlalchemy import Integer, String, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.database import Base


class Consultant(Base):
    __tablename__ = "consultants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(150), unique=True)
    weekly_capacity: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=40.0)
    float_name: Mapped[str | None] = mapped_column(String(100))  # Name as it appears in Float CSV
    color: Mapped[str] = mapped_column(String(7), default="#4C9BE8")  # Hex color for grid display
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
