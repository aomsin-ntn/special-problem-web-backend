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

    # ==========================================
    # สเต็ปที่ 1: อัปโหลดเพื่อดึงข้อมูลอย่างเดียว (ไม่เซฟลง DB)
    # ==========================================
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
        
        degree = ProjectServices.find_match(
            fields1.get("Degree", ""), fields2.get("Degree", ""), degrees, "degree_name_th", "degree_name_en"
        )
        advisor = ProjectServices.find_match(
            fields1.get("Advisor", ""), fields2.get("Advisor", ""), advisors, "advisor_name_th", "advisor_name_en"
        )

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
                "degree_id": degree.degree_id if degree else None,
                "degree_name_th": degree.degree_name_th if degree else fields1.get("Degree", ""),
                "degree_name_en": degree.degree_name_en if degree else fields2.get("Degree", ""),
                "advisor_id": advisor.advisor_id if advisor else None,
                "advisor_name_th": advisor.advisor_name_th if advisor else fields1.get("Advisor", ""),
                "advisor_name_en": advisor.advisor_name_en if advisor else fields2.get("Advisor", ""),
                "students": extracted_students,
                "keywords": extracted_keywords
            }
        }

    # ==========================================
    # สเต็ปที่ 2: รับข้อมูลที่ถูกต้องจากหน้าบ้าน มาเซฟลง DB
    # ==========================================
    async def save_project_data(self, data, db, current_user):
        
        # ==========================================
        # 🚨 ส่วนที่เพิ่มใหม่: จัดการ Degree และ Advisor
        # ==========================================
        actual_degree_id = data.degree_id
        actual_advisor_id = data.advisor_id

        # ถ้าไม่มี degree_id แต่มีชื่อส่งมา ให้ทำการ Find Match
        if not actual_degree_id and (data.degree_name_th or data.degree_name_en):
            db_degrees = await ProjectRepository.get_master_degrees(db) # ดึงข้อมูลปริญญาทั้งหมดมาเทียบ
            match_degree = ProjectServices.find_match(
                data.degree_name_th, data.degree_name_en, db_degrees, "degree_name_th", "degree_name_en"
            )
            if match_degree:
                actual_degree_id = match_degree.degree_id

        # ถ้าไม่มี advisor_id แต่มีชื่อส่งมา ให้ทำการ Find Match
        if not actual_advisor_id and (data.advisor_name_th or data.advisor_name_en):
            db_advisors = await ProjectRepository.get_master_advisors(db) # ดึงข้อมูลอาจารย์ทั้งหมดมาเทียบ
            match_advisor = ProjectServices.find_match(
                data.advisor_name_th, data.advisor_name_en, db_advisors, "advisor_name_th", "advisor_name_en"
            )
            if match_advisor:
                actual_advisor_id = match_advisor.advisor_id
        # ==========================================


        # 1. บันทึกไฟล์
        project_file = ProjectFile(
            file_id=uuid4(),
            file_name=data.file_info.save_name,
            file_path=data.file_info.file_path,
            thumbnail_path=data.file_info.thumbnail_path, 
            uploaded_at=datetime.utcnow()
        )
        await ProjectRepository.create_project_file(db, project_file)

        # 2. บันทึก Project (ใช้ actual_degree_id)
        project = Project(
            project_id=uuid4(),
            title_th=data.title_th,
            title_en=data.title_en,
            abstract_th=data.abstract_th,
            abstract_en=data.abstract_en,
            academic_year=data.academic_year,
            degree_id=actual_degree_id, # เปลี่ยนมาใช้ตัวแปรนี้
            created_by=current_user.user_id,
            is_active=True,
            file_id=project_file.file_id,
            download_count=0
        )
        await ProjectRepository.create_project(db, project)

        # 3. บันทึก Author (วนลูปสร้างตามที่หน้าบ้านส่งมา)
        for index, student_data in enumerate(data.students, start=1):
            if not student_data.student_id: 
                continue # ข้ามถ้าหน้าบ้านไม่ได้ส่งรหัสนักศึกษามา
            
            user = await ProjectServices.get_user_by_student_id(db, student_data.student_id)
            if user:
                user.user_name_th = student_data.student_name_th # อิงตาม Schema ของคุณ
                user.user_name_en = student_data.student_name_en
                user.degree_id = actual_degree_id # เปลี่ยนมาใช้ตัวแปรนี้
            else:
                user = User(
                    user_id=uuid4(),
                    student_id=student_data.student_id,
                    user_name_th=student_data.student_name_th,
                    user_name_en=student_data.student_name_en,
                    degree_id=actual_degree_id, # เปลี่ยนมาใช้ตัวแปรนี้
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

        # 4. บันทึก Advisor (ใช้ actual_advisor_id)
        if actual_advisor_id:
            project_advisor = ProjectAdvisor(
                project_id=project.project_id,
                advisor_id=actual_advisor_id,
                advisor_order=1 
            )
            await ProjectRepository.create_project_advisor(db, project_advisor)

        # 5. บันทึก Keywords
        db_keywords = await ProjectRepository.get_keywords(db)
        final_project_keywords = []

        for kw in data.keywords:
            # เช็คว่าคำนี้มีในฐานข้อมูลหรือยัง
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