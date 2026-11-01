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
import { VOCABULARY, SupportedLanguage } from '@/i18n/vocabulary';

export default function WishCustomerPage({ params }: { params: { token: string } }) {
  const [lang, setLang] = useState<SupportedLanguage>('en');
  const [selectedDocs, setSelectedDocs] = useState<Record<string, boolean>>({
    pan: true,
    aadhaar: true,
    salary: false,
  });
  const [isWorking, setIsWorking] = useState(false);
  const [isGranted, setIsGranted] = useState(false);

  const t = VOCABULARY[lang];

  const handleToggle = (key: string) => {
    setSelectedDocs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleGrant = (e: React.FormEvent) => {
    e.preventDefault();
    setIsWorking(true);

    setTimeout(() => {
      setIsWorking(false);
      setIsGranted(true);
    }, 1200);
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col justify-between items-center">
      <Banner type="demo" />

      <main className="max-w-lg w-full p-4 sm:p-6 space-y-6">
        {/* Header & Language Switcher */}
        <div className="flex items-center justify-between border-b border-hairline pb-4">
          <div>
            <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block">
              DJINN WISH PACK • OPPORTUNITY WISH
            </span>
            <h1 className="font-serif text-2xl text-ink font-normal">Customer Wish Link</h1>
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

        {/* Wish Stepper */}
        <Stepper
          steps={[
            { index: '01', label: t.stepper.s1, status: 'completed' },
            { index: '02', label: t.stepper.s2, status: 'completed' },
            { index: '03', label: t.stepper.s3, status: 'completed' },
            { index: '04', label: t.stepper.s4, status: isGranted ? 'completed' : 'current' },
            { index: '05', label: t.stepper.s5, status: isGranted ? 'completed' : 'pending' },
          ]}
          nextDeadline="24 HOURS (EXPIRES 2026-11-02)"
        />

        {/* Consent Specification Banner - STRICTLY LITERAL, ZERO SLANG */}
        <Banner
          type="consent"
          requester="Apex Mutual Bank (Demo)"
          purpose="Lending Credit & Underwriting Verification under DPDPA"
          expiry="24 Hours (Single-Use Wish Token)"
        />

        {!isGranted ? (
          <form onSubmit={handleGrant} className="space-y-6">
            <Section
              index={t.sections.s02.split(' ')[0]}
              title={t.sections.s02.split(' ').slice(1).join(' ')}
              caption="Granular document selection from customer device vault"
            >
              <div className="space-y-3">
                <label className="flex items-start gap-3 p-3 border border-hairline bg-surface rounded-[2px] cursor-pointer min-h-[48px]">
                  <input
                    type="checkbox"
                    checked={selectedDocs.pan}
                    onChange={() => handleToggle('pan')}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-ink">Permanent Account Number (PAN)</span>
                      <span className="font-mono text-[10px] text-status-success uppercase font-bold">
                        IN VAULT ✓
                      </span>
                    </div>
                    <p className="font-mono text-xs text-ink-muted mt-0.5">Masked: ABXXXXXXXF</p>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 border border-hairline bg-surface rounded-[2px] cursor-pointer min-h-[48px]">
                  <input
                    type="checkbox"
                    checked={selectedDocs.aadhaar}
                    onChange={() => handleToggle('aadhaar')}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-ink">Offline Aadhaar XML</span>
                      <span className="font-mono text-[10px] text-status-success uppercase font-bold">
                        IN VAULT ✓
                      </span>
                    </div>
                    <p className="font-mono text-xs text-ink-muted mt-0.5">Last 4 digits: 4321 only</p>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 border border-hairline bg-surface rounded-[2px] cursor-pointer min-h-[48px]">
                  <input
                    type="checkbox"
                    checked={selectedDocs.salary}
                    onChange={() => handleToggle('salary')}
                    className="mt-1"
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-ink">Salary Statement (Q3)</span>
                      <span className="font-mono text-[10px] text-status-missing uppercase font-bold">
                        OPTIONAL
                      </span>
                    </div>
                    <p className="font-mono text-xs text-ink-muted mt-0.5">Withholding marks request as Partial</p>
                  </div>
                </label>
              </div>
            </Section>

            {isWorking ? (
              <div className="p-4 border border-hairline bg-surface rounded-[2px] text-center font-mono text-xs text-ink animate-pulse">
                {t.workingState}
              </div>
            ) : (
              <Button type="submit" variant="primary" className="w-full">
                {t.summonButton}
              </Button>
            )}
          </form>
        ) : (
          <Panel caption="WISH STATUS CONFIRMATION" badge={<StatusDot state="verified" />}>
            <div className="text-center space-y-2 py-4">
              <h2 className="font-serif text-2xl text-ink font-normal">{t.wishGranted}</h2>
              <p className="font-mono text-xs text-ink-muted uppercase">
                PACKAGE REF: <span className="font-bold text-ink">PKG-DJINN-992144</span>
              </p>
              <p className="font-sans text-xs text-ink leading-relaxed max-w-sm mx-auto pt-2">
                Consented documents have been encrypted with the bank's RSA-OAEP public key and securely dispatched. Server copies are queued for retention deletion.
              </p>
            </div>
          </Panel>
        )}
      </main>

      {/* Powered by Djinn Footer Strip */}
      <footer className="w-full border-t border-hairline bg-surface py-3 px-4 flex items-center justify-between text-xs font-mono text-ink-muted">
        <span>{t.poweredBy}</span>
        <button className="underline hover:text-ink">
          {t.createWishLink}
        </button>
      </footer>
    </div>
  );
}
