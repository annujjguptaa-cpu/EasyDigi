"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function ClaimSettlementPage() {
  const params = useParams();
  const token = params?.id as string;

  const [loading, setLoading] = useState(false);
  const [bankLast4, setBankLast4] = useState("");
  const [settlementResult, setSettlementResult] = useState<any>(null);
  const [grievanceText, setGrievanceText] = useState("");
  const [escalationResult, setEscalationResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  async function handleInitiateSettlement(e: React.FormEvent) {
    e.preventDefault();
    if (!bankLast4 || bankLast4.length !== 4) {
      setError("Please enter exactly 4 digits for bank account last-4.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/insurance/settlement/initiate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_token: token,
          bank_account_last4: bankLast4,
          payment_mode: "NEFT",
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Settlement failed");
      }
      setSettlementResult(await res.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleEscalate(e: React.FormEvent) {
    e.preventDefault();
    if (!grievanceText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/insurance/settlement/escalate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_token: token,
          grievance_text: grievanceText,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Escalation failed");
      }
      setEscalationResult(await res.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white">Settlement Payout & Ombudsman Escalation</h1>
          <p className="text-xs text-slate-400">Claim Token: {token}</p>
        </div>
        <Link href="/insurance" className="text-xs bg-slate-800 text-slate-300 px-3 py-1.5 rounded">
          ← Back to Hub
        </Link>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-rose-950/40 border border-rose-900/60 rounded-xl text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Settlement Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold text-white mb-2">Initiate Mock NEFT Settlement Payout</h2>
        <p className="text-xs text-slate-400 mb-4">
          For APPROVED claims only. Never stores full account numbers (masked to last 4 only). Generates instant mock UTR reference.
        </p>

        <form onSubmit={handleInitiateSettlement} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            maxLength={4}
            placeholder="Account Last 4 (e.g. 5678)"
            value={bankLast4}
            onChange={(e) => setBankLast4(e.target.value)}
            className="w-48 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-5 py-2 rounded-lg disabled:opacity-50"
          >
            {loading ? "Processing..." : "Process NEFT Payout"}
          </button>
        </form>

        {settlementResult && (
          <div className="mt-4 p-4 bg-slate-950 border border-emerald-900/60 rounded-lg">
            <span className="text-xs font-semibold text-emerald-400">✓ Settlement Executed</span>
            <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
              <div>
                <span className="text-slate-500 text-[10px]">UTR Number:</span>
                <p className="font-mono text-slate-200">{settlementResult.utr_number}</p>
              </div>
              <div>
                <span className="text-slate-500 text-[10px]">Account (Masked):</span>
                <p className="font-mono text-slate-200">****{settlementResult.bank_account_last4}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Ombudsman Escalation */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-2">Grievance & Insurance Ombudsman Escalation</h2>
        <p className="text-xs text-slate-400 mb-4">
          If your claim has been rejected or delayed beyond regulatory timelines, register a formal grievance with the Insurance Ombudsman.
        </p>

        <form onSubmit={handleEscalate} className="space-y-3">
          <textarea
            rows={3}
            placeholder="Describe your grievance or disputed claim details..."
            value={grievanceText}
            onChange={(e) => setGrievanceText(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-4 py-2 rounded-lg disabled:opacity-50"
          >
            Escalate to Ombudsman
          </button>
        </form>

        {escalationResult && (
          <div className="mt-4 p-4 bg-slate-950 border border-indigo-900/60 rounded-lg">
            <span className="text-xs font-semibold text-indigo-400">Ombudsman Escalation Registered</span>
            <p className="text-xs font-mono text-slate-300 mt-1">Ref: {escalationResult.escalation_ref}</p>
            <p className="text-[11px] text-slate-400 mt-1">{escalationResult.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}
