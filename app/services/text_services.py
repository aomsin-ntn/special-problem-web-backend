# text_service.py
from app.services.spellchecker_services import SpellChecker

class TextService:
    def __init__(self):
        self.error_dict = {
            "ptthn": {"correct": "python", "count": 10},
            "pythn": {"correct": "python", "count": 15},
        }
        self.checker = SpellChecker(self.error_dict, threshold=10)

    def process(self, ocr_text, pdf_text):
        compare = self.checker.compare(ocr_text, pdf_text)
        choice = compare.get("choose")

        final_text = ocr_text if choice == "text1" else pdf_text
        fields = self.checker.extract_fields(final_text)

        return fields

