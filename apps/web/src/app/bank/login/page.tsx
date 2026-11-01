'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Panel, Table } from '@/ui';
import { storeUser, authHeader } from '@/lib/auth';

const API = 'http://127.0.0.1:8000/api/v1';

const SEEDED_STAFF = [
  { email: 'employee@apexbank-demo.com', role: 'Relationship Employee', dept: 'KYC' },
  { email: 'kyc_officer@apexbank-demo.com', role: 'KYC Officer', dept: 'KYC' },
  { email: 'credit_manager@apexbank-demo.com', role: 'Credit Manager', dept: 'CREDIT' },
  { email: 'credit_head@apexbank-demo.com', role: 'Credit Head', dept: 'CREDIT' },
  { email: 'risk_analyst@apexbank-demo.com', role: 'Risk Analyst', dept: 'RISK' },
  { email: 'legal_officer@apexbank-demo.com', role: 'Legal Officer', dept: 'LEGAL' },
  { email: 'tech_officer@apexbank-demo.com', role: 'Technical Officer', dept: 'TECHNICAL' },
  { email: 'ops_specialist@apexbank-demo.com', role: 'Operations', dept: 'OPERATIONS' },
];

export default function BankLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) { setError('Please enter or select an email.'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${API}/bank/me`, { headers: authHeader(email.trim()) });
      if (res.ok) {
        const data = await res.json();
        storeUser({
          email: data.email ?? email.trim(),
          role: data.role ?? '',
          department: data.department ?? '',
          id: data.id ?? '',
        });
        router.push('/bank/dashboard');
      } else if (res.status === 401) {
        setError('Invalid credentials. Use one of the seeded accounts below.');
      } else {
        setError(`Server error (${res.status}). Make sure the backend is running at ${API}.`);
      }
    } catch {
      setError('Cannot reach backend. Ensure FastAPI server is running at http://127.0.0.1:8000.');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { header: 'Email', accessor: (r: typeof SEEDED_STAFF[0]) => <span className="font-mono text-xs">{r.email}</span> },
    { header: 'Role', accessor: (r: typeof SEEDED_STAFF[0]) => r.role },
    { header: 'Dept', accessor: (r: typeof SEEDED_STAFF[0]) => r.dept },
    {
      header: 'Use',
      accessor: (r: typeof SEEDED_STAFF[0]) => (
        <button
          type="button"
          onClick={() => setEmail(r.email)}
          className="font-mono text-[10px] uppercase tracking-wider text-ink underline hover:no-underline"
        >
          Select
        </button>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-paper flex flex-col">
      {/* Demo banner */}
      <div className="bg-ink text-paper font-mono text-xs text-center py-2 px-4 tracking-wider">
        DEMO ENVIRONMENT — Not connected to any real financial system
      </div>

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-md space-y-8">
          {/* Logo / brand */}
          <div className="text-center">
            <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block mb-2">EASYDIGI</span>
            <h1 className="font-serif text-3xl text-ink font-normal">Bank Staff Login</h1>
            <p className="font-mono text-xs text-ink-muted mt-2">Apex Mutual Bank (Demo)</p>
          </div>

          {/* Login card */}
          <Panel>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-1.5">
                <label className="font-mono text-xs text-ink-muted uppercase tracking-wider block">
                  Staff Email
                </label>
                {/* Quick-select dropdown */}
                <select
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full border border-hairline bg-paper text-ink font-mono text-xs px-3 py-2 rounded-[2px] focus:outline-none focus:ring-1 focus:ring-ink mb-2"
                >
                  <option value="">— Select a seeded account —</option>
                  {SEEDED_STAFF.map((s) => (
                    <option key={s.email} value={s.email}>
                      {s.email} ({s.role})
                    </option>
                  ))}
                </select>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="or type your email"
                  className="w-full border border-hairline bg-paper text-ink font-mono text-xs px-3 py-2 rounded-[2px] focus:outline-none focus:ring-1 focus:ring-ink"
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-mono text-xs text-ink-muted uppercase tracking-wider block">
                  Password
                </label>
                <input
                  type="password"
                  defaultValue="demo1234"
                  readOnly
                  className="w-full border border-hairline bg-surface text-ink-muted font-mono text-xs px-3 py-2 rounded-[2px]"
                />
                <p className="font-mono text-[10px] text-ink-muted">Demo mode — password is always demo1234</p>
              </div>

              {error && (
                <div className="border border-status-error bg-status-error/10 rounded-[2px] px-3 py-2 font-mono text-xs text-status-error">
                  {error}
                </div>
              )}

              <Button type="submit" variant="primary" className="w-full" disabled={loading}>
                {loading ? 'SIGNING IN…' : 'SIGN IN'}
              </Button>
            </form>
          </Panel>

          {/* Seeded accounts reference */}
          <div className="space-y-2">
            <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block">
              Demo Accounts
            </span>
            <Table
              columns={columns}
              data={SEEDED_STAFF}
              keyExtractor={(r) => r.email}
            />
          </div>
        </div>
      </main>

      <footer className="border-t border-hairline bg-surface px-6 py-3 font-mono text-xs text-ink-muted text-center">
        EasyDigi · Demo Build 2026-11 · Backend at http://127.0.0.1:8000
      </footer>
    </div>
  );
}
