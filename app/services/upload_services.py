from http.client import HTTPException

from app.models.advisor import Advisor
from app.models.correction_dictionary import CorrectionDictionary
from app.models.incorrect_word import IncorrectWord
from app.schemas.project_schema import ProjectSubmitRequest
from sqlmodel import select

from app.services.file_services import FileServices
from app.services.ocr_services import OCRServices
from app.services.text_services import TextServices
from app.services.project_services import ProjectServices
from app.services.textcomparison_services import TextComparisonServices
from app.services.user_services import UserServices

from app.config import settings

from app.models.user import User, Role
from app.models.project_file import ProjectFile
from app.models.project import Project
from app.models.project_advisor import ProjectAdvisor
from app.models.project_author import ProjectAuthor
from app.models.project_keyword import ProjectKeyword
from app.models.keyword import Keyword

from uuid import uuid4
from datetime import datetime, timezone
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
        degrees = await ProjectServices.get_master_degrees(db)
        advisors = await ProjectServices.get_master_advisors(db)
        departments = await ProjectServices.get_master_departments(db)
        faculties = await ProjectServices.get_master_faculties(db)
        keywords = await ProjectServices.get_keywords(db)
        
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
        # จัดเตรียมข้อมูล Keyword ส่งให้หน้าบ้าน (แบบจับคู่ลำดับอย่างเดียว)
        keywords_th = fields.get("keywords_th", [])
        keywords_en = fields.get("keywords_en", [])
        extracted_keywords = []

        # ใช้ zip_longest เพื่อจับคู่คำต่อคำตามลำดับที่เจอ
        # ถ้าไทยมี 3 คำ อังกฤษมี 5 คำ คำที่เกินมาของไทยจะเป็น ""
        for kw_th, kw_en in zip_longest(keywords_th, keywords_en, fillvalue=""):
            extracted_keywords.append({
                "keyword_id": None,             # ส่งเป็น None ไปก่อนเพื่อให้หน้าบ้านจัดการ
                "keyword_text_th": kw_th.strip(),
                "keyword_text_en": kw_en.strip()
            })

        # แทนที่ค่าเดิมใน fields ด้วย List ของคู่คำ
        fields["keywords"] = extracted_keywords

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
                "academic_year_be": fields.get("academic_year_be", ""),
                "academic_year_ce": fields.get("academic_year_ce", ""),

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