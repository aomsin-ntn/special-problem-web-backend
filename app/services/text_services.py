# text_services.py
from deepcut import deepcut

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

        # 2. รวมข้อความเพื่อ Extract (ยังไม่เช็คคำผิด)
        # เราใช้ ext_text เป็นหลักเพราะปกติความแม่นยำสูงกว่า OCR ในเชิงโครงสร้าง
        full_text = " | ".join([res["ext"] if res["ext"] else res["ocr"] for res in results])

        # 3. Extract ข้อมูลออกมาก่อน
        fields = extract_services.extract_fields(full_text)

        # 4. นำค่าที่ Extract ได้ มาไล่เช็คคำผิดทีละฟิลด์ (เฉพาะ Text fields)
        report_spell_res = []
        
        # รายชื่อฟิลด์ที่ต้องการเช็คคำผิด
        fields_to_check = ["title_th", "title_en", "abstract_th", "abstract_en", "keywords_th", "keywords_en"]

        for key in fields_to_check:
            text_val = fields.get(key)
            if text_val and isinstance(text_val, str):
                # เช็คคำผิดเฉพาะฟิลด์นั้นๆ
                tokens = deepcut.tokenize(spell_services.clean_text(text_val), custom_dict)
                spell_info = spell_services.check_spelling(tokens)
                
                if spell_info["incorrect"] > 0:
                    report_spell_res.append({
                        "field": key,
                        "stats": spell_info
                    })

        return fields, report_spell_res