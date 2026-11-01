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

export default function InsurancePortalPage() {
  const [activeStage, setActiveStage] = useState<'01' | '02' | '03' | '04' | '05'>('03');

  const claims = [
    {
      id: 'CLM-7701',
      claimant: 'Rahul Verma',
      policyType: 'Health Inpatient (Cashless)',
      amount: '₹1,45,000',
      evidenceDocs: 'Discharge Summary, Hospital Bill, Pharmacy Receipts',
      checksStatus: 'verified' as const,
      reviewDecision: 'READY',
    },
    {
      id: 'CLM-7702',
      claimant: 'Priya S. Sharma',
      policyType: 'Motor Own-Damage',
      amount: '₹32,500',
      evidenceDocs: 'Driving License, Repair Estimate, Incident Photo',
      checksStatus: 'flagged' as const,
      reviewDecision: 'NAME MISMATCH',
    },
  ];

  return (
    <div className="min-h-screen bg-paper flex flex-col">
      <Banner type="demo" />

      {/* Header */}
      <header className="border-b border-hairline bg-surface px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="font-mono text-xs text-ink-muted uppercase">INSURANCE CLAIMS PROCESSING</span>
          <h1 className="font-serif text-2xl text-ink font-normal">DocFlow Insurer Workspace</h1>
        </div>
        <div className="flex gap-2">
          {(['01 INTIMATION', '02 EVIDENCE', '03 CHECKS', '04 REVIEW', '05 SETTLEMENT'] as const).map((stage) => {
            const num = stage.split(' ')[0] as any;
            return (
              <button
                key={stage}
                onClick={() => setActiveStage(num)}
                className={`font-mono text-xs px-3 py-1.5 rounded-[2px] border transition ${
                  activeStage === num
                    ? 'border-ink bg-ink text-paper font-semibold'
                    : 'border-hairline bg-paper text-ink-muted hover:text-ink'
                }`}
              >
                {stage}
              </button>
            );
          })}
        </div>
      </header>

      {/* Main Workspace */}
      <main className="max-w-6xl mx-auto w-full p-6 space-y-6">
        <Section
          index={activeStage}
          title={
            activeStage === '01'
              ? 'Intimation & First Notice of Loss'
              : activeStage === '02'
              ? 'Customer Consented Evidence'
              : activeStage === '03'
              ? 'Cross-Check & Fraud Anomaly Engine'
              : activeStage === '04'
              ? 'Medical / Technical Review Slice'
              : 'Settlement & Approval Verdict'
          }
          caption="Claims evaluation with immutable cryptographic verification"
        >
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Table
                caption="ACTIVE CLAIMS IN QUEUE"
                data={claims}
                keyExtractor={(c) => c.id}
                columns={[
                  { header: 'CLAIM ID', accessor: (c) => <span className="font-mono text-ink-muted">{c.id}</span> },
                  { header: 'CLAIMANT', accessor: (c) => <span className="font-semibold text-ink">{c.claimant}</span> },
                  { header: 'POLICY TYPE', accessor: (c) => <span>{c.policyType}</span> },
                  { header: 'CLAIMED', accessor: (c) => <span className="font-mono">{c.amount}</span> },
                  { header: 'CHECKS', accessor: (c) => <StatusDot state={c.checksStatus} /> },
                ]}
              />

              {/* Watermarked Document Preview */}
              <Panel caption="DOCUMENT VIEWER (STAFF WATERMARK ACTIVE)">
                <div className="relative border border-hairline bg-paper p-8 rounded-[2px] min-h-[220px] flex flex-col justify-center items-center text-center">
                  <div className="absolute inset-0 flex items-center justify-center opacity-10 pointer-events-none select-none text-2xl font-mono uppercase tracking-widest text-ink rotate-[-15deg]">
                    APEX CLAIMS • VERIFIED BY USER-MED-09 • 2026-11-01
                  </div>
                  <p className="font-serif text-lg text-ink">Inpatient Discharge Summary</p>
                  <p className="font-mono text-xs text-ink-muted mt-1">
                    SHA-256 Digest Verified • Encrypted Device Vault Slice
                  </p>
                </div>
              </Panel>
            </div>

            {/* Sidebar Review & Cited Summary */}
            <div className="space-y-6">
              <Panel caption="CITED COVERAGE SUMMARY" badge={<StatusDot state="verified" />}>
                <p className="font-sans text-xs text-ink leading-relaxed mb-4">
                  "Claimant Rahul Verma has an active Comprehensive Health Shield policy [POLICY Ref: POL-881]. Admission duration and diagnosis verified against hospital discharge record [HOSPITAL Ref: MED-992]. Code outcome: COVERAGE_APPROVED."
                </p>
                <div className="border-t border-hairline pt-3 flex flex-col gap-2">
                  <Button variant="primary" className="w-full">
                    APPROVE SETTLEMENT
                  </Button>
                  <Button variant="secondary" className="w-full">
                    RAISE QUERY TO CUSTOMER
                  </Button>
                </div>
              </Panel>

              <Panel caption="FRAUD & ANOMALY CHECKS">
                <div className="space-y-2 text-xs font-mono">
                  <div className="flex justify-between items-center text-status-success">
                    <span>Identity Cross-Check:</span>
                    <span>MATCH (100%)</span>
                  </div>
                  <div className="flex justify-between items-center text-status-success">
                    <span>Policy Inception Lag:</span>
                    <span>PASS (>90 DAYS)</span>
                  </div>
                  <div className="flex justify-between items-center text-status-success">
                    <span>Duplicate Claim Scan:</span>
                    <span>CLEAR</span>
                  </div>
                </div>
              </Panel>
            </div>
          </div>
        </Section>
      </main>
    </div>
  );
}
