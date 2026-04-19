import re

class ExtractServices:
    # 1. STOP_ALL: กำแพงกั้นที่ฉลาดขึ้น จะหยุดเมื่อเจอ "หัวข้อ" จริงๆ เท่านั้น
    # ใช้ Lookahead เพื่อตรวจสอบว่าต้องตามด้วย : หรือช่องว่างถึงจะนับเป็นจุดสิ้นสุด
    STOP_ALL = r'(?:\bชื่อนักศึกษา\b[:\s]|\bชื่อผู้จัดทำ\b[:\s]|\bผู้จัดทำ\b[:\s]|Students?[:\s]|ปริญญา|ภาค.{0,2}วิชา|คณะ|คญะ|มหาวิทยาลัย|มหาวิท.*ลัย|ปีการศึกษา|อาจารย์|บทคัดย่อ|คำสำคัญ|Degree|Department|Faculty|School|University|Academic|Advisor|Abstr?act|Abstact|Keywords?|Keywors|Title\b|title\b|\||$)'

    TH_PATTERNS = {
        "title_th": r'(?:หัวข้อ.{0,3}(?:โครงงาน|ปัญหา|สหกิจ).{0,3}พิเศษ|หัวข้อ|เรื่อง|โครงการสหกิจศึกษา|สหกิจศึกษา|โครงการ)[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "degree_th": r'ปริญญา[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "department_th": r'ภาควิชา[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "faculty_th": r'(?:คณะ|คญะ)[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "university_th": r'(?:มหาวิทยาลัย|มหาวิท.*ลัย)[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "year_th": r'ปีการศึกษา[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "advisor_th": r'(?:อาจารย์.{0,2}ที่ปรึกษา|คณะกรรมการ.{0,2}ที่ปรึกษา)[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "abstract_th": r'บทคัดย่อ[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "keywords_th": r'คำสำคัญ[:\s]*(.*?)(?=' + STOP_ALL + ')'
    }

    EN_PATTERNS = {
        "title_en": r'(?:Title|title)[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "degree_en": r'Degree[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "department_en": r'Department[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "faculty_en": r'(?:Faculty|School)[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "university_en": r'University[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "year_en": r'(?:Academic\s*Year|AcademicYear)[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "advisor_en": r'Advisor[:\s]*(.*?)(?=\bAbstr?act\b|\bAbstact\b|' + STOP_ALL + ')',
        "abstract_en": r'(?:Abstr?act|Abstact)[:\s]*(.*?)(?=' + STOP_ALL + ')',
        "keywords_en": r'(?:Keywords?|Keywors)[:\s]*(.*?)(?=' + STOP_ALL + ')'
    }

    @staticmethod
    def _normalize_id(raw_id):
        """แก้ไขความผิดพลาดของ OCR ในรหัสนักศึกษา (O -> 0, I/l -> 1)"""
        if not raw_id: return ""
        s = raw_id.upper().replace(' ', '')
        s = s.replace('O', '0').replace('I', '1').replace('L', '1')
        return re.sub(r'\D', '', s)

    @staticmethod
    def _clean_text(text, is_title=False):
        if not text or not text.strip(): return None
        
        # ลบขยะ OCR เบื้องต้น
        text = re.sub(r'[\[\]\{\}\|\\/]', '', text)
        
        if is_title:
            # 1. ลบคำนำหน้าที่เป็นหัวข้อ (ฝั่งไทย)
            text = re.sub(r'^(?:โครงการสหกิจศึกษา|สหกิจศึกษา|โครงการ|เรื่อง|หัวข้อ)[:\s]*', '', text, flags=re.IGNORECASE).strip()
            
            # 2. ป้องกันกรณีชื่อเรื่องมีคำว่า "นักศึกษา" หรือ "Student" ปนมาท้ายประโยค
            # จะตัดทิ้งเฉพาะเมื่อคำเหล่านี้อยู่ติดกับรหัสตัวเลข หรืออยู่ท้ายสตริงจริงๆ เท่านั้น
            text = re.sub(r'\s+(?:student\s*id|student\s*d|รหัสนักศึกษา|รหัส)\s*[:\d].*$', '', text, flags=re.IGNORECASE).strip()
            text = re.sub(r'^[:\s]+', '', text).strip()

        cleaned = re.sub(r'\s{2,}', ' ', text).strip()
        return cleaned if cleaned else None

    @staticmethod
    def extract_students(text: str):
        # ดึงข้อมูลไทยโดยใช้ Pattern: "คำนำหน้า + ชื่อ + รหัส" เพื่อความแม่นยำสูงสุด
        th_data = re.findall(r'(นาย|นางสาว|นาง)\s*([ก-๙\sฺ]{2,50})\s*(?:\D{0,10})?(\d[O0-9Il\s]{7,12})', text)
        
        en_map = {}
        # ดึงชื่ออังกฤษที่อยู่หน้ารหัส (รหัสช่วยระบุตัวตนเพื่อนำไปแมตช์กับชื่อไทย)
        en_candidates = re.findall(r'(?:miss\.?|mr\.?|mrs\.?|miss|mr|mrs)?\s*([a-z\s\.]{5,50})\s*(?:\bstudents?\b\s*)?(\d[O0-9Il\s]{7,12})', text, re.IGNORECASE)
        
        for name, rid in en_candidates:
            clean_id = ExtractServices._normalize_id(rid)
            if not clean_id: continue
            
            # คลีนชื่ออังกฤษ (ตัดคำขยะ เช่น university, title ที่อาจไหลมาแปะหน้าชื่อ)
            clean_name = re.sub(r'(?:title|students?|id|student\s*d|university|faculty|department)[:\s]*', '', name, flags=re.IGNORECASE).strip()
            if len(clean_name.split()) >= 2:
                en_map[clean_id] = clean_name

        if not th_data: return []

        return [
            {
                "student_id": ExtractServices._normalize_id(rid),
                "student_name_th": ExtractServices._clean_text(f"{p}{n.strip()}"),
                "student_name_en": en_map.get(ExtractServices._normalize_id(rid), None)
            } for p, n, rid in th_data
        ]

    @staticmethod
    def extract_advisors(text: str):
        th_m = re.search(r'(?:อาจารย์ที่ปรึกษา|คณะกรรมการที่ปรึกษา)[:\s]*(.*?)(?=' + ExtractServices.STOP_ALL + ')', text, re.DOTALL | re.IGNORECASE)
        en_m = re.search(r'Advisor[:\s]*(.*?)(?=\bAbstr?act\b|\bAbstact\b|' + ExtractServices.STOP_ALL + ')', text, re.DOTALL | re.IGNORECASE)
        
        # ป้องกัน NoneType Error โดยการเช็ค match ก่อนเรียก .group()
        th_val = th_m.group(1).strip() if th_m else ""
        en_val = en_m.group(1).strip() if en_m else ""
        
        th_l = [n.strip() for n in re.split(r'\n|,', th_val) if n.strip()]
        en_l = [n.strip() for n in re.split(r'\n|,', en_val) if n.strip()]
        
        advisors = []
        for i in range(max(len(th_l), len(en_l))):
            advisors.append({
                "advisor_name_th": ExtractServices._clean_text(th_l[i] if i < len(th_l) else None),
                "advisor_name_en": ExtractServices._clean_text(en_l[i] if i < len(en_l) else None)
            })
        return advisors

    @staticmethod
    def extract_fields(text: str):
        # 1. ดึงข้อมูลส่วนที่ใช้ Logic เฉพาะ (Student และ Advisor)
        results = {
            "students": ExtractServices.extract_students(text),
            "advisors": ExtractServices.extract_advisors(text)
        }
        
        # 2. รวม Pattern ทั้งหมด (TH และ EN) เพื่อวนลูปดึงข้อมูลฟิลด์ทั่วไป
        all_patterns = {**ExtractServices.TH_PATTERNS, **ExtractServices.EN_PATTERNS}
        
        for field, pattern in all_patterns.items():
            # ข้ามฟิลด์ที่จัดการไปแล้วในข้อ 1
            if "student" in field or "advisor" in field: 
                continue
            
            # ใช้ Regex ค้นหาข้อมูลตาม Pattern
            match = re.search(pattern, text, re.IGNORECASE | re.UNICODE | re.DOTALL)
            
            if match:
                try:
                    val = match.group(1).strip()
                    
                    # --- ส่วนจัดการ Keyword (รองรับ , ; \n และ เว้นวรรค) ---
                    if "keywords" in field:
                        # แยกด้วยสัญลักษณ์มาตรฐานก่อน
                        raw_items = re.split(r'[,;\n]', val)
                        
                        final_keywords = []
                        for item in raw_items:
                            # ถ้าก้อนที่แยกออกมา มีเว้นวรรคภายใน (กรณีภาษาไทยใช้เว้นวรรคแทนคอมม่า)
                            # เราจะเช็คว่าเป็นภาษาไทยที่มีเว้นวรรคหรือไม่
                            # \u0E00-\u0E7F คือช่วงตัวอักษรไทย
                            if re.search(r'[\u0E00-\u0E7F]', item) and ' ' in item.strip():
                                # แยกย่อยด้วยเว้นวรรค (ตั้งแต่ 1 ช่องขึ้นไป)
                                sub_items = re.split(r'\s+', item.strip())
                                for sub in sub_items:
                                    if sub.strip():
                                        final_keywords.append(ExtractServices._clean_text(sub))
                            else:
                                # ถ้าเป็นภาษาอังกฤษหรือไม่มีเว้นวรรค ให้คลีนและใส่ลงไปเลย
                                if item.strip():
                                    final_keywords.append(ExtractServices._clean_text(item))
                        
                        results[field] = final_keywords
                    # --------------------------------------------------
                    
                    else:
                        # ฟิลด์ทั่วไป (Title, Abstract, etc.)
                        results[field] = ExtractServices._clean_text(val, is_title="title" in field)
                
                except (AttributeError, IndexError):
                    results[field] = [] if "keywords" in field else None
            else:
                # กรณีไม่เจอ Match
                results[field] = [] if "keywords" in field else None
        
        return results