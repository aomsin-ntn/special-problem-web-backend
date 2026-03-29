from sqlmodel import SQLModel,Field
from app.models.degree import Degree
from app.models.department import Department

class DegreeDepartment(SQLModel, table=True):
    degree_id: str = Field(foreign_key="degrees.degree_id", primary_key=True, max_length=6)
    department_id: str = Field(foreign_key="departments.department_id", primary_key=True, max_length=2)
    department_order: int = Field(default=0)
    __tablename__ = "degree_department"