from datetime import datetime, timezone

from app.models import department
from app.models.incorrect_word import IncorrectWord
from app.models.keyword import Keyword
from app.models.project import Project
from app.models.project_advisor import ProjectAdvisor
from app.models.project_advisor import ProjectAdvisor
from app.models.project_author import ProjectAuthor
from app.models.project_file import ProjectFile
from app.models.project_keyword import ProjectKeyword
from app.models.user import Role, User
from app.repository.project_repository import ProjectRepository
from sqlmodel import Session, select
from fastapi import HTTPException
from app.schemas.project_schema import ProjectSubmitRequest
from app.schemas.root_schema import GetProjectRequestParams
from uuid import UUID, uuid4
from app.repository.user_repository import UserRepository
from app.services.textcomparison_services import TextComparisonServices
from app.models.correction_dictionary import CorrectionDictionary
import difflib
import re

class ProjectServices:
    @staticmethod
    async def get_projects(db: Session, request: GetProjectRequestParams):
        print("Debug (request):", request)
        if request.year:
            request.year = ProjectServices.normalize_years(request.year)
        print("Debug (request after normalization):", request)
        projects = await ProjectRepository.get_projects(db, request)
        return projects
    
    @staticmethod
    def normalize_years(years):
        result = []
        for y in years:
            try:
                y = int(y)
                if y > 2400:
                    y -= 543
                result.append(str(y))  
            except (ValueError, TypeError):
                continue
        return result
    
    @staticmethod
    async def get_error_dict(db: Session):
        error_dict = await ProjectRepository.get_error_dict(db)
        return error_dict
    
    @staticmethod
    async def get_custom_dict(db: Session):
        custom_dict = await ProjectRepository.get_custom_dict(db)
        return custom_dict

    @staticmethod
    async def get_dictionary_report(db: Session, table_type: str, page: int, limit: int, sorted_by: str, order: str):
        report = await ProjectRepository.get_dictionary_report(db, table_type, page, limit, sorted_by, order)
        return report
    
    @staticmethod
    async def delete_project(db: Session, project_id: int, user_id: UUID):
        has_permission = await ProjectServices.check_edit_permission(db, project_id, user_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="คุณไม่มีสิทธิ์ลบข้อมูลนี้")
        return await ProjectRepository.delete_project(db, project_id)

    @staticmethod
    async def create_project(db: Session, project_data):
        new_project = await ProjectRepository.create_project(db, project_data)
        return new_project

    @staticmethod
    async def download_projectfile(db:Session,project_id):
        projectfile = await ProjectRepository.download_projectfile(db,project_id)
        if not projectfile:
            raise HTTPException(status_code=404, detail="Project not found")
        return projectfile

    @staticmethod
    async def get_faculty(db: Session):
        faculty = await ProjectRepository.get_faculty(db)
        return faculty

    @staticmethod
    async def get_master_faculties(db:Session):
        faculty = await ProjectRepository.get_master_faculties(db)
        return faculty

    @staticmethod
    async def get_master_departments(db:Session):
        departments = await ProjectRepository.get_master_departments(db)
        return departments

    @staticmethod
    async def get_master_advisors(db:Session):
        advisors = await ProjectRepository.get_master_advisors(db)
        return advisors

    @staticmethod
    async def get_master_degrees(db:Session):
        degrees = await ProjectRepository.get_master_degrees(db)
        return degrees

    @staticmethod
    async def get_user_by_student_id(db:Session, student_id:str):
        user = await UserRepository.get_user_by_student_id(db,student_id)
        return user
    
    @staticmethod
    async def create_project_keyword(db: Session, project_keyword_data):
        new_project_keyword = await ProjectRepository.create_project_keyword(db, project_keyword_data)
        return new_project_keyword
    
    @staticmethod
    async def create_keyword(db: Session, keyword_data):
        new_keyword = await ProjectRepository.create_keyword(db, keyword_data)
        return new_keyword
    
    @staticmethod
    async def create_project_advisor(db: Session, project_advisor_data):
        new_project_advisor = await ProjectRepository.create_project_advisor(db, project_advisor_data)
        return new_project_advisor
    
    @staticmethod
    async def get_keywords(db: Session):
        keywords = await ProjectRepository.get_keywords(db)
        return keywords
    
    @staticmethod
    async def create_project_author(db: Session, project_author_data):
        new_project_author = await ProjectRepository.create_project_author(db, project_author_data)
        return new_project_author
    
    @staticmethod
    async def create_project_file(db: Session, project_file_data):
        new_project_file = await ProjectRepository.create_project_file(db, project_file_data)
        return new_project_file

    @staticmethod
    async def get_project_details(db: Session, project_id: int):
        details = await ProjectRepository.get_project_details(db, project_id)
        result = {}
        for project, user, keyword, faculty, degree, department, project_file, advisor in details:
            pid = project.project_id

            if pid not in result:
                project_dict = project.dict()
                project_dict["authors"] = []
                project_dict["keywords"] = []
                project_dict["faculty"] = faculty.dict()
                project_dict["degree"] = degree.dict()
                project_dict["department"] = department.dict()
                project_dict["project_file"] = project_file.dict()
                project_dict["advisors"] = []
                result[pid] = project_dict

            if user.user_id not in [u["user_id"] for u in result[pid]["authors"]]:
                result[pid]["authors"].append(user.model_dump())

            if advisor.advisor_id not in [a["advisor_id"] for a in result[pid]["advisors"]]:
                result[pid]["advisors"].append(advisor.model_dump())

            if keyword.keyword_id not in [k["keyword_id"] for k in result[pid]["keywords"]]:
                result[pid]["keywords"].append(keyword.model_dump())

        final_result = list(result.values())
        return final_result

    @staticmethod
    async def get_most_downloaded_projects(db: Session):
        projects = await ProjectRepository.get_most_downloaded_projects(db)
        result = {}
        for project, keyword, department in projects:
            pid = project.project_id

            if pid not in result:
                project_dict = project.dict()
                project_dict["keywords"] = []
                project_dict["departments"] = []
                result[pid] = project_dict

            if department.department_id not in [d["department_id"] for d in result[pid]["departments"]]:
                result[pid]["departments"].append(department.model_dump())

            if keyword.keyword_id not in [k["keyword_id"] for k in result[pid]["keywords"]]:
                result[pid]["keywords"].append(keyword.model_dump())
            

        final_result = list(result.values())
        return final_result

    @staticmethod
    def find_match(target_th, target_en, items, th_attr, en_attr):
        def normalize(text):
            if not text: return ""
            # แปลงเป็นตัวพิมพ์เล็ก
            text = str(text).lower()
            # OCR fix: จัดการตัวเลขและตัวอักษรที่มักสับสน (Normalize กลับเป็นตัวเลขเพื่อความแม่นยำ)
            text = text.replace("o", "0").replace("l", "1").replace("s", "5")
            # ลบอักขระพิเศษและช่องว่าง (คงเหลือแค่ตัวอักษรไทย อังกฤษ และตัวเลข)
            text = re.sub(r'[^\w\u0E00-\u0E7F]', '', text) 
            return text

        norm_target_th = normalize(target_th)
        norm_target_en = normalize(target_en)

        best_match = None
        highest_score = 0

        if not items:
            return None

        for item in items:
            # --- FIX: รองรับทั้ง Dictionary (Degree) และ Object (Faculty/Dept) ---
            if isinstance(item, dict):
                raw_db_th = item.get(th_attr, "")
                raw_db_en = item.get(en_attr, "")
            else:
                raw_db_th = getattr(item, th_attr, "")
                raw_db_en = getattr(item, en_attr, "")

            db_th = normalize(raw_db_th)
            db_en = normalize(raw_db_en)

            # 1. คำนวณความใกล้เคียง (SequenceMatcher)
            score_th = difflib.SequenceMatcher(None, norm_target_th, db_th).ratio() if norm_target_th and db_th else 0
            score_en = difflib.SequenceMatcher(None, norm_target_en, db_en).ratio() if norm_target_en and db_en else 0
            
            current_score = max(score_th, score_en)

            # 2. กรณี Exact Match (หลัง Normalize) ให้คะแนนเต็มทันที
            if (norm_target_th and norm_target_th == db_th) or (norm_target_en and norm_target_en == db_en):
                current_score = 1.0

            # 3. กรณี "เป็นส่วนหนึ่งของกันและกัน" (Partial Match)
            # เช่น OCR อ่านได้ "วิศวกรรมศาสตร" แต่ DB คือ "วิศวกรรมศาสตรบัณฑิต"
            elif (norm_target_th and norm_target_th in db_th) or (db_th and db_th in norm_target_th):
                current_score = max(current_score, 0.85)
            
            elif (norm_target_en and norm_target_en in db_en) or (db_en and db_en in norm_target_en):
                current_score = max(current_score, 0.85)

            # บันทึกค่าที่ดีที่สุด
            if current_score > highest_score:
                highest_score = current_score
                best_match = item

        # คืนค่าถ้าความมั่นใจเกิน 0.6
        print(f"[Match Debug] Best Score: {highest_score:.2f} for '{target_th or target_en}'")
        return best_match if highest_score > 0.6 else None
    
    @staticmethod
    def find_match_keywords(target_th, target_en, items, th_attr, en_attr):
        def normalize(text):
            if not text: return ""
            # แปลงเป็นตัวพิมพ์เล็ก
            text = str(text).lower()
            # OCR fix: จัดการตัวเลขและตัวอักษรที่มักสับสน (Normalize กลับเป็นตัวเลขเพื่อความแม่นยำ)
            text = text.replace("o", "0").replace("l", "1").replace("s", "5")
            # ลบอักขระพิเศษและช่องว่าง (คงเหลือแค่ตัวอักษรไทย อังกฤษ และตัวเลข)
            text = re.sub(r'[^\w\u0E00-\u0E7F]', '', text) 
            return text

        norm_target_th = normalize(target_th)
        norm_target_en = normalize(target_en)

        best_match = None
        highest_score = 0

        if not items:
            return None

        for item in items:
            # --- FIX: รองรับทั้ง Dictionary (Degree) และ Object (Faculty/Dept) ---
            if isinstance(item, dict):
                raw_db_th = item.get(th_attr, "")
                raw_db_en = item.get(en_attr, "")
            else:
                raw_db_th = getattr(item, th_attr, "")
                raw_db_en = getattr(item, en_attr, "")

            db_th = normalize(raw_db_th)
            db_en = normalize(raw_db_en)

            # 1. คำนวณความใกล้เคียง (SequenceMatcher)
            score_th = difflib.SequenceMatcher(None, norm_target_th, db_th).ratio() if norm_target_th and db_th else 0
            score_en = difflib.SequenceMatcher(None, norm_target_en, db_en).ratio() if norm_target_en and db_en else 0
            
            current_score = max(score_th, score_en)

            # 2. กรณี Exact Match (หลัง Normalize) ให้คะแนนเต็มทันที
            if (norm_target_th and norm_target_th == db_th) or (norm_target_en and norm_target_en == db_en):
                current_score = 1.0

            # 3. กรณี "เป็นส่วนหนึ่งของกันและกัน" (Partial Match)
            # เช่น OCR อ่านได้ "วิศวกรรมศาสตร" แต่ DB คือ "วิศวกรรมศาสตรบัณฑิต"
            elif (norm_target_th and norm_target_th in db_th) or (db_th and db_th in norm_target_th):
                current_score = max(current_score, 0.85)
            
            elif (norm_target_en and norm_target_en in db_en) or (db_en and db_en in norm_target_en):
                current_score = max(current_score, 0.85)

            # บันทึกค่าที่ดีที่สุด
            if current_score > highest_score:
                highest_score = current_score
                best_match = item

        # คืนค่าถ้าความมั่นใจเกิน 0.6
        print(f"[Match Debug] Best Score: {highest_score:.2f} for '{target_th or target_en}'")
        return best_match if highest_score > 0.9 else None
    
    @staticmethod
    async def check_edit_permission(db: Session, project_id: UUID, user_id: UUID) -> bool:
        is_owner = await ProjectRepository.is_project_owner(db, project_id, user_id)
        return is_owner

    @staticmethod
    async def get_project_details_check_permission(db: Session, project_id: int, user_id: UUID):
        has_permission = await ProjectServices.check_edit_permission(db, project_id, user_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="คุณไม่มีสิทธิ์เข้าถึงข้อมูลนี้")
        return await ProjectServices.get_project_details(db, project_id)
    
    @staticmethod
    async def save_project_data(data: ProjectSubmitRequest, old_data: ProjectSubmitRequest, db, current_user):
        """
        บันทึกข้อมูลโปรเจกต์ทั้งหมดลงฐานข้อมูล (Atomic Operation)
        """
        try:
            comparison_tool = TextComparisonServices()
            fields_to_check = ["title_th", "title_en", "abstract_th", "abstract_en", "academic_year_be", "academic_year_ce"]
            comparison_results = {}

            # --- 0. เปรียบเทียบข้อมูลเพื่อเก็บ Log (OCR vs User Edit) ---
            for field in fields_to_check:
                old_val = getattr(old_data, field) if hasattr(old_data, field) else ""
                new_val = getattr(data, field) if hasattr(data, field) else ""

                # กรณี Keywords (หากถูกส่งมาเป็น list)
                if isinstance(old_val, list): old_val = ", ".join(filter(None, old_val))
                if isinstance(new_val, list): new_val = ", ".join(filter(None, new_val))

                diff_list = comparison_tool.compare_as_list(str(old_val), str(new_val))
                if diff_list:
                    comparison_results[field] = diff_list
            # --- ต่อจากส่วนเปรียบเทียบข้อมูลที่คุณเขียนไว้ ---
            if comparison_results:
                for field, diffs in comparison_results.items():
                    for change in diffs:
                        # สนใจเฉพาะจุดที่มีการแก้ไข (from และ to ต้องไม่เป็น None)
                        incorrect = change.get("from")
                        correct = change.get("to")
                        
                        if incorrect and correct:
                            # 1. ค้นหาใน CorrectionDictionary ว่ามีคำผิดนี้อยู่หรือยัง
                            existing_dic = db.exec(select(CorrectionDictionary).where(CorrectionDictionary.incorrect_word == incorrect)).first()
                            
                            if existing_dic:
                                # 1. บวก Count รวมของคำผิดนี้เสมอ
                                existing_dic.count += 1
                                existing_dic.updated_at = datetime.utcnow()
                                
                                # 2. ตรวจสอบและเพิ่มคำใหม่เข้าไปในลิสต์ (ถ้ายังไม่มี)
                                current_list = existing_dic.correct_word_list if existing_dic.correct_word_list is not None else []
                                
                                # เช็คว่าคำใหม่ (correct) มีอยู่ในลิสต์ปัจจุบันหรือยัง
                                if correct not in current_list:
                                    # สร้างลิสต์ใหม่เพื่อความชัวร์ว่า SQLAlchemy จะเห็นการเปลี่ยนแปลง (Re-assignment)
                                    new_list = list(current_list) 
                                    new_list.append(correct)
                                    existing_dic.correct_word_list = new_list
                                
                            else:
                                # กรณีสร้าง Entry ใหม่ครั้งแรก
                                new_dic = CorrectionDictionary(
                                    incorrect_word=incorrect,
                                    correct_word_list=[correct], # เริ่มต้นด้วยลิสต์ที่มีคำเดียว
                                    count=1
                                )
                                db.add(new_dic)
                                db.flush() 
                                existing_dic = new_dic

                            # 2. บันทึกลงตารางย่อย IncorrectWord เพื่อเก็บสถิติว่าคำนี้ถูกแก้เป็นอะไรบ่อยที่สุด
                            inc_word_record =  db.exec(select(IncorrectWord).where(
                                    IncorrectWord.word_dic_id == existing_dic.word_dic_id,
                                    IncorrectWord.correct_word == correct
                                )
                            ).first()

                            if inc_word_record:
                                inc_word_record.count += 1
                            else:
                                db.add(IncorrectWord(
                                    word_dic_id=existing_dic.word_dic_id,
                                    correct_word=correct,
                                    count=1
                                ))
            db.flush() # บังคับเคลียร์การเปลี่ยนแปลงใน CorrectionDictionary และ IncorrectWord ลง DB ก่อนที่จะดำเนินการต่อไปกับ Project
            # 1. สั่งระงับ Autoflush ตลอดการทำงานในบล็อกนี้ ป้องกันระบบแทรกคิว
            with db.no_autoflush:
                
                # --- 1. จัดการ Metadata IDs (Faculty, Dept, Degree) ---
                async def get_id(input_data, master_func, th_attr, en_attr, id_attr):
                    if not input_data: return None
                    target_id = getattr(input_data, id_attr, None)
                    if not target_id:
                        master_items = await master_func(db)
                        match = ProjectServices.find_match(
                            getattr(input_data, th_attr, ""), 
                            getattr(input_data, en_attr, ""), 
                            master_items, th_attr, en_attr
                        )
                        return getattr(match, id_attr) if match else None
                    return target_id
                
                actual_degree_id = await get_id(data.degree, ProjectServices.get_master_degrees, "degree_name_th", "degree_name_en", "degree_id")

                # --- 2. บันทึกไฟล์ (ProjectFile) ---
                project_file = ProjectFile(
                    file_id=uuid4(),
                    file_name=data.file_info.save_name,
                    file_path=data.file_info.file_path,
                    thumbnail_path=data.file_info.thumbnail_path, 
                    uploaded_at=datetime.utcnow()
                )
                db.add(project_file)
                db.flush()

                # --- 3. บันทึกโปรเจกต์ (Project) ---
                project = Project(
                    project_id=uuid4(),
                    title_th=data.title_th,
                    title_en=data.title_en,
                    abstract_th=data.abstract_th,
                    abstract_en=data.abstract_en,
                    academic_year_be=data.academic_year_be, 
                    academic_year_ce=data.academic_year_ce,
                    degree_id=actual_degree_id,
                    # faculty_id=actual_faculty_id, # ใส่ตามชื่อ field ใน Model ของคุณ
                    # department_id=actual_dept_id,
                    created_by=current_user.user_id,
                    is_active=True,
                    file_id=project_file.file_id,
                    download_count=0,
                    edit_logs=comparison_results # บันทึกผลการเทียบ OCR ไว้ในตาราง Project เลย (ถ้ามี field)
                )
                db.add(project)
                db.flush()

                # --- 4. บันทึกนักศึกษา (ProjectAuthor) ---
                for idx, s in enumerate(data.students, start=1):
                    if not s.student_id: continue
                    # ตรวจสอบว่ามี User นี้ในระบบหรือยัง
                    user = await ProjectServices.get_user_by_student_id(db, s.student_id)
                    if not user:
                        user = User(
                            user_id=uuid4(),
                            student_id=s.student_id,
                            user_name_th=s.student_name_th,
                            user_name_en=s.student_name_en,
                            degree_id=actual_degree_id,
                            role=Role.STUDENT,
                            email=f"{s.student_id}@kmitl.ac.th"
                        )
                        db.add(user)
                        db.flush()
                    
                    # ผูกความสัมพันธ์ Author
                    db.add(ProjectAuthor(
                        project_id=project.project_id, 
                        user_id=user.user_id, 
                        author_order=idx
                    ))

                # --- 5. บันทึกอาจารย์ (ProjectAdvisor) ---
                for idx, adv in enumerate(data.advisors, start=1):
                    if adv.advisor_id:
                        db.add(ProjectAdvisor(
                            project_id=project.project_id, 
                            advisor_id=adv.advisor_id, 
                            advisor_order=idx
                        ))

                # --- 6. บันทึกคำสำคัญ (Keyword & ProjectKeyword) ---
                db_keywords = await ProjectServices.get_keywords(db)
                used_keyword_ids = set()

                for idx, kw in enumerate(data.keywords, start=1):
                    target_kw_id = None
                    
                    # เช็ค ID ก่อน
                    if hasattr(kw, 'keyword_id') and kw.keyword_id:
                        target_kw_id = kw.keyword_id
                    else:
                        # ถ้าไม่มี ID ให้หาจาก Text Match
                        match = ProjectServices.find_match_keywords(
                            kw.keyword_text_th, kw.keyword_text_en, 
                            db_keywords, "keyword_text_th", "keyword_text_en"
                        )
                        if match:
                            target_kw_id = match.keyword_id
                        else:
                            # ถ้าไม่เจอจริงๆ ให้สร้างใหม่
                            new_kw = Keyword(
                                keyword_id=uuid4(),
                                keyword_text_th=kw.keyword_text_th,
                                keyword_text_en=kw.keyword_text_en
                            )
                            db.add(new_kw)
                            db.flush()

                            target_kw_id = new_kw.keyword_id
                            db_keywords.append(new_kw) # ป้องกันคำซ้ำใน loop เดียวกัน

                    # บันทึกความสัมพันธ์ Keyword
                    if target_kw_id and target_kw_id not in used_keyword_ids:
                        db.add(ProjectKeyword(
                            project_id=project.project_id, 
                            keyword_id=target_kw_id, 
                            keyword_order=idx
                        ))
                        used_keyword_ids.add(target_kw_id)

            db.commit()

            # เมื่อจบ block async with db.begin() ระบบจะ Commit ให้อัตโนมัติ
            return {"status": "success", "project_id": str(project.project_id)}

        except Exception as e:
            db.rollback()
            print(f"Transaction failed: {str(e)}")
            raise e
        
    @staticmethod
    async def save_update_project_data(project_id: str, data: ProjectSubmitRequest, db, current_user):
        project = db.exec(select(Project).where(Project.project_id == project_id)).first()

        if not project:
            raise HTTPException(status_code=404, detail="ไม่พบโปรเจกต์นี้")

        project.title_th = data.title_th
        project.title_en = data.title_en
        project.abstract_th = data.abstract_th
        project.abstract_en = data.abstract_en
        project.academic_year_be = data.academic_year_be
        project.academic_year_ce = data.academic_year_ce
        if data.degree and data.degree.degree_id:
            project.degree_id = data.degree.degree_id

        project.updated_by = current_user.user_id
        project.updated_at = datetime.utcnow()

        existing_advisors = db.exec(
            select(ProjectAdvisor).where(ProjectAdvisor.project_id == project_id)
        ).all()
        for old_adv in existing_advisors:
            db.delete(old_adv)
        db.flush()

        for idx, adv in enumerate(data.advisors, start=1):
            if adv.advisor_id:
                db.add(ProjectAdvisor(
                    project_id=project.project_id,
                    advisor_id=adv.advisor_id,
                    advisor_order=idx
                ))

        # --- อัปเดต Keywords ---
        existing_p_keywords = db.exec(
            select(ProjectKeyword).where(ProjectKeyword.project_id == project_id)
        ).all()
        for old_pkw in existing_p_keywords:
            db.delete(old_pkw)
        db.flush()

        db_keywords = await ProjectServices.get_keywords(db)
        used_keyword_ids = set()

        def clean_text(text: str) -> str:
            return text.strip() if text else ""

        for idx, kw in enumerate(data.keywords, start=1):
            target_kw_id = None

            th_text = clean_text(getattr(kw, "keyword_text_th", ""))
            en_text = clean_text(getattr(kw, "keyword_text_en", ""))

            if not th_text and not en_text:
                continue

            incoming_kw_id = getattr(kw, "keyword_id", None)

            # ถ้ามี id เดิมมา ให้ตรวจว่า text ยังตรงกับ keyword เดิมไหม
            # ถ้าไม่ตรง ให้ถือว่า id เป็น null แล้วไปหาใหม่
            if incoming_kw_id:
                existing_kw = db.exec(
                    select(Keyword).where(Keyword.keyword_id == incoming_kw_id)
                ).first()

                if existing_kw:
                    db_th = clean_text(existing_kw.keyword_text_th)
                    db_en = clean_text(existing_kw.keyword_text_en)

                    same_th = (not th_text and not db_th) or (th_text == db_th)
                    same_en = (not en_text and not db_en) or (en_text == db_en)

                    if same_th and same_en:
                        target_kw_id = existing_kw.keyword_id
                    else:
                        incoming_kw_id = None
                else:
                    incoming_kw_id = None

            # ถ้าไม่มี id หรือ id เดิมใช้ไม่ได้แล้ว -> หา match จาก text ใหม่
            if not target_kw_id:
                match = ProjectServices.find_match_keywords(
                    th_text,
                    en_text,
                    db_keywords,
                    "keyword_text_th",
                    "keyword_text_en"
                )

                if match:
                    target_kw_id = match.keyword_id
                else:
                    new_kw = Keyword(
                        keyword_id=uuid4(),
                        keyword_text_th=th_text,
                        keyword_text_en=en_text
                    )
                    db.add(new_kw)
                    db.flush()
                    target_kw_id = new_kw.keyword_id
                    db_keywords.append(new_kw)

            if target_kw_id and target_kw_id not in used_keyword_ids:
                db.add(ProjectKeyword(
                    project_id=project.project_id,
                    keyword_id=target_kw_id,
                    keyword_order=idx
                ))
                used_keyword_ids.add(target_kw_id)

        try:
            db.commit()
            db.refresh(project)
        except Exception as e:
            db.rollback()
            print(f"Update Error: {e}")
            raise HTTPException(status_code=500, detail="ไม่สามารถอัปเดตข้อมูลได้")

        return {"status": "success", "message": "อัปเดตข้อมูลสำเร็จ"}
    

    @staticmethod
    def validate_extracted_data(data: dict):
        empty_fields = []
        total = 4  # title, abstract, students, advisors

        def has_text(*values):
            return any(str(v).strip() for v in values if v is not None)

        def get_value(item, key, default=""):
            if isinstance(item, dict):
                return item.get(key, default)
            return getattr(item, key, default)

        # --- title ---
        if not has_text(data.get("title_th"), data.get("title_en")):
            empty_fields.append("title")

        # --- abstract ---
        if not has_text(data.get("abstract_th"), data.get("abstract_en")):
            empty_fields.append("abstract")

        # --- students ---
        students = data.get("students", []) or []
        has_students = any(
            has_text(
                get_value(s, "student_name_th"),
                get_value(s, "student_name_en")
            )
            for s in students
        )
        if not has_students:
            empty_fields.append("students")

        # --- advisors ---
        advisors = data.get("advisors", []) or []
        has_advisors = any(
            has_text(
                get_value(a, "advisor_name_th"),
                get_value(a, "advisor_name_en")
            )
            for a in advisors
        )
        if not has_advisors:
            empty_fields.append("advisors")

        empty_count = len(empty_fields)
        null_ratio = empty_count / total

        def has_eng(text):
            return bool(re.search(r"[a-zA-Z]", str(text or "")))

        has_english = any([
            has_eng(data.get("title_en")),
            has_eng(data.get("abstract_en")),
            any(has_eng(get_value(s, "student_name_en")) for s in students),
            any(has_eng(get_value(a, "advisor_name_en")) for a in advisors),
        ])

        print("==== VALIDATION DEBUG ====")
        print("students type:", type(students))
        print("first student type:", type(students[0]) if students else None)
        print("advisors type:", type(advisors))
        print("first advisor type:", type(advisors[0]) if advisors else None)
        print("Has students:", has_students)
        print("Has advisors:", has_advisors)
        print("Empty fields:", empty_fields)
        print("Null ratio:", null_ratio)
        print("Has English:", has_english)

        if null_ratio > 0.6:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "ข้อมูลไม่สมบูรณ์",
                    "missing_fields": empty_fields,
                    "null_ratio": null_ratio
                }
            )

        if not has_english:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "ไม่พบข้อมูลภาษาอังกฤษ",
                    "hint": "OCR อาจอ่านผิด หรือไม่มี field ภาษาอังกฤษเลย"
                }
            )