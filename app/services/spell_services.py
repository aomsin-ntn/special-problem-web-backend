import re
import difflib
import deepcut
from pythainlp.spell import spell
from pythainlp.corpus.common import thai_words
from wordfreq import top_n_list
from app.services.project_services import ProjectServices

class SpellServices:

    TITLE_KEYS = r'(?:หัวข้อ(?:ปัญหาพิเศษ|สหกิจศึกษา|โครงงานพิเศษ)|Title:?|title:?)'
    STUDENT_KEYS = r'(?:ชื่อนักศึกษา|ชื่อผู้จัดทำ|Student Name|By:?|ผู้จัดทำ|student id?\s+(?:mr|miss|mrs)\b|students?(?=\s*(?:mr\.?|miss\.?|mrs\.?|นาย|นางสาว|นาง)))'
    DEGREE_KEYS = r'(?:ปริญญา|Degree)'
    DEPARTMENT_KEYS = r'(?:ภาควิชา|Department)'
    FACULTY_KEYS = r'(?:คณะ|Faculty|School)'
    UNIVERSITY_KEYS = r'(?:มหาวิทยาลัย|University)'
    ACADEMIC_YEAR_KEYS = r'(?:ปีการศึกษา|Academic\s*Year:?|AcademicYear)'
    ADVISOR_KEYS = r'(?:อาจารย์ที่ปรึกษา|Advisor)'
    ABSTRACT_KEYS = r'(?:บทคัดย่อ|Abstract)'
    KEYWORDS_KEYS = r'(?:คำสำคัญ:?|Keywords:?)'

    def __init__(self, error_dict=None, custom_dict=None):
        self.spell_cache = {}
        self.error_dict = {}
        if error_dict:
            for item in error_dict:
                wrong = item[0]
                correct = item[1]
                self.error_dict[wrong] = {"correct": correct}
        self.custom_segmentation_dict = list(set(custom_dict)) if custom_dict else []
        self.thai_dict = set(thai_words())
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
    
    def build_pattern(self, start, end):
        return rf'{start}\s*(.*?)(?={end}|$)'
    
    def extract_fields(self, text: str) -> dict:

        text = self.clean_text(text)

        patterns = {
            'Title': rf'{self.TITLE_KEYS}\s*(.*?)(?={self.STUDENT_KEYS}|$)',
            'Degree': self.build_pattern(self.DEGREE_KEYS, self.DEPARTMENT_KEYS),
            'Department': self.build_pattern(self.DEPARTMENT_KEYS, self.FACULTY_KEYS),
            'Faculty': self.build_pattern(self.FACULTY_KEYS, self.UNIVERSITY_KEYS),
            'University': self.build_pattern(self.UNIVERSITY_KEYS, self.ACADEMIC_YEAR_KEYS),
            'AcademicYear': self.build_pattern(self.ACADEMIC_YEAR_KEYS, self.ADVISOR_KEYS),
            'Advisor': self.build_pattern(self.ADVISOR_KEYS, self.ABSTRACT_KEYS),
            'Abstract': self.build_pattern(self.ABSTRACT_KEYS, self.KEYWORDS_KEYS),
            'Keywords': rf'{self.KEYWORDS_KEYS}\s*(.*)',
        }

        results = {}

        for key, pat in patterns.items():
            m = re.search(pat, text, flags=re.DOTALL | re.IGNORECASE)
            if m:
                results[key] = m.group(1).strip()

        name_block = None
        
        # ใช้ STUDENT_KEYS เพื่อหาจุดเริ่มต้นที่แม่นยำขึ้น
        m = re.search(
            rf'(?:{self.STUDENT_KEYS})(.*?)(?=\s*(?:ปริญญา|degree))',
            text,
            flags=re.DOTALL | re.IGNORECASE
        )

        if m:
            name_block = m.group(1).strip()
            # ลบส่วนที่เคยชดเชย match_prefix ของเดิมทิ้งไป เพื่อไม่ให้ชื่อเบิ้ล

        students = []

        if name_block:
            matches = re.findall(
                r'((?:mr\.?|miss\.?|mrs\.?|นาย|นางสาว|นาง)?\s*[a-zA-Z\u0E00-\u0E7F\s\.\-]+?)\s*(?:รหัสนักศึกษา|student id|id)?\s*(\d{6,})',
                name_block,
                flags=re.IGNORECASE
            )

            for name, sid in matches:
                name_clean = name.strip()

                # 1. ลบคำขยะ (students/ชื่อนักศึกษา) ที่อาจคั่นอยู่หน้าชื่อคนที่ 2
                name_clean = re.sub(r'^(?:students?|ชื่อนักศึกษา)\s*', '', name_clean, flags=re.IGNORECASE).strip()
                
                # 2. ป้องกันคำนำหน้าซ้ำซ้อน (เช่น "นางสาว นางสาว" หรือ "miss miss")
                name_clean = re.sub(r'^(mr\.?|miss\.?|mrs\.?|นาย|นางสาว|นาง)\s*\1', r'\1', name_clean, flags=re.IGNORECASE).strip()

                if not name_clean:
                    continue

                students.append({
                    "name": name_clean,
                    "id": sid.strip() if sid else None
                })

            # 🔥 fallback ถ้าไม่เจออะไรเลย
            if not students and name_block:
                students.append({
                    "name": name_block.strip(),
                    "id": None
                })

        if students:
            results['Students'] = students

        for k, v in results.items():
            if isinstance(v, str):

                v = v.replace("\n", " ")
                v = re.sub(r'\.{2,}', '', v)
                v = v.lstrip(': ').strip()
                v = re.sub(r'\s+', ' ', v)

                results[k] = v.strip()

        if 'Title' not in results:
            m = re.search(r'^(.*?)(?=ชื่อนักศึกษา)', text)
            if m:
                results['Title'] = m.group(1).strip()

        # fix University
        if 'University' in results:
            uni = results['University']
            uni = re.sub(r'(University)\s*\1+', r'\1', uni, flags=re.IGNORECASE)
            uni = re.sub(r'\s+', ' ', uni)
            results['University'] = uni.strip()

        if 'Keywords' in results and isinstance(results['Keywords'], str):
            keywords_text = results['Keywords']
            # ตรวจสอบว่ามีเครื่องหมายจุลภาค (,) หรือไม่
            if ',' in keywords_text:
                # แยกคำด้วยเครื่องหมาย , แล้วตัดช่องว่างหน้า-หลังของแต่ละคำออก
                keywords_list = [kw.strip() for kw in keywords_text.split(',')]
            else:
                # แยกคำด้วยเว้นวรรค
                keywords_list = [kw.strip() for kw in keywords_text.split()]
            
            # กรองเอาเฉพาะคำที่ไม่ใช่ค่าว่าง
            results['Keywords'] = [kw for kw in keywords_list if kw]

        return results


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