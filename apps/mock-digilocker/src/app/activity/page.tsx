'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/config';

interface ActivityItem {
  id: string;
  requester: string;
  purpose: string;
  documents: string[];
  timestamp: number;
  expiry: string;
  status: string;
}

interface ConsentItem {
  id: string;
  token: string;
  requester: string;
  scopes: string[];
  granted_at: number;
  status: string;
}

export default function ActivityPage() {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [consents, setConsents] = useState<ConsentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [revoking, setRevoking] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [actRes, cnsRes] = await Promise.all([
        fetch(`${API_URL}/mock-digilocker/activities`),
        fetch(`${API_URL}/mock-digilocker/consents`),
      ]);
      if (actRes.ok) {
        setActivities(await actRes.json());
      }
      if (cnsRes.ok) {
        setConsents(await cnsRes.json());
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (token: string) => {
    const ok = window.confirm(
      'Are you sure you want to revoke consent? This will notify the bank and initiate 24-hour retention deletion.'
    );
    if (!ok) return;

    setRevoking(token);
    try {
      const res = await fetch(`${API_URL}/mock-digilocker/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });
      if (res.ok) {
        alert('Consent revoked. Bank has been notified and retention clock started.');
        loadData();
      }
    } catch {
      alert('Failed to revoke consent');
    } finally {
      setRevoking(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#0F172A]">Activity & Consent Log</h1>
          <p className="text-xs text-[#64748B] mt-0.5">
            Real-time immutable audit trail of institutional data pulls and granted consents.
          </p>
        </div>
        <Link
          href="/"
          className="text-xs font-semibold text-[#0284C7] hover:underline"
        >
          &larr; Back to Issued Documents
        </Link>
      </div>

      {/* Active Consents Section */}
      <div className="bg-white border border-[#CBD5E1] rounded shadow-xs overflow-hidden">
        <div className="bg-[#F8FAFC] border-b border-[#CBD5E1] px-6 py-3">
          <h2 className="font-bold text-xs uppercase tracking-wider text-[#334155]">
            Active Institutional Consents
          </h2>
        </div>

        {loading ? (
          <div className="p-6 text-center text-xs font-mono text-[#64748B]">Loading consents...</div>
        ) : consents.length === 0 ? (
          <div className="p-6 text-center text-xs text-[#64748B]">
            No active third-party consents.
          </div>
        ) : (
          <div className="divide-y divide-[#E2E8F0]">
            {consents.map((c) => (
              <div key={c.id} className="p-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-[#0F172A]">{c.requester}</span>
                    <span
                      className={`font-mono text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                        c.status === 'GRANTED'
                          ? 'bg-[#ECFDF5] text-[#065F46] border border-[#A7F3D0]'
                          : 'bg-[#FEF2F2] text-[#991B1B] border border-[#FECACA]'
                      }`}
                    >
                      {c.status}
                    </span>
                  </div>
                  <div className="text-xs text-[#64748B] mt-1 font-mono">
                    Scopes: {c.scopes.join(', ')} • Granted: {new Date(c.granted_at * 1000).toLocaleString()}
                  </div>
                </div>

                {c.status === 'GRANTED' && (
                  <button
                    onClick={() => handleRevoke(c.token)}
                    disabled={revoking === c.token}
                    className="text-xs font-semibold px-3 py-1.5 border border-[#EF4444] text-[#EF4444] hover:bg-[#FEF2F2] rounded transition-colors"
                  >
                    {revoking === c.token ? 'Revoking...' : 'Revoke Consent'}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Access History Activity Log */}
      <div className="bg-white border border-[#CBD5E1] rounded shadow-xs overflow-hidden">
        <div className="bg-[#F8FAFC] border-b border-[#CBD5E1] px-6 py-3">
          <h2 className="font-bold text-xs uppercase tracking-wider text-[#334155]">
            Data Access Log (Live Stream)
          </h2>
        </div>

        {activities.length === 0 ? (
          <div className="p-6 text-center text-xs text-[#64748B]">
            No access events recorded yet. Complete a wish flow to view logged events.
          </div>
        ) : (
          <div className="divide-y divide-[#E2E8F0]">
            {activities.map((a) => (
              <div key={a.id} className="p-4 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-[#0F172A]">
                    {a.requester} accessed {a.documents.length} documents
                  </span>
                  <span className="font-mono text-xs text-[#64748B]">
                    {new Date(a.timestamp * 1000).toLocaleTimeString()}
                  </span>
                </div>
                <div className="text-xs text-[#64748B]">
                  Purpose: <span className="text-[#334155]">{a.purpose}</span> • Expiry: {a.expiry}
                </div>
                <div className="font-mono text-[11px] text-[#475569] bg-[#F8FAFC] p-2 border border-[#E2E8F0] rounded mt-2">
                  Retrieved items: {a.documents.join(', ')}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
