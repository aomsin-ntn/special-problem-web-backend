from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, select,or_, and_
from app.models.correction_dictionary import CorrectionDictionary
from app.models.custom_dictionary import CustomDictionary
from app.models.incorrect_word import IncorrectWord

class SpellRepository:

    @staticmethod
    async def get_error_dict(db: Session):
        result = db.exec(
            select(IncorrectWord,CorrectionDictionary)
            .join(CorrectionDictionary,IncorrectWord.word_dic_id == CorrectionDictionary.word_dic_id)
            .where(IncorrectWord.count >= 10 )
        ).all()
        return result
    
    @staticmethod
    async def get_custom_dict(db: Session):
        result = db.exec(
            select(CustomDictionary.cus_word)
        ).all()
        return result
    
    @staticmethod
    async def get_dictionary_report(db: Session, table_type: str, page: int, limit: int, sorted_by: str, order: str):

        query = None
        model = None

        # 1. เลือก Model ตาม Tab ที่กดมาจาก Frontend
        if table_type == "incorrect":
            model = IncorrectWord
            #  Join เอา incorrect_word ออกมาจากตาราง CorrectionDictionary ด้วย
            query = select(IncorrectWord, CorrectionDictionary.incorrect_word).join(
                CorrectionDictionary, IncorrectWord.word_dic_id == CorrectionDictionary.word_dic_id
            )
        elif table_type == "correction":
            model = CorrectionDictionary
            query = select(CorrectionDictionary)
        elif table_type == "custom":
            model = CustomDictionary
            query = select(CustomDictionary)
        else:
            return {"data": [], "metadata": {"total_items": 0, "total_pages": 1, "current_page": page, "per_page": limit}}

        # 2. จัดการเรื่อง Sorting
        if sorted_by:
            #  ดักเงื่อนไขกรณีที่สั่ง Sort ด้วยคอลัมน์ที่เรา Join มา (incorrect_word)
            if table_type == "incorrect" and sorted_by == "incorrect_word":
                column = CorrectionDictionary.incorrect_word
            else:
                column = getattr(model, sorted_by)
                
            order_by_clause = column.asc() if order == "asc" else column.desc()
            query = query.order_by(order_by_clause)
        else:
            if table_type == "custom":
                query = query.order_by(CustomDictionary.cus_word.asc())
            else:
                query = query.order_by(model.count.desc())

        # 3. จัดการเรื่อง Pagination
        total_items = db.exec(select(func.count()).select_from(query.subquery())).one()
        total_pages = (total_items + limit - 1) // limit

        paged_data = db.exec(query.offset((page - 1) * limit).limit(limit)).all()

        # 4. แปลงข้อมูลให้ส่งออกไปหน้าเว็บได้ถูกต้อง
        result_data = []
        for item in paged_data:
            if table_type == "incorrect":
                # สำหรับ incorrect มันจะคืนค่าเป็น tuple (IncorrectWord, incorrect_text)
                inc_word_obj, incorrect_text = item
                item_dict = inc_word_obj.model_dump()
                item_dict["incorrect_word"] = incorrect_text # ยัดคำผิดเข้าไปใน Dictionary
                result_data.append(item_dict)
            else:
                result_data.append(item.model_dump())

        return {
            "data": result_data,
            "metadata": {
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page,
                "per_page": limit
            }
        }
    
    @staticmethod
    async def get_correction_by_incorrect(db, incorrect):
        return db.exec(
            select(CorrectionDictionary).where(
                CorrectionDictionary.incorrect_word == incorrect
            )
        ).first()
    
    @staticmethod
    async def create_correction_no_commit(db: Session, incorrect: str, correct: str):
        correction = CorrectionDictionary(
            incorrect_word=incorrect,
            correct_word_list=[correct],
            count=1
        )
        db.add(correction)
        db.flush()
        return correction
    
    @staticmethod
    async def update_correction_no_commit(db: Session, correction: CorrectionDictionary, correct: str):
        correction.count += 1
        correction.updated_at = datetime.utcnow()

        current_list = correction.correct_word_list or []

        if correct not in current_list:
            new_list = list(current_list)
            new_list.append(correct)
            correction.correct_word_list = new_list

        db.add(correction)
        db.flush()
        return correction
    
    @staticmethod
    async def get_incorrect_word_record(db: Session, word_dic_id, correct: str):
        return db.exec(
            select(IncorrectWord).where(
                IncorrectWord.word_dic_id == word_dic_id,
                IncorrectWord.correct_word == correct
            )
        ).first()
    
    @staticmethod
    async def upsert_incorrect_word_no_commit(db: Session, word_dic_id, correct: str):
        record = await SpellRepository.get_incorrect_word_record(
            db=db,
            word_dic_id=word_dic_id,
            correct=correct
        )

        if record:
            record.count += 1
            db.add(record)
        else:
            record = IncorrectWord(
                word_dic_id=word_dic_id,
                correct_word=correct,
                count=1
            )
            db.add(record)

        db.flush()
        return record
    
    @staticmethod
    async def create_custom_word(db: Session, cus_word: str):
        custom_word = CustomDictionary(cus_word=cus_word)
        db.add(custom_word)
        db.flush()
        return custom_word