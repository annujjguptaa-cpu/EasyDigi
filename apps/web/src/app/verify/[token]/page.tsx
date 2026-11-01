'use client';

import React, { useState } from 'react';
import {
  Banner,
  Section,
  Panel,
  Button,
  StatusDot,
  Stepper,
} from '@/ui';
import { VOCABULARY } from '@/i18n/vocabulary';

export default function CustomerVerifyPage({ params }: { params: { token: string } }) {
  const [lang, setLang] = useState<'en' | 'hi' | 'hinglish'>('en');
  const [messages, setMessages] = useState([
    {
      role: 'agent',
      text: 'Hello! I am your DocFlow assistant. We need 2 missing documents to complete your verification with Apex Mutual Bank.',
      text_hi: 'नमस्ते! मैं आपका डॉकफ्लो सहायक हूँ। सत्यापन पूरा करने के लिए हमें 2 दस्तावेजों की आवश्यकता है।',
      text_hinglish: 'Namaste! Main aapka DocFlow assistant hoon. Verification complete karne ke liye 2 missing documents chahiye.',
    },
  ]);
  const [inputVal, setInputVal] = useState('');

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim()) return;

    const userText = inputVal;
    setInputVal('');

    setMessages((prev) => [
      ...prev,
      { role: 'user', text: userText, text_hi: userText, text_hinglish: userText },
      {
        role: 'agent',
        text: 'Thank you. Please use the camera or file upload button below to provide the document securely.',
        text_hi: 'धन्यवाद। कृपया दस्तावेज़ सुरक्षित रूप से अपलोड करने के लिए नीचे दिए गए बटन का उपयोग करें।',
        text_hinglish: 'Shukriya! Kripya neeche diye upload button se document safely provide karein.',
      },
    ]);
  };

  const getMessageText = (msg: (typeof messages)[0]) => {
    if (lang === 'hi') return msg.text_hi;
    if (lang === 'hinglish') return msg.text_hinglish;
    return msg.text;
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col items-center">
      <Banner type="demo" />

      <main className="max-w-md w-full p-4 sm:p-6 space-y-6">
        {/* Header & Language Switcher */}
        <div className="flex items-center justify-between border-b border-hairline pb-3">
          <div>
            <span className="font-mono text-xs text-ink-muted uppercase">SESSION: {params.token || 'SESS-9921'}</span>
            <h1 className="font-serif text-xl text-ink font-normal">Customer Verification</h1>
          </div>
          <div className="flex gap-1 font-mono text-xs">
            {(['en', 'hi', 'hinglish'] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                className={`px-2 py-1 rounded-[2px] border ${
                  lang === l
                    ? 'border-ink bg-ink text-paper font-semibold'
                    : 'border-hairline bg-surface text-ink-muted'
                }`}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Progress Strip */}
        <div className="flex items-center justify-between p-3 border border-hairline bg-surface rounded-[2px]">
          <span className="font-mono text-xs text-ink-muted uppercase">VERIFICATION PROGRESS</span>
          <span className="font-mono text-xs font-bold text-ink">3 OF 5 DOCUMENTS</span>
        </div>

        {/* Stepper */}
        <Stepper
          steps={[
            { index: '01', label: 'Consent', status: 'completed' },
            { index: '02', label: 'DigiLocker', status: 'completed' },
            { index: '03', label: 'Gap Fill', status: 'current' },
            { index: '04', label: 'Vault Save', status: 'pending' },
          ]}
        />

        {/* Chat History */}
        <div className="space-y-3 min-h-[280px]">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`p-4 rounded-[2px] border text-base ${
                m.role === 'agent'
                  ? 'border-hairline bg-surface text-ink mr-8'
                  : 'border-ink bg-ink text-paper ml-8'
              }`}
            >
              <span className="block font-mono text-[10px] uppercase tracking-wider mb-1 opacity-70">
                {m.role === 'agent' ? 'AI ASSISTANT' : 'YOU'}
              </span>
              <p className={lang === 'hi' ? 'font-devanagari leading-relaxed' : 'font-sans'}>
                {getMessageText(m)}
              </p>
            </div>
          ))}
        </div>

        {/* Upload Slots */}
        <Panel caption="MISSING DOCUMENT SLOTS">
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 border border-hairline bg-paper/50 rounded-[2px]">
              <div>
                <p className="font-sans font-semibold text-sm text-ink">Salary Slip (Q3)</p>
                <p className="font-mono text-xs text-ink-muted">PDF or JPEG (Max 5MB)</p>
              </div>
              <Button variant="secondary" className="min-h-[40px] px-3 py-1">
                UPLOAD
              </Button>
            </div>
          </div>
        </Panel>

        {/* User Input Form */}
        <form onSubmit={handleSend} className="space-y-3">
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder={
              lang === 'hi'
                ? 'अपना संदेश यहाँ लिखें...'
                : 'Type your message or clarification...'
            }
            className="w-full px-4 py-3 border border-hairline bg-surface text-ink text-base rounded-[2px] focus:outline-none focus:ring-2 focus:ring-ink"
          />
          <Button type="submit" variant="primary" className="w-full">
            SEND MESSAGE
          </Button>
        </form>
      </main>
    </div>
  );
}
