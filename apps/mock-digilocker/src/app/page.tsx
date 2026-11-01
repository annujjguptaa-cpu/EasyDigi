'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { API_URL } from '@/lib/config';

interface DocItem {
  id: string;
  type: string;
  title: string;
  issuer: string;
  date: string;
  shared_with: string | null;
}

interface ProfileData {
  profile_key: string;
  name: string;
  mobile_masked: string;
  aadhaar_last4: string;
  documents: DocItem[];
}

export default function DigiLockerHomePage() {
  const [profileKey, setProfileKey] = useState('clean_file');
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem('dl_current_profile');
    if (stored) {
      setProfileKey(stored);
    }
  }, []);

  useEffect(() => {
    loadProfileDocs();
    const interval = setInterval(loadProfileDocs, 4000);
    return () => clearInterval(interval);
  }, [profileKey]);

  const loadProfileDocs = async () => {
    try {
      const res = await fetch(`${API_URL}/mock-digilocker/profile/${profileKey}`);
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* User Header Profile */}
      <div className="bg-white border border-[#CBD5E1] p-6 rounded shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="text-[10px] font-mono uppercase text-[#64748B] block">Citizen Account</span>
          <h1 className="text-xl font-bold text-[#0F172A]">{profile?.name || 'Rahul Verma'}</h1>
          <div className="text-xs text-[#64748B] font-mono mt-0.5">
            Aadhaar: XXXX-XXXX-{profile?.aadhaar_last4 || '4001'} • Mobile: {profile?.mobile_masked || 'XXXXXX9921'}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/signin"
            className="text-xs font-semibold text-[#0284C7] border border-[#0284C7] px-3 py-1.5 rounded hover:bg-[#F0F9FF]"
          >
            Switch Profile
          </Link>
          <Link
            href="/activity"
            className="text-xs font-semibold bg-[#0284C7] text-white px-3 py-1.5 rounded hover:bg-[#0369A1]"
          >
            View Activity Log &rarr;
          </Link>
        </div>
      </div>

      {/* Issued Documents Section */}
      <div className="bg-white border border-[#CBD5E1] rounded shadow-xs overflow-hidden">
        <div className="bg-[#F8FAFC] border-b border-[#CBD5E1] px-6 py-3 flex items-center justify-between">
          <h2 className="font-bold text-xs uppercase tracking-wider text-[#334155]">
            Issued Documents (Verified Repositories)
          </h2>
          <span className="text-xs font-mono text-[#64748B]">
            Total: {profile?.documents.length || 0}
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs font-mono text-[#64748B]">
            Syncing documents with state repositories...
          </div>
        ) : (
          <div className="divide-y divide-[#E2E8F0]">
            {profile?.documents.map((doc) => (
              <div key={doc.id} className="p-4 flex items-center justify-between hover:bg-[#F8FAFC]">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-[#0F172A]">{doc.title}</span>
                    {doc.shared_with && (
                      <span className="bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] font-mono text-[10px] px-2 py-0.5 rounded font-semibold">
                        Shared with {doc.shared_with}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-[#64748B]">
                    Issued by <span className="font-medium text-[#334155]">{doc.issuer}</span> • Date: {doc.date}
                  </div>
                </div>

                <button
                  onClick={() => alert(`Simulated document view for: ${doc.title}`)}
                  className="text-xs font-mono text-[#0284C7] hover:underline"
                >
                  View Record
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
