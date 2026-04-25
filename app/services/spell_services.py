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
            # error_dict_rows จะเป็น [(IncorrectWord, CorrectionDictionary), ...]
            for inc_obj, corr_obj in error_dict:
                # inc_obj.word คือ คำที่ผิด
                # corr_obj.correct_word คือ คำที่ถูก
                wrong = inc_obj.word.strip()
                correct = corr_obj.correct_word.strip()
                
                if wrong not in self.error_dict:
                    self.error_dict[wrong] = []
                
                if correct not in self.error_dict[wrong]:
                    self.error_dict[wrong].append(correct)
                
        # เก็บไว้ใช้กับ deepcut.tokenize
        self.custom_segmentation_dict = list(set(custom_dict)) if custom_dict else []
        
        # รวมคำเฉพาะทางเข้ากับ Dictionary ภาษาไทยมาตรฐาน
        self.thai_dict = set(thai_words())
        if custom_dict:
            # อัปเดตไทยดิคด้วยคำเฉพาะทาง เพื่อให้ถือว่าเป็นคำที่ 'ถูก' (Priority 2)
            self.thai_dict.update(self.custom_segmentation_dict)
            
        self.eng_dict = set(top_n_list("en", 50000))

    @classmethod
    async def create(cls, db):
        error_dict = await SpellRepository.get_error_dict(db)
        custom_dict = await SpellRepository.get_custom_dict(db)
        return cls(error_dict=error_dict, custom_dict=custom_dict)

    def clean_text(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'[^\w\s\.\,\:\-\/\u0E00-\u0E7F\(\)\[\]\@\%\+\#]', '', text)
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
        stats = {"total": 0, "correct": 0, "incorrect": 0, "wrong_words": []}
        
        for word in [w.strip() for w in word_list if w.strip()]:
            stats["total"] += 1
            
            # 1. ข้ามตัวเลข (ไทย/อารบิก) และสัญลักษณ์
            if word.isdigit() or re.match(r'^[๐-๙]+$', word) or re.match(r'^[^a-zA-Z0-9\u0E00-\u0E7F]+$', word):
                stats["correct"] += 1
                continue

            # 2. Priority 1: ตรวจสอบใน Error Dict (Database) ก่อนเสมอ
            if word in self.error_dict:
                stats["incorrect"] += 1
                stats["wrong_words"].append({
                    "word": word,
                    "suggestions": self.error_dict[word], # ส่ง List คำแนะนำออกไปเลย
                    "source": "error_dict"
                })
                continue

            # 3. Priority 2: ตรวจสอบความถูกต้องตาม Standard Dict
            is_eng = bool(re.match(r'^[a-zA-Z]+$', word))
            word_to_check = word.lower() if is_eng else word
            valid_dict = self.eng_dict if is_eng else self.thai_dict

            if word_to_check in valid_dict:
                stats["correct"] += 1
                continue
            custom_suggestion, custom_score = self.get_custom_suggestion(word, threshold=0.7)

            if custom_suggestion:
                stats["incorrect"] += 1
                stats["wrong_words"].append({
                    "word": word,
                    "suggestions": [custom_suggestion],
                    "source": "custom_dict_similarity",
                    "score": round(custom_score, 2)
                })
                continue

            # 4. Priority 3: ถ้าไม่เจอเลย ให้ถาม Suggestion Engine
            sug = self.get_suggestions(word, is_eng)
            if sug and sug[0] != word:
                stats["incorrect"] += 1
                stats["wrong_words"].append({
                    "word": word,
                    "suggestions": sug[:5],
                    "source": "engine_suggestion"
                })
            else:
                # ถ้าไม่มีคำแนะนำ ให้ถือว่าอาจเป็นชื่อเฉพาะที่เขียนถูกแล้ว
                stats["correct"] += 1

        stats["error_percent"] = round((stats["incorrect"] / stats["total"]) * 100, 2) if stats["total"] > 0 else 0
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
        
    def get_custom_suggestion(self, word: str, threshold=0.7):
        if not word or len(word.strip()) < 2:
            return None, 0

        best_match = None
        best_score = 0

        for custom_word in self.custom_segmentation_dict:
            score = difflib.SequenceMatcher(
                None,
                word.lower(),
                str(custom_word).lower()
            ).ratio()

            if score > best_score:
                best_score = score
                best_match = custom_word

        if best_score >= threshold:
            return best_match, best_score

        return None, best_score
    
    def should_mark_wrong(tokens, i, valid_words):
        word = tokens[i].strip()

        if not word:
            return False

        prev_word = tokens[i - 1].strip() if i > 0 else ""
        next_word = tokens[i + 1].strip() if i < len(tokens) - 1 else ""

        # 🔥 เคสสำคัญ: ตัวเดียว + คำถัดไป
        if len(word) == 1 and next_word:
            merged = word + next_word
            if merged in valid_words:
                return False   # ไม่ผิด

        # 🔥 ปกติ
        if word in valid_words:
            return False

        # รวมคำ
        candidates = []

        if prev_word:
            candidates.append(prev_word + word)

        if next_word:
            candidates.append(word + next_word)

        if prev_word and next_word:
            candidates.append(prev_word + word + next_word)

        if any(c in valid_words for c in candidates):
            return False

        return True