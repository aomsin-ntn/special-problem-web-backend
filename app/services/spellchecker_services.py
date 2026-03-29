from pythainlp.spell import spell
from pythainlp.corpus.common import thai_words
from attacut import tokenize
import re


class SpellChecker:
    def __init__(self, error_dict, threshold=10):
        self.error_dict = error_dict
        self.threshold = threshold
        self.thai_dict = set(thai_words())
        self.spell_cache = {}

    def is_english(self, word):
        return re.match(r'^[a-zA-Z0-9:_\-\.\(\)]+$', word) is not None

    def extract_fields(self, text: str) -> dict:
        pattern = {
            'หัวข้อ': r'(?:หัวข้อ(?:ปัญหาพิเศษ|สหกิจศึกษา|โครงงานพิเศษ)|สหกิจศึกษา)\s*(.*?)(?=\sชื่อนักศึกษา|$)',
            'ชื่อนักศึกษา': r'ชื่อนักศึกษา\s*(.*?)(?=\sปริญญา|$)',
            'ปริญญา': r'ปริญญา\s*(.*?)(?=\sภาควิชา|$)',
            'ภาควิชา': r'ภาควิชา\s*(.*?)(?=\sคณะ|ปีการศึกษา|$)',
            'คณะ': r'คณะ\s*(.*?)(?=\sมหาวิทยาลัย|$)',
            'มหาวิทยาลัย': r'มหาวิทยาลัย\s*(.*?)(?=\sปีการศึกษา|$)',
            'ปีการศึกษา': r'ปีการศึกษา\s*(.*?)(?=\sอาจารย์ที่ปรึกษา|$)',
            'อาจารย์ที่ปรึกษา': r'อาจารย์ที่ปรึกษา\s*(.*?)(?=\sบทคัดย่อ|$)',
            'บทคัดย่อ': r'บทคัดย่อ\s*(.*?)(?=\sคำสำคัญ|$)',
            'คำสำคัญ': r'(?:คำสำคัญ:|คำสำคัญ)\s*(.*?)(?=\sTitle|$)',
        }
        results = {}
        for key, pat in pattern.items():
            m = re.search(pat, text, flags=re.DOTALL)
            if m:
                results[key] = m.group(1).strip()
        return results

    def check_spelling(self, word_list):
        correct = 0
        incorrect = 0
        wrong_words = []

        for word in word_list:

            # 1) error_dict ก่อน
            if word in self.error_dict and self.error_dict[word]["count"] >= self.threshold:
                incorrect += 1
                wrong_words.append({
                    "word": word,
                    "suggestions": [self.error_dict[word]["correct"]],
                    "source": "error_dict"
                })
                continue

            # 2) อังกฤษ → ถือว่าถูก
            if self.is_english(word):
                correct += 1
                continue

            # 3) ไทย → อยู่ใน dict
            if word in self.thai_dict:
                correct += 1
                continue

            # 4) ใช้ spell + cache
            if word in self.spell_cache:
                suggestions = self.spell_cache[word]
            else:
                suggestions = spell(word, engine="symspell")
                self.spell_cache[word] = suggestions

            incorrect += 1
            wrong_words.append({
                "word": word,
                "suggestions": suggestions[:5],
                "source": "spell"
            })

        total = len(word_list)
        error_percent = (incorrect / total) * 100

        return {
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "error_percent": round(error_percent, 2),
            "wrong_words": wrong_words
        }

    def compare(self, text1, text2):
        token1 = tokenize(text1)
        token2 = tokenize(text2)
        cleaned1 = [w for w in token1 if w.strip() != ""]
        cleaned2 = [w for w in token2 if w.strip() != ""]
        result1 = self.check_spelling(cleaned1)
        result2 = self.check_spelling(cleaned2)

        if result1["error_percent"] > result2["error_percent"]:
            conclusion = "OCR Text has more errors"
            return result2
        elif result1["error_percent"] < result2["error_percent"]:
            conclusion = "Extracted Text has more errors"
            return result1
        else:
            conclusion = "Both texts have the same number of errors"
            return result1