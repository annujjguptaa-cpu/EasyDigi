'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button, Panel, Table, StatusDot } from '@/ui';
import { getStoredUser, clearUser, authHeader, StaffUser } from '@/lib/auth';
import { useNotifications } from '@/lib/useNotifications';

const API = 'http://127.0.0.1:8000/api/v1';

interface CaseSummary {
  id: string;
  reference_code: string;
  customer_name: string;
  loan_type: string;
  status: string;
  workflow_state: string;
  created_at: string;
  updated_at: string;
  link_expires_at: string;
}

export default function BankDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<StaffUser | null>(null);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNotifs, setShowNotifs] = useState(false);
  const [resetting, setResetting] = useState(false);

  const handleResetDemo = async () => {
    if (!user) return;
    const ok = window.confirm('Are you sure you want to reset demo data? This will wipe all cases, links, notifications, and consents.');
    if (!ok) return;
    setResetting(true);
    try {
      const res = await fetch(`${API}/bank/reset-demo-data`, {
        method: 'POST',
        headers: authHeader(user.email),
      });
      if (res.ok) {
        alert('Demo data wiped clean. Fresh slate established.');
        loadCases();
      }
    } catch {
      alert('Failed to reset demo data');
    } finally {
      setResetting(false);
    }
  };

  const { notifications, unreadCount, markAsRead } = useNotifications(user?.email ?? null);

  useEffect(() => {
    const stored = getStoredUser();
    if (!stored) {
      router.push('/login');
      return;
    }
    setUser(stored);
  }, [router]);

  useEffect(() => {
    if (!user) return;
    loadCases();
  }, [user]);

  const loadCases = async () => {
    if (!user) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/bank/cases`, {
        headers: authHeader(user.email),
      });
      if (res.ok) {
        const data = await res.json();
        setCases(data);
      } else {
        setError(`Failed to load cases (${res.status})`);
      }
    } catch {
      setError('Cannot reach server. Ensure FastAPI is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    clearUser();
    router.push('/login');
  };

  const formatWorkflowState = (state: string) => {
    const map: Record<string, { label: string; state: 'verified' | 'flagged' | 'missing' | 'error' | 'success' }> = {
      link_created: { label: 'Link Created', state: 'missing' },
      link_opened: { label: 'Link Opened', state: 'flagged' },
      consent_given: { label: 'Consent Given', state: 'flagged' },
      documents_received: { label: 'Documents Received', state: 'verified' },
      ready_for_review: { label: 'Ready for Review', state: 'verified' },
      sent_to_departments: { label: 'Sent to Departments', state: 'verified' },
      in_review: { label: 'In Review', state: 'flagged' },
      query_raised: { label: 'Query Raised', state: 'error' },
      decided: { label: 'Decided', state: 'verified' },
    };
    return map[state] || { label: state, state: 'missing' };
  };

  const columns = [
    {
      header: 'Reference',
      accessor: (r: CaseSummary) => (
        <span className="font-mono text-xs font-semibold">{r.reference_code}</span>
      ),
    },
    {
      header: 'Customer',
      accessor: (r: CaseSummary) => <span className="font-serif font-medium">{r.customer_name}</span>,
    },
    {
      header: 'Product',
      accessor: (r: CaseSummary) => r.loan_type.replace('_', ' '),
    },
    {
      header: 'Workflow State',
      accessor: (r: CaseSummary) => {
        const badge = formatWorkflowState(r.workflow_state);
        return (
          <div className="flex items-center gap-2">
            <StatusDot state={badge.state} />
            <span className="text-xs uppercase tracking-wider">{badge.label}</span>
          </div>
        );
      },
    },
    {
      header: 'Created',
      accessor: (r: CaseSummary) => (
        <span className="font-mono text-xs text-ink/70">
          {r.created_at ? new Date(r.created_at).toLocaleString() : '—'}
        </span>
      ),
    },
    {
      header: 'Action',
      accessor: (r: CaseSummary) => (
        <Link href={`/bank/cases/${r.id}`}>
          <Button variant="secondary">
            View Case
          </Button>
        </Link>
      ),
    },
  ];

  if (!user) {
    return <div className="min-h-screen bg-paper p-8 text-ink">Loading staff session...</div>;
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      {/* Top Bar */}
      <header className="border-b border-hairline bg-surface/60 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-xl font-serif font-bold tracking-tight">
              EasyDigi <span className="text-xs font-mono font-normal uppercase text-ink/60 border border-hairline px-2 py-0.5 ml-2">Bank Workspace</span>
            </Link>
          </div>

          <div className="flex items-center gap-4">
            {/* Notification Bell */}
            <div className="relative">
              <button
                onClick={() => setShowNotifs(!showNotifs)}
                className="relative border border-hairline px-3 py-1.5 text-xs font-mono uppercase bg-paper hover:bg-surface flex items-center gap-2"
              >
                <span>NOTIFICATIONS</span>
                {unreadCount > 0 && (
                  <span className="bg-status-amber text-ink font-bold text-[10px] px-1.5 py-0.2 rounded-full">
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Slide-Down */}
              {showNotifs && (
                <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-paper border border-hairline shadow-md p-3 z-50">
                  <div className="flex items-center justify-between border-b border-hairline pb-2 mb-2">
                    <span className="font-mono text-xs uppercase font-semibold">Events Feed</span>
                    <button onClick={() => setShowNotifs(false)} className="text-xs font-mono text-ink/60">
                      Close
                    </button>
                  </div>
                  {notifications.length === 0 ? (
                    <p className="text-xs text-ink/60 py-4 text-center">No notifications yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {notifications.map((n) => (
                        <div
                          key={n.id}
                          onClick={() => markAsRead(n.id)}
                          className={`p-2 border border-hairline cursor-pointer text-xs ${
                            n.is_read ? 'bg-paper text-ink/70' : 'bg-surface font-medium'
                          }`}
                        >
                          <div className="flex justify-between font-mono text-[10px] text-ink/60 mb-1">
                            <span>{n.case_ref}</span>
                            <span>{new Date(n.created_at).toLocaleTimeString()}</span>
                          </div>
                          <div>{n.message}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Staff info */}
            <div className="text-right text-xs">
              <div className="font-mono font-medium">{user.email}</div>
              <div className="text-[10px] uppercase text-ink/60">{user.role} ({user.department})</div>
            </div>

            <Button variant="secondary" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-serif font-bold">Lending Cases</h1>
            <p className="text-xs text-ink/60 font-mono mt-1">Apex Mutual Bank • Active Underwriting Pipeline</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleResetDemo}
              disabled={resetting}
              className="text-xs font-mono px-3 py-2 border border-status-error/40 text-status-error hover:bg-status-error/10 uppercase"
            >
              {resetting ? 'Resetting...' : 'Reset Demo Data'}
            </button>
            <Link href="/cases/new">
              <Button variant="primary">
                + NEW REQUEST
              </Button>
            </Link>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-3 border border-status-flagged/40 bg-status-flagged/10 text-xs font-mono text-ink">
            {error}
          </div>
        )}

        <Panel caption="Verification Requests Table">
          {loading ? (
            <div className="p-8 text-center text-xs font-mono text-ink/60">Loading pipeline cases...</div>
          ) : cases.length === 0 ? (
            <div className="p-8 text-center text-xs font-mono text-ink/60">
              No cases yet. Click &ldquo;+ NEW REQUEST&rdquo; above to generate your first borrower link.
            </div>
          ) : (
            <Table columns={columns} data={cases} keyExtractor={(c) => c.id} />
          )}
        </Panel>
      </main>
    </div>
  );
}
