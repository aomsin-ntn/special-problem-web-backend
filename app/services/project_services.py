from datetime import datetime, timezone

import deepcut

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
from app.repository.master_data_repository import MasterDataRepository
from app.repository.project_repository import ProjectRepository
from sqlmodel import Session, select
from fastapi import HTTPException
from app.schemas.project_schema import ProjectSubmitRequest
from app.schemas.root_schema import GetProjectRequestParams
from uuid import UUID, uuid4
from app.repository.user_repository import UserRepository
from app.services.comparison_services import ComparisonServices
from app.models.correction_dictionary import CorrectionDictionary
from app.services.spell_services import SpellServices
import difflib
import re

from app.services.user_services import UserServices

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
    async def delete_project(db: Session, project_id: int, user_id: UUID):
        has_permission = await ProjectServices.check_edit_permission(db, project_id, user_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this resource")
        return await ProjectRepository.delete_project(db, project_id)
    
    @staticmethod
    async def get_expired_temp_files(db: Session, expiration_minutes: int = 60):
        expired_files = await ProjectRepository.get_expired_temp_files(db, expiration_minutes)
        return expired_files
    
    @staticmethod
    async def delete_project_file(db: Session, file_id: UUID):
        project_file = await ProjectRepository.get_project_file_by_id(db, file_id)
        if not project_file:
            raise HTTPException(status_code=404, detail="File not found")
        await ProjectRepository.delete_project_file(db, file_id)
        return project_file

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
    async def get_user_by_student_id(db:Session, student_id:str):
        user = await UserRepository.get_user_by_student_id(db,student_id)
        return user
    
    @staticmethod
    async def get_keywords(db: Session):
        keywords = await ProjectRepository.get_keywords(db)
        return keywords
    
    @staticmethod
    async def get_project_file_by_hash(db: Session, file_hash: str):
        project_file = await ProjectRepository.get_project_file_by_hash(db, file_hash)
        return project_file

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
    async def update_project_file(db: Session, project_file):
        updated_file = await ProjectRepository.update_project_file(db, project_file)
        return updated_file
    
    @staticmethod
    async def create_project_file(db: Session, file_data):
        project_file = await ProjectRepository.create_project_file(db, file_data)
        return project_file
    
    @staticmethod
    async def get_active_project_by_file_id(db: Session, file_id: UUID):
        project = await ProjectRepository.get_active_project_by_file_id(db, file_id)
        return project

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
    def is_match_90(text1: str, text2: str) -> bool:
        norm1 = ProjectServices.normalize(text1)
        norm2 = ProjectServices.normalize(text2)

        if not norm1 or not norm2:
            return False

        score = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        return score >= 0.9

    @staticmethod
    async def check_duplicate_project(db, fields):
        title_th = fields.get("title_th") or ""
        title_en = fields.get("title_en") or ""
        year = fields.get("academic_year_ce") or ""

        input_students = fields.get("students", []) or []

        projects = await ProjectRepository.get_active_projects_for_duplicate_check(
            db=db,
            year=year
        )

        for project in projects:
            title_match = (
                ProjectServices.is_match_90(title_th, project.title_th)
                or ProjectServices.is_match_90(title_en, project.title_en)
            )

            if not title_match:
                continue

            db_students = await ProjectRepository.get_project_students(
                db=db,
                project_id=project.project_id
            )

            for input_student in input_students:
                input_th = input_student.get("student_name_th") or ""
                input_en = input_student.get("student_name_en") or ""

                for row in db_students:
                    user = row.User if hasattr(row, "User") else row[1]

                    student_match = (
                        ProjectServices.is_match_90(input_th, user.user_name_th)
                        or ProjectServices.is_match_90(input_en, user.user_name_en)
                    )

                    if student_match:
                        return project

        return None
    
    @staticmethod
    def normalize(text):
        if not text: return ""
        # แปลงเป็นตัวพิมพ์เล็ก
        text = str(text).lower()
        # OCR fix: จัดการตัวเลขและตัวอักษรที่มักสับสน (Normalize กลับเป็นตัวเลขเพื่อความแม่นยำ)
        # ลบอักขระพิเศษและช่องว่าง (คงเหลือแค่ตัวอักษรไทย อังกฤษ และตัวเลข)
        text = re.sub(r'[^\w\u0E00-\u0E7F]', '', text) 
        return text

    @staticmethod
    def find_match(target_th, target_en, items, th_attr, en_attr):
        norm_target_th = ProjectServices.normalize(target_th)
        norm_target_en = ProjectServices.normalize(target_en)

        if len(norm_target_th) < 3 and len(norm_target_en) < 3:
            return None

        best_match = None
        highest_score = 0
        best_lang = None

        if not items:
            return None

        for item in items:
            if isinstance(item, dict):
                raw_db_th = item.get(th_attr, "")
                raw_db_en = item.get(en_attr, "")
            else:
                raw_db_th = getattr(item, th_attr, "")
                raw_db_en = getattr(item, en_attr, "")

            db_th = ProjectServices.normalize(raw_db_th)
            db_en = ProjectServices.normalize(raw_db_en)

            score_th = difflib.SequenceMatcher(
                None, norm_target_th, db_th
            ).ratio() if norm_target_th and db_th else 0

            score_en = difflib.SequenceMatcher(
                None, norm_target_en, db_en
            ).ratio() if norm_target_en and db_en else 0

            # exact match
            if norm_target_th and norm_target_th == db_th:
                score_th = 1.0

            if norm_target_en and norm_target_en == db_en:
                score_en = 1.0

            # partial match
            if norm_target_th and db_th:
                if norm_target_th in db_th or db_th in norm_target_th:
                    score_th = max(score_th, 0.85)

            if norm_target_en and db_en:
                if norm_target_en in db_en or db_en in norm_target_en:
                    score_en = max(score_en, 0.85)

            if score_th >= score_en:
                current_score = score_th
                current_lang = "th"
            else:
                current_score = score_en
                current_lang = "en"

            if current_score > highest_score:
                highest_score = current_score
                best_match = item
                best_lang = current_lang

        print(
            f"[Match Debug] Best Score: {highest_score:.2f} "
            f"({best_lang}) for '{target_th or target_en}'"
        )

        return best_match if highest_score > 0.6 else None
    
    @staticmethod
    def find_match_keywords(target_th, target_en, items, th_attr, en_attr):
        norm_target_th = ProjectServices.normalize(target_th)
        norm_target_en = ProjectServices.normalize(target_en)

        # กัน keyword สั้นเกินไป
        if norm_target_th and len(norm_target_th) < 2:
            norm_target_th = ""

        if norm_target_en and len(norm_target_en) < 2:
            norm_target_en = ""

        if not norm_target_th and not norm_target_en:
            return None

        best_match = None
        highest_avg_score = 0.0

        if not items:
            return None

        for item in items:
            if isinstance(item, dict):
                raw_db_th = item.get(th_attr, "")
                raw_db_en = item.get(en_attr, "")
            else:
                raw_db_th = getattr(item, th_attr, "")
                raw_db_en = getattr(item, en_attr, "")

            db_th = ProjectServices.normalize(raw_db_th)
            db_en = ProjectServices.normalize(raw_db_en)

            score_th = 0.0
            score_en = 0.0
            used_scores = []

            if norm_target_th and db_th:
                score_th = difflib.SequenceMatcher(None, norm_target_th, db_th).ratio()

                if norm_target_th == db_th:
                    score_th = 1.0

                if len(norm_target_th) >= 3:
                    if norm_target_th in db_th or db_th in norm_target_th:
                        score_th = max(score_th, 0.9)

                used_scores.append(score_th)

            if norm_target_en and db_en:
                score_en = difflib.SequenceMatcher(None, norm_target_en, db_en).ratio()

                if norm_target_en == db_en:
                    score_en = 1.0

                if len(norm_target_en) >= 3:
                    if norm_target_en in db_en or db_en in norm_target_en:
                        score_en = max(score_en, 0.9)

                used_scores.append(score_en)

            if not used_scores:
                continue

            avg_score = sum(used_scores) / len(used_scores)

            if len(used_scores) == 2:
                is_match = score_th >= 0.9 and score_en >= 0.9
            else:
                is_match = avg_score >= 0.9

            if is_match and avg_score > highest_avg_score:
                highest_avg_score = avg_score
                best_match = item

        return best_match
    
    @staticmethod
    async def check_edit_permission(db: Session, project_id: UUID, user_id: UUID) -> bool:
        is_owner = await ProjectRepository.is_project_owner(db, project_id, user_id)
        return is_owner

    @staticmethod
    async def get_project_details_check_permission(db: Session, project_id: int, user_id: UUID):
        has_permission = await ProjectServices.check_edit_permission(db, project_id, user_id)
        if not has_permission:
            raise HTTPException(status_code=403, detail="You do not have permission to access this resource")
        return await ProjectServices.get_project_details(db, project_id)
    
    @staticmethod
    async def save_project(data: ProjectSubmitRequest, old_data: ProjectSubmitRequest, db, current_user):
        """
        บันทึกข้อมูลโปรเจกต์ทั้งหมดลงฐานข้อมูล (Atomic Operation)
        """
        try:
            spell_services = await SpellServices.create(db)
            comparison_tool = ComparisonServices()

            # --- Normalize academic year ---
            if not data.academic_year_be and data.academic_year_ce:
                try:
                    ce = int(str(data.academic_year_ce).strip())
                    if 1900 < ce < 2200:
                        data.academic_year_be = str(ce + 543)
                except ValueError:
                    pass

            fields_to_check = [
                "title_th",
                "title_en",
                "abstract_th",
                "abstract_en",
                "keywords_th",
                "keywords_en"
            ]

            comparison_results = {}

            # --- 0. เปรียบเทียบข้อมูล OCR vs User Edit ---
            for field in fields_to_check:
                old_val = getattr(old_data, field, "") if hasattr(old_data, field) else ""
                new_val = getattr(data, field, "") if hasattr(data, field) else ""

                if isinstance(old_val, list):
                    old_val = ", ".join(filter(None, old_val))

                if isinstance(new_val, list):
                    new_val = ", ".join(filter(None, new_val))

                diff_list = comparison_tool.compare_as_list(str(old_val), str(new_val))

                if diff_list:
                    comparison_results[field] = diff_list

            # --- 1. Learn correction dictionary ---
            if comparison_results:
                for field, diffs in comparison_results.items():
                    for change in diffs:
                        incorrect = change.get("from")
                        correct = change.get("to")

                        if not incorrect or not correct:
                            continue

                        if incorrect == correct:
                            continue

                        # กันประโยคยาว / rewrite
                        if len(incorrect.split()) > 3:
                            continue

                        # ตรวจว่าคำเดิมเป็นคำผิดจริงไหม
                        tokens = deepcut.tokenize(
                            spell_services.clean_text(incorrect),
                            spell_services.custom_segmentation_dict
                        )

                        spell_info = spell_services.check_spelling(tokens)

                        if spell_info.get("incorrect", 0) == 0:
                            continue

                        await SpellServices.save_correction_no_commit(
                            db=db,
                            incorrect=incorrect,
                            correct=correct
                        )

            db.flush()

            with db.no_autoflush:

                # --- 2. Degree ID ---
                async def get_id(input_data, master_func, th_attr, en_attr, id_attr):
                    if not input_data:
                        return None

                    target_id = getattr(input_data, id_attr, None)

                    if target_id:
                        return target_id

                    master_items = await master_func(db)

                    match = ProjectServices.find_match(
                        getattr(input_data, th_attr, ""),
                        getattr(input_data, en_attr, ""),
                        master_items,
                        th_attr,
                        en_attr
                    )

                    return getattr(match, id_attr) if match else None

                actual_degree_id = await get_id(
                    data.degree,
                    MasterDataRepository.get_master_degrees_data,
                    "degree_name_th",
                    "degree_name_en",
                    "degree_id"
                )

                # --- 3. ProjectFile ---
                project_file = await ProjectRepository.get_project_file_by_id(db, data.file_info.file_id)

                if not project_file:
                    raise HTTPException(status_code=404, detail="File not found")
                
                await ProjectRepository.mark_file_as_saved(db, data.file_info.file_id)

                # --- 4. Project ---
                project = await ProjectRepository.create_project_no_commit(
                    db=db,
                    title_th=data.title_th,
                    title_en=data.title_en,
                    abstract_th=data.abstract_th,
                    abstract_en=data.abstract_en,
                    academic_year_be=data.academic_year_be,
                    academic_year_ce=data.academic_year_ce,
                    degree_id=actual_degree_id,
                    created_by=current_user.user_id,
                    file_id=project_file.file_id
                )

                # --- 5. Students / Authors ---
                for idx, s in enumerate(data.students, start=1):
                    if not s.student_id:
                        continue

                    user = await ProjectServices.get_user_by_student_id(db, s.student_id)

                    if not user:
                        user = await UserServices.create_user_no_commit(
                            db=db,
                            student_id=s.student_id,
                            user_name_th=s.student_name_th,
                            user_name_en=s.student_name_en,
                            degree_id=actual_degree_id,
                            role=Role.STUDENT,
                            email=f"{s.student_id}@kmitl.ac.th"
                        )

                    await ProjectRepository.add_project_author_no_commit(
                        db=db,
                        project_id=project.project_id,
                        user_id=user.user_id,
                        author_order=idx
                    )

                # --- 6. Advisors ---
                for idx, adv in enumerate(data.advisors, start=1):
                    if adv.advisor_id:
                        await ProjectRepository.add_project_advisor_no_commit(
                            db=db,
                            project_id=project.project_id,
                            advisor_id=adv.advisor_id,
                            advisor_order=idx
                        )

                # --- 7. Keywords ---
                db_keywords = await ProjectRepository.get_keywords(db)
                used_keyword_ids = set()

                for idx, kw in enumerate(data.keywords, start=1):
                    th_text = (kw.keyword_text_th or "").strip()
                    en_text = (kw.keyword_text_en or "").strip()

                    if not th_text and not en_text:
                        continue

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
                        new_kw = await ProjectRepository.create_keyword_no_commit(
                            db=db,
                            th_text=th_text,
                            en_text=en_text
                        )

                        target_kw_id = new_kw.keyword_id
                        db_keywords.append(new_kw)

                    if target_kw_id and target_kw_id not in used_keyword_ids:
                        await ProjectRepository.add_project_keyword_no_commit(
                            db=db,
                            project_id=project.project_id,
                            keyword_id=target_kw_id,
                            keyword_order=idx
                        )
                        used_keyword_ids.add(target_kw_id)
            return {
                "status": "success",
                "project_id": str(project.project_id)
            }

        except Exception as e:
            db.rollback()
            print(f"Transaction failed: {str(e)}")
            raise e
        
    @staticmethod
    async def update_project(project_id: str, data: ProjectSubmitRequest, db, current_user):
        try:
            project = await ProjectRepository.get_project_by_id(db, project_id)

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            if not data.academic_year_be and data.academic_year_ce:
                try:
                    ce = int(str(data.academic_year_ce).strip())
                    if 1900 < ce < 2200:
                        data.academic_year_be = str(ce + 543)
                except ValueError:
                    pass

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

            with db.no_autoflush:
                await ProjectRepository.delete_project_advisors_no_commit(db, project_id)

                for idx, adv in enumerate(data.advisors, start=1):
                    if adv.advisor_id:
                        await ProjectRepository.add_project_advisor_no_commit(
                            db=db,
                            project_id=project.project_id,
                            advisor_id=adv.advisor_id,
                            advisor_order=idx
                        )

                await ProjectRepository.delete_project_keywords_no_commit(db, project_id)

                db_keywords = await ProjectRepository.get_keywords(db)
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

                    if incoming_kw_id:
                        existing_kw = await ProjectRepository.get_keyword_by_id(db, incoming_kw_id)

                        if existing_kw:
                            db_th = clean_text(existing_kw.keyword_text_th)
                            db_en = clean_text(existing_kw.keyword_text_en)

                            same_th = (not th_text and not db_th) or (th_text == db_th)
                            same_en = (not en_text and not db_en) or (en_text == db_en)

                            if same_th and same_en:
                                target_kw_id = existing_kw.keyword_id

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
                            new_kw = await ProjectRepository.create_keyword_no_commit(
                                db=db,
                                th_text=th_text,
                                en_text=en_text
                            )
                            target_kw_id = new_kw.keyword_id
                            db_keywords.append(new_kw)

                    if target_kw_id and target_kw_id not in used_keyword_ids:
                        await ProjectRepository.add_project_keyword_no_commit(
                            db=db,
                            project_id=project.project_id,
                            keyword_id=target_kw_id,
                            keyword_order=idx
                        )
                        used_keyword_ids.add(target_kw_id)

            db.commit()
            db.refresh(project)

            return {"status": "success", "message": "อัปเดตข้อมูลสำเร็จ"}

        except HTTPException:
            db.rollback()
            raise

        except Exception as e:
            db.rollback()
            print(f"Update Error: {e}")
            raise HTTPException(status_code=500, detail="ไม่สามารถอัปเดตข้อมูลได้")
    

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
            has_eng(data.get("abstract_en"))
        ])

        print("----------VALIDATION DEBUG----------")
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
                print("Error : Incomplete data with high null ratio"),  # Debug: แสดงข้อความผิดพลาดใน Log
                status_code=422,
                detail={
                    "message": "Incomplete data",
                    "missing_fields": empty_fields,
                    "null_ratio": null_ratio
                }
            )

        if not has_english:
            raise HTTPException(
                print("Error : No English data found"),  # Debug: แสดงข้อความผิดพลาดใน Log
                status_code=422,
                detail={
                    "message": "No English data found",
                    "hint": "OCR might have read incorrectly, or there's no English field available"
                }
            )