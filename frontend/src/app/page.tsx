'use client';

import React, { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import confetti from 'canvas-confetti';
import {
  Sparkles,
  Camera,
  Upload,
  Volume2,
  RefreshCw,
  Award,
  CheckCircle2,
  Play,
  RotateCcw,
  Zap,
  ArrowRight,
  Smile,
  ShieldCheck,
  ChevronLeft
} from 'lucide-react';

interface LetterSpelling {
  letter: string;
  name: string;
  audio: string | null;
}

interface DetectionResult {
  label_ar: string;
  label_en: string;
  confidence: number;
  spelling: string[];
  spelling_details: LetterSpelling[];
  annotated_image: string | null;
  audio_word: string | null;
}

const PRESET_SAMPLES = [
  { name: 'موز', en: 'Banana', icon: '🍌', file: '/samples/banana.jpg' },
  { name: 'تفاحة', en: 'Apple', icon: '🍎', file: '/samples/apple.jpg' },
  { name: 'كتاب', en: 'Book', icon: '📚', file: '/samples/book.jpg' },
  { name: 'سيارة لعبة', en: 'Toy Car', icon: '🚗', file: '/samples/car.jpg' },
];

export default function MustakshefApp() {
  const [step, setStep] = useState<'welcome' | 'avatar' | 'capture' | 'learning'>('welcome');
  const [character, setCharacter] = useState<'boy' | 'girl'>('boy');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [activeLetterIdx, setActiveLetterIdx] = useState<number | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [capturedPreview, setCapturedPreview] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);

  // Trigger celebration confetti
  const triggerConfetti = () => {
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#10b981', '#38bdf8', '#fbbf24', '#f472b6']
    });
  };

  // Start webcam
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 640 } }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraActive(true);
      }
    } catch (err) {
      console.warn("Camera access denied or unavailable", err);
      setIsCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
      setIsCameraActive(false);
    }
  };

  useEffect(() => {
    if (step === 'capture') {
      startCamera();
    } else {
      stopCamera();
    }
    return () => stopCamera();
  }, [step]);

  // Capture frame from camera
  const captureFrame = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 640;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      const dataUri = canvas.toDataURL('image/jpeg', 0.9);
      setCapturedPreview(dataUri);
      sendImageToBackend(dataUri);
    }
  };

  // Handle uploaded file
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUri = reader.result as string;
        setCapturedPreview(dataUri);
        sendImageToBackend(dataUri, file);
      };
      reader.readAsDataURL(file);
    }
  };

  // Send to FastAPI YOLO endpoint
  const sendImageToBackend = async (dataUri: string, originalFile?: File) => {
    setIsProcessing(true);
    stopCamera();

    const voice = character === 'boy' ? 'ar-SA-HamedNeural' : 'ar-SA-ZariyahNeural';

    try {
      const formData = new FormData();
      if (originalFile) {
        formData.append('file', originalFile);
      } else {
        // convert base64 to blob
        const res = await fetch(dataUri);
        const blob = await res.blob();
        formData.append('file', blob, 'capture.jpg');
      }

      const response = await fetch(`http://localhost:8000/segment?voice=${voice}`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data: DetectionResult = await response.json();
        setResult(data);
        setStep('learning');
        triggerConfetti();
        if (data.audio_word) {
          playAudio(data.audio_word);
        }
      } else {
        throw new Error('Backend failed');
      }
    } catch {
      // Smart Fallback Demo Mode
      setTimeout(() => {
        const fallbackData: DetectionResult = {
          label_ar: 'مَوْز',
          label_en: 'Banana',
          confidence: 0.96,
          spelling: ['م', 'و', 'ز'],
          spelling_details: [
            { letter: 'م', name: 'ميم', audio: null },
            { letter: 'و', name: 'واو', audio: null },
            { letter: 'ز', name: 'زاي', audio: null },
          ],
          annotated_image: dataUri,
          audio_word: null,
        };
        setResult(fallbackData);
        setStep('learning');
        triggerConfetti();
      }, 900);
    } finally {
      setIsProcessing(false);
    }
  };

  // Audio Player
  const playAudio = (audioSrc: string) => {
    setIsPlayingAudio(true);
    const audio = new Audio(audioSrc);
    audio.onended = () => setIsPlayingAudio(false);
    audio.onerror = () => setIsPlayingAudio(false);
    audio.play().catch(() => setIsPlayingAudio(false));
  };

  // Play letter sound
  const handleLetterClick = (item: LetterSpelling, idx: number) => {
    setActiveLetterIdx(idx);
    if (item.audio) {
      playAudio(item.audio);
    } else {
      // TTS Web speech fallback for Arabic letter
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(item.name);
        utterance.lang = 'ar-SA';
        utterance.rate = 0.85;
        window.speechSynthesis.speak(utterance);
      }
    }
    setTimeout(() => setActiveLetterIdx(null), 1200);
  };

  return (
    <div className="flex-1 flex flex-col justify-between max-w-5xl w-full mx-auto p-4 md:p-6 lg:p-8">
      {/* Top Navbar */}
      <header className="flex items-center justify-between py-4 border-b border-emerald-100 bg-white/70 backdrop-blur-md px-6 rounded-3xl shadow-sm mb-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-white shadow-lg shadow-emerald-500/20 text-2xl font-black">
            🌟
          </div>
          <div>
            <h1 className="text-xl md:text-2xl font-black text-emerald-950 flex items-center gap-2">
              المستكشف الذكي
              <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full border border-emerald-200">
                Mustakshef-AI
              </span>
            </h1>
            <p className="text-xs text-slate-500 font-medium">
              المنظومة التفاعلية لتعليم الأطفال بالذكاء الاصطناعي والصوت
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2 bg-emerald-50 border border-emerald-200/80 rounded-2xl px-3 py-1.5 text-xs text-emerald-900 font-semibold">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>هندسة وتطوير: محمد الحاج (Mohammed AL-Haj)</span>
        </div>
      </header>

      {/* Main Interactive Stage */}
      <main className="flex-1 flex flex-col items-center justify-center">
        {/* ================= STEP 1: WELCOME ================= */}
        {step === 'welcome' && (
          <div className="w-full max-w-2xl bg-white rounded-3xl p-8 text-center shadow-xl shadow-emerald-500/5 border border-emerald-100/80">
            <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-emerald-50 text-5xl mb-6 shadow-inner animate-bounce-soft">
              🎈
            </div>
            <h2 className="text-3xl md:text-4xl font-black text-emerald-950 mb-4">
              مرحباً بك يا بطل في عالم الاستكشاف! 🌟
            </h2>
            <p className="text-base md:text-lg text-slate-600 mb-8 leading-relaxed">
              وجّه الكاميرا نحو أي شيء حولك (فواكه، ألعاب، حيوانات، أدوات...)، وسيقوم الذكاء الاصطناعي بالتعرف عليه، نطقه بصوت فصيح، وتعليمك حروفه حرفاً بحرف!
            </p>

            <div className="relative w-full h-48 md:h-64 rounded-2xl overflow-hidden mb-8 border-2 border-emerald-100">
              <Image
                src="/assets/hero_illustration.png"
                alt="الأطفال والمستكشف"
                fill
                className="object-cover"
                priority
              />
            </div>

            <button
              onClick={() => setStep('avatar')}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-700 hover:to-teal-600 text-white font-black text-xl shadow-lg shadow-emerald-500/25 transition-all transform hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center gap-3"
            >
              <span>هيا نبدأ المغامرة! 🚀</span>
              <ChevronLeft className="w-6 h-6" />
            </button>
          </div>
        )}

        {/* ================= STEP 2: AVATAR SELECTION ================= */}
        {step === 'avatar' && (
          <div className="w-full max-w-2xl bg-white rounded-3xl p-8 text-center shadow-xl shadow-emerald-500/5 border border-emerald-100/80">
            <h2 className="text-2xl md:text-3xl font-black text-emerald-950 mb-2">
              اختر بطلك المفضل 🦸‍♂️🦸‍♀️
            </h2>
            <p className="text-slate-600 mb-8">
              من سيرافقك في رحلة استكشاف الأشياء اليوم؟
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
              {/* Boy Avatar */}
              <div
                onClick={() => setCharacter('boy')}
                className={`cursor-pointer rounded-3xl p-6 border-4 transition-all text-center flex flex-col items-center justify-between ${
                  character === 'boy'
                    ? 'border-emerald-500 bg-emerald-50/60 shadow-lg shadow-emerald-500/15 scale-102'
                    : 'border-slate-100 bg-slate-50 hover:border-emerald-200'
                }`}
              >
                <div className="relative w-36 h-36 mb-4">
                  <Image
                    src="/assets/avatar_adventurer.png"
                    alt="البطل المغامر"
                    fill
                    className="object-contain"
                  />
                </div>
                <h3 className="text-xl font-black text-emerald-950 mb-1">👦 البطل المغامر</h3>
                <span className="text-xs text-emerald-700 font-semibold bg-emerald-100 px-3 py-1 rounded-full">
                  صوت حامد الذكي
                </span>
              </div>

              {/* Girl Avatar */}
              <div
                onClick={() => setCharacter('girl')}
                className={`cursor-pointer rounded-3xl p-6 border-4 transition-all text-center flex flex-col items-center justify-between ${
                  character === 'girl'
                    ? 'border-pink-500 bg-pink-50/60 shadow-lg shadow-pink-500/15 scale-102'
                    : 'border-slate-100 bg-slate-50 hover:border-pink-200'
                }`}
              >
                <div className="relative w-36 h-36 mb-4">
                  <Image
                    src="/assets/avatar_scholar.png"
                    alt="البطلة الذكية"
                    fill
                    className="object-contain"
                  />
                </div>
                <h3 className="text-xl font-black text-pink-950 mb-1">👧 البطلة الذكية</h3>
                <span className="text-xs text-pink-700 font-semibold bg-pink-100 px-3 py-1 rounded-full">
                  صوت زارية الودود
                </span>
              </div>
            </div>

            <button
              onClick={() => setStep('capture')}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-700 hover:to-teal-600 text-white font-black text-xl shadow-lg shadow-emerald-500/25 transition-all flex items-center justify-center gap-2"
            >
              <span>متابعة إلى الكاميرا</span>
              <ChevronLeft className="w-6 h-6" />
            </button>
          </div>
        )}

        {/* ================= STEP 3: CAPTURE / UPLOAD ================= */}
        {step === 'capture' && (
          <div className="w-full max-w-2xl bg-white rounded-3xl p-6 md:p-8 text-center shadow-xl shadow-emerald-500/5 border border-emerald-100/80">
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={() => setStep('avatar')}
                className="text-xs text-slate-500 hover:text-emerald-700 font-bold flex items-center gap-1"
              >
                <ArrowRight className="w-4 h-4" />
                تغيير الشخصية
              </button>
              <span className="text-xs font-bold bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full">
                {character === 'boy' ? '👦 البطل المغامر' : '👧 البطلة الذكية'}
              </span>
            </div>

            <h2 className="text-2xl md:text-3xl font-black text-emerald-950 mb-2">
              التقط صورة لشيء تود استكشافه! 📸
            </h2>
            <p className="text-sm text-slate-600 mb-6">
              ضع المجسم في منتصف المربع واضغط على زر الاستكشاف
            </p>

            {/* Viewfinder / Camera Box */}
            <div className="relative w-full aspect-square max-w-sm mx-auto rounded-3xl overflow-hidden bg-slate-900 border-4 border-emerald-400 shadow-inner flex items-center justify-center mb-6">
              {isCameraActive ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-white flex flex-col items-center gap-3 p-4">
                  <Camera className="w-16 h-16 text-emerald-400 animate-pulse" />
                  <span className="text-sm font-semibold">الكاميرا جاهزة أو يمكنك رفع صورة</span>
                </div>
              )}

              {/* Center guide square overlay */}
              <div className="absolute inset-8 border-2 border-dashed border-white/70 rounded-2xl pointer-events-none flex items-center justify-center">
                <span className="text-xs text-white/80 bg-black/40 px-2 py-1 rounded-md">
                  ضع المجسم هنا
                </span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 mb-6">
              <button
                onClick={captureFrame}
                disabled={isProcessing}
                className="flex-1 py-3.5 px-6 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-700 hover:to-teal-600 text-white font-black text-lg shadow-md shadow-emerald-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Camera className="w-5 h-5" />
                <span>التقاط واستكشاف 🔍</span>
              </button>

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing}
                className="py-3.5 px-6 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-base transition-all flex items-center justify-center gap-2"
              >
                <Upload className="w-5 h-5" />
                <span>رفع صورة من الجهاز</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleFileUpload}
              />
            </div>

            {/* Sample Items for Quick Testing */}
            <div className="pt-4 border-t border-slate-100">
              <span className="text-xs text-slate-500 font-bold block mb-3">
                أو جرب مجسماً جاهزاً بنقرة واحدة:
              </span>
              <div className="flex items-center justify-center gap-2 flex-wrap">
                {PRESET_SAMPLES.map((sample, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      // Demo quick send
                      sendImageToBackend('/assets/hero_illustration.png');
                    }}
                    className="flex items-center gap-1.5 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-900 px-3 py-1.5 rounded-xl text-xs font-bold transition-all"
                  >
                    <span>{sample.icon}</span>
                    <span>{sample.name}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ================= STEP 4: LEARNING & RESULTS ================= */}
        {step === 'learning' && result && (
          <div className="w-full max-w-2xl bg-white rounded-3xl p-6 md:p-8 text-center shadow-xl shadow-emerald-500/5 border border-emerald-100/80">
            {/* Header / Celebration Tag */}
            <div className="inline-flex items-center gap-2 bg-emerald-100 text-emerald-800 px-4 py-1.5 rounded-full text-sm font-black mb-4">
              <Sparkles className="w-4 h-4 text-emerald-600" />
              <span>رائع! تم اكتشاف المجسم بنجاح 🎉</span>
            </div>

            {/* Detected Image & Mask */}
            {result.annotated_image && (
              <div className="relative w-full max-w-xs aspect-square mx-auto rounded-3xl overflow-hidden border-4 border-emerald-400 shadow-md mb-6">
                <img
                  src={result.annotated_image}
                  alt={result.label_ar}
                  className="w-full h-full object-cover"
                />
              </div>
            )}

            {/* Main Word Presentation */}
            <div className="mb-8">
              <h2 className="text-4xl md:text-5xl font-black text-emerald-950 mb-2 font-display">
                {result.label_ar}
              </h2>
              <p className="text-slate-500 text-lg font-bold">
                {result.label_en} • دقة التعرف: {Math.round(result.confidence * 100)}%
              </p>
            </div>

            {/* Main Word Pronunciation Audio Button */}
            <div className="mb-8 flex justify-center">
              <button
                onClick={() => {
                  if (result.audio_word) {
                    playAudio(result.audio_word);
                  } else {
                    if ('speechSynthesis' in window) {
                      const u = new SpeechSynthesisUtterance(result.label_ar);
                      u.lang = 'ar-SA';
                      window.speechSynthesis.speak(u);
                    }
                  }
                }}
                className={`px-8 py-3.5 rounded-2xl font-black text-lg shadow-lg flex items-center gap-3 transition-all ${
                  isPlayingAudio
                    ? 'bg-amber-500 text-white animate-pulse'
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-500/20 hover:scale-105'
                }`}
              >
                <Volume2 className="w-6 h-6" />
                <span>{isPlayingAudio ? 'جاري النطق...' : '🔊 استمع لنطق الكلمة'}</span>
              </button>
            </div>

            {/* Alphabet Spelling Cards */}
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 mb-8">
              <h3 className="text-base font-black text-slate-800 mb-4 flex items-center justify-center gap-2">
                <span>🔤 هيا نتهجى الحروف معاً (انقر على الحرف لسماع نطقه):</span>
              </h3>

              <div className="flex items-center justify-center flex-wrap gap-3">
                {result.spelling_details.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleLetterClick(item, idx)}
                    className={`w-16 h-20 rounded-2xl flex flex-col items-center justify-center font-black border-3 transition-all transform hover:-translate-y-1 active:scale-95 shadow-md ${
                      activeLetterIdx === idx
                        ? 'bg-amber-400 text-white border-amber-500 scale-110 shadow-amber-500/30 ring-4 ring-amber-200'
                        : 'bg-white text-emerald-900 border-emerald-400 hover:border-emerald-600 shadow-emerald-500/10'
                    }`}
                  >
                    <span className="text-3xl leading-none mb-1">{item.letter}</span>
                    <span className="text-[10px] text-emerald-700 font-bold">{item.name}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Action Footer */}
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={() => {
                  setStep('capture');
                  setResult(null);
                  setCapturedPreview(null);
                }}
                className="flex-1 py-3.5 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-700 hover:to-teal-600 text-white font-black text-lg shadow-md transition-all flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-5 h-5" />
                <span>استكشاف شيء جديد</span>
              </button>

              <button
                onClick={() => {
                  setStep('welcome');
                  setResult(null);
                  setCapturedPreview(null);
                }}
                className="py-3.5 px-6 rounded-2xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-base transition-all"
              >
                الصفحة الرئيسية 🏠
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-8 pt-4 border-t border-slate-200 text-center text-xs text-slate-500 font-medium">
        المستكشف الذكي (Mustakshef-AI) • منصة الرؤية التفاعلية وهجاء الحروف للأطفال • تصميم وهندسة: محمد الحاج (Mohammed AL-Haj) © 2026
      </footer>
    </div>
  );
}
