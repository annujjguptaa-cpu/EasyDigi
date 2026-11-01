'use client';

import React from 'react';

const PORTALS = [
  {
    href: '/bank/dashboard',
    label: 'EXPERIENCE 1: BANK DASHBOARD',
    title: 'Bank Underwriting Workspace',
    desc: 'Staff login, active cases, live notification bell, "Send to Departments", Maker-Checker RBAC.',
    tag: 'EXPERIENCE 1',
    tagColor: 'text-status-verified font-bold',
  },
  {
    href: '/c/demo-clean-token-00000001',
    label: 'EXPERIENCE 2: CUSTOMER LINK',
    title: 'Customer Verification Link',
    desc: 'Signed single-use link, plain-language consent, simulated DigiLocker persona sandbox, zero bank UI.',
    tag: 'EXPERIENCE 2',
    tagColor: 'text-status-flagged font-bold',
  },
  {
    href: '/wish/demo-wish-token-001',
    label: 'CUSTOMER WISH LINK',
    title: 'Djinn Wish Pack Portal',
    desc: 'Trilingual consent flow. Grant, review and revoke document access.',
    tag: 'DJINN WISH PACK',
    tagColor: 'text-status-verified',
  },
  {
    href: '/lender',
    label: 'OPEN BANK PORTAL',
    title: 'Lender Workspace',
    desc: 'Department slices, maker-checker RBAC, watermarked evidence, cited decisions.',
    tag: 'BANK PORTAL',
    tagColor: 'text-status-flagged',
  },
  {
    href: '/insurance',
    label: 'OPEN INSURER PORTAL',
    title: 'Insurance Portal',
    desc: 'Risk slices, underwriting checklist, RSA-encrypted package exchange.',
    tag: 'INSURER PORTAL',
    tagColor: 'text-status-flagged',
  },
  {
    href: '/vault',
    label: 'OPEN DEVICE VAULT',
    title: 'Device Vault',
    desc: 'AES-256-GCM document storage. Encrypted blobs, masked fields, retention schedule.',
    tag: 'VAULT',
    tagColor: 'text-ink-muted',
  },
  {
    href: '/mock-digilocker',
    label: 'OPEN MOCK CONSENT',
    title: 'Mock DigiLocker',
    desc: 'DEMO ONLY — mimics OAuth 2.0 PKCE consent flow. Never connects to real DigiLocker.',
    tag: 'DEMO ONLY',
    tagColor: 'text-status-error',
  },
  {
    href: '/metrics',
    label: 'OPEN METRICS',
    title: 'Platform Metrics',
    desc: 'Consent logs, audit trail, wish ledger, PII-safe operational dashboard.',
    tag: 'OPS',
    tagColor: 'text-ink-muted',
  },
  {
    href: '/design',
    label: 'OPEN DESIGN SYSTEM',
    title: 'Design System',
    desc: '"Precision Instrument on Paper" — tokens, components, dark mode, i18n gallery.',
    tag: 'DEV',
    tagColor: 'text-ink-muted',
  },
];

const API_LINKS = [
  { href: 'http://127.0.0.1:8000/docs', label: 'FastAPI Swagger /docs' },
  { href: 'http://127.0.0.1:8000/api/v1/health', label: 'Health Check' },
  { href: 'http://127.0.0.1:8000/api/v1/wishes/', label: 'Wish API' },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-paper flex flex-col">
      {/* Top Demo Banner */}
      <div className="bg-ink text-paper font-mono text-xs text-center py-2 px-4 tracking-wider">
        DEMO ENVIRONMENT — Not connected to any real financial system or government API
      </div>

      {/* Header */}
      <header className="border-b border-hairline bg-surface px-6 md:px-12 py-6">
        <div className="max-w-6xl mx-auto flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block mb-1">
              EASYDIGI
            </span>
            <h1 className="font-serif text-3xl md:text-4xl text-ink font-normal leading-tight">
              EasyDigi
            </h1>
            <p className="font-sans text-sm text-ink-muted mt-1 max-w-md">
              AI-powered lending document platform. Paper-first design. DPDPA-aligned consent. Code decides eligibility.
            </p>
          </div>
          <div className="flex gap-2">
            {API_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-xs px-3 py-1.5 border border-hairline bg-paper text-ink-muted hover:text-ink rounded-[2px] transition-colors"
              >
                {l.label} ↗
              </a>
            ))}
          </div>
        </div>
      </header>

      {/* Portal Grid */}
      <main className="max-w-6xl mx-auto w-full px-6 md:px-12 py-10 flex-1">
        <div className="mb-6">
          <span className="font-mono text-xs text-ink-muted uppercase tracking-widest">
            01 — PLATFORM PORTALS
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {PORTALS.map((p) => (
            <a
              key={p.href}
              href={p.href}
              className="group flex flex-col justify-between border border-hairline bg-surface hover:bg-paper rounded-[2px] p-5 transition-colors min-h-[160px]"
            >
              <div>
                <span className={`font-mono text-[10px] uppercase font-bold tracking-wider ${p.tagColor}`}>
                  {p.tag}
                </span>
                <h2 className="font-serif text-lg text-ink font-normal mt-1 group-hover:underline">
                  {p.title}
                </h2>
                <p className="font-sans text-xs text-ink-muted leading-relaxed mt-1">
                  {p.desc}
                </p>
              </div>
              <span className="font-mono text-xs text-ink mt-4 group-hover:underline">
                {p.label} →
              </span>
            </a>
          ))}
        </div>

        {/* Architecture note */}
        <div className="mt-12 border-t border-hairline pt-8">
          <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block mb-4">
            02 — ARCHITECTURE QUICK REF
          </span>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs text-ink-muted">
            <div className="border border-hairline bg-surface rounded-[2px] p-4">
              <span className="text-ink font-bold block mb-2">BACKEND</span>
              FastAPI 0.115 · SQLite/aiosqlite · AES-256-GCM + RSA-OAEP<br />
              MockDigiLocker PKCE · DeterministicEligibilityEngine<br />
              PII masking log filter · 36 tests passing
            </div>
            <div className="border border-hairline bg-surface rounded-[2px] p-4">
              <span className="text-ink font-bold block mb-2">FRONTEND</span>
              Next.js 14 · Tailwind CSS · Lucide React<br />
              Paper tokens · Dark mode · EN/HI/Hinglish i18n<br />
              /wish/[token] · /lender · /vault · /design
            </div>
            <div className="border border-hairline bg-surface rounded-[2px] p-4">
              <span className="text-ink font-bold block mb-2">HARD RULES</span>
              No real Aadhaar collected in UI<br />
              Max last-4 digits persisted<br />
              LLM sees masked data only<br />
              Code decides — LLM only explains
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-hairline bg-surface px-6 py-3 flex items-center justify-between font-mono text-xs text-ink-muted">
        <span>Powered by EasyDigi · Demo Build 2026-11</span>
        <span>
          <a href="/design" className="underline hover:text-ink">Create your own wish →</a>
        </span>
      </footer>
    </div>
  );
}
