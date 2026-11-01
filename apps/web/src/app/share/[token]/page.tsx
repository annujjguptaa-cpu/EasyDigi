'use client';

import React, { useState } from 'react';
import {
  Banner,
  Section,
  Panel,
  Button,
  StatusDot,
} from '../../../../packages/ui/src';

export default function ShareConsentPage({ params }: { params: { token: string } }) {
  const [selectedDocs, setSelectedDocs] = useState<Record<string, boolean>>({
    pan: true,
    aadhaar: true,
    salary: false,
  });
  const [statusMsg, setStatusMsg] = useState('');

  const handleToggle = (key: string) => {
    setSelectedDocs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleShare = (e: React.FormEvent) => {
    e.preventDefault();
    const isPartial = !Object.values(selectedDocs).every(Boolean);
    setStatusMsg(
      `Package generated with client hybrid encryption (RSA-OAEP + AES-GCM). Status: ${
        isPartial ? 'PARTIAL CONSENT' : 'FULL CONSENT'
      }. Access granted to Apex Mutual Bank.`
    );
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col items-center">
      <Banner type="demo" />

      <main className="max-w-lg w-full p-4 sm:p-6 space-y-6">
        <header className="border-b border-hairline pb-4">
          <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block">
            ONE-TIME ENCRYPTED SHARING
          </span>
          <h1 className="font-serif text-2xl text-ink font-normal">Consent & Document Selection</h1>
        </header>

        {/* Consent Specification Banner */}
        <Banner
          type="consent"
          requester="Apex Mutual Bank (Demo)"
          purpose="Home Loan Underwriting & Regulatory KYC"
          expiry="7 Days (Single-Use Token)"
        />

        <form onSubmit={handleShare} className="space-y-6">
          <Section
            index="01"
            title="Requested Documents"
            caption="Checkboxes allow you to grant or withhold specific items"
          >
            <div className="space-y-3">
              <label className="flex items-start gap-3 p-3 border border-hairline bg-surface rounded-[2px] cursor-pointer">
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
                      IN YOUR VAULT ✓
                    </span>
                  </div>
                  <p className="font-mono text-xs text-ink-muted mt-0.5">Masked: ABXXXXXXXF</p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 border border-hairline bg-surface rounded-[2px] cursor-pointer">
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
                      IN YOUR VAULT ✓
                    </span>
                  </div>
                  <p className="font-mono text-xs text-ink-muted mt-0.5">Last 4 digits: 4321 only</p>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3 border border-hairline bg-surface rounded-[2px] cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedDocs.salary}
                  onChange={() => handleToggle('salary')}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-ink">Salary Slip (Q3)</span>
                    <span className="font-mono text-[10px] text-status-missing uppercase font-bold">
                      OPTIONAL / DENIABLE
                    </span>
                  </div>
                  <p className="font-mono text-xs text-ink-muted mt-0.5">Withholding marks request as Partial</p>
                </div>
              </label>
            </div>
          </Section>

          {statusMsg ? (
            <div className="p-4 border border-status-verified bg-status-verified/10 rounded-[2px] font-mono text-xs text-ink">
              {statusMsg}
            </div>
          ) : (
            <div className="space-y-3">
              <Button type="submit" variant="primary" className="w-full">
                ENCRYPT & SHARE CONSENTED PACKAGE
              </Button>
              <Button type="button" variant="secondary" className="w-full">
                CANCEL REQUEST
              </Button>
            </div>
          )}
        </form>
      </main>
    </div>
  );
}
