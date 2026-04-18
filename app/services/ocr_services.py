from app.core.ocr_engine import OCREngine

class OCRServices:
    def __init__(self, poppler_path):
        self.engine = OCREngine(poppler_path=poppler_path)

    def extract(self, path, page):
        ocr_text = self.engine.process_document_ocr(path, page_num=page)
        pdf_text = self.engine.pdf_to_text(path, page_num=page)
        return ocr_text, pdf_text

    def get_thumbnail(self, path):
        return self.engine.pdf_to_image(path, page_num=1)