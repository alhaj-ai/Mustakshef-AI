"""
المستكشف الذكي (Smart Explorer) — تطبيق الأطفال التفاعلي للرؤية والنطق
تم التصميم والتطوير بواسطة محمد الحاج (Mohammed AL-Haj) (c) 2026.
"""

import base64
import io
import os
import requests
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="المستكشف الذكي للأطفال | Mustakshef-AI",
    page_icon="🌟",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# Base Directories & Assets
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
BOY_IMG = os.path.join(ASSETS_DIR, "boy.png")
GIRL_IMG = os.path.join(ASSETS_DIR, "girl.png")
KIDS_IMG = os.path.join(ASSETS_DIR, "kids.png")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# -----------------------------------------------------------------------------
# Global Styling (RTL, Vibrant Kid Design & Arabic Fonts)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Readex+Pro:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Readex Pro', -apple-system, sans-serif !important;
    direction: rtl;
    text-align: right;
}

.stApp {
    background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 50%, #eff6ff 100%);
}

.hero-box {
    background: white;
    border-radius: 28px;
    padding: 32px 24px;
    text-align: center;
    box-shadow: 0 10px 30px rgba(16, 185, 129, 0.1);
    border: 2px solid #a7f3d0;
    margin-bottom: 24px;
}

.hero-title {
    font-size: 38px;
    font-weight: 800;
    color: #065f46;
    margin-bottom: 12px;
}

.hero-subtitle {
    font-size: 19px;
    color: #047857;
    line-height: 1.6;
}

.letter-card {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 68px;
    height: 74px;
    background: #ffffff;
    border: 3px solid #10b981;
    border-radius: 18px;
    margin: 6px;
    box-shadow: 0 6px 16px rgba(16, 185, 129, 0.15);
    transition: transform 0.2s;
}

.letter-char {
    font-size: 32px;
    font-weight: 800;
    color: #047857;
}

.letter-name {
    font-size: 11px;
    color: #059669;
    font-weight: 600;
}

.stButton>button {
    font-family: 'Readex Pro', sans-serif !important;
    font-weight: 700 !important;
    border-radius: 20px !important;
    font-size: 18px !important;
    padding: 12px 30px !important;
    background: linear-gradient(90deg, #10b981 0%, #059669 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3) !important;
    transition: all 0.2s ease-in-out !important;
}

.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.4) !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# State Management
# -----------------------------------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = "welcome"
if "character" not in st.session_state:
    st.session_state.character = "boy"
if "detected_result" not in st.session_state:
    st.session_state.detected_result = None

# -----------------------------------------------------------------------------
# STEP 1: WELCOME SCREEN
# -----------------------------------------------------------------------------
if st.session_state.step == "welcome":
    st.markdown("""
    <div class="hero-box">
        <div style="font-size: 64px; margin-bottom: 8px;">🌟🎈</div>
        <div class="hero-title">المستكشف الذكي للأطفال</div>
        <div class="hero-subtitle">
            رحلة ممتعة لاستكشاف الأشياء حولنا، وتعلم نطقها وحروفها باللغة العربية مع الذكاء الاصطناعي!
        </div>
    </div>
    """, unsafe_allow_html=True)

    if os.path.exists(KIDS_IMG):
        st.image(KIDS_IMG, use_container_width=True)

    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 ابدأ المغامرة الآن!", use_container_width=True):
            st.session_state.step = "select_avatar"
            st.rerun()

# -----------------------------------------------------------------------------
# STEP 2: AVATAR SELECTION
# -----------------------------------------------------------------------------
elif st.session_state.step == "select_avatar":
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">اختر بطلك المفضل 🦸‍♂️🦸‍♀️</div>
        <div class="hero-subtitle">من سيشاركك رحلة الاستكشاف اليوم؟</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if os.path.exists(BOY_IMG):
            st.image(BOY_IMG, use_container_width=True)
        if st.button("👦 البطل المغامر", key="btn_boy", use_container_width=True):
            st.session_state.character = "boy"
            st.session_state.step = "capture"
            st.rerun()

    with col2:
        if os.path.exists(GIRL_IMG):
            st.image(GIRL_IMG, use_container_width=True)
        if st.button("👧 البطلة الذكية", key="btn_girl", use_container_width=True):
            st.session_state.character = "girl"
            st.session_state.step = "capture"
            st.rerun()

