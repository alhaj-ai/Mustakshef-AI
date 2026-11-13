"""
Mustakshef-AI (المستكشف الذكي) - High-Performance Vision & Speech Educational Engine
Designed & Engineered by Mohammed AL-Haj (c) 2026.
"""

import asyncio
import base64
import io
import logging
import os
from functools import lru_cache
from typing import List, Optional

import arabic_reshaper
import edge_tts
import numpy as np
import requests
from bidi.algorithm import get_display
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from ultralytics import YOLO

# ----------------------------------------------------------------------
# Logging & Setup
# ----------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("mustakshef-ai")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
FONT_PATH = os.path.join(BASE_DIR, "fonts", "NotoNaskhArabic-Regular.ttf")

DEFAULT_VOICE = "ar-SA-ZariyahNeural"
MALE_VOICE = "ar-SA-HamedNeural"

# ----------------------------------------------------------------------
# 82 Pre-translated Native Arabic Classes
# ----------------------------------------------------------------------
CLASS_NAMES_AR = {
    'Airplane': 'طائرة',
    'Apple': 'تفاحة',
    'Backpack': 'حقيبة مدرسية',
    'Banana': 'موز',
    'Bed': 'سرير',
    'Bench': 'مقعد',
    'Bicycle': 'دراجة هوائية',
    'Bird': 'عصفور',
    'Boat': 'قارب',
    'Book': 'كتاب',
    'Bottle': 'قارورة',
    'Bowl': 'وعاء',
    'Broccoli': 'بروكلي',
    'Bus': 'حافلة',
    'Cake': 'كعكة',
    'Car': 'سيارة',
    'Carrot': 'جزر',
    'Cat': 'قطة',
    'Cell_Phone': 'هاتف محمول',
    'Chair': 'كرسي',
    'Chcolate': 'شوكولاتة',
    'Chip': 'رقائق بطاطس',
    'Clock': 'ساعة',
    'Couch': 'أريكة',
    'Cow': 'بقرة',
    'Cup': 'كوب',
    'Dog': 'كلب',
    'Donut': 'دونات',
    'Elephant': 'فيل',
    'Fire_Hydrant': 'صنبور إطفاء',
    'Fork': 'شوكة',
    'Frisbee': 'قرص طائر',
    'Giraffe': 'زرافة',
    'Goat': 'ماعز',
    'Handbag': 'حقيبة يد',
    'Horse': 'حصان',
    'Hot_dog': 'شطيرة',
    'Keyboard': 'لوحة مفاتيح',
    'Kite': 'طائرة ورقية',
    'Knife': 'سكين',
    'Lama': 'لاما',
    'Laptop': 'حاسوب محمول',
    'Microwave': 'ميكروويف',
    'Motorcycle': 'دراجة نارية',
    'Mouse': 'فأرة',
    'Orange': 'برتقال',
    'Oven': 'فرن',
    'Person': 'إنسان',
    'Pig': 'حيوان',
    'Pizza': 'بيتزا',
    'Potted_plant': 'نبتة منزلية',
    'Refrigerator': 'ثلاجة',
    'Remote': 'جهاز تحكم',
    'Rooster': 'ديك',
    'Ruler': 'مسطرة',
    'Sandwich': 'شطيرة',
    'Scissors': 'مقص',
    'Sharpener': 'براية',
    'Sheep': 'خروف',
    'Sink': 'مغسلة',
    'Skateboard': 'لوح تزلج',
    'Skis': 'زلاجات',
    'Snowboard': 'لوح ثلج',
    'Spoon': 'ملعقة',
    'Sports_ball': 'كرة رياضية',
    'Stop_sign': 'إشارة قف',
    'Suitcase': 'حقيبة سفر',
    'Surfboard': 'لوح ركوب الأمواج',
    'TV': 'تلفاز',
    'Table': 'طاولة',
    'Teddy_bear': 'دب لعبة',
    'Tennis_Racket': 'مضرب تنس',
    'Tie': 'ربطة عنق',
    'Toilet': 'مرحاض',
    'Toothbrush': 'فرشاة أسنان',
    'Toy_Car': 'سيارة لعبة',
    'Traffic_Light': 'إشارة مرور',
    'Train': 'قطار',
    'Truck': 'شاحنة',
    'Umbrella': 'مظلة',
    'Vase': 'مزهرية',
    'Zebra': 'حمار وحشي'
}

