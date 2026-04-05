from pythainlp.spell import spell
from pythainlp.corpus.common import thai_words
from attacut import tokenize
import re
import difflib
from wordfreq import top_n_list


class SpellChecker:
    def __init__(self, error_dict, threshold=10):
        self.error_dict = error_dict
        self.threshold = threshold
        self.thai_dict = set(thai_words())
        self.spell_cache = {}

        # English dictionary
        self.eng_dict = set(top_n_list("en", 50000))

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


    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        text = re.sub(r'\r\n|\r|\n', '', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()

        # remove ......
        text = re.sub(r'\.{2,}', '', text)

        # lowercase English
        text = re.sub(r'[A-Z]+', lambda m: m.group(0).lower(), text)

        # remove weird symbols
        text = re.sub(r'[^\w\s\.\,\:\-\/\u0E00-\u0E7F]', '', text)

        return text


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

    def is_english(self, word):
        return re.match(r'^[a-zA-Z]+$', word) is not None

    def is_symbol(self, word):
        return re.match(r'^[^a-zA-Z0-9\u0E00-\u0E7F]+$', word) is not None

    def check_english(self, word):
        word_lower = word.lower()

        if word_lower in self.eng_dict:
            return True, []

        suggestions = difflib.get_close_matches(word_lower, self.eng_dict, n=3, cutoff=0.8)

        if suggestions:
            return False, suggestions

        return True, []

    def check_spelling(self, word_list):
        correct = 0
        incorrect = 0
        wrong_words = []

        for word in word_list:
            word = word.strip()

            if not word:
                continue

            if self.is_symbol(word) or word.isdigit():
                correct += 1
                continue

            if word in self.error_dict and self.error_dict[word]["count"] >= self.threshold:
                incorrect += 1
                wrong_words.append({
                    "word": word,
                    "suggestions": [self.error_dict[word]["correct"]],
                    "source": "error_dict"
                })
                continue

            if self.is_english(word):
                is_correct, suggestions = self.check_english(word)

                if is_correct:
                    correct += 1
                else:
                    incorrect += 1
                    wrong_words.append({
                        "word": word,
                        "suggestions": suggestions,
                        "source": "english_spell"
                    })
                continue

            if word in self.thai_dict:
                correct += 1
                continue

            if word in self.spell_cache:
                suggestions = self.spell_cache[word]
            else:
                suggestions = spell(word, engine="symspell")
                self.spell_cache[word] = suggestions

            if not suggestions or suggestions[0] == word:
                correct += 1
                continue

            incorrect += 1
            wrong_words.append({
                "word": word,
                "suggestions": suggestions[:5],
                "source": "spell"
            })

        total = len(word_list)
        error_percent = (incorrect / total) * 100 if total > 0 else 0

        return {
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "error_percent": round(error_percent, 2),
            "wrong_words": wrong_words
        }

    def compare(self, text1, text2):
        token1 = tokenize(self.clean_text(text1))
        token2 = tokenize(self.clean_text(text2))

        result1 = self.check_spelling(token1)
        result2 = self.check_spelling(token2)

        if result1["error_percent"] > result2["error_percent"]:
            return {"choose": "text2", "result": result2}
        elif result1["error_percent"] < result2["error_percent"]:
            return {"choose": "text1", "result": result1}
        else:
            return {"choose": "text1", "result": result1}