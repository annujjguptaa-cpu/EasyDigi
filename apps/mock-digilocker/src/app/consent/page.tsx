'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { API_URL } from '@/lib/config';

function ConsentForm() {
  const searchParams = useSearchParams();

  const token = searchParams.get('token') || '';
  const requester = searchParams.get('requester') || 'Apex Mutual Bank';
  const purpose = searchParams.get('purpose') || 'Home Loan Underwriting';
  const scopesRaw = searchParams.get('scopes') || 'PAN,AADHAAR_OFFLINE';
  const redirectUri = searchParams.get('redirect_uri') || '';

  const scopes = scopesRaw.split(',').filter(Boolean);

  const [loading, setLoading] = useState(false);
  const [profileKey, setProfileKey] = useState('clean_file');

  useEffect(() => {
    const stored = localStorage.getItem('dl_current_profile');
    if (stored) {
      setProfileKey(stored);
    }
  }, []);

  const handleAllow = async () => {
    setLoading(true);
    try {
      // 1. Submit consent grant to API
      await fetch(`${API_URL}/c/${token}/consent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agreed: true }),
      });

      // 2. Fetch/submit matching documents from current profile
      await fetch(`${API_URL}/c/${token}/documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_key: profileKey,
          selected_documents: scopes,
        }),
      });

      // 3. Return to customer wish page
      if (redirectUri) {
        window.location.href = redirectUri;
      } else {
        alert('Consent granted! You can now return to the application tab.');
      }
    } catch {
      alert('Error recording consent grant');
      setLoading(false);
    }
  };

  const handleDeny = async () => {
    try {
      await fetch(`${API_URL}/c/${token}/decline`, { method: 'POST' });
    } catch {
      // ignore
    }
    if (redirectUri) {
      window.location.href = redirectUri;
    } else {
      window.close();
    }
  };

  return (
    <div className="max-w-lg mx-auto my-8 bg-white border border-[#CBD5E1] rounded shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-[#0284C7] text-white p-6 text-center">
        <h1 className="text-xl font-bold">Data Sharing Consent Request</h1>
        <p className="text-xs text-[#E0F2FE] mt-1">
          Government Certified DigiLocker Gateway
        </p>
      </div>

      <div className="p-6 space-y-6">
        <div className="border-b border-[#E2E8F0] pb-4">
          <span className="text-[10px] font-mono uppercase text-[#64748B] block">Requester Entity</span>
          <div className="text-base font-bold text-[#0F172A]">{requester}</div>
          <div className="text-xs text-[#64748B] mt-0.5">Purpose: {purpose}</div>
        </div>

        <div>
          <span className="text-xs font-semibold text-[#334155] uppercase tracking-wider block mb-2">
            Requested Document Records ({scopes.length})
          </span>
          <div className="space-y-2">
            {scopes.map((s) => (
              <div
                key={s}
                className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded flex items-center justify-between text-xs"
              >
                <span className="font-mono font-bold text-[#0F172A]">{s}</span>
                <span className="text-[10px] bg-[#E0F2FE] text-[#0284C7] font-semibold px-2 py-0.5 rounded">
                  Read Access
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="p-3 bg-[#F1F5F9] border border-[#CBD5E1] text-[11px] text-[#475569] rounded leading-relaxed">
          <strong>Privacy Declaration:</strong> By clicking &ldquo;Allow&rdquo;, you permit {requester} to pull
          the above verified credentials. Only masked fields are transferred over an encrypted tunnel.
        </div>

        <div className="flex items-center justify-between gap-4 pt-2">
          <button
            type="button"
            onClick={handleDeny}
            className="w-1/2 py-2.5 border border-[#EF4444] text-[#EF4444] hover:bg-[#FEF2F2] text-xs font-bold rounded uppercase tracking-wider transition-colors"
          >
            Deny
          </button>
          <button
            type="button"
            onClick={handleAllow}
            disabled={loading}
            className="w-1/2 py-2.5 bg-[#0284C7] hover:bg-[#0369A1] text-white text-xs font-bold rounded uppercase tracking-wider transition-colors"
          >
            {loading ? 'Processing...' : 'Allow Access'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ConsentPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-xs font-mono text-[#64748B]">
          Loading consent parameters...
        </div>
      }
    >
      <ConsentForm />
    </Suspense>
  );
}
