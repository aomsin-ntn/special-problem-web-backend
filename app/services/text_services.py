# text_services.py
from deepcut import deepcut
import re

from app.services.spell_services import SpellServices
from app.services.extract_services import ExtractServices


class TextServices:
    def __init__(self):
        pass

    async def process(self, results, db):
        spell_services = await SpellServices.create(db)
        extract_services = ExtractServices()

        selected_texts = []

        # 1. เลือก best_text ต่อหน้าอย่างเดียว
        # ยังไม่เก็บคำผิดตรงนี้ เพราะยังไม่รู้ว่า text อยู่ field ไหน
        for page_index, res in enumerate(results):
            ext_text = res.get("ext", "") or ""
            ocr_text = res.get("ocr", "") or ""

            best_text = self._select_best_text_only(
                ext_text=ext_text,
                ocr_text=ocr_text,
                spell_services=spell_services
            )

            if not best_text.strip():
                continue

            selected_texts.append(best_text)

        # 2. รวม best_text ทั้งหมด
        full_text = "\n\n---PAGE---\n\n".join(selected_texts)

        print("----------Raw DATA ----------")
        print(full_text)

        # 3. Extract fields จาก text ที่เลือกแล้ว
        fields = extract_services.extract_fields(full_text)

        # 4. ค่อย spell check แยกตาม field
        report_spell_res = self._spell_check_fields(
            fields=fields,
            spell_services=spell_services
        )

        print("----------Spell Check Report ----------")
        print(report_spell_res)

        return fields, report_spell_res

    @staticmethod
    def is_broken_text(text: str) -> bool:
        if not text:
            return False

        length = max(len(text), 1)

        thai_count = len(re.findall(r"[ก-๙]", text))
        weird_count = len(re.findall(r"[^\x00-\x7Fก-๙]", text))

        thai_ratio = thai_count / length
        weird_ratio = weird_count / length

        # ตัวอักษรแปลกที่เจอบ่อยจาก PDF extract พัง
        broken_patterns = [
            r"ǰ",
            r"Ĵ",
            r"\*[A-Z]+",      # เช่น *OTUJUVUF
            r"[A-Z]{2,}ǰ",
            r"[A-Za-z]+ǰ",
        ]

        has_broken_pattern = any(
            re.search(pattern, text)
            for pattern in broken_patterns
        )

        # ไทยพัง หรือ อังกฤษพัง
        return (
            (weird_ratio > 0.03 and thai_ratio < 0.4)
            or has_broken_pattern
        )
    
    def _select_best_text_only(self, ext_text, ocr_text, spell_services):
        ext_text = TextServices.clean_ocr_noise(ext_text)
        ocr_text = TextServices.clean_ocr_noise(ocr_text)

        ext_bad = TextServices.is_broken_text(ext_text)
        ocr_bad = TextServices.is_broken_text(ocr_text)

        # ถ้า extracted พัง แต่ OCR ไม่พัง → ใช้ OCR
        if ext_bad and not ocr_bad and ocr_text.strip():
            return ocr_text

        # ถ้า OCR พัง แต่ extracted ไม่พัง → ใช้ extracted
        if ocr_bad and not ext_bad and ext_text.strip():
            return ext_text

        # ถ้าทั้งคู่ไม่พัง → เทียบ error rate เพื่อเลือกตัวที่ดีกว่า
        if not ext_bad and not ocr_bad and ext_text.strip() and ocr_text.strip():
            best_text, _spell_info = spell_services.compare(ext_text, ocr_text)
            return best_text

        # fallback
        if ext_text.strip():
            return ext_text

        if ocr_text.strip():
            return ocr_text

        return ""

    def _spell_check_fields(self, fields, spell_services):
        fields_to_check = [
            "title_th",
            "title_en",
            "abstract_th",
            "abstract_en",
            "keywords_th",
            "keywords_en"
        ]

        report_spell_res = []

        for field_name in fields_to_check:
            field_value = fields.get(field_name)

            if not field_value:
                continue

            # รองรับ string และ list เช่น keywords
            if isinstance(field_value, list):
                field_text = " ".join(str(v) for v in field_value if v)
            elif isinstance(field_value, str):
                field_text = field_value
            else:
                continue

            field_text = spell_services.clean_text(field_text)

            if not field_text:
                continue

            field_tokens = deepcut.tokenize(
                field_text,
                spell_services.custom_segmentation_dict
            )

            spell_info = spell_services.check_spelling(field_tokens)

            wrong_words = spell_info.get("wrong_words", []) or []

            if wrong_words:
                report_spell_res.append({
                    "field": field_name,
                    "stats": {
                        "total": spell_info.get("total", 0),
                        "correct": spell_info.get("correct", 0),
                        "incorrect": spell_info.get("incorrect", 0),
                        "error_percent": spell_info.get("error_percent", 0),
                        "wrong_words": wrong_words
                    }
                })

        return report_spell_res
    
    @staticmethod
    def clean_ocr_noise(text: str) -> str:
        if not text:
            return ""

        text = str(text)

        text = text.replace("ฺ", "")
        text = text.replace("|", "\n")
        text = text.replace("\\", " ")

        # ลบ control chars แต่ไม่ลบ newline
        text = re.sub(r"[\r\t]+", " ", text)

        # clean ทีละบรรทัด
        lines = []
        for line in text.split("\n"):
            line = re.sub(r"[ ]+", " ", line).strip()
            if line:
                lines.append(line)

        return "\n".join(lines)

    
