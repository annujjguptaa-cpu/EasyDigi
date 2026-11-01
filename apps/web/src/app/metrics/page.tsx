'use client';

import React from 'react';
import {
  Banner,
  Section,
  Panel,
  StatusDot,
} from '@/ui';

export default function MetricsPage() {
  const metrics = {
    avgTimeToComplete: '4.2 Minutes',
    followUpsPerFile: '0.4 (Down from 3.2)',
    readinessDistribution: {
      green: '78%',
      amber: '16%',
      red: '6%',
    },
    baselineComparison: [
      {
        metric: 'Turnaround Time (TAT)',
        docflow: '4.2 Minutes',
        traditional: '3 to 5 Days',
        improvement: '98% Reduction',
      },
      {
        metric: 'Customer Document Drop-off',
        docflow: '8.4%',
        traditional: '42.0%',
        improvement: '80% Lower Drop-off',
      },
      {
        metric: 'Cross-Check Verification Cost',
        docflow: '₹18 / file',
        traditional: '₹450 / file',
        improvement: '96% Cost Savings',
      },
    ],
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col items-center">
      <Banner type="demo" />

      <main className="max-w-5xl w-full p-4 sm:p-6 space-y-6">
        <header className="border-b border-hairline pb-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="font-mono text-xs text-ink-muted uppercase tracking-widest block">
              PLATFORM OPERATIONAL EFFICIENCY
            </span>
            <h1 className="font-serif text-2xl text-ink font-normal">DocFlow Analytics & Readiness</h1>
          </div>
          <div className="font-mono text-xs text-ink-muted">
            LAST UPDATED: 2026-11-01 19:45 UTC
          </div>
        </header>

        {/* Top KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Panel caption="AVG TIME TO COMPLETE">
            <p className="font-serif text-3xl text-ink">{metrics.avgTimeToComplete}</p>
            <p className="font-mono text-xs text-status-success mt-1">From consent link to bank file ready</p>
          </Panel>

          <Panel caption="FOLLOW-UPS PER FILE">
            <p className="font-serif text-3xl text-ink">{metrics.followUpsPerFile}</p>
            <p className="font-mono text-xs text-status-success mt-1">Single consolidated gap prompt</p>
          </Panel>

          <Panel caption="READINESS PROFILE">
            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="flex items-center gap-1.5"><StatusDot state="success" label="GREEN" /></span>
                <span className="font-bold">{metrics.readinessDistribution.green}</span>
              </div>
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="flex items-center gap-1.5"><StatusDot state="flagged" label="AMBER" /></span>
                <span className="font-bold">{metrics.readinessDistribution.amber}</span>
              </div>
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="flex items-center gap-1.5"><StatusDot state="error" label="RED" /></span>
                <span className="font-bold">{metrics.readinessDistribution.red}</span>
              </div>
            </div>
          </Panel>
        </div>

        {/* Baseline Comparison Panel */}
        <Section
          index="01"
          title="Baseline Comparison"
          caption="Sample baseline numbers clearly labelled as assumptions"
        >
          <div className="border border-hairline bg-surface rounded-[2px] overflow-hidden">
            <div className="p-3 bg-amber-50 border-b border-amber-200 text-amber-900 font-mono text-xs">
              <strong>Methodology Note:</strong> Baseline numbers are based on industry benchmarks for Indian retail lending underwriting operations (assuming manual document collection and phone follow-ups).
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse font-sans text-xs">
                <thead>
                  <tr className="border-b border-hairline bg-paper/40 font-mono text-[11px] text-ink-muted uppercase">
                    <th className="p-3">METRIC</th>
                    <th className="p-3">DOCFLOW PLATFORM</th>
                    <th className="p-3">INDUSTRY BASELINE (ASSUMPTION)</th>
                    <th className="p-3">EFFICIENCY GAIN</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-hairline">
                  {metrics.baselineComparison.map((row, i) => (
                    <tr key={i} className="hover:bg-paper/30">
                      <td className="p-3 font-semibold text-ink">{row.metric}</td>
                      <td className="p-3 font-mono text-ink font-bold">{row.docflow}</td>
                      <td className="p-3 font-mono text-ink-muted">{row.traditional}</td>
                      <td className="p-3 font-mono text-status-success font-bold">{row.improvement}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Section>
      </main>
    </div>
  );
}
