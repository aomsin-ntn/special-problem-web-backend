import re
import cv2
import numpy as np
from pdf2image import convert_from_path
import easyocr

class OCREngine:

    def __init__(self, poppler_path: str | None = None):
        self.poppler_path = poppler_path
        self.reader = easyocr.Reader(["th", "en"], gpu=False)

    @staticmethod
    def joinText(ocr_result, sep=" ") -> str:
        texts = [text.strip() for (_, text, _) in ocr_result if text and text.strip()]
        return sep.join(texts)
    
    def preprocessOCR(self, img_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return th 

    def pdfToImage(self, file_path: str, page_num: int = 1) -> np.ndarray:
        pages = convert_from_path(
            file_path,
            dpi=300,
            first_page=page_num,
            last_page=page_num,
            poppler_path=self.poppler_path  
        )
        pil_img = pages[0]                
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    def extractFields(self, text: str) -> dict:
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

    def processDocumentOCR(self, file_path: str, page_num: int = 4) -> dict:
        img_bgr = self.pdfToImage(file_path,page_num)
        img_bin =  self.preprocessOCR(img_bgr)
        img_rgb = cv2.cvtColor(img_bin, cv2.COLOR_GRAY2RGB)
        ocr_result = self.reader.readtext(img_rgb)
        sentence = self.joinText(ocr_result, sep=" ")
        print(sentence)
        #fields = self.extractFields(sentence)
        return sentence