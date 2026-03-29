from pythainlp.spell import spell
from pythainlp.corpus.common import thai_words
from attacut import tokenize
import re
import difflib


class SpellChecker:
    def __init__(self, error_dict, threshold=10):
        self.error_dict = error_dict
        self.threshold = threshold
        self.thai_dict = set(thai_words())
        self.spell_cache = {}

        # 🔥 English dictionary (basic)
        self.eng_dict = set([
            "python", "system", "data", "model", "project", "student",
            "university", "technology", "application", "computer",
            "science", "engineering", "analysis", "learning"
        ])

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
            'คำสำคัญ': r'(?:คำสำคัญ:|คำสำคัญ)\s*(.*?)(?=\sหัวข้อ|\sTitle|$)'
        }
        results = {}
        for key, pat in pattern.items():
            m = re.search(pat, text, flags=re.DOTALL)
            if m:
                results[key] = m.group(1).strip()
        return results


    # -------------------------
    # language check
    # -------------------------
    def is_english(self, word):
        return re.match(r'^[a-zA-Z]+$', word) is not None

    def is_symbol(self, word):
        return re.match(r'^[^a-zA-Z0-9\u0E00-\u0E7F]+$', word) is not None

    # -------------------------
    # English spell check
    # -------------------------
    def check_english(self, word):
        word_lower = word.lower()

        if word_lower in self.eng_dict:
            return True, []

        suggestions = difflib.get_close_matches(word_lower, self.eng_dict, n=3, cutoff=0.8)

        if suggestions:
            return False, suggestions

        return True, []

    # -------------------------
    # main
    # -------------------------
    def check_spelling(self, word_list):
        correct = 0
        incorrect = 0
        wrong_words = []

        for word in word_list:
            word = word.strip()

            if not word:
                continue

            # 🔥 0) symbol → ข้าม
            if self.is_symbol(word):
                correct += 1
                continue

            # 🔥 0.1) ตัวเลขล้วน → ข้าม
            if word.isdigit():
                correct += 1
                continue

            # 1) error_dict
            if word in self.error_dict and self.error_dict[word]["count"] >= self.threshold:
                incorrect += 1
                wrong_words.append({
                    "word": word,
                    "suggestions": [self.error_dict[word]["correct"]],
                    "source": "error_dict"
                })
                continue

            # 2) English check
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

            # 3) ไทย dict
            if word in self.thai_dict:
                correct += 1
                continue

            # 4) spell ไทย
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

    # -------------------------
    # compare
    # -------------------------
    def compare(self, text1, text2):
        token1 = tokenize(text1)
        token2 = tokenize(text2)

        cleaned1 = [w for w in token1 if w.strip()]
        cleaned2 = [w for w in token2 if w.strip()]

        result1 = self.check_spelling(cleaned1)
        result2 = self.check_spelling(cleaned2)

        if result1["error_percent"] > result2["error_percent"]:
            return {"better": "text2", "result": result2}
        elif result1["error_percent"] < result2["error_percent"]:
            return {"better": "text1", "result": result1}
        else:
            return {"better": "equal", "result": result1}