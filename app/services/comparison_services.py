import difflib
import deepcut

class ComparisonServices:
    def __init__(self, custom_dict=None):
        self.custom_dict = custom_dict if custom_dict else []

    def tokenize(self, text):
        if not text:
            return []
        return deepcut.tokenize(text.strip(), self.custom_dict)

    def compare_as_list(self, source_text, target_text):
        """
        เปรียบเทียบและคืนค่าเป็น list ของคู่คำที่ผิด (from -> to)
        """
        source_tokens = self.tokenize(source_text)
        target_tokens = self.tokenize(target_text)

        d = difflib.Differ()
        diff = list(d.compare(source_tokens, target_tokens))

        error_list = []
        i = 0
        while i < len(diff):
            item = diff[i]
            # ข้ามบรรทัด hint ของ difflib (บรรทัดที่ขึ้นด้วย ?)
            if item.startswith('?'):
                i += 1
                continue

            tag = item[0:2] # '+ ', '- ', '  '
            word = item[2:].strip()

            # กรณีมีการแก้ไข (Replace): เจอ - ตามด้วย + (หรือมี ? คั่นกลาง)
            if tag == '- ':
                next_idx = i + 1
                # ตรวจสอบบรรทัดถัดไป ข้ามบรรทัด '?' ถ้ามี
                if next_idx < len(diff) and diff[next_idx].startswith('?'):
                    next_idx += 1
                
                if next_idx < len(diff) and diff[next_idx].startswith('+ '):
                    # จับคู่เป็นคำผิด -> คำถูก
                    error_list.append({
                        "from": word,
                        "to": diff[next_idx][2:].strip()
                    })
                    i = next_idx + 1 # ข้ามไปตัวถัดจาก +
                else:
                    # กรณีหายไปเฉยๆ ไม่มีตัวมาแทน
                    error_list.append({
                        "from": word,
                        "to": None
                    })
                    i += 1
            
            # กรณีคำเกินมาเฉยๆ (Extra)
            elif tag == '+ ':
                error_list.append({
                    "from": None,
                    "to": word
                })
                i += 1
            else:
                # กรณีคำตรงกัน (Equal) ไม่ต้องเก็บลง list คู่คำผิด
                i += 1

        return error_list