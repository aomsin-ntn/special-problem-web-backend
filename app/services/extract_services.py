import re

class ExtractServices:
    # 1. STOP_GENERAL: กำแพงกั้นแบบ Simple ตัดเครื่องหมายซับซ้อนออกเพื่อความเสถียร
    # ลบพวก .* หรือเงื่อนไขที่ซ้อนกันเยอะๆ ออก เพื่อป้องกัน Regex Error
    STOP_GENERAL = r'(?:ชื่อนักศึกษา|ชื่อผู้จัดทำ|ผู้จัดทำ|Students?|ปริญญา|ภาควิชา|คณะ|มหาวิทยาลัย|มหาวิทลัย|ปีการศึกษา|อาจารย์|บทคัดย่อ|คำสำคัญ|Degree|Department|Faculty|School|University|Academic|Advisor|Abstr?act|Keywords?|Title|\||$)'

    STOP_TITLE = r'(?:ชื่อนักศึกษา|ชื่อผู้จัดทำ|ผู้จัดทำ|Students?|เสนอโดย|\||$)'

    STOP_ABSTRACT = r'(?:คำสำคัญ|Keywords?|Keywors|\||$)'

    TH_PATTERNS = {
        "title_th": r'(?:หัวข้อ\s*(?:โครงงาน|ปัญหา|สหกิจ)พิเศษ|หัวข้อ|เรื่อง|โครงการสหกิจศึกษา|สหกิจศึกษา|โครงการ)[:\s]*(.*?)(?=' + STOP_TITLE + ')',
        "degree_th": r'ปริญญา[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "department_th": r'ภาควิชา[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "faculty_th": r'(?:คณะ|คญะ)[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "university_th": r'(?:มหาวิทยาลัย|มหาวิทลัย)[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "year_th": r'ปีการศึกษา[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "advisor_th": r'(?:อาจารย์.{0,2}ที่ปรึกษา|คณะกรรมการ.{0,2}ที่ปรึกษา)[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "abstract_th": r'บทคัดย่อ[:\s]*(.*?)(?=' + STOP_ABSTRACT + ')',
        "keywords_th": r'คำสำคัญ[:\s]*(.*?)(?=' + STOP_GENERAL + ')'
    }

    EN_PATTERNS = {
        "title_en": r'(?:Title|title)[:\s]*(.*?)(?=' + STOP_TITLE + ')',
        "degree_en": r'Degree[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "department_en": r'Department[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "faculty_en": r'(?:Faculty|School)[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "university_en": r'University[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "year_en": r'(?:Academic\s*Year|AcademicYear)[:\s]*(.*?)(?=' + STOP_GENERAL + ')',
        "advisor_en": r'Advisor[:\s]*(.*?)(?=\bAbstr?act\b|\bAbstact\b|' + STOP_GENERAL + ')',
        "abstract_en": r'(?:Abstr?act|Abstact)[:\s]*(.*?)(?=' + STOP_ABSTRACT + ')',
        "keywords_en": r'(?:Keywords?|Keywors)[:\s]*(.*?)(?=' + STOP_GENERAL + ')'
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

        text = re.sub(r'\s+(?:student\s*id|student\s*d|รหัสนักศึกษา|รหัส).*$', '', text, flags=re.IGNORECASE).strip()
        
        # ลบคำขยะท้ายชื่อคน
        junk_labels = r'\s*(?:รหัสนักศึกษา|รหัส|student\s*id|student\s*d|student|id|students)\b'
        text = re.sub(junk_labels, '', text, flags=re.IGNORECASE).strip()

        if is_title:
            text = re.sub(r'^(?:โครงการสหกิจศึกษา|สหกิจศึกษา|โครงการ|เรื่อง|หัวข้อ)[:\s]*', '', text, flags=re.IGNORECASE).strip()
            text = re.sub(r'\s+(?:student\s*id|student\s*id|รหัสนักศึกษา|รหัส)\s*[:\d].*$', '', text, flags=re.IGNORECASE).strip()
            text = re.sub(r'^[:\s]+', '', text).strip()

        cleaned = re.sub(r'\s{2,}', ' ', text).strip()
        return cleaned if cleaned else None
    
    @staticmethod
    def extract_students(text: str):
        print("------------Debugging Student Extraction (FIXED)------------")

        # -----------------------------
        # 1. Thai students
        # -----------------------------
        th_pattern = r'(นาย|นางสาว|นาง)\s*([ก-๙\sฺ]{2,80})\s*(?:รหัสนักศึกษา|รหัส)?\s*[:\-\s]*(\d[O0-9Il\s]{7,12})'
        th_matches = list(re.finditer(th_pattern, text, re.IGNORECASE))

        th_data = []
        for m in th_matches:
            prefix, name, rid = m.groups()
            sid = ExtractServices._normalize_id(rid)
            name_th = ExtractServices._clean_text(f"{prefix}{name.strip()}")
            th_data.append({
                "student_id": sid,
                "student_name_th": name_th
            })

        # -----------------------------
        # 2. English students (NEW FIX)
        # -----------------------------
        en_pattern = r'(mr\.?|miss\.?|mrs\.?)?\s*([a-z]+\s+[a-z]+)\s*(?:student\s*\|?d|student\s*id|id)?\s*[:\-\s]*(\d[O0-9Il\s]{7,12})'
        en_matches = re.findall(en_pattern, text, re.IGNORECASE)

        en_map = {}

        for prefix, name, rid in en_matches:
            sid = ExtractServices._normalize_id(rid)
            name_en = ExtractServices._clean_text(name)

            if name_en:
                name_en = name_en.title()  # ทำให้เป็น Proper Case
                en_map[sid] = name_en
                print(f"[EN MAP] {sid} => {name_en}")

        # -----------------------------
        # 3. Merge
        # -----------------------------
        results = []

        th_map = {item["student_id"]: item for item in th_data}
        all_ids = set(th_map.keys()) | set(en_map.keys())

        for sid in all_ids:
            th_item = th_map.get(sid, {})
            results.append({
                "student_id": sid,
                "student_name_th": th_item.get("student_name_th"),
                "student_name_en": en_map.get(sid)
            })

            print(f"[FINAL] SID={sid} | TH={th_item.get('student_name_th')} | EN={en_map.get(sid)}")

        return results

    @staticmethod
    def extract_advisors(text: str):
        print("------------Debugging Advisor Extraction------------")
        th_m = re.search(r'(?:อาจารย์ที่ปรึกษา|คณะกรรมการที่ปรึกษา)[:\s]*(.*?)(?=' + ExtractServices.STOP_GENERAL + ')', text, re.DOTALL | re.IGNORECASE)
        en_m = re.search(r'Advisor[:\s]*(.*?)(?=\bAbstr?act\b|\bAbstact\b|' + ExtractServices.STOP_GENERAL + ')', text, re.DOTALL | re.IGNORECASE)
        
        th_val = th_m.group(1).strip() if th_m else ""
        en_val = en_m.group(1).strip() if en_m else ""
        
        th_l = [n.strip() for n in re.split(r'\n|,', th_val) if n.strip()]
        en_l = [n.strip() for n in re.split(r'\n|,', en_val) if n.strip()]
        
        advisors = []
        for i in range(max(len(th_l), len(en_l))):
            name_th = ExtractServices._clean_text(th_l[i] if i < len(th_l) else None)
            name_en = ExtractServices._clean_text(en_l[i] if i < len(en_l) else None)
            print(f"  [Advisor] Match: {name_th} / {name_en}")
            advisors.append({
                "advisor_name_th": name_th,
                "advisor_name_en": name_en
            })
        return advisors

    @staticmethod
    def extract_fields(text: str):
        print("----------START GLOBAL EXTRACTION----------")
        results = {
            "students": ExtractServices.extract_students(text),
            "advisors": ExtractServices.extract_advisors(text)
        }
        
        all_patterns = {**ExtractServices.TH_PATTERNS, **ExtractServices.EN_PATTERNS}
        
        # 1. วนลูปดึงข้อมูลจาก Regex Patterns ทั้งหมด
        for field, pattern in all_patterns.items():
            if "student" in field or "advisor" in field: 
                continue
            
            print(f"Processing: {field}...", end=" ")
            try:
                # ใช้ DOTALL เพื่อให้ดึงข้อมูลข้ามบรรทัดได้
                match = re.search(pattern, text, re.IGNORECASE | re.UNICODE | re.DOTALL)
                
                if match:
                    val = match.group(1)

                    # 🔥 CLEAN OCR (เฉพาะ title + abstract)
                    if "title" in field or "abstract" in field:
                        val = re.sub(r'[\x00-\x1F\x7F]', ' ', val)
                        val = val.replace('|', ' ')
                        val = re.sub(r'\s+', ' ', val).strip()

                    if "keywords" in field:
                        val_cleaned = re.sub(r'\n', ' ', val)
                        raw_items = re.split(r'[,;]', val_cleaned)
                        final_keywords = []

                        for item in raw_items:
                            item = item.strip()
                            if not item:
                                continue

                            if re.search(r'[\u0E00-\u0E7F]', item) and ' ' in item:
                                sub_items = re.split(r'\s{2,}', item)
                                if len(sub_items) == 1:
                                    sub_items = re.split(r'\s+', item)

                                for sub in sub_items:
                                    cleaned_sub = ExtractServices._clean_text(sub)
                                    if cleaned_sub:
                                        final_keywords.append(cleaned_sub)
                            else:
                                cleaned_item = ExtractServices._clean_text(item)
                                if cleaned_item:
                                    final_keywords.append(cleaned_item)

                        results[field] = list(dict.fromkeys(final_keywords))
                        print(f"Done (Found {len(results[field])})")

                    else:
                        results[field] = ExtractServices._clean_text(val, is_title="title" in field)
                        print("Done")
            except re.error as e:
                print(f"REGEX ERROR: {e.msg}")
                results[field] = None

        # 2. --- Logic พิเศษ: เติมปีการศึกษาอัตโนมัติ (BE <-> CE Auto-fill) ---
        def extract_digit(raw_text):
            if not raw_text: return None
            # ดึงตัวเลข 4 หลักตัวแรกที่เจอ
            digit_match = re.search(r'(\d{4})', str(raw_text))
            return int(digit_match.group(1)) if digit_match else None

        year_be_val = extract_digit(results.get("year_th"))
        year_ce_val = extract_digit(results.get("year_en"))

        # Case A: มีแต่ พ.ศ. (TH) -> เติม ค.ศ. (EN)
        if year_be_val and not year_ce_val:
            if 2400 < year_be_val < 2700:
                results["year_en"] = str(year_be_val - 543)
                print(f"  [Auto-fill] Generated year_en from BE: {results['year_en']}")

        # Case B: มีแต่ ค.ศ. (EN) -> เติม พ.ศ. (TH)
        elif year_ce_val and not year_be_val:
            if 1900 < year_ce_val < 2200:
                results["year_th"] = str(year_ce_val + 543)
        
        # Case C: ตรวจสอบความถูกต้องกรณีได้มาทั้งคู่แต่เลขเหมือนกัน (OCR อาจอ่านชื่อหัวข้อผิด)
        elif year_be_val and year_ce_val:
            if year_be_val == year_ce_val and year_be_val > 2400:
                results["year_en"] = str(year_be_val - 543)
                print(f"  [Auto-fill] Corrected year_en: {year_be_val} -> {results['year_en']}")

        results["academic_year_be"] = results.pop("year_th", None)
        results["academic_year_ce"] = results.pop("year_en", None)

        print("----------EXTRACTION COMPLETED----------")
        return results