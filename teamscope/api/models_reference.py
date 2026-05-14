"""
Reference / seed data models — frameworks, impact levels, and control families.
These are pre-populated by database/init/01_seed.sql and are read-only in the app.
"""
from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Framework(Base):
    __tablename__ = "frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # FedRAMP, GovRAMP, CMMC
    description: Mapped[str | None] = mapped_column(Text)

    impact_levels: Mapped[list["ImpactLevel"]] = relationship(back_populates="framework")


class ImpactLevel(Base):
    __tablename__ = "impact_levels"
    __table_args__ = (UniqueConstraint("framework_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("frameworks.id"))
    name: Mapped[str] = mapped_column(String(20), nullable=False)  # Low, Moderate, High, L1, L2, L3

    framework: Mapped["Framework"] = relationship(back_populates="impact_levels")
    control_families: Mapped[list["ControlFamily"]] = relationship(back_populates="impact_level")


class ControlFamily(Base):
    __tablename__ = "control_families"
    __table_args__ = (UniqueConstraint("impact_level_id", "code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    impact_level_id: Mapped[int] = mapped_column(ForeignKey("impact_levels.id"))
    code: Mapped[str] = mapped_column(String(10), nullable=False)   # AC, AU, CA, etc.
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    control_count: Mapped[int] = mapped_column(Integer, nullable=False)

    impact_level: Mapped["ImpactLevel"] = relationship(back_populates="control_families")
