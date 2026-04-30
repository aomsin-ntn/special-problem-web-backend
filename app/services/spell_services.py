import re
import difflib
import deepcut

from pythainlp.spell import spell
from pythainlp.corpus.common import thai_words

from sqlmodel import Session
from wordfreq import top_n_list

from app.repository.spell_repository import SpellRepository

class SpellServices:
    
    @staticmethod
    async def get_dictionary_report(db: Session, table_type: str, page: int, limit: int, sorted_by: str, order: str):
        report = await SpellRepository.get_dictionary_report(db, table_type, page, limit, sorted_by, order)
        return report
    
    @staticmethod
    async def get_error_dict(db: Session):
        error_dict = await SpellRepository.get_error_dict(db)
        return error_dict
    
    @staticmethod
    async def get_custom_dict(db: Session):
        custom_dict = await SpellRepository.get_custom_dict(db)
        return custom_dict
    
    @staticmethod
    async def get_correction_by_incorrect(db: Session, incorrect: str):
        correction = await SpellRepository.get_correction_by_incorrect(db, incorrect)
        return correction
    
    @staticmethod
    async def save_correction_no_commit(db: Session, incorrect: str, correct: str):
        correction = await SpellRepository.get_correction_by_incorrect(
            db=db,
            incorrect=incorrect
        )

        if correction:
            correction = await SpellRepository.update_correction_no_commit(
                db=db,
                correction=correction,
                correct=correct
            )
        else:
            correction = await SpellRepository.create_correction_no_commit(
                db=db,
                incorrect=incorrect,
                correct=correct
            )

        await SpellRepository.upsert_incorrect_word_no_commit(
            db=db,
            word_dic_id=correction.word_dic_id,
            correct=correct
        )

        return correction
    
    @staticmethod
    async def save_custom_word(db: Session, cus_word: str):
        custom_word = await SpellRepository.create_custom_word(db, cus_word)
        return custom_word
    
    def __init__(self, error_dict=None, custom_dict=None):
        self.spell_cache = {}
        self.error_dict = {}

        if error_dict:
            # error_dict_rows = [(IncorrectWord, CorrectionDictionary), ...]
            for inc_obj, corr_obj in error_dict:
                wrong = str(corr_obj.incorrect_word or "").strip()
                correct = str(inc_obj.correct_word or "").strip()
                count = int(inc_obj.count or 0)

                if not wrong or not correct:
                    continue

                if wrong not in self.error_dict:
                    self.error_dict[wrong] = {}

                old_count = self.error_dict[wrong].get(correct, 0)
                self.error_dict[wrong][correct] = max(old_count, count)

            # แปลงจาก dict เป็น list ที่เรียง count มาก -> น้อย
            for wrong, correct_map in self.error_dict.items():
                self.error_dict[wrong] = [
                    correct_word
                    for correct_word, _count in sorted(
                        correct_map.items(),
                        key=lambda item: item[1],
                        reverse=True
                    )
                ]

        self.custom_segmentation_dict = list(set(custom_dict)) if custom_dict else []
        self.custom_word_set = set(self.custom_segmentation_dict)
        self.custom_word_lower_set = {
            str(w).strip().lower()
            for w in self.custom_segmentation_dict
            if str(w).strip()
        }

        self.thai_dict = set(thai_words())
        if custom_dict:
            self.thai_dict.update(self.custom_segmentation_dict)
            

        self.eng_dict = set(top_n_list("en", 50000))

    @classmethod
    async def create(cls, db):
        error_dict = await SpellServices.get_error_dict(db)
        custom_dict = await SpellServices.get_custom_dict(db)
        return cls(error_dict=error_dict, custom_dict=custom_dict)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        text = str(text)

        # ลบตัวพินทุ / under-dot OCR noise
        text = text.replace("ฺ", "")

        # ลบ control chars
        text = re.sub(r'[\r\n\t]+', ' ', text)

        # OCR noise ที่ชอบทำให้ตัดคำพัง
        text = text.replace("|", " ")
        text = text.replace("\\", " ")

        text = re.sub(r'\.{2,}', '.', text)

        text = re.sub(
            r'[^a-zA-Z0-9๐-๙\s\.\,\:\-\/\u0E00-\u0E7F\(\)\[\]\@\%\+\#]',
            '',
            text
        )

        return re.sub(r'\s+', ' ', text).strip()
    
    def get_suggestions(self, word: str, is_eng: bool):
        """ใช้สำหรับคำที่หาไม่เจอทั้งใน Error Dict และ Standard Dict"""
        if is_eng:
            return difflib.get_close_matches(word.lower(), self.eng_dict, n=3, cutoff=0.8)
        
        if word in self.spell_cache: 
            return self.spell_cache[word]
            
        sug = spell(word, engine="symspell")
        self.spell_cache[word] = sug
        return sug

    def check_spelling(self, word_list: list) -> dict:
        stats = {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "wrong_words": []
        }

        THAI_MARKS = {
            "ๆ", "ฯ", "่", "้", "๊", "๋", "์",
            "ั", "ิ", "ี", "ึ", "ื", "ุ", "ู", "็"
        }

        # clean ก่อน spellcheck + แตก token ที่มีช่องว่างข้างใน
        cleaned_tokens = []

        for w in word_list:
            cleaned = self.clean_text(str(w).strip())
            if not cleaned:
                continue

            for part in cleaned.split():
                part = part.strip(".,:;()[]{}\"'“”‘’!?、，")
                if not part:
                    continue

                for sub_part in self.split_thai_suffix_word(part):
                    sub_part = sub_part.strip(".,:;()[]{}\"'“”‘’!?、，")
                    if sub_part:
                        cleaned_tokens.append(sub_part)

        i = 0
        while i < len(cleaned_tokens):
            word = cleaned_tokens[i]
            stats["total"] += 1

            if word in THAI_MARKS:
                stats["correct"] += 1
                i += 1
                continue

            # ข้ามตัวเลขไทย/อารบิก และ symbol ล้วน
            if (
                word.isdigit()
                or re.match(r'^[๐-๙]+$', word)
                or re.match(r'^[^a-zA-Z0-9\u0E00-\u0E7F]+$', word)
            ):
                stats["correct"] += 1
                i += 1
                continue

            is_eng = bool(re.match(r'^[a-zA-Z]+$', word))
            word_to_check = word.lower() if is_eng else word
            valid_dict = self.eng_dict if is_eng else self.thai_dict

            # ถ้าเป็นตัวเดียว ให้ลอง merge แล้วแสดงเป็น phrase เดิม
            if len(word) == 1 and not is_eng:
                merge_result = self.get_single_char_merge_result(
                    tokens=cleaned_tokens,
                    index=i,
                    is_eng=is_eng
                )

                stats["incorrect"] += 1
                stats["wrong_words"].append({
                    "word": merge_result["word"],
                    "suggestions": merge_result["suggestions"],
                    "source": "single_char_merge_or_delete",
                    "merged": merge_result["merged"]
                })

                # ถ้าแนะนำลบ แปลว่าไม่ได้ merge สำเร็จ ให้ขยับแค่ 1 token
                if merge_result["suggestions"] == [""]:
                    i += 1
                else:
                    i = merge_result["end"]

                continue

            if word in self.custom_word_set or (is_eng and word_to_check in self.custom_word_lower_set):
                stats["correct"] += 1
                i += 1
                continue

            if is_eng and word_to_check in self.eng_dict:
                stats["correct"] += 1
                i += 1
                continue

            suggestions = []
            sources = []

            # 1. incorrect dict
            if word in self.error_dict:
                self.add_unique_suggestions(suggestions, self.error_dict[word])
                sources.append("error_dict")

            # 2. custom dict similarity
            custom_suggestions = []

            if word in self.error_dict or word_to_check not in valid_dict:
                custom_suggestions = self.get_custom_suggestions(
                    word,
                    threshold=0.7,
                    limit=5
                )

            if custom_suggestions:
                self.add_unique_suggestions(suggestions, custom_suggestions)
                sources.append("custom_dict_similarity")

            if (not is_eng) and word_to_check in valid_dict and not suggestions:
                stats["correct"] += 1
                i += 1
                continue

            # 3. PyThaiNLP / English suggestion
            engine_suggestions = self.get_suggestions(word, is_eng)
            if engine_suggestions:
                filtered_engine_suggestions = self.filter_engine_suggestions(
                    word=word,
                    suggestions=engine_suggestions,
                    is_eng=is_eng,
                    limit=5
                )

                if filtered_engine_suggestions:
                    self.add_unique_suggestions(suggestions, filtered_engine_suggestions)
                    sources.append("engine_suggestion")

            # 4. ถ้าเจอ suggestion = ผิด
            if suggestions:
                stats["incorrect"] += 1
                stats["wrong_words"].append({
                    "word": word,
                    "suggestions": suggestions,
                    "source": "+".join(sources)
                })

            # 5. ถ้าไม่มี suggestion แต่คำอยู่ dict = ถูก
            elif word_to_check in valid_dict:
                stats["correct"] += 1

            # 6. ไม่มี suggestion และไม่อยู่ dict = อาจเป็นชื่อเฉพาะ
            else:
                stats["correct"] += 1

            i += 1

        stats["error_percent"] = (
            round((stats["incorrect"] / stats["total"]) * 100, 2)
            if stats["total"] > 0
            else 0
        )

        return stats

    def compare(self, text1: str, text2: str):
        # 1. ทำความสะอาดและตัดคำทั้งสองชุด
        # (อย่าลืมใส่ custom_dict=self.custom_segmentation_dict เพื่อความแม่นยำ)
        tokens1 = deepcut.tokenize(self.clean_text(text1),self.custom_segmentation_dict)
        tokens2 = deepcut.tokenize(self.clean_text(text2),self.custom_segmentation_dict)

        # 2. ตรวจสอบคำผิด
        res1 = self.check_spelling(tokens1)
        res2 = self.check_spelling(tokens2)

        # 3. ตัดสินใจเลือกอันที่ error_percent น้อยกว่า
        if res1["error_percent"] <= res2["error_percent"]:
            print("Selected EXTRACTED TEXT (lower error rate)")
            print(f"Error Percent: {res1['error_percent']}% (Extracted) vs {res2['error_percent']}% (OCR)")
            return text1, res1  # ส่งคืนข้อความชุดที่ 1 และรายงานสรุป
        else: 
            print("Selected OCR TEXT (lower error rate)")
            print(f"Error Percent: {res1['error_percent']}% (Extracted) vs {res2['error_percent']}% (OCR)")
            return text2, res2  # ส่งคืนข้อความชุดที่ 2 และรายงานสรุป
        
    def get_custom_suggestions(self, word: str, threshold=0.7, limit=5):
        if not word or len(word.strip()) < 2:
            return []

        word = str(word).strip()
        matches = []

        for custom_word in self.custom_segmentation_dict:
            custom_word = str(custom_word).strip()
            if not custom_word:
                continue

            # คำตรงกันเป๊ะ ไม่ต้องแนะนำตัวเอง
            if custom_word.lower() == word.lower():
                continue

            score = difflib.SequenceMatcher(
                None,
                word.lower(),
                custom_word.lower()
            ).ratio()

            if score >= threshold:
                matches.append((custom_word, score))

        matches.sort(key=lambda item: item[1], reverse=True)
        return [word for word, _score in matches[:limit]]
    
    def add_unique_suggestions(self, result: list, suggestions: list):
        """
        รวมคำแนะนำแบบไม่ซ้ำ
        เช่น custom ได้ วิทยาศาสตร์
        incorrect ได้ วิทยาศาสตร์, วิศวกรรมศาสตร์
        ผลลัพธ์ = วิทยาศาสตร์, วิศวกรรมศาสตร์
        """
        for sug in suggestions or []:
            if sug is None:
                continue

            sug = str(sug).strip()

            # อนุญาต "" เพราะใช้แทนคำแนะนำให้ลบ
            if sug == "":
                if sug not in result:
                    result.append(sug)
                continue

            if sug and sug not in result:
                result.append(sug)
    
    def get_single_char_merge_result(self, tokens: list, index: int, is_eng: bool = False):
        word = tokens[index].strip()

        candidates = []

        # รวมไปข้างหน้า แต่หยุดถ้าเจอ boundary เช่น เช่น/หรือ/และ/,/space
        phrase_tokens = [word]

        for j in range(index + 1, min(len(tokens), index + 5)):
            next_part = tokens[j].strip()

            if self.is_merge_boundary(next_part):
                break

            phrase_tokens.append(next_part)

            original_phrase = " ".join(phrase_tokens)
            merged_word = "".join(phrase_tokens)

            candidates.append({
                "start": index,
                "end": j + 1,
                "word": original_phrase,
                "merged": merged_word
            })

        # รวมย้อนหลัง แต่หยุดถ้าเจอ boundary
        phrase_tokens = [word]

        for j in range(index - 1, max(-1, index - 5), -1):
            prev_part = tokens[j].strip()

            if self.is_merge_boundary(prev_part):
                break

            phrase_tokens.insert(0, prev_part)

            original_phrase = " ".join(phrase_tokens)
            merged_word = "".join(phrase_tokens)

            candidates.append({
                "start": j,
                "end": index + 1,
                "word": original_phrase,
                "merged": merged_word
            })

        # รวมหน้า + ตัวเอง + หลัง เฉพาะกรณีที่ไม่มี boundary คั่น
        for left_size in range(1, 4):
            start = index - left_size
            if start < 0:
                continue

            left_tokens = tokens[start:index]

            if any(self.is_merge_boundary(t) for t in left_tokens):
                continue

            for right_size in range(1, 4):
                end = index + right_size + 1
                if end > len(tokens):
                    continue

                right_tokens = tokens[index + 1:end]

                if any(self.is_merge_boundary(t) for t in right_tokens):
                    continue

                phrase_tokens = left_tokens + [word] + right_tokens
                original_phrase = " ".join(t.strip() for t in phrase_tokens if t.strip())
                merged_word = "".join(t.strip() for t in phrase_tokens if t.strip())

                candidates.append({
                    "start": start,
                    "end": end,
                    "word": original_phrase,
                    "merged": merged_word
                })

        # ตัดซ้ำ
        unique_candidates = []
        seen = set()

        for item in candidates:
            key = (item["start"], item["end"], item["merged"])

            if key not in seen:
                seen.add(key)
                unique_candidates.append(item)

        # ให้คำยาวกว่าถูกเช็คก่อน เช่น มหาวิทยาลัย ก่อน มหา
        unique_candidates.sort(key=lambda x: len(x["merged"]), reverse=True)

        valid_dict = self.eng_dict if is_eng else self.thai_dict

        for item in unique_candidates:
            merged = self.clean_text(item["merged"])
            check_merged = merged.lower() if is_eng else merged

            suggestions = []

            # 1. รวมแล้วเป็นคำถูก หรืออยู่ใน custom dict
            if (
                check_merged in valid_dict
                or merged in self.custom_word_set
                or (is_eng and check_merged in self.custom_word_lower_set)
            ):
                self.add_unique_suggestions(suggestions, [merged])

            # 2. รวมแล้วอยู่ใน incorrect dict
            if merged in self.error_dict:
                self.add_unique_suggestions(suggestions, self.error_dict[merged])

            # 3. ถ้ายังไม่มี suggestion ค่อยเช็ค custom similarity
            if not suggestions:
                custom_suggestions = self.get_custom_suggestions(merged, threshold=0.7)
                self.add_unique_suggestions(suggestions, custom_suggestions)

            # 4. ถ้ายังไม่มี suggestion ค่อยถาม engine
            if not suggestions:
                engine_suggestions = self.get_suggestions(merged, is_eng)

                filtered_engine_suggestions = self.filter_engine_suggestions(
                    word=merged,
                    suggestions=engine_suggestions,
                    is_eng=is_eng,
                    limit=5
                )

                self.add_unique_suggestions(suggestions, filtered_engine_suggestions)

            if suggestions:
                return {
                    "start": item["start"],
                    "end": item["end"],
                    "word": item["word"],
                    "merged": merged,
                    "suggestions": suggestions
                }

        return {
            "start": index,
            "end": index + 1,
            "word": word,
            "merged": word,
            "suggestions": [""]
        }
    
    def split_thai_suffix_word(self, word: str) -> list[str]:
        suffix_words = [
            "และ", "หรือ", "กับ", "ของ", "ใน", "จาก",
            "โดย", "เพื่อ", "ที่", "เป็น", "มี", "ได้"
        ]

        # ถ้าทั้งคำถูกอยู่แล้ว ไม่ต้องแยก
        if word in self.thai_dict or word in self.custom_word_set:
            return [word]

        for suffix in suffix_words:
            if word.endswith(suffix) and len(word) > len(suffix) + 1:
                prefix = word[:-len(suffix)]

                if prefix and prefix not in self.thai_dict:
                    return [prefix, suffix]

        return [word]
    
    def is_merge_boundary(self, token: str) -> bool:
        token = str(token).strip()

        if not token:
            return True

        # punctuation / symbol
        if re.match(r'^[^a-zA-Z0-9\u0E00-\u0E7F]+$', token):
            return True

        # คำที่ไม่ควรถูกลากไปรวมกับคำผิด
        stop_words = {
            "เช่น", "หรือ", "และ", "กับ", "ของ", "ใน", "จาก", "โดย",
            "เพื่อ", "ที่", "คือ", "เป็น", "มี", "ได้", "ให้", "ว่า",
            "ระบบ", "คำ", "ตัวอย่าง", "ถ้า", "หาก", "พบ", "ควร", "ไม่",
            "สามารถ", "รวม", "ออก", "เข้า", "แล้ว", "นั้น", "นี้", "อย่าง"
        }

        return token in stop_words
    
    def filter_engine_suggestions(
        self,
        word: str,
        suggestions: list,
        is_eng: bool = False,
        limit: int = 5
    ) -> list[str]:
        result = []

        word = str(word).strip()
        word_lower = word.lower()

        for sug in suggestions or []:
            sug = str(sug).strip()

            if not sug:
                continue

            # ไม่เอาคำเดิม
            if sug == word:
                continue

            # กัน suggestion ที่สั้นเกินไป เช่น เอกส
            if len(sug) < 2:
                continue

            # ถ้าคำผิดยาวมาก แต่ suggestion สั้นลงเยอะเกินไป มักไม่น่าใช่
            # เช่น ประมวลผ -> ประมวล อาจไม่ใช่ที่ต้องการ
            if len(word) >= 5 and len(sug) < len(word):
                # ยกเว้นกรณีที่ suggestion เป็น substring ที่ดูสมเหตุสมผล แต่โดยระบบ OCR ส่วนใหญ่ไม่ควรตัดสั้นลง
                continue

            # อังกฤษ lowercase เทียบ
            if is_eng and sug.lower() == word_lower:
                continue

            if sug not in result:
                result.append(sug)

            if len(result) >= limit:
                break

        return result