'use client';

import React, { useState } from 'react';
import {
  Section,
  Panel,
  Button,
  StatusDot,
  DocumentRow,
  Stepper,
  Banner,
  Table,
} from '@/ui';

export default function DesignSystemGalleryPage() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
  };

  const sampleDocs = [
    {
      id: 'DOC-8821',
      docType: 'Permanent Account Number (PAN)',
      maskedFields: { pan: 'ABXXXXXXXF', name: 'Rahul Verma' },
      status: 'verified' as const,
      source: 'DigiLocker' as const,
    },
    {
      id: 'DOC-8822',
      docType: 'Offline Aadhaar XML',
      maskedFields: { id_last4: '4321', name: 'Rahul Verma' },
      status: 'verified' as const,
      source: 'DigiLocker' as const,
    },
    {
      id: 'DOC-8823',
      docType: 'Salary Statement (Q3)',
      maskedFields: { employer: 'Apex Cloud Systems', net_pay: '85,000' },
      status: 'flagged' as const,
      source: 'Upload' as const,
    },
    {
      id: 'DOC-8824',
      docType: 'Graduation Degree Certificate',
      maskedFields: { degree: 'B.Tech CS' },
      status: 'missing' as const,
      source: 'Upload' as const,
    },
  ];

  return (
    <div className="min-h-screen p-6 md:p-12 max-w-6xl mx-auto space-y-12 transition-colors">
      <header className="flex flex-wrap items-center justify-between border-b border-hairline pb-4 gap-4">
        <div>
          <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block">
            EASYDIGI DESIGN SYSTEM
          </span>
          <h1 className="font-serif text-3xl text-ink font-normal tracking-tight mt-1">
            Precision Instrument on Paper
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={toggleTheme}>
            THEME: {theme.toUpperCase()}
          </Button>
        </div>
      </header>

      {/* 01 BANNER PATTERNS */}
      <Section index="01" title="Banners & Consent Specifications" caption="Permanent demo notice & explicit consent metadata">
        <div className="space-y-4">
          <Banner type="demo" />
          <Banner
            type="consent"
            requester="Apex Mutual Bank (Demo)"
            purpose="Lending Credit & Underwriting Verification"
            expiry="7 Days (Auto-Revoked)"
          />
        </div>
      </Section>

      {/* 02 STATUS DOTS & LEGEND */}
      <Section index="02" title="Status Indicators" caption="Never conveyed by colour alone (paired with icon and label)">
        <div className="flex flex-wrap items-center gap-6 p-4 border border-hairline bg-surface rounded-[2px]">
          <StatusDot state="verified" />
          <StatusDot state="flagged" />
          <StatusDot state="missing" />
          <StatusDot state="error" />
          <StatusDot state="success" />
        </div>
      </Section>

      {/* 03 STEPPERS */}
      <Section index="03" title="Timeline & Stepper" caption="Numbered stages with hairline connectors">
        <Stepper
          steps={[
            { index: '01', label: 'Consent Link', status: 'completed' },
            { index: '02', label: 'DigiLocker Mock', status: 'completed' },
            { index: '03', label: 'Agent Gap Fill', status: 'current' },
            { index: '04', label: 'Device Vault', status: 'pending' },
            { index: '05', label: 'Bank Review', status: 'pending' },
          ]}
          nextDeadline="04 NOV 2026 18:00 UTC"
        />
      </Section>

      {/* 04 PANELS & BUTTONS */}
      <Section index="04" title="Panels & Actions" caption="Single black action button, outlined secondary actions">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Panel caption="PRIMARY DECISION PANEL" badge={<StatusDot state="verified" />}>
            <p className="font-sans text-sm text-ink mb-4">
              All identity credentials have been cross-verified against official registers.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button variant="primary">CONTINUE TO VAULT</Button>
              <Button variant="secondary">VIEW DETAILS</Button>
            </div>
          </Panel>

          <Panel caption="DATA MINIMIZATION NOTICE">
            <p className="font-sans text-sm text-ink mb-4">
              Documents are retained inside your personal device vault. The bank only receives permitted department slices.
            </p>
            <Button variant="danger">REVOKE CONSENT</Button>
          </Panel>
        </div>
      </Section>

      {/* 05 DOCUMENT LIST ROWS */}
      <Section index="05" title="Document List Rows" caption="Mono file ID, masked fields, and verified status">
        <div className="border border-hairline bg-surface rounded-[2px] divide-y divide-hairline">
          {sampleDocs.map((doc) => (
            <DocumentRow
              key={doc.id}
              id={doc.id}
              docType={doc.docType}
              maskedFields={doc.maskedFields}
              status={doc.status}
              source={doc.source}
            />
          ))}
        </div>
      </Section>

      {/* 06 DENSE DESKTOP TABLE */}
      <Section index="06" title="Table Pattern (Bank & Insurer Portal)" caption="Dense layout with internal horizontal scroll">
        <Table
          caption="ACTIVE LENDING VERIFICATION CASES"
          data={sampleDocs}
          keyExtractor={(d) => d.id}
          columns={[
            { header: 'FILE ID', accessor: (d) => <span className="font-mono text-ink-muted">{d.id}</span> },
            { header: 'DOCUMENT TYPE', accessor: (d) => <span className="font-semibold text-ink">{d.docType}</span> },
            { header: 'SOURCE', accessor: (d) => <span className="font-mono text-[10px] uppercase text-ink-muted">{d.source}</span> },
            { header: 'STATUS', accessor: (d) => <StatusDot state={d.status} /> },
            {
              header: 'ACTION',
              accessor: () => (
                <button className="font-mono text-xs underline text-ink hover:text-ink-muted">
                  INSPECT
                </button>
              ),
            },
          ]}
        />
      </Section>
    </div>
  );
}
