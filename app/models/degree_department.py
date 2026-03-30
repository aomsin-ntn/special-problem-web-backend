from sqlmodel import SQLModel,Field
from app.models.degree import Degree
from app.models.department import Department
from uuid import UUID, uuid4

class DegreeDepartment(SQLModel, table=True):
    degree_id: UUID = Field(foreign_key="degrees.degree_id", primary_key=True)
    department_id: UUID = Field(foreign_key="departments.department_id", primary_key=True)
    department_order: int = Field(default=0)
    __tablename__ = "degree_department"