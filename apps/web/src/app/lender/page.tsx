'use client';

import React, { useState } from 'react';
import {
  Banner,
  Section,
  Panel,
  Button,
  StatusDot,
  Table,
} from '@/ui';

export default function LenderPortalPage() {
  const [selectedDept, setSelectedDept] = useState<'KYC' | 'RISK' | 'CREDIT' | 'OPERATIONS'>('KYC');

  const cases = [
    {
      id: 'REQ-CLEAN-9921',
      customer: 'Rahul Verma',
      product: 'Personal Loan',
      amount: '₹5,00,000',
      status: 'success' as const,
      readiness: 'GREEN (100%)',
    },
    {
      id: 'REQ-MISMATCH-9922',
      customer: 'Priya S. Sharma',
      product: 'Auto Loan',
      amount: '₹7,50,000',
      status: 'flagged' as const,
      readiness: 'AMBER (70%)',
    },
    {
      id: 'REQ-MISSING-9923',
      customer: 'Amit Patel',
      product: 'Education Loan',
      amount: '₹12,00,000',
      status: 'missing' as const,
      readiness: 'RED (30%)',
    },
  ];

  return (
    <div className="min-h-screen bg-paper flex flex-col">
      <Banner type="demo" />

      {/* Header */}
      <header className="border-b border-hairline bg-surface px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="font-mono text-xs text-ink-muted uppercase">LENDING UNDERWRITING PORTAL</span>
          <h1 className="font-serif text-2xl text-ink font-normal">Apex Mutual Bank Workspace</h1>
        </div>
        <div className="flex gap-2 font-mono text-xs">
          {(['KYC', 'RISK', 'CREDIT', 'OPERATIONS'] as const).map((dept) => (
            <button
              key={dept}
              onClick={() => setSelectedDept(dept)}
              className={`px-3 py-1.5 rounded-[2px] border transition ${
                selectedDept === dept
                  ? 'border-ink bg-ink text-paper font-semibold'
                  : 'border-hairline bg-paper text-ink-muted hover:text-ink'
              }`}
            >
              {dept} SLICE
            </button>
          ))}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto w-full p-6 space-y-6">
        <Section
          index="01"
          title="Active Lending Requests & Readiness"
          caption="Data minimization: showing only permitted department slice"
        >
          <Table
            caption="BORROWER VERIFICATION PIPELINE"
            data={cases}
            keyExtractor={(c) => c.id}
            columns={[
              { header: 'REQ CODE', accessor: (c) => <span className="font-mono text-ink-muted">{c.id}</span> },
              { header: 'APPLICANT', accessor: (c) => <span className="font-semibold text-ink">{c.customer}</span> },
              { header: 'LOAN PRODUCT', accessor: (c) => <span>{c.product}</span> },
              { header: 'REQUESTED', accessor: (c) => <span className="font-mono">{c.amount}</span> },
              { header: 'STATUS', accessor: (c) => <StatusDot state={c.status} label={c.readiness} /> },
            ]}
          />
        </Section>

        <Section
          index="02"
          title={`Department Workspace: ${selectedDept}`}
          caption="Strict maker-checker RBAC and watermarked evidence view"
        >
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Watermarked Document Preview */}
              <Panel caption={`WATERMARKED EVIDENCE (${selectedDept} SLICE ONLY)`}>
                <div className="relative border border-hairline bg-paper p-8 rounded-[2px] min-h-[220px] flex flex-col justify-center items-center text-center">
                  <div className="absolute inset-0 flex items-center justify-center opacity-10 pointer-events-none select-none text-2xl font-mono uppercase tracking-widest text-ink rotate-[-15deg]">
                    APEX BANK • {selectedDept} OFFICER • 2026-11-01
                  </div>
                  <p className="font-serif text-lg text-ink">
                    {selectedDept === 'KYC'
                      ? 'Offline Aadhaar XML & PAN Record'
                      : selectedDept === 'RISK' || selectedDept === 'CREDIT'
                      ? 'Verified Q3 Salary Statement & Tax Return'
                      : 'Signed Mandate & Academic Marksheet'}
                  </p>
                  <p className="font-mono text-xs text-ink-muted mt-1">
                    Masked: Only authorized fields decrypted via Bank RSA-OAEP Key
                  </p>
                </div>
              </Panel>
            </div>

            {/* Cited Decision Panel */}
            <div className="space-y-6">
              <Panel caption="CITED SUMMARY & REASON CODES" badge={<StatusDot state="verified" />}>
                <p className="font-sans text-xs text-ink leading-relaxed mb-4">
                  "Identity credentials cross-matched successfully [PAN Ref: DOC-8821] [AADHAAR_OFFLINE Ref: DOC-8822]. Deterministic code evaluation: ELIGIBLE."
                </p>
                <div className="border-t border-hairline pt-3 flex flex-col gap-2">
                  <Button variant="primary" className="w-full">
                    APPROVE CASE (CHECKER)
                  </Button>
                  <Button variant="secondary" className="w-full">
                    RAISE CONSOLIDATED QUERY
                  </Button>
                </div>
              </Panel>
            </div>
          </div>
        </Section>
      </main>
    </div>
  );
}
