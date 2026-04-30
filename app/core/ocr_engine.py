from email.mime import text
import re
from annotated_types import doc
import cv2
import numpy as np
from pdf2image import convert_from_path
import easyocr
import pymupdf

_shared_reader = easyocr.Reader(["th", "en"], gpu=False)

class OCREngine:
    def __init__(self, poppler_path: str | None = None):
        self.poppler_path = poppler_path
        self.reader = _shared_reader

    @staticmethod
    def join_text(ocr_result, sep=" ") -> str:
        texts = [text.strip() for (_, text, _) in ocr_result if text and text.strip()]
        return sep.join(texts)

    @staticmethod
    def join_text_by_lines(ocr_result, y_threshold=None) -> str:
        """
        รวมผล OCR โดยรักษาโครงสร้างบรรทัด
        แทนที่จะรวมทุกคำเป็นบรรทัดเดียว
        """
        if not ocr_result:
            return ""

        items = []

        heights = []
        for bbox, text, conf in ocr_result:
            if not text or not text.strip():
                continue

            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]

            x_min = min(xs)
            y_center = sum(ys) / 4
            height = max(ys) - min(ys)

            heights.append(height)
            items.append({
                "x": x_min,
                "y": y_center,
                "text": text.strip(),
                "conf": conf,
                "height": height
            })

        if not items:
            return ""

        if y_threshold is None:
            avg_height = np.mean(heights) if heights else 20
            y_threshold = max(10, avg_height * 0.6)

        # sort บนลงล่าง
        items.sort(key=lambda item: item["y"])

        lines = []
        current_line = []
        current_y = None

        for item in items:
            if current_y is None:
                current_line = [item]
                current_y = item["y"]
                continue

            if abs(item["y"] - current_y) <= y_threshold:
                current_line.append(item)
                # average y กันบรรทัดเอียงนิดหน่อย
                current_y = sum(i["y"] for i in current_line) / len(current_line)
            else:
                lines.append(current_line)
                current_line = [item]
                current_y = item["y"]

        if current_line:
            lines.append(current_line)

        output_lines = []

        for line in lines:
            # sort ซ้ายไปขวา
            line.sort(key=lambda item: item["x"])
            line_text = " ".join(item["text"] for item in line if item["text"])
            line_text = re.sub(r"\s+", " ", line_text).strip()

            if line_text:
                output_lines.append(line_text)

        return "\n".join(output_lines)

    def preprocess_ocr(self, img_bgr: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return th

    def pdf_to_text(self, file_path: str, page_num: int = 4) -> str:
        doc = pymupdf.open(file_path)
        page = doc[page_num - 1]
        return page.get_text()

    def pdf_to_image(self, file_path: str, page_num: int = 1) -> np.ndarray:
        pages = convert_from_path(
            file_path,
            dpi=300,
            first_page=page_num,
            last_page=page_num,
            poppler_path=self.poppler_path
        )
        pil_img = pages[0]
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def sort_ocr_result(self, ocr_result, y_threshold=None):
        if y_threshold is None:
            heights = [
                max(p[1] for p in bbox) - min(p[1] for p in bbox)
                for bbox, _, _ in ocr_result
            ]
            y_threshold = np.mean(heights) * 0.5 if heights else 15

        items = []
        for bbox, text, conf in ocr_result:
            x = sum([p[0] for p in bbox]) / 4
            y = sum([p[1] for p in bbox]) / 4
            items.append((x, y, bbox, text, conf))

        items.sort(key=lambda x: x[1])

        lines = []
        current_line = []
        current_y = None

        for item in items:
            x, y, bbox, text, conf = item

            if current_y is None:
                current_line.append(item)
                current_y = y
            elif abs(y - current_y) < y_threshold:
                current_line.append(item)
            else:
                lines.append(current_line)
                current_line = [item]
                current_y = y

        if current_line:
            lines.append(current_line)

        sorted_result = []
        for line in lines:
            line.sort(key=lambda x: x[0])
            sorted_result.extend(line)

        return [(bbox, text, conf) for (_, _, bbox, text, conf) in sorted_result]

    def process_document_ocr(self, file_path: str, page_num: int) -> str:
        img_bgr = self.pdf_to_image(file_path, page_num)
        img_bin = self.preprocess_ocr(img_bgr)
        img_rgb = cv2.cvtColor(img_bin, cv2.COLOR_GRAY2RGB)

        ocr_result = self.reader.readtext(img_rgb)

        # สำคัญ: รวมแบบรักษาบรรทัด
        sentence = self.join_text_by_lines(ocr_result)

        return sentence