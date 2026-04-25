from datetime import datetime
import os

from sqlmodel import Session, select,or_, and_
from app.models.project import Project
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.project_file import ProjectFile, Status
from app.models.keyword import Keyword
from app.models.project_keyword import ProjectKeyword
from app.models.project_author import ProjectAuthor
from app.models.degree import Degree
from app.models.department import Department
from app.models.advisor import Advisor
from app.models.project_advisor import ProjectAdvisor
from app.models.degree_department import DegreeDepartment
from app.models.faculty import Faculty
from uuid import UUID, uuid4
from app.schemas.root_schema import GetProjectRequestParams
from sqlalchemy import func

class ProjectRepository:

    # --- 1. Project Search & Discovery ---
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
                        Keyword.keyword_text_en.ilike(f"%{term}%"),
                        Department.department_name_th.ilike(f"%{term}%"),
                        Department.department_name_en.ilike(f"%{term}%"),
                        Faculty.faculty_name_th.ilike(f"%{term}%"),
                        Faculty.faculty_name_en.ilike(f"%{term}%"),
                        Degree.degree_name_th.ilike(f"%{term}%"),
                        Degree.degree_name_en.ilike(f"%{term}%"),
                        Project.academic_year_be.ilike(f"%{term}%"),
                        Project.academic_year_ce.ilike(f"%{term}%")
                    )
                )
            filters.append(and_(*term_conditions))

        if request.department:
            filters.append(Department.department_id.in_(request.department))
        if request.year:
            filters.append(Project.academic_year_ce.in_(request.year))

        if request.sorted_by:
            if request.sorted_by == "downloaded_count":
                order_by = Project.downloaded_count.asc() if request.order == "asc" else Project.downloaded_count.desc()
            elif request.sorted_by == "created_at":
                order_by = Project.created_at.asc() if request.order == "asc" else Project.created_at.desc()
            elif request.sorted_by == "student_id":
                order_by = func.min(User.student_id).asc() if request.order == "asc" else func.min(User.student_id).desc()
            elif request.sorted_by == "user_name_th":
                order_by = func.min(User.user_name_th).asc() if request.order == "asc" else func.min(User.user_name_th).desc()
            elif request.sorted_by == "title_th":
                order_by = Project.title_th.asc() if request.order == "asc" else Project.title_th.desc()
            elif request.sorted_by == "academic_year":
                order_by = Project.academic_year_ce.asc() if request.order == "asc" else Project.academic_year_ce.desc()
        else:
            order_by = Project.created_at.desc()

        paged_projects = db.exec(
            select(Project.project_id)
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
            .join(ProjectFile, Project.file_id == ProjectFile.file_id, isouter=True) 
            .where(*filters, Project.is_active == True)
            .group_by(Project.project_id)
            .order_by(order_by)
            .offset((request.page - 1) * request.limit)
            .limit(request.limit)
        ).all()

        project_ids = list(paged_projects)

        if not project_ids:
            return {
                "data": [],
                "metadata": {
                    "total_items": 0,
                    "total_pages": 1,
                    "current_page": request.page,
                    "per_page": request.limit
                }
            }
    
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
            # ต้องมี ProjectFile join เข้ามาใน total_items ด้วย ไม่เช่นนั้นนับเลขหน้าผิด
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
                    "project_file": project_file.model_dump() if project_file else None 
                }

            if user and user.user_id not in [u["user_id"] for u in result[pid]["users"]]:
                result[pid]["users"].append(user.model_dump())

            if advisor and advisor.advisor_id not in [a["advisor_id"] for a in result[pid]["advisors"]]:
                result[pid]["advisors"].append(advisor.model_dump())

            if keyword and keyword.keyword_id not in [k["keyword_id"] for k in result[pid]["keywords"]]:
                result[pid]["keywords"].append(keyword.model_dump())

        ordered_data = [result[pid] for pid in project_ids if pid in result]
    
        return {
            "data": ordered_data,
            "metadata": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": request.page,
                "per_page": request.limit
            }
        }
    
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
    async def get_project_by_id(db: Session, project_id: UUID):
        project = db.exec(
            select(Project)
            .where(Project.project_id == project_id, Project.is_active == True)
        ).first()
        return project
    
    @staticmethod
    async def get_project_advisors_by_project_id(db: Session, project_id: UUID):
        advisors = db.exec(
            select(Advisor)
            .join(ProjectAdvisor, Advisor.advisor_id == ProjectAdvisor.advisor_id)
            .where(ProjectAdvisor.project_id == project_id)
        ).all()
        return advisors
    
    @staticmethod
    async def get_project_keywords_by_project_id(db: Session, project_id: UUID):
        keywords = db.exec(
            select(Keyword)
            .join(ProjectKeyword, Keyword.keyword_id == ProjectKeyword.keyword_id)
            .where(ProjectKeyword.project_id == project_id)
        ).all()
        return keywords
    
    @staticmethod
    async def get_keyword_by_id(db: Session, keyword_id: UUID):
        keyword = db.exec(
            select(Keyword)
            .where(Keyword.keyword_id == keyword_id)
        ).first()
        return keyword
    
    @staticmethod
    async def get_active_projects_for_duplicate_check(db: Session, year: str):
        return db.exec(
            select(Project).where(
                Project.is_active == True,
                Project.academic_year_ce == year
            )
        ).all()
    
    @staticmethod
    async def get_project_students(db: Session, project_id: UUID):
        return db.exec(
            select(ProjectAuthor, User)
            .join(User, User.user_id == ProjectAuthor.user_id)
            .where(ProjectAuthor.project_id == project_id)
        ).all()
    
    @staticmethod
    async def download_projectfile(db: Session, project_id: UUID):
        project_row = db.exec(
            select(Project, ProjectFile)
            .join(ProjectFile, Project.file_id == ProjectFile.file_id)
            .where(Project.project_id == project_id)
        ).first()

        if not project_row:
            return None

        project, project_file = project_row

        if not project_file:
            return None
        
        if not project_file.file_path or not os.path.exists(project_file.file_path):
            return None

        project.downloaded_count += 1
        db.commit()

        return project_file
    
    @staticmethod
    async def get_project_file_by_hash(db, file_hash: str):
        return db.exec(
            select(ProjectFile).where(ProjectFile.file_hash == file_hash)
        ).first()
    
    @staticmethod
    async def get_project_file_by_id(db: Session, file_id: UUID):
        return db.exec(
            select(ProjectFile)
            .where(ProjectFile.file_id == file_id)
        ).first()
    
    @staticmethod
    async def mark_file_as_saved(db: Session, file_id: UUID):
        project_file = db.get(ProjectFile, file_id)

        if not project_file:
            return None

        project_file.status = Status.SAVED
        db.add(project_file)
        db.flush()

        return project_file

    # --- 2. Create, Update, Delete (CRUD) ---
    @staticmethod
    async def create_project_no_commit(
        db: Session,
        title_th: str,
        title_en: str,
        abstract_th: str,
        abstract_en: str,
        academic_year_be: str,
        academic_year_ce: str,
        degree_id: UUID,
        created_by: UUID,
        file_id: UUID,
    ):
        project = Project(
            project_id=uuid4(),
            title_th=title_th,
            title_en=title_en,
            abstract_th=abstract_th,
            abstract_en=abstract_en,
            academic_year_be=academic_year_be,
            academic_year_ce=academic_year_ce,
            degree_id=degree_id,
            created_by=created_by,
            is_active=True,
            file_id=file_id,
            downloaded_count=0,
            )
        db.add(project)
        db.flush()
        return project
    

    @staticmethod
    async def create_project_file(
        db: Session,
        project_file_info: ProjectFile,
    ):
        project_file = ProjectFile(
            file_id=uuid4(),
            file_name=project_file_info.file_name,
            file_path=project_file_info.file_path,
            file_hash=project_file_info.file_hash,
            thumbnail_path=project_file_info.thumbnail_path,
            uploaded_at=datetime.utcnow(),
            status=Status.TEMP
        )

        db.add(project_file)
        db.commit()
        db.refresh(project_file)

        return project_file

    @staticmethod
    async def create_project_file_no_commit(
        db: Session,
        file_name: str,
        file_path: str,
        file_hash: str,
        thumbnail_path: str | None = None
    ):
        project_file = ProjectFile(
            file_id=uuid4(),
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            thumbnail_path=thumbnail_path,
            uploaded_at=datetime.utcnow()
        )

        db.add(project_file)
        db.flush()

        return project_file
    
    @staticmethod
    async def add_project_author_no_commit(
        db: Session,
        project_id: UUID,
        user_id: UUID,
        author_order: int
    ):
        project_author = ProjectAuthor(
            project_id=project_id,
            user_id=user_id,
            author_order=author_order
        )

        db.add(project_author)
        return project_author
    
    @staticmethod
    async def add_project_advisor_no_commit(
        db: Session,
        project_id: UUID,
        advisor_id: UUID, 
        advisor_order: int
    ):
        project_advisor = ProjectAdvisor(
            project_id=project_id,
            advisor_id=advisor_id,
            advisor_order=advisor_order
        )
        db.add(project_advisor)
        return project_advisor
    
    @staticmethod
    async def create_keyword_no_commit(
        db: Session, 
        th_text: str, 
        en_text: str
    ):
        keyword = Keyword(
            keyword_id=uuid4(),
            keyword_text_th=th_text,
            keyword_text_en=en_text
        )

        db.add(keyword)
        db.flush()
        return keyword
    
    @staticmethod
    async def add_project_keyword_no_commit(
        db: Session,
        project_id: UUID,
        keyword_id: UUID,
        keyword_order: int
    ):
        project_keyword = ProjectKeyword(
            project_id=project_id,
            keyword_id=keyword_id,
            keyword_order=keyword_order
        )

        db.add(project_keyword)
        return project_keyword
    
    @staticmethod
    async def update_project_file(db, project_file):
        db.add(project_file)
        db.commit()
        db.refresh(project_file)
        return project_file
    
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
    async def delete_project_advisors_no_commit(db: Session, project_id: UUID):
        rows = db.exec(
            select(ProjectAdvisor)
            .where(ProjectAdvisor.project_id == project_id)
        ).all()

        for row in rows:
            db.delete(row)

        db.flush()

    @staticmethod
    async def delete_project_keywords_no_commit(db: Session, project_id: UUID):
        rows = db.exec(
            select(ProjectKeyword)
            .where(ProjectKeyword.project_id == project_id)
        ).all()

        for row in rows:
            db.delete(row)

        db.flush()

    @staticmethod
    async def get_expired_temp_files(db: Session, expired_time: datetime):
        return db.exec(
            select(ProjectFile).where(
                ProjectFile.status == Status.TEMP,
                ProjectFile.uploaded_at < expired_time
            )
        ).all()

    @staticmethod
    async def delete_file_record(db: Session, file: ProjectFile):
        db.delete(file)

    @staticmethod
    async def is_project_owner(db: Session, project_id: UUID, user_id: UUID) -> bool:
        owner = db.exec(
            select(ProjectAuthor)
            .where(ProjectAuthor.project_id == project_id, ProjectAuthor.user_id == user_id)
        ).first()
        return owner is not None

    @staticmethod
    async def get_keyword_suggestions(db: Session):
        result = db.exec(
            select(Keyword)
            .limit(10)
        ).all()
        return result
    
    @staticmethod
    async def get_keywords(db:Session):
        keywords = db.exec(
            select(Keyword)      
        ).all()
        return keywords  
    
    @staticmethod
    async def get_active_project_by_file_id(db: Session, file_id: UUID):
        project =db.exec(
            select(Project)
            .where(
                Project.file_id == file_id,
                Project.is_active == True
            )
        ).first()
        return project