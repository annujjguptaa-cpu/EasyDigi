"use client";

import React, { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

export default function ClaimSharePage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.id as string;

  const [loading, setLoading] = useState(false);
  const [shareResult, setShareResult] = useState<any>(null);
  const [preauthResult, setPreauthResult] = useState<any>(null);
  const [revoked, setRevoked] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  // Mock demo public key
  const DEMO_PUBLIC_KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0DEMO_KEY_FOR_INSURER";

  async function handleShare() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/insurance/share/package`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_token: token,
          consented_doc_refs: ["vault-ref-001", "vault-ref-002"],
          recipient_public_key_b64: DEMO_PUBLIC_KEY,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Share failed");
      }
      const data = await res.json();
      setShareResult(data);
      setRevoked(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handlePreauth() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/insurance/share/preauth`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim_token: token,
          hospital_ref: "HOSP-MAX-01",
          estimated_amount: 45000,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Pre-auth failed");
      }
      const data = await res.json();
      setPreauthResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRevoke() {
    if (!shareResult?.share_token) return;
    try {
      const res = await fetch(`${API_URL}/insurance/share/${shareResult.share_token}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setRevoked(true);
      }
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white">Insurer Consent & Claim Package</h1>
          <p className="text-xs text-slate-400">Claim Token: {token}</p>
        </div>
        <Link href="/insurance" className="text-xs bg-slate-800 text-slate-300 px-3 py-1.5 rounded">
          ← Back to Hub
        </Link>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold text-white mb-2">Hybrid Encrypted Package</h2>
        <p className="text-xs text-slate-400 mb-4">
          Combines AES-256-GCM encrypted claim manifests with RSA-OAEP key wrapping. Only user-consented vault references are packaged.
        </p>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleShare}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium px-4 py-2 rounded-lg disabled:opacity-50"
          >
            {loading ? "Encrypting..." : "Assemble & Encrypt Package"}
          </button>
          <button
            onClick={handlePreauth}
            disabled={loading}
            className="bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium px-4 py-2 rounded-lg disabled:opacity-50"
          >
            Request Cashless Pre-Auth (1hr SLA)
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-950/40 border border-rose-900/60 rounded text-xs text-rose-300">
            {error}
          </div>
        )}

        {shareResult && (
          <div className="mt-5 p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-emerald-400">Encrypted Package Dispatched</span>
              <span className={`text-[10px] px-2 py-0.5 rounded ${revoked ? "bg-rose-950 text-rose-400" : "bg-emerald-950 text-emerald-400"}`}>
                {revoked ? "REVOKED" : "ACTIVE"}
              </span>
            </div>
            <p className="text-xs font-mono text-slate-300 break-all mb-1">Share Token: {shareResult.share_token}</p>
            <p className="text-[11px] text-slate-500 mb-3">Expires: {shareResult.expires_at}</p>
            
            {!revoked && (
              <button
                onClick={handleRevoke}
                className="text-xs bg-rose-900/50 hover:bg-rose-800 text-rose-200 px-3 py-1.5 rounded"
              >
                Revoke Access Token
              </button>
            )}
          </div>
        )}

        {preauthResult && (
          <div className="mt-4 p-4 bg-slate-950 border border-slate-800 rounded-lg">
            <span className="text-xs font-semibold text-teal-400">Cashless Pre-Auth Requested</span>
            <p className="text-xs font-mono text-slate-300 mt-1">Ref: {preauthResult.preauth_ref}</p>
            <p className="text-[11px] text-slate-400 mt-1">Hospital: {preauthResult.hospital_ref} • Amount: ₹{preauthResult.estimated_amount}</p>
            <span className="inline-block mt-2 text-[10px] bg-teal-950 text-teal-300 border border-teal-800 px-2 py-0.5 rounded">
              Status: {preauthResult.status} (Valid: {preauthResult.expires_in_hours}h)
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
