import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'المستكشف الذكي | Mustakshef-AI — المنظومة التفاعلية لتعليم الأطفال بالذكاء الاصطناعي',
  description: 'تطبيق ذكي للأطفال يدمج الرؤية الحاسوبية ونماذج YOLO والتعلم الصوتي لتعليم أسماء الأشياء وحروفها باللغة العربية الفصحى.',
  keywords: ['تعليم أطفال', 'ذكاء اصطناعي عربي', 'YOLO segmentation', 'Edge TTS', 'رؤية حاسوبية', 'هجاء الحروف العربية'],
  authors: [{ name: 'Mohammed AL-Haj' }],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl">
      <body className="min-h-screen bg-slate-50 flex flex-col antialiased selection:bg-emerald-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
