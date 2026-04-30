from datetime import datetime
from fastapi import HTTPException

from app.models.project_file import ProjectFile, Status
from app.repository.master_data_repository import MasterDataRepository
from app.services.file_services import FileServices
from app.services.ocr_services import OCRServices
from app.services.text_services import TextServices
from app.services.project_services import ProjectServices

from sqlalchemy.exc import IntegrityError

from app.config import settings

from itertools import zip_longest
import time

from starlette.concurrency import run_in_threadpool
import asyncio


class UploadServices:
    def __init__(self):
        self.file_services = FileServices()
        self.ocr_services = OCRServices(poppler_path=settings.poppler_path)
        self.text_services = TextServices()

    @staticmethod
    def get_val(item, attr, default=None):
        if item is None:
            return default

        # dict
        if isinstance(item, dict):
            return item.get(attr, default)

        # object ที่มี attribute จริง
        if hasattr(item, attr):
            return getattr(item, attr)

        return default

    async def handle_upload(self, file, pages, db, current_user):
        # save file
        start_time = time.time()
        dest, save_name = self.file_services.save(file) 

        try:
            # create thumbnail
            thumbnail_img = self.ocr_services.get_thumbnail(str(dest))
            thumbnail_path = self.file_services.save_thumbnail(thumbnail_img)

            # create project file
            project_file = ProjectFile(
                file_path=str(dest),
                file_name=save_name,
                thumbnail_path=str(thumbnail_path),
                status=Status.TEMP
            )

            project_file_info = await ProjectServices.create_project_file(
                db=db,
                project_file=project_file
            )

        except Exception as e:
            self.file_services.safe_delete(str(dest))

            if "thumbnail_path" in locals():
                self.file_services.safe_delete(str(thumbnail_path))

            raise e


        # OCR + extract
        sorted_pages = sorted(pages)
        raw_ocr_results = []
        
        for page_num in sorted_pages:
            ocr_data, ext_data = await run_in_threadpool(
                self.ocr_services.extract,
                str(dest),
                page_num
            )
            raw_ocr_results.append({
                "ocr": ocr_data,
                "ext": ext_data
            })

        # process text
        fields, spell_res = await self.text_services.process(raw_ocr_results, db)
        
        # get Master Data
        degrees = await MasterDataRepository.get_master_degrees_data(db)
        advisors = await MasterDataRepository.get_master_advisors(db)
        departments = await MasterDataRepository.get_master_departments(db)
        faculties = await MasterDataRepository.get_master_faculties(db)
        # print("----------Debug Master Data from DB----------")
        # print(f"Advisors: {advisors}")
        # print(f"Degrees: {degrees}")
        # print(f"Departments: {departments}")
        # print(f"Faculties: {faculties}")
        print("----------Debug DATA ----------")
        print(fields.get("degree_name_th", ""), fields.get("degree_name_en", ""))
        print(fields.get("advisors_name_th", ""), fields.get("advisors_name_en", ""))
        print(fields.get("students", []))   # Debug: แสดงค่าที่ ExtractServices ดึงมาได้สำหรับ Degree

        # Matching Metadata (Degree, Dept, Faculty)
        metadata_keys = ["degree", "department", "faculty"]
        matched_metadata = {}
        for key in metadata_keys:
            matched_metadata[key] = ProjectServices.find_match(
                fields.get(f"{key}_th", ""),
                fields.get(f"{key}_en", ""),
                degrees if key == "degree" else (departments if key == "department" else faculties),
                f"{key}_name_th",
                f"{key}_name_en"
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
        
        master_keywords = await ProjectServices.get_keywords(db)

        extracted_keywords = []


        # ใช้ zip_longest เพื่อจับคู่คำต่อคำตามลำดับที่เจอ
        # ถ้าไทยมี 3 คำ อังกฤษมี 5 คำ คำที่เกินมาของไทยจะเป็น ""
        for kw_th, kw_en in zip_longest(keywords_th, keywords_en, fillvalue=""):
            # ลองหาว่า Keyword คู่นี้มีอยู่ใน DB หรือไม่
            matched_kw = ProjectServices.find_match_keywords(
                kw_th.strip(), 
                kw_en.strip(), 
                master_keywords, 
                "keyword_text_th", 
                "keyword_text_en"
            )
            
            extracted_keywords.append({
                # ถ้าเจอใน DB ให้เอา ID มา ถ้าไม่เจอให้เป็น None (เพื่อรอ Insert ใหม่)
                "keyword_id": self.get_val(matched_kw, "keyword_id"), 
                "keyword_text_th": self.get_val(matched_kw, "keyword_text_th", kw_th.strip()),
                "keyword_text_en": self.get_val(matched_kw, "keyword_text_en", kw_en.strip())
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
                "file_id": project_file_info.file_id,
                "file_path": project_file_info.file_path,
                "save_name": project_file_info.file_name,
                "thumbnail_path": project_file_info.thumbnail_path
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
                    "degree_id": self.get_val(matched_metadata["degree"], "degree_id"),
                    "degree_name_th": self.get_val(matched_metadata["degree"], "degree_name_th", fields.get("degree_th", "")),
                    "degree_name_en": self.get_val(matched_metadata["degree"], "degree_name_en", fields.get("degree_en", ""))
                },
                "department": {
                    "department_id": self.get_val(matched_metadata["department"], "department_id"),
                    "department_name_th": self.get_val(matched_metadata["department"], "department_name_th", fields.get("department_th", "")),
                    "department_name_en": self.get_val(matched_metadata["department"], "department_name_en", fields.get("department_en", "")),
                },
                "faculty": {
                    "faculty_id": self.get_val(matched_metadata["faculty"], "faculty_id"),
                    "faculty_name_th": self.get_val(matched_metadata["faculty"], "faculty_name_th", fields.get("faculty_th", "")),
                    "faculty_name_en": self.get_val(matched_metadata["faculty"], "faculty_name_en", fields.get("faculty_en", ""))
                },
                "advisors": extracted_advisors,
                "students": extracted_students,
                "keywords": extracted_keywords
            },

            "spell_errors": spell_res
        }
