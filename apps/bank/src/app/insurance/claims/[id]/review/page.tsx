"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function ClaimReviewPage() {
  const params = useParams();
  const token = params?.id as string;

  const [loading, setLoading] = useState(false);
  const [flagsResult, setFlagsResult] = useState<any>(null);
  const [coverageResult, setCoverageResult] = useState<any>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  async function handleRunChecks() {
    setLoading(true);
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/insurance/checks/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_token: token }),
      });
      if (res.ok) {
        setFlagsResult(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleComputeCoverage() {
    setLoading(true);
    setActionMessage(null);
    try {
      const res = await fetch(`${API_URL}/insurance/coverage/compute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim_token: token }),
      });
      if (res.ok) {
        setCoverageResult(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/insurance/coverage/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_token: token,
          officer_id: "OFFICER-DEMO-01",
          approved_amount: coverageResult?.breakdown?.payable_amount || 48500,
          notes: "Approved after deterministic coverage assessment.",
        }),
      });
      if (res.ok) {
        setActionMessage("Claim successfully approved by Human Officer. Settlement initiated.");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white">Coverage Assessment & Underwriter Review</h1>
          <p className="text-xs text-slate-400">Claim Token: {token}</p>
        </div>
        <Link href="/insurance" className="text-xs bg-slate-800 text-slate-300 px-3 py-1.5 rounded">
          ← Back to Hub
        </Link>
      </div>

      {actionMessage && (
        <div className="mb-6 p-4 bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs rounded-xl">
          {actionMessage}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={handleRunChecks}
          disabled={loading}
          className="bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium px-4 py-2 rounded-lg"
        >
          Run Consistency & Fraud Checks
        </button>
        <button
          onClick={handleComputeCoverage}
          disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-4 py-2 rounded-lg"
        >
          Compute Deterministic Coverage (Code)
        </button>
      </div>

      {/* Flags & Query */}
      {flagsResult && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold text-white mb-2">Consistency Flags (Human Review Only)</h2>
          {flagsResult.flags?.length === 0 ? (
            <p className="text-xs text-emerald-400">✓ All consistency checks passed. No fraud signals detected.</p>
          ) : (
            <div className="space-y-2 mb-4">
              {flagsResult.flags.map((flag: any, i: number) => (
                <div key={i} className="p-3 bg-slate-950 border border-amber-900/50 rounded-lg text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-amber-400">{flag.flag_type}</span>
                    <span className="text-[10px] bg-rose-950 text-rose-300 px-2 py-0.5 rounded font-mono">{flag.severity}</span>
                  </div>
                  <pre className="mt-2 text-[10px] text-slate-400 font-mono overflow-x-auto">{JSON.stringify(flag.evidence, null, 2)}</pre>
                </div>
              ))}
            </div>
          )}

          {flagsResult.consolidated_query && (
            <div className="p-3 bg-amber-950/30 border border-amber-800/60 rounded text-xs text-amber-200 mt-3">
              <p className="font-semibold text-[11px] uppercase tracking-wider mb-1">One-Shot Consolidated Query (No Drips):</p>
              <p className="whitespace-pre-line text-slate-300">{flagsResult.consolidated_query}</p>
            </div>
          )}
        </div>
      )}

      {/* Deterministic Coverage Card */}
      {coverageResult && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-white">Coverage Assessment Breakdown</h2>
            <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium ${
              coverageResult.status === "COVERED" ? "bg-emerald-950 text-emerald-400 border border-emerald-800" :
              coverageResult.status === "PARTLY_COVERED" ? "bg-amber-950 text-amber-400 border border-amber-800" :
              "bg-rose-950 text-rose-400 border border-rose-800"
            }`}>
              {coverageResult.status}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-950 p-3 rounded-lg text-xs mb-4">
            <div>
              <p className="text-[10px] text-slate-500">Requested</p>
              <p className="font-semibold text-slate-200">₹{coverageResult.breakdown?.requested_amount?.toLocaleString("en-IN")}</p>
            </div>
            <div>
              <p className="text-[10px] text-slate-500">Deductible</p>
              <p className="font-semibold text-slate-200">₹{coverageResult.breakdown?.deductible?.toLocaleString("en-IN")}</p>
            </div>
            <div>
              <p className="text-[10px] text-slate-500">Co-Pay ({coverageResult.breakdown?.co_pay_pct}%)</p>
              <p className="font-semibold text-slate-200">₹{coverageResult.breakdown?.co_pay_amount?.toLocaleString("en-IN")}</p>
            </div>
            <div>
              <p className="text-[10px] text-emerald-400 font-medium">Final Payable</p>
              <p className="font-bold text-emerald-400 text-sm">₹{coverageResult.breakdown?.payable_amount?.toLocaleString("en-IN")}</p>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 mb-4">
            <span className="font-semibold text-slate-300">Deterministic Reasons:</span>{" "}
            {coverageResult.reason_codes?.join(", ")}
          </div>

          <div className="pt-3 border-t border-slate-800 flex justify-end gap-3">
            <button
              onClick={handleApprove}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg"
            >
              Approve Claim (Human Officer)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
