from sqlmodel import select, Session

from app.models.advisor import Advisor
from app.models.degree import Degree
from app.models.degree_department import DegreeDepartment
from app.models.department import Department
from app.models.faculty import Faculty


class MasterDataRepository:

    @staticmethod
    async def get_master_faculties(db:Session):
        faculty = db.exec(
            select(Faculty)
        ).all()
        return faculty
    
    @staticmethod
    async def get_master_advisors(db:Session):
        advisors = db.exec(
            select(Advisor)
        ).all()
        return advisors

    @staticmethod
    async def get_master_departments(db:Session):
        departments = db.exec(
            select(Department)
        ).all()
        return departments

    @staticmethod
    async def get_master_degrees_data(db:Session):
        degrees = db.exec(
            select(Degree)
        ).all()
        return degrees

    @staticmethod
    async def get_master_degrees(db:Session):
        result = db.exec(
            select(
                Degree.degree_id, 
                Degree.degree_name_th, 
                Degree.degree_name_en, 
                DegreeDepartment.department_id
            )
            .join(DegreeDepartment, Degree.degree_id == DegreeDepartment.degree_id)
        ).all()
        
        return [
            {
                "degree_id": row.degree_id,
                "degree_name_th": row.degree_name_th,
                "degree_name_en": row.degree_name_en,
                "department_id": row.department_id
            }
            for row in result
        ]