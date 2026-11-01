'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button, Panel, StatusDot } from '@/ui';

const API = 'http://127.0.0.1:8000/api/v1';

interface CaseInfo {
  reference_code: string;
  customer_name: string;
  loan_type: string;
  required_documents: string[];
  workflow_state: string;
  expires_at: string;
  bank_name: string;
}

interface SubmittedDoc {
  type: string;
  status: string;
}

export default function CustomerLinkExperience() {
  const params = useParams();
  const token = params.token as string;

  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [caseInfo, setCaseInfo] = useState<CaseInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);

  // Step 1: Consent
  const [consented, setConsented] = useState(false);
  const [consentLoading, setConsentLoading] = useState(false);

  // Step 2: DigiLocker Profile Pick
  const [submittingProfile, setSubmittingProfile] = useState(false);

  // Step 3: Received Docs
  const [docs, setDocs] = useState<SubmittedDoc[]>([]);

  useEffect(() => {
    if (!token) return;
    initLink();
  }, [token]);

  const initLink = async () => {
    setLoading(true);
    try {
      // 1. Mark link as opened
      await fetch(`${API}/c/${token}/open`, { method: 'POST' }).catch(() => {});

      // 2. Fetch case details
      const res = await fetch(`${API}/c/${token}`);
      if (res.ok) {
        const data = await res.json();
        setCaseInfo(data);
        if (data.workflow_state === 'consent_given') {
          setStep(2);
        } else if (data.workflow_state === 'documents_received') {
          // Fetch existing docs
          const docRes = await fetch(`${API}/c/${token}/documents`);
          if (docRes.ok) {
            const docData = await docRes.json();
            setDocs(docData);
          }
          setStep(3);
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

  const handleConsentSubmit = async () => {
    if (!consented) return;
    setConsentLoading(true);
    try {
      const res = await fetch(`${API}/c/${token}/consent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agreed: true }),
      });
      if (res.ok) {
        setStep(2);
      }
    } catch {
      // Proceed in UI for demo
      setStep(2);
    } finally {
      setConsentLoading(false);
    }
  };

  const handleSelectProfile = async (profileKey: string) => {
    setSubmittingProfile(true);
    try {
      const res = await fetch(`${API}/c/${token}/documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_key: profileKey }),
      });
      if (res.ok) {
        const json = await res.json();
        setDocs(json.documents || []);
        setStep(3);
      }
    } catch {
      setStep(3);
    } finally {
      setSubmittingProfile(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-6 text-xs font-mono text-ink">
        Establishing secure document submission session...
      </div>
    );
  }

  if (errorStatus === 410) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 border border-hairline bg-surface text-center space-y-4">
          <div className="font-mono text-xs uppercase text-status-critical font-bold">Session Notice</div>
          <h1 className="text-xl font-serif font-bold">This link has expired or was already used.</h1>
          <p className="text-xs text-ink/70">
            For security, verification links are strictly single-use and expire within 24 hours.
            Please request a fresh link from your bank relationship manager.
          </p>
        </div>
      </div>
    );
  }

  if (errorStatus === 404 || !caseInfo) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-6">
        <div className="max-w-md w-full p-8 border border-hairline bg-surface text-center space-y-4">
          <div className="font-mono text-xs uppercase text-ink/60">Not Found</div>
          <h1 className="text-xl font-serif font-bold">Link Not Found</h1>
          <p className="text-xs text-ink/70">
            The verification token is invalid or has been decommissioned.
          </p>
        </div>
      </div>
    );
  }

  const hasMismatch = docs.some((d) => d.status === 'MISMATCH');
  const hasMissing = docs.length < (caseInfo.required_documents?.length || 3);

  return (
    <div className="min-h-screen bg-paper text-ink p-4 md:p-8 font-serif">
      <div className="mx-auto max-w-lg">
        {/* Customer Header - Bank branded, NO bank dashboard chrome */}
        <div className="text-center mb-8 pb-4 border-b border-hairline">
          <div className="font-mono text-[11px] uppercase tracking-wider text-ink/60 mb-1">
            {caseInfo.bank_name}
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Secure Document Submission</h1>
          <p className="font-mono text-xs text-ink/60 mt-1">
            Application Ref: <span className="font-bold text-ink">{caseInfo.reference_code}</span>
          </p>
        </div>

        {/* Progress Stepper */}
        <div className="flex justify-between items-center mb-8 font-mono text-[11px] border-b border-hairline pb-3">
          <span className={step >= 1 ? 'font-bold text-ink' : 'text-ink/40'}>1. Consent</span>
          <span>&rarr;</span>
          <span className={step >= 2 ? 'font-bold text-ink' : 'text-ink/40'}>2. DigiLocker</span>
          <span>&rarr;</span>
          <span className={step >= 3 ? 'font-bold text-ink' : 'text-ink/40'}>3. Documents</span>
          <span>&rarr;</span>
          <span className={step >= 4 ? 'font-bold text-ink' : 'text-ink/40'}>4. Complete</span>
        </div>

        {/* STEP 1: Consent */}
        {step === 1 && (
          <div className="space-y-6">
            <Panel caption="Data Access Consent Agreement">
              <div className="space-y-4 text-xs font-serif leading-relaxed">
                <p>
                  Welcome, <strong>{caseInfo.customer_name}</strong>. To process your{' '}
                  <strong>{caseInfo.loan_type.replace('_', ' ')}</strong> application,{' '}
                  {caseInfo.bank_name} requires digital verification of the following documents:
                </p>

                <div className="p-3 bg-surface border border-hairline font-mono space-y-1">
                  {caseInfo.required_documents.map((doc) => (
                    <div key={doc} className="flex items-center gap-2">
                      <span className="text-status-ok font-bold">✓</span>
                      <span>{doc}</span>
                    </div>
                  ))}
                </div>

                <p className="text-[11px] text-ink/70">
                  By clicking agree, you authorize {caseInfo.bank_name} to fetch your verified
                  records via government-certified repositories. Your data is encrypted at rest and in transit.
                </p>

                <label className="flex items-start gap-3 p-3 border border-hairline bg-surface/50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={consented}
                    onChange={(e) => setConsented(e.target.checked)}
                    className="mt-0.5 h-4 w-4"
                  />
                  <span className="text-xs">
                    I grant consent to {caseInfo.bank_name} to request and verify the above documents for loan processing.
                  </span>
                </label>
              </div>
            </Panel>

            <div className="text-center">
              <Button
                variant="primary"
                onClick={handleConsentSubmit}
                disabled={!consented || consentLoading}
              >
                {consentLoading ? 'Authorizing...' : 'I AGREE & CONTINUE'}
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: Mock DigiLocker Demo Profile Picker */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="p-3 border border-status-flagged/40 bg-status-flagged/10 text-xs font-mono text-ink">
              <span className="font-bold text-status-flagged mr-2">[DEMO ONLY]</span>
              This is a simulated DigiLocker sandbox. Choose a seeded persona below to test various lending underwriting outcomes.
            </div>

            <Panel caption="Simulated DigiLocker Sandbox">
              <div className="space-y-3">
                <p className="text-xs text-ink/70">
                  Select which customer scenario to emulate:
                </p>

                <div
                  onClick={() => handleSelectProfile('clean_file')}
                  className="p-4 border border-hairline bg-surface hover:border-ink cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-sm">Rahul Verma (Clean Profile)</span>
                    <span className="font-mono text-[10px] bg-status-ok/20 text-ink px-2 py-0.5 border border-status-ok/40">
                      100% Match
                    </span>
                  </div>
                  <p className="text-xs text-ink/70">
                    PAN, Aadhaar, 3 Months Salary Slips & Bank Statements match seamlessly.
                  </p>
                </div>

                <div
                  onClick={() => handleSelectProfile('name_mismatch')}
                  className="p-4 border border-hairline bg-surface hover:border-ink cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-sm">Priya S. Sharma (Name Discrepancy)</span>
                    <span className="font-mono text-[10px] bg-status-amber/20 text-ink px-2 py-0.5 border border-status-amber/40">
                      Amber Alert
                    </span>
                  </div>
                  <p className="text-xs text-ink/70">
                    PAN says &ldquo;Priya Sharma&rdquo; while Aadhaar says &ldquo;Priya Sunita Sharma&rdquo;.
                  </p>
                </div>

                <div
                  onClick={() => handleSelectProfile('missing_docs')}
                  className="p-4 border border-hairline bg-surface hover:border-ink cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-sm">Amit Patel (Missing Documents)</span>
                    <span className="font-mono text-[10px] bg-status-critical/20 text-ink px-2 py-0.5 border border-status-critical/40">
                      Incomplete
                    </span>
                  </div>
                  <p className="text-xs text-ink/70">
                    Only PAN card fetched. Salary slips and Aadhaar are missing.
                  </p>
                </div>
              </div>
            </Panel>

            {submittingProfile && (
              <div className="text-center font-mono text-xs">
                Connecting to DigiLocker sandbox & fetching digital artifacts...
              </div>
            )}
          </div>
        )}

        {/* STEP 3: Documents Review & AI Assistant */}
        {step === 3 && (
          <div className="space-y-6">
            <Panel caption="Verified Records Retrieved">
              <div className="space-y-3">
                {docs.map((doc, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 border border-hairline bg-surface">
                    <span className="font-mono text-xs font-semibold">{doc.type}</span>
                    <div className="flex items-center gap-2">
                      <StatusDot state={doc.status === 'VERIFIED' ? 'verified' : 'flagged'} />
                      <span className="font-mono text-[11px] uppercase">{doc.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>

            {/* Scoped Agent Chat only if gaps exist */}
            {(hasMismatch || hasMissing) && (
              <Panel caption="EasyDigi Verification Assistant">
                <div className="bg-surface p-3 border border-hairline text-xs space-y-2">
                  <div className="font-mono text-[10px] text-ink/60 font-bold uppercase">System Guidance</div>
                  <p>
                    {hasMismatch
                      ? 'Notice: A minor name variation was detected between your PAN and Aadhaar records. Our bank officers will review this automatically.'
                      : 'Notice: Some requested documents were not available in your DigiLocker. You can proceed, and your bank officer may request manual upload.'}
                  </p>
                </div>
              </Panel>
            )}

            <div className="text-center">
              <Button variant="primary" onClick={() => setStep(4)}>
                All Looks Good &rarr; Submit Application
              </Button>
            </div>
          </div>
        )}

        {/* STEP 4: Confirmation & Vault Option */}
        {step === 4 && (
          <div className="text-center space-y-6">
            <div className="p-8 border border-hairline bg-surface space-y-4">
              <div className="text-3xl">✓</div>
              <h2 className="text-xl font-bold">Documents Submitted Successfully</h2>
              <p className="text-xs text-ink/70 font-serif leading-relaxed">
                Your documents have been securely encrypted and delivered to {caseInfo.bank_name}.
                Our underwriting team will notify you once review is complete.
              </p>
              <div className="font-mono text-xs p-2 bg-paper border border-hairline inline-block">
                Reference Code: {caseInfo.reference_code}
              </div>
            </div>

            <div className="pt-4 border-t border-hairline">
              <Link href="/vault">
                <Button variant="secondary">
                  Save Verified Documents to My Vault &rarr;
                </Button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
