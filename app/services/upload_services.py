from app.schemas.project_schema import ProjectSubmitRequest

from app.services.file_services import FileServices
from app.services.ocr_services import OCRServices
from app.services.text_services import TextServices
from app.services.project_services import ProjectServices
from app.services.textcomparison_services import TextComparisonServices

from app.config import settings

from app.repository.user_repository import UserRepository
from app.repository.project_repository import ProjectRepository

from app.models.user import User, Role
from app.models.project_file import ProjectFile
from app.models.project import Project
from app.models.project_advisor import ProjectAdvisor
from app.models.project_author import ProjectAuthor
from app.models.project_keyword import ProjectKeyword
from app.models.keyword import Keyword

from uuid import uuid4
from datetime import datetime
from itertools import zip_longest
import time

class UploadServices:
    def __init__(self):
        self.file_services = FileServices()
        self.ocr_services = OCRServices(poppler_path=settings.poppler_path)
        self.text_services = TextServices()


    async def handle_upload(self, file, pages, db, current_user):
        # save file
        start_time = time.time()
        dest, save_name = self.file_services.save(file)

        # thumbnail
        thumbnail_img = self.ocr_services.get_thumbnail(str(dest))
        thumbnail_path = self.file_services.save_thumbnail(thumbnail_img)

        # OCR + extract
        sorted_pages = sorted(pages)
        raw_ocr_results = []
        
        for page_num in sorted_pages:
            ocr_data, ext_data = self.ocr_services.extract(str(dest), page_num)
            raw_ocr_results.append({
                "ocr": ocr_data,
                "ext": ext_data
            })

        # process text
        fields, spell_res = await self.text_services.process(raw_ocr_results, db)
        
        # get Master Data
        degrees = await ProjectRepository.get_master_degrees(db)
        advisors = await ProjectRepository.get_master_advisors(db)
        departments = await ProjectRepository.get_master_departments(db)
        faculties = await ProjectRepository.get_master_faculties(db)
        
        # Matching Metadata (Degree, Dept, Faculty)
        metadata_mappings = [
            ("degree", degrees, "degree_name"),
            ("department", departments, "department_name"),
            ("faculty", faculties, "faculty_name")
        ]

        matched_metadata = {}
        for key, collection, field_name in metadata_mappings:
            matched_metadata[key] = ProjectServices.find_match(
                fields.get(f"{key}_th", ""),
                fields.get(f"{key}_en", ""),
                collection,
                f"{field_name}_th",
                f"{field_name}_en"
            ) 

        advisors_list = fields.get("advisors", [])  # ค่าจาก ExtractServices.extract_advisors
        extracted_advisors = []

        for adv_item in advisors_list:
            adv_th = adv_item.get("advisor_name_th", "")
            adv_en = adv_item.get("advisor_name_en", "")
            matched_adv = ProjectServices.find_match(
                adv_th, adv_en, advisors, "advisor_name_th", "advisor_name_en"
            )
            extracted_advisors.append({
                "advisor_id": matched_adv.advisor_id if matched_adv else None,
                "advisor_name_th": matched_adv.advisor_name_th if matched_adv else adv_th,
                "advisor_name_en": matched_adv.advisor_name_en if matched_adv else adv_en
            })

        # จัดเตรียมข้อมูล Keyword ส่งให้หน้าบ้าน
        keywords_th = fields.get("keywords_th", [])
        keywords_en = fields.get("keywords_en", [])
        extracted_keywords = []

        # ใช้ zip_longest เพื่อจับคู่คำต่อคำ ถ้าฝั่งไหนน้อยกว่าจะเติม "" (ตามที่คุณเขียน)
        for kw_th, kw_en in zip_longest(keywords_th, keywords_en, fillvalue=""):
            if kw_th or kw_en:
                extracted_keywords.append({
                    "keyword_text_th": kw_th if kw_th else None,
                    "keyword_text_en": kw_en if kw_en else None
                })

        # จัดเตรียมข้อมูล Student ส่งให้หน้าบ้าน
        students_data = fields.get("students", []) # คีย์ควรเป็นตัวเล็กตามที่เขียนใน ExtractServices
        extracted_students = []
        for s in students_data:
                extracted_students.append({
                    "student_id": s.get("student_id", ""),
                    "student_name_th": s.get("student_name_th", ""),
                    "student_name_en": s.get("student_name_en", "")
                })
        end_time = time.time()  # 2. บันทึกเวลาเมื่อทำงานเสร็จ
        processing_time = round(end_time - start_time, 2)
        print(f"Total processing time: {processing_time} seconds")  # 3. แสดงเวลาที่ใช้ในการประมวลผล
        # 5. ส่ง JSON คืนหน้าบ้านให้ User ตรวจสอบ
        return {
            "file_info": {
                "file_path": str(dest),
                "save_name": save_name,
                "thumbnail_path": str(thumbnail_path)
            },
            "form_data": {
                "title_th": fields.get("title_th", ""),
                "title_en": fields.get("title_en", ""),
                "abstract_th": fields.get("abstract_th", ""),
                "abstract_en": fields.get("abstract_en", ""),
                "academic_year": fields.get("academic_year", ""),
                
                # จัดกลุ่มเป็นก้อน โดยอ้างอิง Key ให้ถูกต้อง
                "degree": {
                    "degree_id": matched_metadata["degree"].degree_id if matched_metadata.get("degree") else None,
                    "degree_name_th": matched_metadata["degree"].degree_name_th if matched_metadata.get("degree") else fields.get("degree_th", ""),
                    "degree_name_en": matched_metadata["degree"].degree_name_en if matched_metadata.get("degree") else fields.get("degree_en", "")
                },
                "department": {
                    "department_id": matched_metadata["department"].department_id if matched_metadata.get("department") else None,
                    "department_name_th": matched_metadata["department"].department_name_th if matched_metadata.get("department") else fields.get("department_th", ""),
                    "department_name_en": matched_metadata["department"].department_name_en if matched_metadata.get("department") else fields.get("department_en", "")
                },
                "faculty": {
                    "faculty_id": matched_metadata["faculty"].faculty_id if matched_metadata.get("faculty") else None,
                    "faculty_name_th": matched_metadata["faculty"].faculty_name_th if matched_metadata.get("faculty") else fields.get("faculty_th", ""),
                    "faculty_name_en": matched_metadata["faculty"].faculty_name_en if matched_metadata.get("faculty") else fields.get("faculty_en", "")
                },
                "advisors": extracted_advisors,
                "students": extracted_students,
                "keywords": extracted_keywords
            },

            "spell_errors": spell_res
        }

    @staticmethod
    async def save_project_data(data: ProjectSubmitRequest, old_data: ProjectSubmitRequest, db, current_user: User):
        comparison_tool = TextComparisonServices()
        fields_to_check = ["title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en"]
        comparison_results = {}

        for field in fields_to_check:
            # ดึงข้อมูลจากก้อนเก่า (OCR/Extract เดิม) และก้อนใหม่ (ที่ User แก้ไข)
            # หมายเหตุ: .get(field) ใช้ได้ทั้งกับ dict หรือถ้าเป็น object ให้ใช้ getattr(obj, field)
            old_val = getattr(old_data, field) if hasattr(old_data, field) else ""
            new_val = getattr(data, field) if hasattr(data, field) else ""

            # กรณีที่เป็น Keywords (ซึ่งเป็น List) ให้แปลงเป็น String ก่อนเปรียบเทียบ
            if isinstance(old_val, list):
                old_val = ", ".join(filter(None, old_val))
            if isinstance(new_val, list):
                new_val = ", ".join(filter(None, new_val))

            # เรียกใช้เครื่องมือเปรียบเทียบ
            diff_list = comparison_tool.compare_as_list(old_val, new_val)
            
            # เก็บเฉพาะฟิลด์ที่มีความแตกต่าง (มี error_list ไม่เป็นค่าว่าง)
            if diff_list:
                comparison_results[field] = diff_list
        # 1. จัดการ Metadata (ใช้ ID ถ้ามี ถ้าไม่มีให้ลอง Match ใหม่)
        async def get_id(input_data, master_func, th_attr, en_attr, id_attr):
            target_id = getattr(input_data, id_attr)
            if not target_id:
                master_items = await master_func(db)
                match = ProjectServices.find_match(
                    getattr(input_data, th_attr), 
                    getattr(input_data, en_attr), 
                    master_items, th_attr, en_attr
                )
                return getattr(match, id_attr) if match else None
            return target_id

        actual_faculty_id = await get_id(data.faculty, ProjectRepository.get_master_faculties, "faculty_name_th", "faculty_name_en", "faculty_id")
        actual_dept_id = await get_id(data.department, ProjectRepository.get_master_departments, "department_name_th", "department_name_en", "department_id")
        actual_degree_id = await get_id(data.degree, ProjectRepository.get_master_degrees, "degree_name_th", "degree_name_en", "degree_id")

        # 2. บันทึกไฟล์
        project_file = ProjectFile(
            file_id=uuid4(),
            file_name=data.file_info.save_name,
            file_path=data.file_info.file_path,
            thumbnail_path=data.file_info.thumbnail_path, 
            uploaded_at=datetime.utcnow()
        )
        await ProjectRepository.create_project_file(db, project_file)

        # 3. บันทึกโปรเจกต์
        project = Project(
            project_id=uuid4(),
            title_th=data.title_th,
            title_en=data.title_en,
            abstract_th=data.abstract_th,
            abstract_en=data.abstract_en,
            academic_year=data.academic_year,
            degree_id=actual_degree_id,
            # faculty_id=actual_faculty_id, # ใส่ตามโครงสร้าง Table ของคุณ
            # department_id=actual_dept_id,
            created_by=current_user.user_id,
            is_active=True,
            file_id=project_file.file_id,
            download_count=0
        )
        await ProjectRepository.create_project(db, project)

        # 4. บันทึกนักศึกษา (Author)
        for idx, s in enumerate(data.students, start=1):
            if not s.student_id: continue
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
                await UserRepository.create_user(db, user)
            
            await ProjectRepository.create_project_author(db, ProjectAuthor(
                project_id=project.project_id, user_id=user.user_id, author_order=idx
            ))

        # 5. บันทึกอาจารย์ (Advisor)
        for idx, adv in enumerate(data.advisors, start=1):
            if adv.advisor_id:
                await ProjectRepository.create_project_advisor(db, ProjectAdvisor(
                    project_id=project.project_id, advisor_id=adv.advisor_id, advisor_order=idx
                ))

        # 6. บันทึกคำสำคัญ (Keyword)
        db_keywords = await ProjectRepository.get_keywords(db)
        for idx, kw in enumerate(data.keywords, start=1):
            match = ProjectServices.find_match(
                kw.keyword_text_th, kw.keyword_text_en, db_keywords, "keyword_text_th", "keyword_text_en"
            )
            target_kw = match
            if not target_kw:
                target_kw = Keyword(
                    keyword_id=uuid4(),
                    keyword_text_th=kw.keyword_text_th,
                    keyword_text_en=kw.keyword_text_en
                )
                await ProjectRepository.create_keyword(db, target_kw)

            await ProjectRepository.create_project_keyword(db, ProjectKeyword(
                project_id=project.project_id, keyword_id=target_kw.keyword_id, keyword_order=idx
            ))

        return {"status": "success", "project_id": project.project_id}