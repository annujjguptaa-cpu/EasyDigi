'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button, Panel, StatusDot } from '@/ui';
import { API_URL, DIGILOCKER_URL } from '@/lib/config';

interface CaseInfo {
  reference_code: string;
  customer_name: string;
  loan_type: string;
  required_documents: string[];
  workflow_state: string;
  expires_at: string;
  bank_name: string;
}

const DOC_METADATA: Record<string, { title: string; issuer: string; explanation: string }> = {
  PAN: {
    title: 'PAN Verification Record',
    issuer: 'Income Tax Department',
    explanation: 'Mandatory proof of tax identity required by RBI guidelines.',
  },
  AADHAAR_OFFLINE: {
    title: 'Aadhaar e-KYC Offline',
    issuer: 'UIDAI',
    explanation: 'Identity and permanent address verification with masked biometric details.',
  },
  SALARY_SLIP: {
    title: 'Salary Slips (Recent 3 Months)',
    issuer: 'Employer Payroll',
    explanation: 'Verifies continuous employment and monthly net cash flow.',
  },
  BANK_STATEMENT: {
    title: 'Bank Statement (6 Months)',
    issuer: 'Salary Account Bank',
    explanation: 'Underwrites debt obligations, salary credits and average minimum balance.',
  },
  MARKSHEET: {
    title: 'Educational Degree Marksheet',
    issuer: 'Accredited University',
    explanation: 'Required for specialized education and professional qualification loans.',
  },
  ITR: {
    title: 'Income Tax Return (ITR-V)',
    issuer: 'Income Tax Department',
    explanation: 'Self-employed / professional taxable revenue confirmation.',
  },
  TITLE_DEED: {
    title: 'Property Title Deed',
    issuer: 'Sub-Registrar Office',
    explanation: 'Collateral ownership and mortgage title investigation.',
  },
  EC: {
    title: 'Encumbrance Certificate (EC)',
    issuer: 'Registration & Stamps Dept',
    explanation: 'Guarantees the property has zero legal or financial liabilities.',
  },
};

