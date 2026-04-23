# text_services.py
from deepcut import deepcut
import os

from app.services.spell_services import SpellServices
from app.services.project_services import ProjectServices
from app.services.extract_services import ExtractServices

class TextServices:
    def __init__(self):
        # ไม่จำเป็นต้องสร้างตัวเปล่าไว้ที่นี่ก็ได้ 
        # เพราะเราต้องการ error_dict จาก DB มา Initialize ใน process
        pass

    async def process(self, results, db):
        # 1. เตรียม Services
        error_dict = await ProjectServices.get_error_dict(db)
        custom_dict = await ProjectServices.get_custom_dict(db)
        spell_services = SpellServices(error_dict=error_dict, custom_dict=custom_dict)
        extract_services = ExtractServices()

        # 2. เปรียบเทียบเพื่อเลือกเวอร์ชันที่ดีที่สุด (Best Version) ของแต่ละหน้า
        selected_texts = []
        for res in results:
            ext_text = res.get("ext", "")
            ocr_text = res.get("ocr", "")

            # ถ้ามีอย่างใดอย่างหนึ่งว่าง ให้ใช้อีกอันทันที
            if not ext_text:
                selected_texts.append(ocr_text)
                continue
            if not ocr_text:
                selected_texts.append(ext_text)
                continue

            # ถ้ามีทั้งคู่ ให้ใช้เมธอด compare ที่คุณเขียนไว้เพื่อเลือกอันที่ error_percent ต่ำกว่า
            best_text, _res = spell_services.compare(ext_text, ocr_text)
            selected_texts.append(best_text)
            # selected_texts.append(ocr_text)  # สมมติว่า ext_text ดีกว่าเสมอในตอนนี้ (คุณสามารถเปลี่ยนกลับไปใช้ compare ได้ตามต้องการ)

        # รวมข้อความจากหน้าที่ดีที่สุดเข้าด้วยกัน
        full_text = " | ".join(selected_texts)

        print("----------Raw DATA ----------")
        print(full_text)

        # 3. Extract ข้อมูลจากข้อความที่กรองมาแล้ว
        fields = extract_services.extract_fields(full_text)
        print("Debug Keywords: ", fields.get("keywords_th"), fields.get("keywords_en"))

        # 4. สรุปรายงานคำผิดจากฟิลด์ที่กำหนด
        report_spell_res = []
        fields_to_check = ["title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en"]

        for key in fields_to_check:
            text_val = fields.get(key)
            if text_val and isinstance(text_val, str):
                # ตรวจสอบคำผิดเพื่อทำสถิติส่งคืนหน้าบ้าน
                tokens = deepcut.tokenize(spell_services.clean_text(text_val), custom_dict)
                spell_info = spell_services.check_spelling(tokens)
                
                if spell_info["incorrect"] > 0:
                    report_spell_res.append({
                        "field": key,
                        "stats": spell_info
                    })
        
        return fields, report_spell_res