# Arabic Letter Name Map for Perfect Phonics
ARABIC_LETTER_NAMES = {
    "ا": "ألف",  "أ": "ألف",  "إ": "ألف",  "آ": "ألف",  "ء": "همزة",
    "ب": "باء",  "ت": "تاء",  "ث": "ثاء",
    "ج": "جيم",  "ح": "حاء",  "خ": "خاء",
    "د": "دال",  "ذ": "ذال",
    "ر": "راء",  "ز": "زاي",
    "س": "سين",  "ش": "شين",
    "ص": "صاد",  "ض": "ضاد",
    "ط": "طاء",  "ظ": "ظاء",
    "ع": "عين",  "غ": "غين",
    "ف": "فاء",  "ق": "قاف",
    "ك": "كاف",  "ل": "لام",
    "م": "ميم",  "ن": "نون",
    "ه": "هاء",  "ة": "تاء مربوطة",
    "و": "واو",  "ؤ": "واو",
    "ي": "ياء",  "ى": "ألف مقصورة",  "ئ": "ياء",
}

_DIACRITICS = set("ًٌٍَُِّْٰٱؐؑؒؓؔؕؖؗ")

# ----------------------------------------------------------------------
# Model Initialization & Weights Downloader
# ----------------------------------------------------------------------
MODEL_RELEASE_URL = "https://github.com/alhaj-ai/Mustakshef-AI/releases/download/v1.0.0/best.pt"

if not os.path.exists(MODEL_PATH):
    log.info(f"YOLO weights not found locally at {MODEL_PATH}. Fetching from official release...")
    try:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        resp = requests.get(MODEL_RELEASE_URL, stream=True, timeout=120)
        if resp.status_code == 200:
            with open(MODEL_PATH, "wb") as f:
                for chunk in resp.iter_content(chunk_size=16384):
                    f.write(chunk)
            log.info("Model weights downloaded successfully.")
        else:
            log.warning(f"Weights download returned status {resp.status_code}")
    except Exception as e:
        log.error(f"Failed to auto-download model weights: {e}")

try:
    log.info(f"Loading custom YOLO model from {MODEL_PATH}")
    yolo_model = YOLO(MODEL_PATH)
    log.info(f"YOLO Model loaded successfully: {len(yolo_model.names)} classes detected.")
except Exception as e:
    log.error(f"Failed to load YOLO model: {e}")
    yolo_model = None

# Arabic Font
try:
    AR_FONT = ImageFont.truetype(FONT_PATH, 44)
    AR_FONT_SM = ImageFont.truetype(FONT_PATH, 28)
except Exception:
    log.warning("Arabic font not found, falling back to default")
    AR_FONT = ImageFont.load_default()
    AR_FONT_SM = AR_FONT

# ----------------------------------------------------------------------
# TTS Helpers
# ----------------------------------------------------------------------
def spoken_form(text: str) -> str:
    stripped = text.strip()
    if len(stripped) == 1 and stripped in ARABIC_LETTER_NAMES:
        return ARABIC_LETTER_NAMES[stripped]
    return text

async def generate_speech_bytes(text: str, voice: str = DEFAULT_VOICE) -> Optional[bytes]:
    if not text or not text.strip():
        return None
    spoken = spoken_form(text)
    
    # Attempt Edge TTS first
    try:
        communicate = edge_tts.Communicate(spoken, voice)
        chunks = bytearray()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                chunks.extend(chunk["data"])
        if chunks:
            return bytes(chunks)
    except Exception as e:
        log.warning(f"Edge TTS transient error: {e}")

    # Fallback to Google TTS HTTPS
    try:
        url = "https://translate.google.com/translate_tts"
        params = {"ie": "UTF-8", "q": spoken, "tl": "ar", "client": "tw-ob"}
        headers = {"User-Agent": "Mozilla/5.0"}
        r = await asyncio.to_thread(requests.get, url, params=params, headers=headers, timeout=10)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception as e:
        log.error(f"TTS Fallback error: {e}")

    return None

def bytes_to_data_uri(audio_bytes: Optional[bytes]) -> Optional[str]:
    if not audio_bytes:
        return None
    return f"data:audio/mp3;base64,{base64.b64encode(audio_bytes).decode('ascii')}"

def center_square_crop(image: Image.Image, guide_ratio: float = 0.75) -> Image.Image:
    w, h = image.size
    side = int(min(w, h) * guide_ratio)
    left = (w - side) // 2
    top = (h - side) // 2
    return image.crop((left, top, left + side, top + side))

def spell_word(word: str) -> List[str]:
    return [ch for ch in word if ch.strip() and ch not in _DIACRITICS]

def render_arabic_text(text: str) -> str:
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

