import re

class ExtractServices:
    # 1. STOP_GENERAL: กำแพงกั้นแบบ Simple ตัดเครื่องหมายซับซ้อนออกเพื่อความเสถียร
    # ลบพวก .* หรือเงื่อนไขที่ซ้อนกันเยอะๆ ออก เพื่อป้องกัน Regex Error
    SECTION_PREFIX = r'(?:^|\n|\||\s{2,})\s*'
    
    PAGE_THEN_NEW_SECTION = (
        r'\n\s*---PAGE---\s*\n'
        r'(?:[ก-ฮa-zA-Z]\s*\n)?'
        r'\s*(?:'
        r'หัวข้อ\s*(?:โครงงาน|ปัญหา|สหกิจ)พิเศษ|หัวข้อ|เรื่อง|'
        r'ชื่อนักศึกษา|ชื่อผู้จัดทำ|ผู้จัดทำ|เสนอโดย|'
        r'ปริญญา|ภาควิชา|คณะ|มหาวิทยาลัย|มหาวิทลัย|ปีการศึกษา|'
        r'อาจารย์(?:.{0,2}ที่ปรึกษา)?|บทคัดย่อ|คำสำคัญ|'
        r'Title|Students?|Degree|Department|Faculty|School|University|'
        r'Academic\s*Year|Advisor|Abstr?act|Abstact|Keywords?|Keywors'
        r')'
        r'\s*[:：]?'
    )

    PAGE_THEN_KEYWORDS_TH = (
        r'\n\s*---PAGE---\s*\n'
        r'(?:[ก-ฮa-zA-Z]\s*\n)?'
        r'\s*คำสำคัญ\s*[:：]?'
    )

    PAGE_THEN_KEYWORDS_EN = (
        r'\n\s*---PAGE---\s*\n'
        r'(?:[ก-ฮa-zA-Z]\s*\n)?'
        r'\s*(?:Keywords?|Keywors)\s*[:：]?'
    )
    
    STOP_METADATA = (
        r'(?='
        + PAGE_THEN_NEW_SECTION +
        r'|'
        + SECTION_PREFIX +
        r'(?:'
        r'หัวข้อ\s*(?:โครงงาน|ปัญหา|สหกิจ)พิเศษ|หัวข้อ|เรื่อง|'
        r'ชื่อนักศึกษา|ชื่อผู้จัดทำ|ผู้จัดทำ|เสนอโดย|'
        r'ปริญญา|ภาควิชา|คณะ|มหาวิทยาลัย|มหาวิทลัย|ปีการศึกษา|'
        r'อาจารย์(?:.{0,2}ที่ปรึกษา)?|บทคัดย่อ|คำสำคัญ|'
        r'Title|Students?|Degree|Department|Faculty|School|University|'
        r'Academic\s*Year|Advisor|Abstr?act|Abstact|Keywords?|Keywors'
        r')'
        r'\s*[:：]?'
        r'|$)'
    )

    STOP_TITLE = (
        r'(?='
        + SECTION_PREFIX +
        r'(?:ชื่อนักศึกษา|ชื่อผู้จัดทำ|ผู้จัดทำ|เสนอโดย|Students?)'
        r'\s*[:：]?'
        r'|$)'
    )

    STOP_ABSTRACT_TH = (
        r'(?='
        + PAGE_THEN_KEYWORDS_TH +
        r'|'
        + SECTION_PREFIX +
        r'คำสำคัญ\s*[:：]?'
        r'|$)'
    )


    STOP_ABSTRACT_EN = (
        r'(?='
        + PAGE_THEN_KEYWORDS_EN +
        r'|'
        + SECTION_PREFIX +
        r'(?:Keywords?|Keywors)\s*[:：]?'
        r'|$)'
    )




    TH_PATTERNS = {
        "title_th": SECTION_PREFIX + r'(?:หัวข้อ\s*(?:โครงงาน|ปัญหา|สหกิจ)พิเศษ|หัวข้อ|เรื่อง|โครงการสหกิจศึกษา|สหกิจศึกษา|โครงการ)\s*[:：]?\s*(.*?)' + STOP_TITLE,
        "degree_th": SECTION_PREFIX + r'ปริญญา\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "department_th": SECTION_PREFIX + r'ภาควิชา\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "faculty_th": SECTION_PREFIX + r'(?:คณะ|คญะ)\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "university_th": SECTION_PREFIX + r'(?:มหาวิทยาลัย|มหาวิทลัย)\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "year_th": SECTION_PREFIX + r'ปีการศึกษา\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "advisor_th": SECTION_PREFIX + r'(?:อาจารย์.{0,2}ที่ปรึกษา|คณะกรรมการ.{0,2}ที่ปรึกษา)\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "abstract_th": SECTION_PREFIX + r'บทคัดย่อ\s*[:：]?\s*(.*?)' + STOP_ABSTRACT_TH,
        "keywords_th": SECTION_PREFIX + r'คำสำคัญ\s*[:：]?\s*(.*?)' + STOP_METADATA,
    }

    EN_PATTERNS = {
        "title_en": SECTION_PREFIX + r'Title\s*[:：]?\s*(.*?)' + STOP_TITLE,
        "degree_en": SECTION_PREFIX + r'Degree\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "department_en": SECTION_PREFIX + r'Department\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "faculty_en": SECTION_PREFIX + r'(?:Faculty|School)\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "university_en": SECTION_PREFIX + r'University\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "year_en": SECTION_PREFIX + r'(?:Academic\s*Year|AcademicYear)\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "advisor_en": SECTION_PREFIX + r'Advisor\s*[:：]?\s*(.*?)' + STOP_METADATA,
        "abstract_en": SECTION_PREFIX + r'(?:Abstract|Abstact)\s*[:：]?\s*(.*?)' + STOP_ABSTRACT_EN,
        "keywords_en": SECTION_PREFIX + r'(?:Keywords?|Keywors)\s*[:：]?\s*(.*?)' + STOP_METADATA,
    }

    @staticmethod
    def _normalize_id(raw_id):
        """แก้ไขความผิดพลาดของ OCR ในรหัสนักศึกษา (O -> 0, I/l -> 1)"""
        if not raw_id: return ""
        s = raw_id.upper().replace(' ', '')
        s = s.replace('O', '0').replace('I', '1').replace('L', '1')
        return re.sub(r'\D', '', s)

    @staticmethod
    def _clean_text(text, is_title=False, remove_id_labels=False):
        if not text or not text.strip():
            return None

        # ลบขยะ OCR เบื้องต้น
        text = re.sub(r'[\[\]\{\}\|\\/]', '', str(text))

        # ใช้เฉพาะตอน clean ชื่อคน / student เท่านั้น
        if remove_id_labels:
            text = re.sub(
                r'\s+(?:student\s*id|student\s*d|รหัสนักศึกษา|รหัส).*$', 
                '', 
                text, 
                flags=re.IGNORECASE
            ).strip()

            junk_labels = r'\s*(?:รหัสนักศึกษา|รหัส|student\s*id|student\s*d|id)\b'
            text = re.sub(junk_labels, '', text, flags=re.IGNORECASE).strip()

        if is_title:
            text = re.sub(
                r'^(?:โครงการสหกิจศึกษา|สหกิจศึกษา|โครงการ|เรื่อง|หัวข้อ)[:\s]*',
                '',
                text,
                flags=re.IGNORECASE
            ).strip()

            # ใช้เฉพาะ title ได้ แต่ไม่ควรลบคำว่า Student เฉย ๆ
            text = re.sub(
                r'\s+(?:student\s*id|รหัสนักศึกษา|รหัส)\s*[:\d].*$',
                '',
                text,
                flags=re.IGNORECASE
            ).strip()

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
            name_th = ExtractServices._clean_text(
                f"{prefix}{name.strip()}",
                remove_id_labels=True
            )
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
            name_en = ExtractServices._clean_text(
                name,
                remove_id_labels=True
            )

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
        th_m = re.search(
            r'(?:อาจารย์ที่ปรึกษา|คณะกรรมการที่ปรึกษา)\s*[:：]?\s*(.*?)' + ExtractServices.STOP_METADATA,
            text,
            re.DOTALL | re.IGNORECASE
        )
        en_m = re.search(
            r'Advisor\s*[:：]?\s*(.*?)' + ExtractServices.STOP_METADATA,
            text,
            re.DOTALL | re.IGNORECASE
        )
        
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
                    if "abstract" in field:
                        val = ExtractServices._clean_paragraph_text(val)

                    elif "title" in field:
                        val = re.sub(r'[\x00-\x1F\x7F]', ' ', val)
                        val = val.replace('|', ' ')
                        val = re.sub(r'\s+', ' ', val).strip()

                    if "keywords" in field:
                        results[field] = ExtractServices._split_keywords(val)
                        print(f"Done (Found {len(results[field])})")

                    elif "abstract" in field:
                        results[field] = val
                        print("Done")

                    else:
                        results[field] = ExtractServices._clean_text(
                            val,
                            is_title="title" in field
                        )
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
    
    @staticmethod
    def _split_keywords(value):
        if not value:
            return []

        value = str(value).strip()

        # อนุญาตให้ keyword ข้ามหน้าได้ โดยเปลี่ยน page marker เป็น newline
        value = re.sub(r'\n\s*---PAGE---\s*\n', '\n', value)

        value = value.replace("|", "\n")

        value = re.sub(
            r'^(?:คำสำคัญ|Keywords?|Keywors)\s*[:：]?\s*',
            '',
            value,
            flags=re.IGNORECASE
        ).strip()

        if re.search(r'[,;，、]', value):
            raw_items = re.split(r'[,;，、]', value)
        elif "\n" in value:
            raw_items = re.split(r'\n+', value)
        elif re.search(r'\s{2,}', value):
            raw_items = re.split(r'\s{2,}', value)
        else:
            raw_items = [value]

        final_keywords = []

        for item in raw_items:
            cleaned = ExtractServices._clean_text(item)
            if cleaned:
                final_keywords.append(cleaned)

        return list(dict.fromkeys(final_keywords))
    
    @staticmethod
    def _clean_paragraph_text(text: str) -> str | None:
        if not text or not str(text).strip():
            return None

        text = str(text)

        # ลบ control chars แต่เก็บ newline ไว้ก่อน
        text = text.replace("ฺ", "")
        text = text.replace("|", "\n")
        text = text.replace("\\", " ")
        text = re.sub(r"[\r\t]+", " ", text)

        # clean ทีละบรรทัด
        lines = []
        for line in text.split("\n"):
            line = re.sub(r"[ ]+", " ", line).strip()
            if line:
                lines.append(line)

        if not lines:
            return None

        merged = []

        for line in lines:
            if not merged:
                merged.append(line)
                continue

            prev = merged[-1]

            prev_last = prev[-1] if prev else ""
            line_first = line[0] if line else ""

            # ถ้าบรรทัดก่อนหน้าลงท้ายไทย และบรรทัดใหม่ขึ้นต้นไทย
            # ส่วนใหญ่คือ OCR/PDF ตัดบรรทัดกลางประโยค → ต่อแบบไม่เว้นวรรค
            if re.match(r"[ก-๙]", prev_last) and re.match(r"[ก-๙]", line_first):
                merged[-1] = prev + line

            # อังกฤษ/ตัวเลข/วงเล็บ ควรเว้นวรรค
            else:
                merged[-1] = prev + " " + line

        result = " ".join(merged)

        # จัดช่องว่างรอบ punctuation
        result = re.sub(r"\s+([,.;:!?])", r"\1", result)
        result = re.sub(r"\(\s+", "(", result)
        result = re.sub(r"\s+\)", ")", result)
        result = re.sub(r"\s{2,}", " ", result).strip()

        return result if result else None