from sqlmodel import SQLModel, create_engine, Session
from app.models.faculty import Faculty
from app.models.department import Department
from app.models.degree import Degree
from app.models.advisor import Advisor
from app.models.keyword import Keyword
from app.models.project_file import ProjectFile
from app.models.correction_dictionary import CorrectionDictionary
from app.models.degree_department import DegreeDepartment
from app.models.user import User
from app.models.incorrect_word import IncorrectWord
from app.models.project import Project
from app.models.project_author import ProjectAuthor
from app.models.project_advisor import ProjectAdvisor
from app.models.project_keyword import ProjectKeyword
from app.models.session import Session as UserSession
from app.config import settings

db_host = settings.database_url
engine = create_engine(db_host, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_db():
    with Session(engine) as session:
        yield session
