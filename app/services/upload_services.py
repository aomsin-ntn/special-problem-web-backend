from app.services.file_services import FileService
from app.services.ocr_services import OCRService
from app.services.text_services import TextService
from app.config import settings
from app.repository.project_repository import ProjectRepository
from app.services.project_services import ProjectServices
from app.models.user import User, Role
from app.repository.user_repository import UserRepository
from uuid import uuid4
from app.models.project_file import ProjectFile
from app.models.project import Project
from app.models.project_advisor import ProjectAdvisor
from app.models.project_author import ProjectAuthor
from app.models.project_keyword import ProjectKeyword
from app.models.keyword import Keyword
from datetime import datetime
from itertools import zip_longest

class UploadServices:
    def __init__(self):
        self.file_service = FileService()
        self.ocr_service = OCRService(poppler_path=settings.poppler_path)
        self.text_service = TextService()


    async def handle_upload(self, file, pages, db, current_user):
        # 1. save file
        dest, save_name = self.file_service.save(file)

        # 2. thumbnail
        thumbnail_img = self.ocr_service.get_thumbnail(str(dest))
        thumbnail_path = self.file_service.save_thumbnail(thumbnail_img)

        # 3. OCR + extract
        pages = sorted(pages)[:2]
        ocr1, pdf1 = self.ocr_service.extract(str(dest), pages[0])
        ocr2, pdf2 = self.ocr_service.extract(str(dest), pages[1])

        # 4. process text
        fields1 = self.text_service.process(ocr1, pdf1)
        fields2 = self.text_service.process(ocr2, pdf2)

        degrees = await ProjectRepository.get_master_degrees(db)
        advisors = await ProjectRepository.get_master_advisors(db)
        departments = await ProjectRepository.get_master_departments(db)
        faculties = await ProjectRepository.get_master_faculties(db)
        
        degree = ProjectServices.find_match(
            fields1.get("Degree", ""), fields2.get("Degree", ""), degrees, "degree_name_th", "degree_name_en"
        )
        advisor = ProjectServices.find_match(
            fields1.get("Advisor", ""), fields2.get("Advisor", ""), advisors, "advisor_name_th", "advisor_name_en"
        )
        department = ProjectServices.find_match(
            fields1.get("Department", ""), fields2.get("Department", ""), departments, "department_name_th", "department_name_en"
        )
        faculty = ProjectServices.find_match(
            fields1.get("Faculty", ""), fields2.get("Faculty", ""), faculties, "faculty_name_th", "faculty_name_en"
        )        

        advisor_th_text = fields1.get("Advisor", "")
        advisor_en_text = fields2.get("Advisor", "")
        extracted_advisors = []
        if advisor_th_text or advisor_en_text or advisor:
            extracted_advisors.append({
                "advisor_id": advisor.advisor_id if advisor else None,
                "advisor_name_th": advisor.advisor_name_th if advisor else advisor_th_text,
                "advisor_name_en": advisor.advisor_name_en if advisor else advisor_en_text
            })

        # จัดเตรียมข้อมูล Keyword ส่งให้หน้าบ้าน
        keywords_th = fields1.get("Keywords", [])
        keywords_en = fields2.get("Keywords", [])
        extracted_keywords = []
        for kw_th, kw_en in zip_longest(keywords_th, keywords_en, fillvalue=""):
            if kw_th or kw_en:
                extracted_keywords.append({"th": kw_th, "en": kw_en})

        # จัดเตรียมข้อมูล Student ส่งให้หน้าบ้าน
        students_th = fields1.get("Students", [])
        students_en = fields2.get("Students", [])
        extracted_students = []
        
        if len(students_th) > 0:
            extracted_students.append({
                "student_id": students_th[0].get("id", ""),
                "name_th": students_th[0].get("name", ""),
                "name_en": students_en[0].get("name", "") if len(students_en) > 0 else ""
            })
        if len(students_th) > 1:
            extracted_students.append({
                "student_id": students_th[1].get("id", ""),
                "name_th": students_th[1].get("name", ""),
                "name_en": students_en[1].get("name", "") if len(students_en) > 1 else ""
            })

        # 5. ส่ง JSON คืนหน้าบ้านให้ User ตรวจสอบ
        return {
            "file_info": {
                "file_path": str(dest),
                "save_name": save_name,
                "thumbnail_path": str(thumbnail_path)
            },
            "form_data": {
                "title_th": fields1.get("Title", ""),
                "title_en": fields2.get("Title", ""),
                "abstract_th": fields1.get("Abstract", ""),
                "abstract_en": fields2.get("Abstract", ""),
                "academic_year": fields1.get("AcademicYear", ""),
                
                # จัดกลุ่มเป็นก้อน
                "degree": {
                    "degree_id": degree.degree_id if degree else None,
                    "degree_name_th": degree.degree_name_th if degree else fields1.get("Degree", ""),
                    "degree_name_en": degree.degree_name_en if degree else fields2.get("Degree", "")
                },
                "department": {
                    "department_id": department.department_id if department else None,
                    "department_name_th": department.department_name_th if department else fields1.get("Department", ""),
                    "department_name_en": department.department_name_en if department else fields2.get("Department", "")
                },
                "faculty": {
                    "faculty_id": faculty.faculty_id if faculty else None,
                    "faculty_name_th": faculty.faculty_name_th if faculty else fields1.get("Faculty", ""),
                    "faculty_name_en": faculty.faculty_name_en if faculty else fields2.get("Faculty", "")
                },
                "advisors": extracted_advisors,
                "students": extracted_students,
                "keywords": extracted_keywords
            }
        }

    @staticmethod
    async def save_project_data(data, db, current_user):
        actual_degree_id = data.degree.degree_id
        actual_faculty_id = data.faculty.faculty_id
        actual_department_id = data.department.department_id

        # 1. เช็คและหา Faculty (คณะ)
        if not actual_faculty_id and (data.faculty.faculty_name_th or data.faculty.faculty_name_en):
            db_faculties = await ProjectRepository.get_master_faculties(db)
            match_faculty = ProjectServices.find_match(
                data.faculty.faculty_name_th, data.faculty.faculty_name_en, db_faculties, "faculty_name_th", "faculty_name_en"
            )
            if match_faculty:
                actual_faculty_id = match_faculty.faculty_id

        # 2. เช็คและหา Department (ภาควิชา)
        if not actual_department_id and (data.department.department_name_th or data.department.department_name_en):
            db_departments = await ProjectRepository.get_master_departments(db)
            match_department = ProjectServices.find_match(
                data.department.department_name_th, data.department.department_name_en, db_departments, "department_name_th", "department_name_en"
            )
            if match_department:
                actual_department_id = match_department.department_id

        # 3. เช็คและหา Degree (ปริญญา)
        if not actual_degree_id and (data.degree.degree_name_th or data.degree.degree_name_en):
            db_degrees = await ProjectRepository.get_master_degrees(db) 
            match_degree = ProjectServices.find_match(
                data.degree.degree_name_th, data.degree.degree_name_en, db_degrees, "degree_name_th", "degree_name_en"
            )
            if match_degree:
                actual_degree_id = match_degree.degree_id

        # 4. เช็คและหา Advisor (รองรับหลายคน)
        db_advisors = await ProjectRepository.get_master_advisors(db) # ดึง Master Data มาครั้งเดียว
        valid_advisor_ids = []

        for adv in data.advisors: # วนลูปตามที่หน้าบ้านส่งมา
            adv_id = adv.advisor_id
            
            # ถ้าไม่มี ID ให้ค้นหาจากชื่อ
            if not adv_id and (adv.advisor_name_th or adv.advisor_name_en):
                match_advisor = ProjectServices.find_match(
                    adv.advisor_name_th, adv.advisor_name_en, db_advisors, "advisor_name_th", "advisor_name_en"
                )
                if match_advisor:
                    adv_id = match_advisor.advisor_id

            # ถ้าได้ ID มาแล้ว (และยังไม่ซ้ำในลิสต์) ให้เก็บไว้เตรียมบันทึก
            if adv_id and adv_id not in valid_advisor_ids:
                valid_advisor_ids.append(adv_id)
        
        # สร้าง ProjectFile
        project_file = ProjectFile(
            file_id=uuid4(),
            file_name=data.file_info.save_name,
            file_path=data.file_info.file_path,
            thumbnail_path=data.file_info.thumbnail_path, 
            uploaded_at=datetime.utcnow()
        )
        await ProjectRepository.create_project_file(db, project_file)

        # บันทึก Project 
        project = Project(
            project_id=uuid4(),
            title_th=data.title_th,
            title_en=data.title_en,
            abstract_th=data.abstract_th,
            abstract_en=data.abstract_en,
            academic_year=data.academic_year,
            degree_id=actual_degree_id,
            created_by=current_user.user_id,
            is_active=True,
            file_id=project_file.file_id,
            download_count=0
        )
        await ProjectRepository.create_project(db, project)

        # บันทึก Author (นักศึกษา)
        for index, student_data in enumerate(data.students, start=1):
            if not student_data.student_id: 
                continue 
            
            user = await ProjectServices.get_user_by_student_id(db, student_data.student_id)
            if user:
                user.user_name_th = student_data.student_name_th
                user.user_name_en = student_data.student_name_en
                user.degree_id = actual_degree_id 
            else:
                user = User(
                    user_id=uuid4(),
                    student_id=student_data.student_id,
                    user_name_th=student_data.student_name_th,
                    user_name_en=student_data.student_name_en,
                    degree_id=actual_degree_id,
                    role=Role.STUDENT,
                    email=student_data.student_id + "@kmitl.ac.th",
                    password_hash=None
                )
            await UserRepository.create_user(db, user)

            author = ProjectAuthor(
                project_id=project.project_id,
                user_id=user.user_id,
                author_order=index
            )
            await ProjectRepository.create_project_author(db, author)

        # บันทึก Advisor (วนลูปสร้างตามจำนวนอาจารย์ที่กรองมาได้)
        for index, adv_id in enumerate(valid_advisor_ids, start=1):
            project_advisor = ProjectAdvisor(
                project_id=project.project_id,
                advisor_id=adv_id,
                advisor_order=index # ลำดับอาจารย์คนที่ 1, 2, ...
            )
            await ProjectRepository.create_project_advisor(db, project_advisor)

        # บันทึก Keywords
        db_keywords = await ProjectRepository.get_keywords(db)
        final_project_keywords = []

        for kw in data.keywords:
            match = ProjectServices.find_match(
                kw.keyword_text_th, kw.keyword_text_en, db_keywords, "keyword_text_th", "keyword_text_en"
            )
            
            if match:
                final_project_keywords.append(match)
            else:
                new_keyword = Keyword(
                    keyword_id=uuid4(),
                    keyword_text_th=kw.keyword_text_th,
                    keyword_text_en=kw.keyword_text_en
                )
                await ProjectRepository.create_keyword(db, new_keyword)
                final_project_keywords.append(new_keyword)

        # นำ Keyword มาผูกกับ Project
        for order, kw in enumerate(final_project_keywords, start=1):
            project_keyword = ProjectKeyword(
                project_id=project.project_id,
                keyword_id=kw.keyword_id,
                keyword_order=order
            )
            await ProjectRepository.create_project_keyword(db, project_keyword)

        return {
            "status": "success", 
            "message": "บันทึกข้อมูลโปรเจกต์สำเร็จ", 
            "project_id": project.project_id
        }