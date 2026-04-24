# text_services.py
from deepcut import deepcut

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

    def _select_best_text(self, ext_text, ocr_text, spell_services):
        """
        คืนค่า:
        - best_text
        - spell_info ของ best_text นั้น
        """

        # มีทั้ง ext และ ocr -> ใช้ compare ซึ่งตรวจคำผิดให้แล้ว
        if ext_text and ocr_text:
            return spell_services.compare(ext_text, ocr_text)

        # มีแค่อย่างใดอย่างหนึ่ง
        best_text = ext_text or ocr_text or ""

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
                    "wrong_words": found_words
                })

        return report_spell_res