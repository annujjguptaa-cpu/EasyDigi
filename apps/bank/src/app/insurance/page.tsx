"use client";

import React, { useState } from "react";
import Link from "next/link";

interface MockClaim {
  id: string;
  claim_number: string;
  type: string;
  claimant: string;
  incident_date: string;
  status: string;
  amount: number;
  token: string;
}

const SEEDED_CLAIMS: MockClaim[] = [
  { id: "1", claim_number: "CLM-HLT-2024-8801", type: "health_cashless", claimant: "Rajan Nair", incident_date: "2024-10-24", status: "APPROVED", amount: 48500, token: "demo-token-rajan" },
  { id: "2", claim_number: "CLM-HLT-2024-8802", type: "health_reimbursement", claimant: "Sunita Rao", incident_date: "2024-10-15", status: "QUERY_RAISED", amount: 125000, token: "demo-token-sunita" },
  { id: "3", claim_number: "CLM-MOT-2024-8803", type: "motor_own_damage", claimant: "Vikram Malhotra", incident_date: "2024-10-20", status: "REJECTED", amount: 80000, token: "demo-token-vikram" },
  { id: "4", claim_number: "CLM-MOT-2024-8804", type: "motor_theft", claimant: "Ananya Sen", incident_date: "2024-10-18", status: "DOCS_PENDING", amount: 650000, token: "demo-token-ananya" },
  { id: "5", claim_number: "CLM-LIF-2024-8805", type: "life_death", claimant: "Ramesh Gupta", incident_date: "2024-10-01", status: "IN_REVIEW", amount: 2500000, token: "demo-token-ramesh" },
];

export default function InsuranceDashboardPage() {
  const [claimNumberInput, setClaimNumberInput] = useState("");
  const [generatedLink, setGeneratedLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  async function handleGenerateLink(e: React.FormEvent) {
    e.preventDefault();
    if (!claimNumberInput.trim()) return;
    setLoading(true);
    setError(null);
    setGeneratedLink(null);

    try {
      const res = await fetch(`${API_URL}/insurance/claims/generate-link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_number: claimNumberInput.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to generate link");
      }
      const data = await res.json();
      setGeneratedLink(data.intake_url || `http://localhost:3001/claim/${data.token}`);
    } catch (err: any) {
      setError(err.message || "Failed to generate intake link.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      {/* Banner */}
      <div className="bg-amber-950/60 border border-amber-800/80 rounded-xl p-3 mb-6 text-amber-300 text-xs flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span>⚠️</span>
          <span><strong>DEMO ONLY:</strong> DocFlow Insurance Claims Management & Verification Module. Synthetic sample data.</span>
        </div>
        <span className="font-mono bg-amber-900/60 px-2 py-0.5 rounded text-[10px]">Strict Consent Enforced</span>
      </div>

      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">DocFlow Insurance Hub</h1>
          <p className="text-sm text-slate-400">Claims verification, multi-department routing, and deterministic coverage assessment</p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/" className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-2 rounded-lg transition-colors border border-slate-700">
            ← Bank Loan Desk
          </Link>
        </div>
      </header>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <p className="text-xs text-slate-400">Active Claims</p>
          <p className="text-2xl font-bold text-white mt-1">5</p>
          <p className="text-[10px] text-emerald-400 mt-1">5 Fictional Scenarios</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <p className="text-xs text-slate-400">In Review / Query</p>
          <p className="text-2xl font-bold text-amber-400 mt-1">2</p>
          <p className="text-[10px] text-slate-400 mt-1">Single-query consolidated</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <p className="text-xs text-slate-400">Approved / Settled</p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">1</p>
          <p className="text-[10px] text-slate-400 mt-1">Mock UTR Ready</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <p className="text-xs text-slate-400">Rejected / Lapsed</p>
          <p className="text-2xl font-bold text-rose-400 mt-1">1</p>
          <p className="text-[10px] text-slate-400 mt-1">Ombudsman Escalation</p>
        </div>
      </div>

      {/* Intake Link Generator */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-8">
        <h2 className="text-sm font-semibold text-white mb-2">Generate Customer Claim Intake Link</h2>
        <p className="text-xs text-slate-400 mb-4">
          Issue a secure, expiring link to the claimant to begin mobile evidence collection and device vault submission.
        </p>
        <form onSubmit={handleGenerateLink} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="Enter Claim Number (e.g., CLM-HLT-2024-8801)"
            value={claimNumberInput}
            onChange={(e) => setClaimNumberInput(e.target.value)}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? "Generating..." : "Generate Intake Link"}
          </button>
        </form>

        {error && (
          <div className="mt-3 text-xs text-rose-400 bg-rose-950/40 border border-rose-900/60 p-2.5 rounded-lg">
            {error}
          </div>
        )}

        {generatedLink && (
          <div className="mt-4 p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between gap-3">
            <div className="truncate">
              <p className="text-[10px] text-slate-400">Direct Customer Link:</p>
              <a href={generatedLink} target="_blank" rel="noreferrer" className="text-xs text-indigo-400 hover:underline font-mono">
                {generatedLink}
              </a>
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(generatedLink)}
              className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded"
            >
              Copy
            </button>
          </div>
        )}
      </div>

      {/* Claims List */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-white">Seeded Insurance Claims</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/50 text-[10px] uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Claim Number</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Claimant</th>
                <th className="py-3 px-4">Incident Date</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {SEEDED_CLAIMS.map((claim) => (
                <tr key={claim.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-medium text-white">{claim.claim_number}</td>
                  <td className="py-3.5 px-4 capitalize">{claim.type.replace(/_/g, " ")}</td>
                  <td className="py-3.5 px-4">{claim.claimant}</td>
                  <td className="py-3.5 px-4 text-slate-400">{claim.incident_date}</td>
                  <td className="py-3.5 px-4">₹{claim.amount.toLocaleString("en-IN")}</td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                      claim.status === "APPROVED" ? "bg-emerald-950 text-emerald-400 border border-emerald-800" :
                      claim.status === "REJECTED" ? "bg-rose-950 text-rose-400 border border-rose-800" :
                      claim.status === "QUERY_RAISED" ? "bg-amber-950 text-amber-400 border border-amber-800" :
                      "bg-blue-950 text-blue-400 border border-blue-800"
                    }`}>
                      {claim.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <Link
                        href={`/insurance/claims/${claim.token}/timeline`}
                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px]"
                      >
                        Timeline
                      </Link>
                      <Link
                        href={`/insurance/claims/${claim.token}/review`}
                        className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px]"
                      >
                        Review
                      </Link>
                      <Link
                        href={`/insurance/claims/${claim.token}/share`}
                        className="px-2 py-1 bg-indigo-900/40 hover:bg-indigo-900/60 text-indigo-300 border border-indigo-800/50 rounded text-[11px]"
                      >
                        Share
                      </Link>
                      <Link
                        href={`/insurance/claims/${claim.token}/settlement`}
                        className="px-2 py-1 bg-emerald-950 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-800/50 rounded text-[11px]"
                      >
                        Settlement
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
