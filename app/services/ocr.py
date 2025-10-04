from dataclasses import dataclass
from typing import Optional
import io
import cv2
import numpy as np
from PIL import Image
import pytesseract

@dataclass
class OCRResult:
    text: str
    engine: str
    preprocessing_variant: str


def _load_image(image_bytes: bytes) -> np.ndarray:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _preprocess_variants(image_bgr: np.ndarray):
    variants = {}

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Base
    variants["gray"] = gray

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    variants["clahe"] = clahe.apply(gray)

    # Adaptive threshold
    variants["adaptive"] = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )

    # Bilateral filter + Otsu
    smoothed = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    _, otsu = cv2.threshold(smoothed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants["otsu_bilateral"] = otsu

    # Sharpen
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    variants["sharpen"] = cv2.filter2D(gray, -1, kernel)

    return variants


def _run_tesseract(img: np.ndarray, psm: int) -> str:
    config = f"--oem 3 --psm {psm} -l eng"
    return pytesseract.image_to_string(img, config=config)


def perform_ocr(image_bytes: bytes) -> OCRResult:
    image_bgr = _load_image(image_bytes)
    variants = _preprocess_variants(image_bgr)

    best_text = ""
    best_variant = ""

    for name, variant in variants.items():
        text = _run_tesseract(variant, psm=6)
        if len(text) > len(best_text):
            best_text = text
            best_variant = name

    # Fallback try PSM 7
    if len(best_text.strip()) < 4:
        for name, variant in variants.items():
            text = _run_tesseract(variant, psm=7)
            if len(text) > len(best_text):
                best_text = text
                best_variant = f"{name}_psm7"

    return OCRResult(text=best_text.strip(), engine="tesseract", preprocessing_variant=best_variant)
