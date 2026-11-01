'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function SignInPage() {
  const router = useRouter();
  const [aadhaarInput, setAadhaarInput] = useState('');
  const [otpInput, setOtpInput] = useState('');
  const [step, setStep] = useState<'aadhaar' | 'otp'>('aadhaar');
  const [selectedProfile, setSelectedProfile] = useState('clean_file');

  const handleAadhaarSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (aadhaarInput.length < 4) {
      alert('Please enter any 12-digit demo Aadhaar number');
      return;
    }
    setStep('otp');
  };

  const handleOtpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Save chosen profile in localStorage
    localStorage.setItem('dl_current_profile', selectedProfile);
    localStorage.setItem('dl_aadhaar_last4', aadhaarInput.slice(-4));
    router.push('/');
  };

  return (
    <div className="max-w-md mx-auto my-12 bg-white border border-[#CBD5E1] p-8 rounded shadow-xs space-y-6">
      <div className="text-center">
        <h1 className="text-xl font-bold text-[#0F172A]">Sign In to DigiLocker Sandbox</h1>
        <p className="text-xs text-[#64748B] mt-1">
          Demo identity gateway. Enter any dummy 12-digit Aadhaar / Mobile number.
        </p>
      </div>

      {/* Profile Selector */}
      <div>
        <label className="block text-xs font-semibold text-[#334155] mb-2 uppercase tracking-wider">
          Choose Demo Persona
        </label>
        <div className="space-y-2">
          {[
            { id: 'clean_file', name: 'Rahul Verma', desc: 'Clean profile — 100% records present' },
            { id: 'name_mismatch', name: 'Priya S. Sharma', desc: 'Name discrepancy between PAN & Aadhaar' },
            { id: 'missing_docs', name: 'Amit Patel', desc: 'Missing salary slips and education records' },
          ].map((p) => (
            <label
              key={p.id}
              onClick={() => setSelectedProfile(p.id)}
              className={`block p-3 border rounded cursor-pointer transition-colors ${
                selectedProfile === p.id
                  ? 'border-[#0284C7] bg-[#F0F9FF]'
                  : 'border-[#E2E8F0] hover:bg-[#F8FAFC]'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-[#0F172A]">{p.name}</span>
                <input
                  type="radio"
                  name="persona"
                  checked={selectedProfile === p.id}
                  onChange={() => {}}
                />
              </div>
              <div className="text-[11px] text-[#64748B] mt-0.5">{p.desc}</div>
            </label>
          ))}
        </div>
      </div>

      {step === 'aadhaar' ? (
        <form onSubmit={handleAadhaarSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#334155] mb-1">
              Demo Aadhaar / Mobile Number
            </label>
            <input
              type="text"
              required
              value={aadhaarInput}
              onChange={(e) => setAadhaarInput(e.target.value)}
              placeholder="e.g. 5555 4444 3333"
              className="w-full border border-[#CBD5E1] p-2.5 text-sm rounded font-mono focus:outline-[#0284C7]"
            />
            <span className="text-[10px] text-[#64748B] block mt-1">
              Hint: Enter any 12 digits. Only the last 4 digits are retained in memory.
            </span>
          </div>

          <button
            type="submit"
            className="w-full bg-[#0284C7] hover:bg-[#0369A1] text-white py-2.5 text-xs font-bold rounded uppercase tracking-wider transition-colors"
          >
            Continue &rarr;
          </button>
        </form>
      ) : (
        <form onSubmit={handleOtpSubmit} className="space-y-4">
          <div className="p-3 bg-[#FEF3C7] border border-[#FDE68A] text-xs text-[#92400E] rounded">
            <strong>Demo OTP Hint:</strong> Enter <span className="font-mono font-bold">123456</span>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#334155] mb-1">
              One-Time Password (OTP)
            </label>
            <input
              type="text"
              required
              value={otpInput}
              onChange={(e) => setOtpInput(e.target.value)}
              placeholder="123456"
              className="w-full border border-[#CBD5E1] p-2.5 text-sm rounded font-mono text-center tracking-widest focus:outline-[#0284C7]"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-[#0284C7] hover:bg-[#0369A1] text-white py-2.5 text-xs font-bold rounded uppercase tracking-wider transition-colors"
          >
            Verify & Sign In
          </button>
        </form>
      )}
    </div>
  );
}
