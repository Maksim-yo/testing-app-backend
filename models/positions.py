from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from db.database import Base
from sqlalchemy.orm import relationship

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=False, index=True)
    description = Column(String)
    access_level = Column(String, default="basic")
    salary = Column(Integer)
    has_system_access = Column(Boolean, default=False)
    belbin_requirements = relationship("BelbinPositionRequirement", back_populates="position")
    employees = relationship("Employee", back_populates="position", foreign_keys="[Employee.position_id]")

    created_by_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE") )
    created_by = relationship("Employee", back_populates="created_positions", foreign_keys=[created_by_id])
