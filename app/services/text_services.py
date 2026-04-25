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
        selected_wrong_words = []

        # 1. เลือก best_text ต่อหน้า และเก็บคำผิดจากหน้านั้น
        for page_index, res in enumerate(results):
            ext_text = res.get("ext", "") or ""
            ocr_text = res.get("ocr", "") or ""

            best_text, spell_info = self._select_best_text(
                ext_text=ext_text,
                ocr_text=ocr_text,
                spell_services=spell_services
            )

            if not best_text.strip():
                continue

            selected_texts.append(best_text)

            for wrong_word in spell_info.get("wrong_words", []) or []:
                word_text = wrong_word.get("word")

                if not word_text:
                    continue

                selected_wrong_words.append({
                    "page": page_index + 1,
                    "word": word_text,
                    "suggestions": wrong_word.get("suggestions", []),
                    "source": wrong_word.get("source")
                })

        # 2. รวมข้อความ แล้ว extract fields
        full_text = " ".join(selected_texts)

        print("----------Raw DATA ----------")
        print(full_text)

        fields = extract_services.extract_fields(full_text)

        # 3. เอาคำผิดทั้งหมด ไป map ว่าอยู่ field ไหน
        report_spell_res = self._map_wrong_words_to_fields(
            fields=fields,
            wrong_words=selected_wrong_words,
            spell_services=spell_services
        )

        print("----------Spell Check Report ----------")
        print(report_spell_res)

        return fields, report_spell_res
    
    @staticmethod
    def _thai_ratio(text: str) -> float:
        if not text:
            return 0
        thai_chars = re.findall(r"[ก-๙]", text)
        return len(thai_chars) / len(text)

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
    
    def _select_best_text(self, ext_text, ocr_text, spell_services):
        ext_text = TextServices.clean_ocr_noise(ext_text)
        ocr_text = TextServices.clean_ocr_noise(ocr_text)

        ext_bad = TextServices.is_broken_text(ext_text)
        ocr_bad = TextServices.is_broken_text(ocr_text)

        # ถ้า extracted พัง แต่ OCR ไม่พัง → ใช้ OCR
        if ext_bad and not ocr_bad and ocr_text.strip():
            best_text = ocr_text

        # ถ้า OCR พัง แต่ extracted ไม่พัง → ใช้ extracted
        elif ocr_bad and not ext_bad and ext_text.strip():
            best_text = ext_text

        # ถ้าทั้งคู่ไม่พัง → ค่อย compare error rate
        elif not ext_bad and not ocr_bad and ext_text and ocr_text:
            return spell_services.compare(ext_text, ocr_text)

        # fallback
        else:
            best_text = ocr_text if ext_bad and ocr_text.strip() else (ext_text or ocr_text)

        if not best_text.strip():
            return "", {
                "wrong_words": [],
                "error_percent": 0
            }

        tokens = deepcut.tokenize(
            spell_services.clean_text(best_text),
            spell_services.custom_segmentation_dict
        )

        spell_info = spell_services.check_spelling(tokens)

        return best_text, spell_info

    def _map_wrong_words_to_fields(self, fields, wrong_words, spell_services):
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

            # รองรับทั้ง string และ list เช่น keywords
            if isinstance(field_value, list):
                field_text = " ".join(str(v) for v in field_value if v)
            elif isinstance(field_value, str):
                field_text = field_value
            else:
                continue

            # tokenize field นี้ครั้งเดียว
            field_tokens = deepcut.tokenize(
                spell_services.clean_text(field_text),
                spell_services.custom_segmentation_dict
            )
            field_token_set = set(field_tokens)

            found_words = []
            seen_words_in_field = set()

            # เอาคำผิดทั้งหมดมาเช็คว่าอยู่ใน field นี้ไหม
            for wrong_word in wrong_words:
                word_text = wrong_word.get("word")

                if not word_text:
                    continue

                # กันคำซ้ำเฉพาะใน field เดียวกัน
                if word_text in field_token_set and word_text not in seen_words_in_field:
                    found_words.append({
                        "word": word_text,
                        "suggestions": wrong_word.get("suggestions", []),
                        "source": wrong_word.get("source")
                    })
                    seen_words_in_field.add(word_text)

            if found_words:
                report_spell_res.append({
                    "field": field_name,
                    "stats": {
                        "total": len(field_tokens),
                        "incorrect": len(found_words),
                        "error_percent": round((len(found_words) / len(field_tokens)) * 100, 2) if field_tokens else 0,
                        "wrong_words": found_words
                    }
                })

        return report_spell_res
    
    @staticmethod
    def clean_ocr_noise(text: str) -> str:
        if not text:
            return ""

        text = text.replace("ฺ", "")
        text = re.sub(r'[\x00-\x1F\x7F]', ' ', text)
        text = text.replace("|", " ").replace("\\", " ")

        # 🔥 punctuation fix
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r',{2,}', ',', text)
        text = re.sub(r':{2,}', ':', text)
        text = re.sub(r'-{2,}', '-', text)
        text = re.sub(r'\s+([.,:;])', r'\1', text)
        text = re.sub(r'([.,:;])([^\s])', r'\1 \2', text)

        text = re.sub(r'[ \t]+', ' ', text)

        return text.strip()
    
