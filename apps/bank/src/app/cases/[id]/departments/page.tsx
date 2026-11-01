'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button, Panel, StatusDot } from '@/ui';
import { getStoredUser, authHeader, StaffUser } from '@/lib/auth';

const API = 'http://127.0.0.1:8000/api/v1';

interface DepartmentTask {
  id: string;
  department: string;
  status: string;
  summary: string;
}

interface EligibilityResult {
  is_eligible: boolean;
  status: string;
  rules_triggered: string[];
  explanation: string;
}

export default function DepartmentProgressPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [user, setUser] = useState<StaffUser | null>(null);
  const [tasks, setTasks] = useState<DepartmentTask[]>([]);
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [caseRef, setCaseRef] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Decision Modal
  const [activeTask, setActiveTask] = useState<DepartmentTask | null>(null);
  const [decisionStatus, setDecisionStatus] = useState('APPROVED');
  const [decisionNotes, setDecisionNotes] = useState('');
  const [deciding, setDeciding] = useState(false);

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
    loadProgress();
  }, [user, caseId]);

  const loadProgress = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/bank/cases/${caseId}/departments`, {
        headers: authHeader(user.email),
      });
      if (res.ok) {
        const json = await res.json();
        setTasks(json.department_tasks || []);
        setEligibility(json.eligibility_result || null);
        setCaseRef(json.case_reference || '');
      } else {
        setError(`Failed to fetch department status (${res.status})`);
      }
    } catch {
      setError('Cannot reach server.');
    } finally {
      setLoading(false);
    }
  };

  const handleDecisionSubmit = async () => {
    if (!user || !activeTask) return;
    setDeciding(true);
    setError('');
    try {
      const res = await fetch(`${API}/bank/cases/${caseId}/departments/${activeTask.id}/decide`, {
        method: 'POST',
        headers: authHeader(user.email),
        body: JSON.stringify({
          task_id: activeTask.id,
          new_status: decisionStatus,
          notes: decisionNotes,
        }),
      });

      if (res.ok) {
        setActiveTask(null);
        setDecisionNotes('');
        loadProgress();
      } else {
        const errJson = await res.json().catch(() => ({}));
        setError(errJson.detail || 'Access Denied: You cannot approve tasks outside your department.');
      }
    } catch {
      setError('Failed to record decision.');
    } finally {
      setDeciding(false);
    }
  };

  if (!user || loading) {
    return (
      <div className="min-h-screen bg-paper text-ink p-8 font-mono text-xs">
        Loading department status...
      </div>
    );
  }

  const isCreditHead = user.role === 'CREDIT_HEAD';

  return (
    <div className="min-h-screen bg-paper text-ink p-6">
      <div className="mx-auto max-w-5xl">
        {/* Header & Back link */}
        <div className="mb-6 flex items-center justify-between">
          <Link href={`/bank/cases/${caseId}`} className="text-xs font-mono uppercase underline">
            &larr; Back to Case Timeline
          </Link>
          <div className="text-xs font-mono text-ink/60">
            Signed in as: <span className="font-semibold text-ink">{user.role}</span> ({user.department})
          </div>
        </div>

        <div className="border-b border-hairline pb-4 mb-6">
          <h1 className="text-2xl font-serif font-bold">Department Maker-Checker Workflow</h1>
          <p className="text-xs font-mono text-ink/70 mt-1">
            Case: <span className="font-bold text-ink">{caseRef}</span> • Scoped Department Isolation
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 border border-status-flagged/40 bg-status-flagged/10 text-xs font-mono text-ink">
            {error}
          </div>
        )}

        {/* Per-Department Progress Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {tasks.map((task) => {
            const canAct = user.role === 'ADMIN' || user.department === task.department;
            const statusKind: 'verified' | 'flagged' | 'missing' | 'error' | 'success' =
              task.status === 'APPROVED'
                ? 'verified'
                : task.status === 'REJECTED'
                ? 'error'
                : 'flagged';

            return (
              <Panel key={task.id} caption={`${task.department} Department`}>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-ink/60">Current State</span>
                    <div className="flex items-center gap-2">
                      <StatusDot state={statusKind} />
                      <span className="text-xs font-mono font-bold uppercase">{task.status}</span>
                    </div>
                  </div>

                  <div className="bg-surface p-3 border border-hairline text-xs font-serif leading-relaxed">
                    {task.summary || 'Awaiting initial department review.'}
                  </div>

                  <div className="pt-2 flex justify-between items-center border-t border-hairline/60">
                    <span className="text-[10px] font-mono text-ink/60">
                      {canAct ? 'You have access' : 'View only (RBAC restricted)'}
                    </span>
                    <Button
                      variant={canAct ? 'primary' : 'secondary'}
                      disabled={!canAct}
                      onClick={() => {
                        setActiveTask(task);
                        setDecisionStatus(task.status);
                      }}
                    >
                      {canAct ? 'Update Decision' : 'Locked'}
                    </Button>
                  </div>
                </div>
              </Panel>
            );
          })}
        </div>

        {/* Credit Head Verdict & Deterministic Eligibility */}
        <Panel caption="Final Underwriting & Eligibility Result">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase text-ink/70">
                Rule Engine Status (Deterministic Code, No ML)
              </span>
              {eligibility && (
                <div className="flex items-center gap-2">
                  <StatusDot state={eligibility.is_eligible ? 'verified' : 'error'} />
                  <span className="font-mono text-xs font-bold uppercase">
                    {eligibility.status}
                  </span>
                </div>
              )}
            </div>

            {eligibility ? (
              <div className="bg-surface p-4 border border-hairline space-y-2">
                <div className="text-xs font-serif leading-relaxed">
                  {eligibility.explanation}
                </div>
                {eligibility.rules_triggered.length > 0 && (
                  <div className="pt-2 border-t border-hairline/60 font-mono text-[11px] text-ink/70">
                    <span className="font-bold">Triggered Conditions:</span>
                    <ul className="list-disc pl-4 mt-1 space-y-0.5">
                      {eligibility.rules_triggered.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs font-mono text-ink/60">
                Awaiting complete document extraction to compute rule-based eligibility.
              </p>
            )}

            {isCreditHead && (
              <div className="p-3 bg-paper border-2 border-ink text-xs font-mono flex items-center justify-between">
                <span>Credit Head Authority Enabled — Final Approval Power</span>
                <span className="font-bold uppercase text-status-ok">Authorized</span>
              </div>
            )}
          </div>
        </Panel>
      </div>

      {/* Decision Modal */}
      {activeTask && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-paper border border-hairline max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-serif font-bold">
              Update {activeTask.department} Decision
            </h3>
            <p className="text-xs text-ink/70 font-mono">
              Enforcing Maker-Checker RBAC isolation. All decisions are immutably logged.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-mono uppercase mb-1">New Status</label>
                <select
                  value={decisionStatus}
                  onChange={(e) => setDecisionStatus(e.target.value)}
                  className="w-full bg-surface border border-hairline p-2 text-xs focus:outline-none"
                >
                  <option value="IN_REVIEW">IN_REVIEW</option>
                  <option value="QUERY_RAISED">QUERY_RAISED</option>
                  <option value="APPROVED">APPROVED</option>
                  <option value="REJECTED">REJECTED</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase mb-1">Decision Notes</label>
                <textarea
                  rows={3}
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                  placeholder="e.g. Identity verified against government database. All signatures match."
                  className="w-full bg-surface border border-hairline p-2 text-xs focus:outline-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-hairline">
              <Button variant="secondary" onClick={() => setActiveTask(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleDecisionSubmit}
                disabled={deciding}
              >
                {deciding ? 'Recording...' : 'CONFIRM DECISION'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
