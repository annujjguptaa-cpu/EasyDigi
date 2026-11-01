'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button, Panel } from '@/ui';
import { getStoredUser, authHeader, StaffUser } from '@/lib/auth';

const API = 'http://127.0.0.1:8000/api/v1';

const DOC_OPTIONS = [
  { id: 'PAN', label: 'PAN Card (Permanent Account Number)' },
  { id: 'AADHAAR_OFFLINE', label: 'Aadhaar (Offline XML / Masked)' },
  { id: 'SALARY_SLIP', label: 'Salary Slips (Recent 3 months)' },
  { id: 'BANK_STATEMENT', label: 'Bank Statement (6 months)' },
  { id: 'MARKSHEET', label: 'Educational Marksheet / Degree' },
  { id: 'ITR', label: 'Income Tax Return (ITR-V)' },
  { id: 'TITLE_DEED', label: 'Property Title Deed / Conveyance' },
  { id: 'EC', label: 'Encumbrance Certificate (EC)' },
];

export default function NewCasePage() {
  const router = useRouter();
  const [user, setUser] = useState<StaffUser | null>(null);

  const [customerName, setCustomerName] = useState('');
  const [customerPhone, setCustomerPhone] = useState('XXXXXX9901');
  const [loanType, setLoanType] = useState('HOME_LOAN');
  const [requiredDocs, setRequiredDocs] = useState<string[]>([
    'PAN',
    'AADHAAR_OFFLINE',
    'SALARY_SLIP',
  ]);
  const [ttlHours, setTtlHours] = useState(24);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<{
    case_reference: string;
    case_id: string;
    customer_link: string;
    whatsapp_stub: string;
    sms_stub: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const stored = getStoredUser();
    if (!stored) {
      router.push('/login');
      return;
    }
    setUser(stored);
  }, [router]);

  const toggleDoc = (docId: string) => {
    setRequiredDocs((prev) =>
      prev.includes(docId) ? prev.filter((d) => d !== docId) : [...prev, docId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    if (!customerName.trim()) {
      setError('Please enter customer name');
      return;
    }
    if (requiredDocs.length === 0) {
      setError('Select at least one required document');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API}/bank/cases`, {
        method: 'POST',
        headers: authHeader(user.email),
        body: JSON.stringify({
          customer_name: customerName.trim(),
          customer_phone_masked: customerPhone.trim(),
          loan_type: loanType,
          required_documents: requiredDocs,
          ttl_hours: ttlHours,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data);
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || `Server returned ${res.status}`);
      }
    } catch {
      setError('Cannot connect to backend server at http://127.0.0.1:8000');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (!result) return;
    navigator.clipboard.writeText(result.customer_link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="min-h-screen bg-paper text-ink p-6">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 flex items-center justify-between">
          <Link href="/dashboard" className="text-xs font-mono uppercase underline">
            &larr; Back to Dashboard
          </Link>
          <span className="text-xs font-mono text-ink/60">Apex Mutual Bank</span>
        </div>

        <h1 className="text-2xl font-serif font-bold mb-2">Create Customer Verification Link</h1>
        <p className="text-xs text-ink/70 font-mono mb-6">
          Generates a signed, single-use, expiring link for prospective borrower document submission.
        </p>

        {error && (
          <div className="mb-6 p-3 border border-status-flagged/40 bg-status-flagged/10 text-xs font-mono text-ink">
            {error}
          </div>
        )}

        {!result ? (
          <form onSubmit={handleSubmit} className="space-y-6">
            <Panel caption="Borrower Details">
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono uppercase mb-1">Customer Full Name</label>
                  <input
                    type="text"
                    required
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    placeholder="e.g. Rahul Verma"
                    className="w-full bg-surface border border-hairline px-3 py-2 text-sm focus:outline-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-mono uppercase mb-1">Masked Mobile</label>
                    <input
                      type="text"
                      value={customerPhone}
                      onChange={(e) => setCustomerPhone(e.target.value)}
                      className="w-full bg-surface border border-hairline px-3 py-2 text-sm font-mono focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-mono uppercase mb-1">Loan Product</label>
                    <select
                      value={loanType}
                      onChange={(e) => setLoanType(e.target.value)}
                      className="w-full bg-surface border border-hairline px-3 py-2 text-sm focus:outline-none"
                    >
                      <option value="HOME_LOAN">Home Loan</option>
                      <option value="PERSONAL_LOAN">Personal Loan</option>
                      <option value="EDUCATION_LOAN">Education Loan</option>
                      <option value="BUSINESS_LOAN">Business Loan</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase mb-1">Link Expiry TTL</label>
                  <select
                    value={ttlHours}
                    onChange={(e) => setTtlHours(Number(e.target.value))}
                    className="w-full bg-surface border border-hairline px-3 py-2 text-sm focus:outline-none"
                  >
                    <option value={24}>24 Hours (Default)</option>
                    <option value={48}>48 Hours</option>
                    <option value={72}>72 Hours</option>
                  </select>
                </div>
              </div>
            </Panel>

            <Panel caption="Required Documents Checklist">
              <div className="space-y-2">
                {DOC_OPTIONS.map((doc) => (
                  <label
                    key={doc.id}
                    className="flex items-center gap-3 p-2 border border-hairline/60 bg-surface/30 cursor-pointer hover:bg-surface"
                  >
                    <input
                      type="checkbox"
                      checked={requiredDocs.includes(doc.id)}
                      onChange={() => toggleDoc(doc.id)}
                      className="h-4 w-4"
                    />
                    <span className="text-xs font-mono font-medium">{doc.id}</span>
                    <span className="text-xs text-ink/70">— {doc.label}</span>
                  </label>
                ))}
              </div>
            </Panel>

            <div className="flex justify-end gap-3">
              <Link href="/dashboard">
                <Button variant="secondary" type="button">
                  Cancel
                </Button>
              </Link>
              <Button variant="primary" type="submit" disabled={loading}>
                {loading ? 'Generating Link...' : 'SUMMON SECURE LINK'}
              </Button>
            </div>
          </form>
        ) : (
          <Panel caption="Verification Link Created Successfully">
            <div className="space-y-6">
              <div>
                <span className="text-xs font-mono uppercase text-ink/60">Case Reference</span>
                <div className="text-lg font-mono font-bold mt-0.5">{result.case_reference}</div>
              </div>

              <div>
                <span className="text-xs font-mono uppercase text-ink/60">Generated Customer URL</span>
                <div className="p-3 bg-surface border border-hairline font-mono text-xs break-all mt-1">
                  {result.customer_link}
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <Button variant="primary" onClick={copyToClipboard}>
                  {copied ? '✓ COPIED TO CLIPBOARD' : 'COPY LINK'}
                </Button>
                <a href={result.whatsapp_stub} target="_blank" rel="noopener noreferrer">
                  <Button variant="secondary">
                    Send via WhatsApp (Stub)
                  </Button>
                </a>
                <a href={result.sms_stub}>
                  <Button variant="secondary">
                    Send via SMS (Stub)
                  </Button>
                </a>
              </div>

              <div className="pt-4 border-t border-hairline flex justify-between items-center">
                <button
                  type="button"
                  onClick={() => {
                    setResult(null);
                    setCustomerName('');
                  }}
                  className="text-xs font-mono underline"
                >
                  Create another request
                </button>
                <Link href={`/bank/cases/${result.case_id}`}>
                  <Button variant="secondary">
                    View Case Timeline &rarr;
                  </Button>
                </Link>
              </div>
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}