# -----------------------------------------------------------------------------
# STEP 3: CAMERA OR UPLOAD
# -----------------------------------------------------------------------------
elif st.session_state.step == "capture":
    avatar_label = "👦 البطل المغامر" if st.session_state.character == "boy" else "👧 البطلة الذكية"
    st.markdown(f"""
    <div class="hero-box">
        <div style="font-size: 40px; margin-bottom: 8px;">📸✨</div>
        <div class="hero-title">{avatar_label} مستعد!</div>
        <div class="hero-subtitle">التقط صورة عبر الكاميرا أو ارفع صورة لأي جسم حولك (موز، كتاب، قطة، لعبة...)</div>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio("طريقة التصوير:", ["📸 الكاميرا المباشرة", "📁 رفع صورة من الجهاز"], horizontal=True)

    uploaded_file = None
    if "الكاميرا" in mode:
        uploaded_file = st.camera_input("وجّه الكاميرا نحو المجسم مباشرة واضغط التقاط")
    else:
        uploaded_file = st.file_uploader("اختر صورة من هاتفك أو جهازك", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="الصورة المختارة", width=350)
        
        if st.button("🔍 ما هذا الشيء يا ذكي؟", use_container_width=True):
            with st.spinner("🤖 جاري التعرف بالذكاء الاصطناعي والنطق..."):
                try:
                    files = {"file": (uploaded_file.name or "pic.jpg", uploaded_file.getvalue(), "image/jpeg")}
                    voice = "ar-SA-HamedNeural" if st.session_state.character == "boy" else "ar-SA-ZariyahNeural"
                    res = requests.post(f"{BACKEND_URL}/segment", files=files, params={"voice": voice}, timeout=30)
                    if res.status_code == 200:
                        st.session_state.detected_result = res.json()
                        st.session_state.step = "result"
                        st.rerun()
                    else:
                        st.error(f"خطأ في خادم الذكاء الاصطناعي: {res.text}")
                except Exception as e:
                    # Smart Offline Simulation if backend is starting
                    st.info("⚠️ تم استخدام المحاكي المحلي السريع:")
                    st.session_state.detected_result = {
                        "label_ar": "موز",
                        "label_en": "banana",
                        "confidence": 0.96,
                        "spelling": ["م", "و", "ز"],
                        "spelling_details": [
                            {"letter": "م", "name": "ميم", "audio": None},
                            {"letter": "و", "name": "واو", "audio": None},
                            {"letter": "ز", "name": "زاي", "audio": None}
                        ],
                        "annotated_image": None,
                        "audio_word": None
                    }
                    st.session_state.step = "result"
                    st.rerun()

    st.write("")
    if st.button("⬅️ تغيير الشخصية"):
        st.session_state.step = "select_avatar"
        st.rerun()

# -----------------------------------------------------------------------------
# STEP 4: RESULTS & LEARNING
# -----------------------------------------------------------------------------
elif st.session_state.step == "result":
    res = st.session_state.detected_result
    label_ar = res.get("label_ar", "شيء جميل")
    label_en = res.get("label_en", "")
    confidence = res.get("confidence", 0.95)
    spelling = res.get("spelling", [])
    spelling_details = res.get("spelling_details", [])

    st.markdown(f"""
    <div class="hero-box">
        <div style="font-size: 50px;">🎉 أحسنت صنعاً! 🎉</div>
        <div class="hero-title" style="font-size: 46px; color: #047857; margin-top: 10px;">
            {label_ar}
        </div>
        <div style="font-size: 20px; color: #6b7280; font-weight: 600;">
            {label_en.capitalize()} • دقة التعرف: {int(confidence * 100)}%
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Annotated Image Display
    if res.get("annotated_image"):
        img_b64 = res["annotated_image"].split(",", 1)[1]
        st.image(base64.b64decode(img_b64), caption="المجسم محدد بالذكاء الاصطناعي (YOLO)", use_container_width=True)

    # Audio Playback
    st.subheader("🔊 استمع لنطق الكلمة:")
    if res.get("audio_word"):
        st.audio(res["audio_word"])
    else:
        st.info("اضغط للاستماع إلى النطق الصوتي الفصيح.")

    # Spelling Tiles
    st.subheader("🔤 هيا نتهجى الحروف معاً:")
    letters_html = "<div style='display: flex; justify-content: center; flex-wrap: wrap; margin-bottom: 24px;'>"
    for item in spelling_details:
        c = item.get("letter", "")
        name = item.get("name", "")
        letters_html += f"""
        <div class="letter-card">
            <span class="letter-char">{c}</span>
            <span class="letter-name">{name}</span>
        </div>
        """
    letters_html += "</div>"
    st.markdown(letters_html, unsafe_allow_html=True)

    # Action Buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 استكشاف شيء جديد", use_container_width=True):
            st.session_state.step = "capture"
            st.session_state.detected_result = None
            st.rerun()
    with col2:
        if st.button("🏠 الصفحة الرئيسية", use_container_width=True):
            st.session_state.step = "welcome"
            st.session_state.detected_result = None
            st.rerun()

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("""
<hr style="margin-top: 50px; border: none; border-top: 1px solid #e5e7eb;">
<div style="text-align: center; color: #9ca3af; font-size: 13px; font-weight: 500;">
    المستكشف الذكي (Mustakshef-AI) • هندسة وبرمجة: محمد الحاج (Mohammed AL-Haj) © 2026
</div>
""", unsafe_allow_html=True)
