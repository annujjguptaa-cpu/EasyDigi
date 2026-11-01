'use client';

import React, { useState } from 'react';
import {
  Banner,
  Section,
  Panel,
  Button,
  StatusDot,
} from '@/ui';

export default function MockDigiLockerPage() {
  const [dummyId, setDummyId] = useState('0000 0000 0000');
  const [dummyOtp, setDummyOtp] = useState('123456');
  const [step, setStep] = useState<'AUTH' | 'CONSENT'>('AUTH');
  const [statusMsg, setStatusMsg] = useState('');

  const handleAuthSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setStep('CONSENT');
  };

  const handleDecision = (action: 'ALLOW' | 'DENY') => {
    if (action === 'DENY') {
      setStatusMsg('Consent Denied. No documents or tokens will be issued.');
    } else {
      setStatusMsg('Consent Allowed (Simulated). Redirecting back to EasyDigi...');
    }
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col items-center">
      <Banner type="demo" />

      <main className="max-w-md w-full p-6 mt-6 space-y-6">
        <Banner
          type="consent"
          requester="EasyDigi (Simulated Aggregator)"
          purpose="Simulated Identity Pull (Demo)"
          expiry="10 Minutes (PKCE TTL)"
        />

        <Panel caption="DIGILOCKER / AGGREGATOR SIMULATOR">
          {step === 'AUTH' ? (
            <form onSubmit={handleAuthSubmit} className="space-y-4">
              <div className="p-3 border border-status-flagged/40 bg-status-flagged/10 rounded-[2px] font-mono text-xs text-ink">
                <strong>DEMO ONLY:</strong> Enter any 12 digits and dummy OTP <code>123456</code>. Raw values are discarded immediately without saving.
              </div>

              <div>
                <label className="block font-mono text-xs text-ink-muted uppercase mb-1">
                  DEMO ID / AADHAAR
                </label>
                <input
                  type="text"
                  value={dummyId}
                  onChange={(e) => setDummyId(e.target.value)}
                  className="w-full px-3 py-2 border border-hairline bg-surface text-ink text-sm rounded-[2px] focus:outline-none focus:ring-2 focus:ring-ink"
                />
              </div>

              <div>
                <label className="block font-mono text-xs text-ink-muted uppercase mb-1">
                  DEMO OTP
                </label>
                <input
                  type="text"
                  value={dummyOtp}
                  onChange={(e) => setDummyOtp(e.target.value)}
                  className="w-full px-3 py-2 border border-hairline bg-surface text-ink text-sm rounded-[2px] focus:outline-none focus:ring-2 focus:ring-ink"
                />
              </div>

              <Button type="submit" variant="primary" className="w-full">
                VERIFY & CONTINUE
              </Button>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2 border border-hairline bg-paper/50 p-3 rounded-[2px]">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span>PAN Record</span>
                  <StatusDot state="verified" />
                </div>
                <div className="flex items-center justify-between font-mono text-xs">
                  <span>Aadhaar XML (Masked)</span>
                  <StatusDot state="verified" />
                </div>
                <div className="flex items-center justify-between font-mono text-xs">
                  <span>Salary Statement</span>
                  <StatusDot state="verified" />
                </div>
              </div>

              {statusMsg ? (
                <div className="p-3 border border-status-verified bg-status-verified/10 font-mono text-xs text-ink rounded-[2px]">
                  {statusMsg}
                </div>
              ) : (
                <div className="flex gap-3">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => handleDecision('DENY')}
                    className="flex-1"
                  >
                    DENY
                  </Button>
                  <Button
                    type="button"
                    variant="primary"
                    onClick={() => handleDecision('ALLOW')}
                    className="flex-1"
                  >
                    ALLOW & SHARE
                  </Button>
                </div>
              )}
            </div>
          )}
        </Panel>
      </main>
    </div>
  );
}
