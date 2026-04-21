import re
import difflib
import deepcut

from pythainlp.spell import spell
from pythainlp.corpus.common import thai_words

from wordfreq import top_n_list

class SpellServices:

    def __init__(self, error_dict=None, custom_dict=None):
        self.spell_cache = {}
        self.error_dict = {}
        if error_dict:
            # สมมติ item คือ [wrong, correct]
            for wrong, correct in error_dict:
                self.error_dict[wrong] = {"correct": correct}
                
        # เก็บไว้ใช้กับ deepcut.tokenize
        self.custom_segmentation_dict = list(set(custom_dict)) if custom_dict else []
        
        # รวมคำเฉพาะทางเข้ากับ Dictionary ภาษาไทยมาตรฐาน
        self.thai_dict = set(thai_words())
        if custom_dict:
            # อัปเดตไทยดิคด้วยคำเฉพาะทาง เพื่อให้ถือว่าเป็นคำที่ 'ถูก' (Priority 2)
            self.thai_dict.update(self.custom_segmentation_dict)
            
        self.eng_dict = set(top_n_list("en", 50000))

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
                    "suggestions": [self.error_dict[word]["correct"]],
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
            
            return text1, res1  # ส่งคืนข้อความชุดที่ 1 และรายงานสรุป
        else: 
            return text2, res2  # ส่งคืนข้อความชุดที่ 2 และรายงานสรุป