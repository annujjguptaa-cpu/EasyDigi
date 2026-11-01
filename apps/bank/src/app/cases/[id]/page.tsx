'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button, Panel, StatusDot } from '@/ui';
import { getStoredUser, authHeader, StaffUser } from '@/lib/auth';

const API = 'http://127.0.0.1:8000/api/v1';

interface CaseDetail {
  id: string;
  reference_code: string;
  customer_name: string;
  loan_type: string;
  status: string;
  workflow_state: string;
  created_at: string;
  customer_link: string;
  readiness_score: number;
  timeline: Array<{
    action: string;
    actor: string;
    at: string;
    details: Record<string, unknown>;
  }>;
  documents: Array<{
    id: string;
    type: string;
    status: string;
    masked_fields: Record<string, unknown>;
  }>;
  department_tasks: Array<{
    id: string;
    department: string;
    status: string;
    summary: string;
  }>;
}

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [user, setUser] = useState<StaffUser | null>(null);
  const [data, setData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Consolidated query state
  const [queryMsg, setQueryMsg] = useState('');
  const [querySending, setQuerySending] = useState(false);
  const [querySuccess, setQuerySuccess] = useState(false);

  // Send to departments modal state
  const [showSendModal, setShowSendModal] = useState(false);
  const [selectedDepts, setSelectedDepts] = useState<string[]>([
    'KYC',
    'CREDIT',
    'RISK',
    'OPERATIONS',
  ]);
  const [sendingDepts, setSendingDepts] = useState(false);

  useEffect(() => {
    const stored = getStoredUser();
    if (!stored) {
      router.push('/login');
      return;
    }
    setUser(stored);
  }, [router]);

  useEffect(() => {
    if (!user || !caseId) return;
    loadCase();
  }, [user, caseId]);

  const loadCase = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/bank/cases/${caseId}`, {
        headers: authHeader(user.email),
      });
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        setError(`Failed to load case (${res.status})`);
      }
    } catch {
      setError('Cannot connect to API server.');
    } finally {
      setLoading(false);
    }
  };

  const handleRaiseQuery = async () => {
    if (!user || !queryMsg.trim()) return;
    setQuerySending(true);
    setQuerySuccess(false);
    try {
      const res = await fetch(`${API}/bank/cases/${caseId}/query`, {
        method: 'POST',
        headers: authHeader(user.email),
        body: JSON.stringify({ message: queryMsg.trim() }),
      });
      if (res.ok) {
        setQuerySuccess(true);
        setQueryMsg('');
        loadCase();
      }
    } catch {
      setError('Failed to send query.');
    } finally {
      setQuerySending(false);
    }
  };

  const handleSendToDepartments = async () => {
    if (!user || selectedDepts.length === 0) return;
    setSendingDepts(true);
    try {
      const res = await fetch(`${API}/bank/cases/${caseId}/send-to-departments`, {
        method: 'POST',
        headers: authHeader(user.email),
        body: JSON.stringify({ departments: selectedDepts }),
      });
      if (res.ok) {
        setShowSendModal(false);
        router.push(`/bank/cases/${caseId}/departments`);
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || 'Failed to dispatch to departments');
      }
    } catch {
      setError('Cannot reach server.');
    } finally {
      setSendingDepts(false);
    }
  };

  if (!user || loading) {
    return (
      <div className="min-h-screen bg-paper text-ink p-8 font-mono text-xs">
        Loading case data...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-paper text-ink p-8">
        <div className="p-3 border border-status-flagged/40 bg-status-flagged/10 text-xs font-mono text-ink">
          {error || 'Case not found'}
        </div>
        <Link href="/dashboard" className="text-xs font-mono underline mt-4 inline-block">
          &larr; Back to Dashboard
        </Link>
      </div>
    );
  }

  const canSendToDepartments =
    data.workflow_state === 'documents_received' || data.workflow_state === 'ready_for_review';

  return (
    <div className="min-h-screen bg-paper text-ink p-6">
      <div className="mx-auto max-w-6xl">
        {/* Navigation breadcrumbs */}
        <div className="mb-6 flex items-center justify-between">
          <Link href="/dashboard" className="text-xs font-mono uppercase underline">
            &larr; Back to Cases
          </Link>
          <div className="flex gap-2">
            <Link href={`/bank/cases/${caseId}/departments`}>
              <Button variant="secondary">
                View Department Progress &rarr;
              </Button>
            </Link>
          </div>
        </div>

        {/* Case Header */}
        <div className="border-b border-hairline pb-4 mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-serif font-bold">{data.customer_name}</h1>
              <span className="font-mono text-sm px-2 py-0.5 bg-surface border border-hairline">
                {data.reference_code}
              </span>
            </div>
            <div className="text-xs font-mono text-ink/70 mt-1">
              Product: {data.loan_type.replace('_', ' ')} • State:{' '}
              <span className="uppercase font-semibold">{data.workflow_state}</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <span className="text-[10px] font-mono uppercase text-ink/60 block">Readiness</span>
              <div className="text-2xl font-mono font-bold">{data.readiness_score}%</div>
            </div>

            <Button
              variant="primary"
              disabled={!canSendToDepartments}
              onClick={() => setShowSendModal(true)}
            >
              SEND TO DEPARTMENTS
            </Button>
          </div>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: Timeline & Consolidated Query */}
          <div className="space-y-6">
            <Panel caption="Event Timeline & Audit Log">
              <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                {data.timeline.length === 0 ? (
                  <p className="text-xs font-mono text-ink/60">No events recorded yet.</p>
                ) : (
                  data.timeline.map((entry, idx) => (
                    <div key={idx} className="flex gap-3 text-xs border-l-2 border-hairline pl-3 py-1">
                      <div className="font-mono text-[10px] text-ink/50 whitespace-nowrap pt-0.5">
                        {new Date(entry.at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </div>
                      <div>
                        <div className="font-mono font-semibold uppercase">{entry.action}</div>
                        <div className="text-ink/70 text-[11px]">Actor: {entry.actor}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Panel>

            <Panel caption="Raise Consolidated Query to Customer">
              <div className="space-y-3">
                <p className="text-xs text-ink/70">
                  Notify the customer of any missing document clarifications or gap resolutions.
                </p>
                <textarea
                  rows={3}
                  value={queryMsg}
                  onChange={(e) => setQueryMsg(e.target.value)}
                  placeholder="e.g. Please provide clarification on name spelling difference on PAN card."
                  className="w-full bg-surface border border-hairline p-2 text-xs focus:outline-none"
                />
                <div className="flex justify-between items-center">
                  {querySuccess && (
                    <span className="text-xs font-mono text-status-ok font-semibold">
                      ✓ Query sent and logged
                    </span>
                  )}
                  <div className="ml-auto">
                    <Button
                      variant="secondary"
                      onClick={handleRaiseQuery}
                      disabled={querySending || !queryMsg.trim()}
                    >
                      {querySending ? 'Sending...' : 'SEND QUERY'}
                    </Button>
                  </div>
                </div>
              </div>
            </Panel>
          </div>

          {/* Right Column: Received Documents & Masked Data */}
          <div className="space-y-6">
            <Panel caption={`Received Documents (${data.documents.length})`}>
              {data.documents.length === 0 ? (
                <div className="p-6 text-center text-xs font-mono text-ink/60">
                  Customer has not submitted documents yet.
                  {data.customer_link && (
                    <div className="mt-3">
                      <span className="block text-[10px] text-ink/50">Active customer URL:</span>
                      <code className="text-[11px] p-1 bg-surface border border-hairline block break-all">
                        {data.customer_link}
                      </code>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {data.documents.map((doc) => (
                    <div key={doc.id} className="p-3 border border-hairline bg-surface/40">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-xs font-bold">{doc.type}</span>
                        <div className="flex items-center gap-2">
                          <StatusDot
                            state={
                              doc.status === 'VERIFIED'
                                ? 'verified'
                                : doc.status === 'MISMATCH'
                                ? 'flagged'
                                : 'missing'
                            }
                          />
                          <span className="text-[10px] font-mono uppercase">{doc.status}</span>
                        </div>
                      </div>
                      <div className="bg-paper p-2 border border-hairline/60 font-mono text-[11px] space-y-1">
                        {Object.entries(doc.masked_fields).map(([k, v]) => (
                          <div key={k} className="flex justify-between">
                            <span className="text-ink/60">{k}:</span>
                            <span className="font-semibold">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Panel>
          </div>
        </div>
      </div>

      {/* Send to Departments Modal */}
      {showSendModal && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-paper border border-hairline max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-serif font-bold">Send Case to Departments</h3>
            <p className="text-xs text-ink/70">
              Each department receives only its scoped document slice and citation summaries.
            </p>

            <div className="space-y-2">
              {['KYC', 'CREDIT', 'RISK', 'OPERATIONS', 'LEGAL', 'TECHNICAL'].map((dept) => (
                <label key={dept} className="flex items-center gap-2 text-xs font-mono cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedDepts.includes(dept)}
                    onChange={() =>
                      setSelectedDepts((prev) =>
                        prev.includes(dept) ? prev.filter((d) => d !== dept) : [...prev, dept]
                      )
                    }
                  />
                  <span>{dept} Department</span>
                </label>
              ))}
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-hairline">
              <Button variant="secondary" onClick={() => setShowSendModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleSendToDepartments}
                disabled={sendingDepts || selectedDepts.length === 0}
              >
                {sendingDepts ? 'Dispatching...' : 'CONFIRM DISPATCH'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
