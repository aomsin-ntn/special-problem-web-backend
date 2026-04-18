# text_services.py
from app.services.spell_services import SpellServices
from app.services.project_services import ProjectServices

class TextServices:
    def __init__(self):
        # ไม่จำเป็นต้องสร้างตัวเปล่าไว้ที่นี่ก็ได้ 
        # เพราะเราต้องการ error_dict จาก DB มา Initialize ใน process
        pass

    async def process(self, ocr_text, pdf_text, db):
        # 1. ดึงข้อมูลคำผิดจาก Database
        error_dict = await ProjectServices.get_error_dict(db)
        custom_dict = await ProjectServices.get_custom_dict(db)
        
        # 2. สร้าง instance พร้อมข้อมูล error_dict
        # หมายเหตุ: อย่าลืมว่าใน SpellServices เมธอด compare 
        # ต้องแก้ให้รับแค่ (text1, text2) ตามที่คุยกันรอบก่อน
        checker = SpellServices(error_dict=error_dict,custom_dict=custom_dict)
        
        # 3. ใช้ instance 'checker' (ตัวที่เพิ่งสร้าง) ในการทำงาน
        best_text, spell_res = checker.compare(ocr_text, pdf_text)
        fields = checker.extract_fields(best_text)

        return fields, spell_res