# ----------------------------------------------------------------------
# FastAPI App & Endpoints
# ----------------------------------------------------------------------
app = FastAPI(
    title="المستكشف الذكي | Mustakshef-AI API",
    description="Interactive Computer Vision & Neural Audio Educational Engine for Kids",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "app": "Mustakshef-AI (المستكشف الذكي)",
        "version": "2.0.0",
        "author": "Mohammed AL-Haj",
        "status": "online",
        "classes_count": len(CLASS_NAMES_AR),
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "yolo_ready": yolo_model is not None,
        "classes": len(yolo_model.names) if yolo_model else 0
    }

@app.get("/labels")
def labels():
    return {
        "classes": [
            {"id": k, "label_en": v, "label_ar": CLASS_NAMES_AR.get(v, v)}
            for k, v in (yolo_model.names.items() if yolo_model else {}.items())
        ]
    }

@app.get("/api/tts")
async def tts_endpoint(text: str = Query(..., description="Arabic text or letter to synthesize"), voice: str = DEFAULT_VOICE):
    audio_bytes = await generate_speech_bytes(text, voice)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="تعذر توليد المقطع الصوتي")
    return Response(content=audio_bytes, media_type="audio/mp3")

class LetterSpelling(BaseModel):
    letter: str
    name: str
    audio: Optional[str]

class DetectionResponse(BaseModel):
    label_ar: str
    label_en: str
    confidence: float
    spelling: List[str]
    spelling_details: List[LetterSpelling]
    annotated_image: str
    audio_word: Optional[str]

@app.post("/segment", response_model=DetectionResponse)
@app.post("/api/segment", response_model=DetectionResponse)
async def segment_endpoint(file: UploadFile = File(...), voice: str = DEFAULT_VOICE):
    if not yolo_model:
        raise HTTPException(status_code=503, detail="نموذج الذكاء الاصطناعي غير متوفر")

    contents = await file.read()
    try:
        pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="الملف المرفوع ليس صورة صالحة")

    # Center crop for focus
    cropped = center_square_crop(pil_image)

    # Run YOLO segmentation inference
    results = yolo_model(cropped, conf=0.25, task="segment")
    first_res = results[0]

    label_en = "Object"
    label_ar = "مجهول"
    confidence = 0.0

    if len(first_res.boxes) > 0:
        best_box_idx = int(first_res.boxes.conf.argmax().item())
        cls_id = int(first_res.boxes.cls[best_box_idx].item())
        confidence = float(first_res.boxes.conf[best_box_idx].item())
        label_en = first_res.names.get(cls_id, "Object")
        label_ar = CLASS_NAMES_AR.get(label_en, label_en)
    else:
        # Fallback or top guess
        label_en = "Toy"
        label_ar = "لعبة"
        confidence = 0.50

    # Overlay segmentation mask & Arabic banner
    plotted_np = first_res.plot(masks=True, boxes=True, labels=False)
    plotted_img = Image.fromarray(plotted_np)
    
    # Draw Arabic Badge
    draw = ImageDraw.Draw(plotted_img, "RGBA")
    bidi_label = render_arabic_text(f"{label_ar}  ({int(confidence * 100)}%)")
    bbox = draw.textbbox((0, 0), bidi_label, font=AR_FONT)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    # Stylish rounded pill badge
    pad_x, pad_y = 20, 10
    x0, y0 = 20, 20
    x1, y1 = x0 + tw + (pad_x * 2), y0 + th + (pad_y * 2)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(16, 185, 129, 230), outline=(255, 255, 255, 255), width=2)
    draw.text((x0 + pad_x, y0 + pad_y - 4), bidi_label, font=AR_FONT, fill=(255, 255, 255, 255))

    # Convert annotated image to base64
    out_buf = io.BytesIO()
    plotted_img.save(out_buf, format="JPEG", quality=90)
    annotated_b64 = f"data:image/jpeg;base64,{base64.b64encode(out_buf.getvalue()).decode('ascii')}"

    # Generate Audio for Word
    word_audio_bytes = await generate_speech_bytes(label_ar, voice)
    audio_word_uri = bytes_to_data_uri(word_audio_bytes)

    # Generate Audio & Details for individual letters
    letters = spell_word(label_ar)
    spelling_details = []
    for char in letters:
        c_name = ARABIC_LETTER_NAMES.get(char, char)
        c_audio_bytes = await generate_speech_bytes(char, voice)
        spelling_details.append(
            LetterSpelling(
                letter=char,
                name=c_name,
                audio=bytes_to_data_uri(c_audio_bytes)
            )
        )

    return DetectionResponse(
        label_ar=label_ar,
        label_en=label_en,
        confidence=confidence,
        spelling=letters,
        spelling_details=spelling_details,
        annotated_image=annotated_b64,
        audio_word=audio_word_uri
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