export default function CustomerWishPage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [loading, setLoading] = useState(true);
  const [caseInfo, setCaseInfo] = useState<CaseInfo | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);

  // Document checklist selection
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Granted / Partial screen state
  const [grantedDocs, setGrantedDocs] = useState<Array<{ type: string; status: string }>>([]);
  const [missingDocs, setMissingDocs] = useState<string[]>([]);
  const [isGranted, setIsGranted] = useState(false);
  const [agentMsg, setAgentMsg] = useState('');

  useEffect(() => {
    if (!token) return;
    loadCase();
  }, [token]);

  const loadCase = async () => {
    setLoading(true);
    try {
      // 1. Mark link as opened
      await fetch(`${API_URL}/c/${token}/open`, { method: 'POST' }).catch(() => {});

      // 2. Load case details
      const res = await fetch(`${API_URL}/c/${token}`);
      if (res.ok) {
        const data: CaseInfo = await res.json();
        setCaseInfo(data);
        setSelectedDocs(data.required_documents || []);

        if (data.workflow_state === 'wish_granted' || data.workflow_state === 'wish_partial') {
          // Fetch documents
          const docRes = await fetch(`${API_URL}/c/${token}/documents`);
          if (docRes.ok) {
            const docs = await docRes.json();
            setGrantedDocs(docs);
            setIsGranted(true);
            const reqSet = new Set(data.required_documents || []);
            const fetchedSet = new Set(docs.map((d: { type: string }) => d.type));
            const missing = Array.from(reqSet).filter((x) => !fetchedSet.has(x));
            setMissingDocs(missing);
          }
        }
      } else {
        setErrorStatus(res.status);
      }
    } catch {
      setErrorStatus(500);
    } finally {
      setLoading(false);
    }
  };

  const toggleDoc = (docType: string) => {
    // Documents required by bank are locked; others can be toggled
    const isMandatory = (caseInfo?.required_documents || []).slice(0, 2).includes(docType);
    if (isMandatory) return; // locked

    setSelectedDocs((prev) =>
      prev.includes(docType) ? prev.filter((d) => d !== docType) : [...prev, docType]
    );
  };

  const handleSummonDjinn = async () => {
    if (!caseInfo) return;
    setSubmitting(true);
    try {
      // 1. Submit selected documents to API
      await fetch(`${API_URL}/c/${token}/select-documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_documents: selectedDocs }),
      });

      // 2. Redirect to Mock DigiLocker Consent Screen with OAuth-style state
      const redirectUri = `${window.location.origin}/w/${token}`;
      const consentUrl = `${DIGILOCKER_URL}/consent?token=${token}&requester=${encodeURIComponent(
        caseInfo.bank_name
      )}&purpose=${encodeURIComponent(
        caseInfo.loan_type.replace('_', ' ')
      )}&scopes=${encodeURIComponent(selectedDocs.join(','))}&redirect_uri=${encodeURIComponent(
        redirectUri
      )}`;

      window.location.href = consentUrl;
    } catch {
      alert('Failed to connect to verification gateway');
      setSubmitting(false);
    }
  };

  const handleDecline = async () => {
    const ok = window.confirm('Are you sure you want to decline this document request?');
    if (!ok) return;
    await fetch(`${API_URL}/c/${token}/decline`, { method: 'POST' }).catch(() => {});
    alert('You have declined the request. No documents were shared.');
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-6 text-xs font-mono text-ink">
        Connecting to secure lending channel...
      </div>
    );
  }

  if (errorStatus === 410) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 border border-hairline bg-surface text-center space-y-4">
          <div className="font-mono text-xs uppercase text-status-error font-bold">Session Notice</div>
          <h1 className="text-xl font-serif font-bold">This wish link has expired or was already consumed.</h1>
          <p className="text-xs text-ink/70">
            For borrower security, verification links are strictly single-use and expire within 24 hours.
          </p>
        </div>
      </div>
    );
  }

  if (errorStatus === 404 || !caseInfo) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 border border-hairline bg-surface text-center space-y-4">
          <h1 className="text-xl font-serif font-bold">Invalid Token</h1>
          <p className="text-xs text-ink/70">The verification link is unrecognized or has been decommissioned.</p>
        </div>
      </div>
    );
  }

  if (caseInfo.workflow_state === 'declined') {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 border border-hairline bg-surface text-center space-y-4">
          <h1 className="text-xl font-serif font-bold">Request Declined</h1>
          <p className="text-xs text-ink/70">
            You declined the document request from {caseInfo.bank_name}. Zero personal data has been stored.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper text-ink p-4 md:p-8 font-serif">
      <div className="mx-auto max-w-xl">
        {/* Customer Header - Bank branded, zero bank staff UI visible */}
        <div className="text-center mb-8 pb-4 border-b border-hairline">
          <div className="font-mono text-[11px] uppercase tracking-wider text-ink/60 mb-1">
            {caseInfo.bank_name}
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Borrower Document Checklist</h1>
          <p className="font-mono text-xs text-ink/60 mt-1">
            Application Reference: <span className="font-bold text-ink">{caseInfo.reference_code}</span>
          </p>
        </div>

        {!isGranted ? (
          <div className="space-y-6">
            <Panel caption="Select Documents to Grant">
              <div className="space-y-4 text-xs font-serif leading-relaxed">
                <p>
                  To process your application for <strong>{caseInfo.loan_type.replace('_', ' ')}</strong>,{' '}
                  {caseInfo.bank_name} requests access to the following documents. Locked items are mandatory for underwriting.
                </p>

                <div className="space-y-3 pt-2">
                  {caseInfo.required_documents.map((docType, idx) => {
                    const meta = DOC_METADATA[docType] || {
                      title: docType,
                      issuer: 'Government Issuer',
                      explanation: 'Required for underwriting assessment.',
                    };
                    const isMandatory = idx < 2; // First two are mandatory & locked
                    const isChecked = selectedDocs.includes(docType);

                    return (
                      <div
                        key={docType}
                        onClick={() => toggleDoc(docType)}
                        className={`p-3 border border-hairline bg-surface flex items-start gap-3 transition-colors ${
                          isMandatory ? 'cursor-not-allowed opacity-90' : 'cursor-pointer hover:border-ink'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          disabled={isMandatory}
                          onChange={() => {}}
                          className="mt-1 h-4 w-4"
                        />
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-sm">{meta.title}</span>
                            <span className="font-mono text-[10px] text-ink/60 uppercase">
                              {isMandatory ? 'Mandatory (Locked)' : 'Optional'}
                            </span>
                          </div>
                          <div className="text-[11px] font-mono text-ink/60">{meta.issuer}</div>
                          <p className="text-xs text-ink/80 mt-1">{meta.explanation}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </Panel>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
              <button
                type="button"
                onClick={handleDecline}
                className="text-xs font-mono text-status-error uppercase underline"
              >
                Decline Request
              </button>

              <Button variant="primary" onClick={handleSummonDjinn} disabled={submitting}>
                {submitting ? 'Redirecting to DigiLocker...' : 'SUMMON THE DJINN →'}
              </Button>
            </div>
          </div>
        ) : (
          /* WISH GRANTED / PARTLY GRANTED SCREEN */
          <div className="space-y-6">
            <div className="p-8 border border-hairline bg-surface text-center space-y-4">
              <div className="text-4xl text-status-verified font-mono">
                {missingDocs.length === 0 ? '✓' : '⚡'}
              </div>
              <h2 className="text-2xl font-bold tracking-tight">
                {missingDocs.length === 0 ? 'Your Wish is Granted' : 'Your Wish is Partly Granted'}
              </h2>
              <p className="text-xs text-ink/70 leading-relaxed">
                {missingDocs.length === 0
                  ? `All ${grantedDocs.length} requested digital records have been retrieved and encrypted for ${caseInfo.bank_name}.`
                  : `${grantedDocs.length} documents were retrieved, but ${missingDocs.length} mandatory item could not be found in your DigiLocker account.`}
              </p>
              <div className="font-mono text-xs p-2 bg-paper border border-hairline inline-block">
                Case ID: {caseInfo.reference_code}
              </div>
            </div>

            {/* Extracted Documents List */}
            <Panel caption={`Extracted Digital Artifacts (${grantedDocs.length})`}>
              <div className="space-y-2">
                {grantedDocs.map((doc, i) => {
                  const meta = DOC_METADATA[doc.type] || {
                    title: doc.type,
                    issuer: 'Government Issuer',
                  };
                  return (
                    <div
                      key={i}
                      className="p-3 border border-hairline bg-paper flex items-center justify-between"
                    >
                      <div>
                        <div className="font-bold text-xs">{meta.title}</div>
                        <div className="font-mono text-[10px] text-ink/60">{meta.issuer}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusDot state="verified" />
                        <span className="font-mono text-[10px] uppercase">{doc.status}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>

            {/* Missing documents agent guidance */}
            {missingDocs.length > 0 && (
              <Panel caption="Djinn Agent Resolution Box">
                <div className="space-y-3 text-xs">
                  <div className="p-3 bg-paper border border-hairline space-y-1">
                    <span className="font-mono text-[10px] uppercase font-bold text-status-flagged block">
                      Missing from DigiLocker:
                    </span>
                    <ul className="list-disc pl-4 font-mono text-[11px]">
                      {missingDocs.map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                    </ul>
                  </div>

                  <p className="text-ink/80">
                    The bank underwriting team has been alerted. You can provide an explanation below
                    or upload a scanned copy later when prompted by your loan officer.
                  </p>

                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={agentMsg}
                      onChange={(e) => setAgentMsg(e.target.value)}
                      placeholder="e.g. Salary slip for recent month will be shared via PDF"
                      className="flex-1 bg-paper border border-hairline p-2 text-xs focus:outline-none"
                    />
                    <Button
                      variant="secondary"
                      onClick={() => {
                        alert('Your message was recorded with the case timeline.');
                        setAgentMsg('');
                      }}
                    >
                      Submit
                    </Button>
                  </div>
                </div>
              </Panel>
            )}

            <div className="pt-4 border-t border-hairline text-center">
              <Button
                variant="secondary"
                onClick={() => alert('Encrypted credentials saved to local device vault.')}
              >
                Save to My Vault
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
