from sqlmodel import Session, select,or_, and_
from app.models.project import Project
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.project_file import ProjectFile
from app.models.keyword import Keyword
from app.models.project_keyword import ProjectKeyword
from app.models.project_author import ProjectAuthor
from app.models.degree import Degree
from app.models.department import Department
from app.models.advisor import Advisor
from app.models.project_file import ProjectFile
from app.models.project_advisor import ProjectAdvisor
from app.models.project_author import ProjectAuthor
from app.models.project_keyword import ProjectKeyword
from app.models.degree_department import DegreeDepartment
from app.models.faculty import Faculty
from uuid import UUID
from app.schemas.root_schema import GetProjectRequestParams
from sqlalchemy import func
from app.models.incorrect_word import IncorrectWord
from app.models.correction_dictionary import CorrectionDictionary
from app.models.custom_dictionary import CustomDictionary

class ProjectRepository:
    @staticmethod
    async def get_most_downloaded_projects(db: Session):
        subquery = (
            select(Project.project_id)
            .where(Project.is_active == True)
            .order_by(Project.downloaded_count.desc())
            .limit(5)
            .subquery()
        )

        result = db.exec(
            select(Project, Keyword, Department)
            .join(Degree, Project.degree_id == Degree.degree_id)
            .join(DegreeDepartment, Degree.degree_id == DegreeDepartment.degree_id)
            .join(Department, DegreeDepartment.department_id == Department.department_id)
            .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id)
            .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id)
            .where(Project.project_id.in_(subquery))
        ).all()

        return result
    
    @staticmethod
    async def get_keyword_suggestions(db: Session):
        result = db.exec(
            select(Keyword)
            .limit(10)
        ).all()
        return result

    @staticmethod
    async def get_project_details(db: Session, project_id: UUID):
        result = db.exec(
            select(Project, User, Keyword, Faculty, Degree, Department, ProjectFile, Advisor)
            .join(ProjectAuthor, Project.project_id == ProjectAuthor.project_id)
            .join(User, ProjectAuthor.user_id == User.user_id)
            .join(Degree, Project.degree_id == Degree.degree_id)
            .join(DegreeDepartment, Degree.degree_id == DegreeDepartment.degree_id)
            .join(Department, DegreeDepartment.department_id == Department.department_id)
            .join(Faculty, Department.faculty_id == Faculty.faculty_id)
            .join(ProjectFile, Project.file_id == ProjectFile.file_id)
            .join(ProjectAdvisor, Project.project_id == ProjectAdvisor.project_id)
            .join(Advisor, ProjectAdvisor.advisor_id == Advisor.advisor_id)
            .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id)
            .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id)
            .where(Project.project_id == project_id, Project.is_active == True)
        ).all()
        return result
    
    @staticmethod
    async def get_error_dict(db: AsyncSession):
        result = db.exec(
            select(IncorrectWord,CorrectionDictionary)
            .join(CorrectionDictionary,IncorrectWord.word_dic_id == CorrectionDictionary.word_dic_id)
            .where(IncorrectWord.count >= 10 )
        ).all()
        return result
    
    @staticmethod
    async def get_custom_dict(db: AsyncSession):
        result = db.exec(
            select(CustomDictionary)
        ).all()
        return result

    @staticmethod
    async def create_project(db: AsyncSession, project_data: Project):
        db.add(project_data)
        db.commit()
        db.refresh(project_data)
        return project_data

    @staticmethod
    async def create_project_file(db: AsyncSession, project_file: ProjectFile):
        db.add(project_file)
        db.commit()
        db.refresh(project_file)
        return project_file
    
    @staticmethod
    async def create_project_author(db: AsyncSession, project_author: ProjectAuthor):
        db.add(project_author)
        db.commit()
        db.refresh(project_author)
        return project_author

    @staticmethod
    async def create_project_advisor(db: AsyncSession, project_advisor: ProjectAdvisor):
        db.add(project_advisor)
        db.commit()
        db.refresh(project_advisor)
        return project_advisor
    
    @staticmethod
    async def create_keyword(db: AsyncSession, keyword: Keyword):
        db.add(keyword)
        db.commit()
        db.refresh(keyword)
        return keyword

    @staticmethod
    async def create_project_keyword(db: AsyncSession, project_keyword: ProjectKeyword):
        db.add(project_keyword)
        db.commit()
        db.refresh(project_keyword)
        return project_keyword
    
    @staticmethod
    async def is_project_owner(db: Session, project_id: UUID, user_id: UUID) -> bool:
        owner = db.exec(
            select(ProjectAuthor)
            .where(ProjectAuthor.project_id == project_id, ProjectAuthor.user_id == user_id)
        ).first()
        return owner is not None

    @staticmethod
    async def delete_project(db: Session, project_id: UUID):
        project = db.exec(
            select(Project).where(Project.project_id == project_id)
        ).first()
        print(f"Project query result: {project}")
        if project:
            print(f"Project found: {project.project_id}")
            project.is_active = False  # Mark the project as inactive instead of deleting it
            db.add(project)  # Add the project back to the session to mark it as dirty
            db.commit()
            db.refresh(project) 
        return project

    @staticmethod
    async def get_projects(db: Session, request: GetProjectRequestParams):
        filters = []
        if request.search:
            search_terms = request.search.strip().split()

            term_conditions = []
            for term in search_terms:
                term_conditions.append(
                    or_ (
                        Project.title_en.ilike(f"%{term}%"),
                        Project.title_th.ilike(f"%{term}%"),
                        User.user_name_th.ilike(f"%{term}%"),
                        User.user_name_en.ilike(f"%{term}%"),
                        User.student_id.ilike(f"%{term}%"),
                        Advisor.advisor_name_th.ilike(f"%{term}%"),
                        Advisor.advisor_name_en.ilike(f"%{term}%"),
                        Keyword.keyword_text_th.ilike(f"%{term}%"),
                        Keyword.keyword_text_en.ilike(f"%{term}%")
                    )
                )
            filters.append(and_(*term_conditions))

        if request.department:
            filters.append(Department.department_id.in_(request.department))
        if request.year:
            filters.append(Project.academic_year.in_(request.year))
            
        if request.sorted_by:
            if request.sorted_by == "downloaded_count":
                if request.order == "asc":
                    order_by = Project.downloaded_count.asc()
                else:
                    order_by = Project.downloaded_count.desc()
            elif request.sorted_by == "created_at":
                if request.order == "asc":
                    order_by = Project.created_at.asc()
                else:
                    order_by = Project.created_at.desc()
        else:
            order_by = Project.created_at.desc()

        paged_projects = db.exec(
            select(Project).distinct()
            .join(ProjectAuthor, Project.project_id == ProjectAuthor.project_id)
            .join(User, ProjectAuthor.user_id == User.user_id)
            .join(ProjectAdvisor, Project.project_id == ProjectAdvisor.project_id)
            .join(Advisor, ProjectAdvisor.advisor_id == Advisor.advisor_id)
            .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id, isouter=True) # แนะนำให้ใช้ isouter=True
            .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id, isouter=True)
            .join(Degree, Project.degree_id == Degree.degree_id)
            .join(DegreeDepartment, Degree.degree_id == DegreeDepartment.degree_id)
            .join(Department, DegreeDepartment.department_id == Department.department_id)
            .join(Faculty, Department.faculty_id == Faculty.faculty_id)
            # 👇 เติม isouter=True เพื่อป้องกันโปรเจกต์ที่ไม่มีไฟล์หายไปจากระบบ
            .join(ProjectFile, Project.file_id == ProjectFile.file_id, isouter=True) 
            .where(*filters, Project.is_active == True)
            .order_by(order_by)
            .offset((request.page - 1) * request.limit)
            .limit(request.limit)
        ).all()

        project_ids = [p.project_id for p in paged_projects]

        if not project_ids:
            projects = []
        else:
            projects = db.exec(
                select(Project, User, Advisor, Keyword, Faculty, Department, ProjectFile)
                .join(ProjectAuthor, Project.project_id == ProjectAuthor.project_id)
                .join(User, ProjectAuthor.user_id == User.user_id)
                .join(ProjectAdvisor, Project.project_id == ProjectAdvisor.project_id)
                .join(Advisor, ProjectAdvisor.advisor_id == Advisor.advisor_id)
                .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id, isouter=True)
                .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id, isouter=True)
                .join(Degree, Project.degree_id == Degree.degree_id)
                .join(DegreeDepartment, Degree.degree_id == DegreeDepartment.degree_id)
                .join(Department, DegreeDepartment.department_id == Department.department_id)
                .join(Faculty, Department.faculty_id == Faculty.faculty_id)
                .join(ProjectFile, Project.file_id == ProjectFile.file_id, isouter=True)
                .where(Project.project_id.in_(project_ids))
                .order_by(order_by)
            ).all()

        total_items = db.exec(
            select(func.count(func.distinct(Project.project_id)))
            .join(ProjectAuthor, Project.project_id == ProjectAuthor.project_id)
            .join(User, ProjectAuthor.user_id == User.user_id)
            .join(ProjectAdvisor, Project.project_id == ProjectAdvisor.project_id)
            .join(Advisor, ProjectAdvisor.advisor_id == Advisor.advisor_id)
            .join(ProjectKeyword, Project.project_id == ProjectKeyword.project_id, isouter=True)
            .join(Keyword, ProjectKeyword.keyword_id == Keyword.keyword_id, isouter=True)
            .join(Degree, Project.degree_id == Degree.degree_id)
            .join(DegreeDepartment, Degree.degree_id == DegreeDepartment.degree_id)
            .join(Department, DegreeDepartment.department_id == Department.department_id)
            .join(Faculty, Department.faculty_id == Faculty.faculty_id)
            # 👇 ต้องมี ProjectFile join เข้ามาใน total_items ด้วย ไม่เช่นนั้นนับเลขหน้าผิด
            .join(ProjectFile, Project.file_id == ProjectFile.file_id, isouter=True) 
            .where(*filters, Project.is_active == True)
        ).one()

        total_pages = (total_items + request.limit - 1) // request.limit

        result = {}
        # วนลูป โดยมี project_file ออกมาด้วย
        for project, user, advisor, keyword, faculty, department, project_file in projects:
            pid = project.project_id

            if pid not in result:
                result[pid] = {
                    "project": project.model_dump(),
                    "users": [],
                    "advisors": [],
                    "keywords": [],
                    "faculty": faculty.model_dump(),
                    "department": department.model_dump(),
                    # 👇 แก้ไขให้ดึงจากตัวแปร project_file โดยตรง
                    "project_file": project_file.model_dump() if project_file else None 
                }

            if user and user.user_id not in [u["user_id"] for u in result[pid]["users"]]:
                result[pid]["users"].append(user.model_dump())

            if advisor and advisor.advisor_id not in [a["advisor_id"] for a in result[pid]["advisors"]]:
                result[pid]["advisors"].append(advisor.model_dump())

            if keyword and keyword.keyword_id not in [k["keyword_id"] for k in result[pid]["keywords"]]:
                result[pid]["keywords"].append(keyword.model_dump())

        return {
            "data": list(result.values()),
            "metadata": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": request.page,
                "per_page": request.limit
            }
        }

    @staticmethod
    async def get_faculty(db: Session):
        faculty = db.exec(
            select(Faculty, Department)
            .join(Department, Faculty.faculty_id == Department.faculty_id)
            ).all()

        result = {} 
        for faculty,department in faculty:
            fid = faculty.faculty_id

            if fid not in result:
                result[fid] = {
                    "faculty": faculty.model_dump(),
                    "departments": [],
                }

            # กันซ้ำใน list
            if department.department_id not in [u["department_id"] for u in result[fid]["departments"]]:
                result[fid]["departments"].append(department.model_dump())

        return list(result.values())

    @staticmethod
    async def download_projectfile(db:Session,project_id:UUID):
        project_row = db.exec(
            select(Project, ProjectFile)
            .join(ProjectFile, Project.file_id == ProjectFile.file_id)
            .where(Project.project_id == project_id)
        ).first()

        if not project_row:
            return None

        project, project_file = project_row

        project.downloaded_count += 1
        db.commit()
        return project_file

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

    @staticmethod
    async def get_keywords(db:Session):
        keywords = db.exec(
            select(Keyword)      
        ).all()
        return keywords   
