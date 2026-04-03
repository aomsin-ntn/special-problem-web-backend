from app.services.file_services import FileService
from app.services.ocr_services import OCRService
from app.services.text_services import TextService
from app.config import settings

class UploadServices:
    def __init__(self):
        self.file_service = FileService()
        self.ocr_service = OCRService(poppler_path=settings.poppler_path)
        self.text_service = TextService()

    async def handle_upload(self, file, pages, db):
    # 1. save file
        dest, safe_name = self.file_service.save(file)

        # 2. thumbnail
        thumbnail_img = self.ocr_service.get_thumbnail(str(dest))
        thumbnail_path = self.file_service.save_thumbnail(thumbnail_img)

        # 3. OCR + extract
        pages = sorted(pages)[:2]
        print("pages:", pages)
    
        ocr1, pdf1 = self.ocr_service.extract(str(dest), pages[0])
        ocr2, pdf2 = self.ocr_service.extract(str(dest), pages[1])

        # 4. process text
        fields1 = self.text_service.process(ocr1, pdf1)
        fields2 = self.text_service.process(ocr2, pdf2)

        # 5. บันทึกลง Database
        # user = User(
        #     user_id=uuid4(),
        #     student_id="65555555",
        #     user_name_th=fields1.get("Name",""),
        #     user_name_en=fields2.get("Name",""),
        #     degree_id=None,
        #     role=Role.STUDENT,
        #     email="lnwsomtoyza@kmitl.ac.th",
        #     password_hash=None
        # )

        # project_file = ProjectFile(
        #     file_id=uuid4(),
        #     file_name=file.filename,
        #     file_path=str(dest),
        #     thumbnail_path=str(thumbnail_path), 
        #     uploaded_at=datetime.utcnow()
        # )

        # project = Project(
        #     title_th=fields1.get("Title", ""),
        #     title_en=fields2.get("Title",""),
        #     abstract_th=fields1.get("Abstract",""),
        #     abstract_en=fields2.get("Abstract",""),
        #     academic_year=fields1.get("AcademicYear",""),
        #     degree_id= None,
        #     created_by=user.user_id,
        #     is_active=True,
        #     file_id=project_file.file_id,
        #     download_count=0
        # )

        # await UserRepository.create_user(session, user)
        # await ProjectRepository.create_project_file(session, project_file)
        # await ProjectRepository.create_project(session, project)

        return {
            "original_filename": file.filename,
            "thumbnail_path": thumbnail_path,
            "saved_as": safe_name,
            "fields-th": fields1,
            "fields-en": fields2
        }
            # return 0