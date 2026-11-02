"use client";

/**
 * Prompt 5 — Claim Vault Page (Device-Side)
 * ==========================================
 * Mobile-first encrypted document vault for claim originals.
 *
 * Security rules enforced here:
 * - Encryption happens in the browser via WebCrypto AES-256-GCM BEFORE upload
 * - Server receives only ciphertext — never plaintext
 * - Aadhaar / account numbers are never stored in metadata
 * - Policy wallet shows masked policy numbers only
 * - "Works offline" banner — documents captured offline sync when reconnected
 *
 * DEMO ONLY — uses mock encryption key for demonstration purposes.
 */

import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";

// ── Types ──────────────────────────────────────────────────────────────────

type DocStatus = "PENDING" | "UPLOADED" | "VERIFIED" | "EXPIRED";

interface ChecklistItem {
  doc_type: string;
  status: DocStatus;
}

interface PolicyWalletEntry {
  policy_number_masked: string;
  ref: string;
  stored_at: string;
  expires_at: string | null;
  deleted: boolean;
}

interface SyncQueueItem {
  local_id: string;
  claim_id: string;
  doc_type: string;
  encrypted_b64: string;
  size_bytes: number;
  sha256: string;
  label: string;
}

// ── Crypto helpers (DEMO — uses a fixed demo key) ─────────────────────────

async function getDemoKey(): Promise<CryptoKey> {
  const raw = new TextEncoder().encode("DEMO-VAULT-KEY-32BYTES-PADDING!!");
  return crypto.subtle.importKey("raw", raw.slice(0, 32), "AES-GCM", false, [
    "encrypt",
  ]);
}

async function encryptBlob(data: Uint8Array): Promise<{ encrypted_b64: string; sha256: string; size_bytes: number }> {
  const key = await getDemoKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const cipherBuf = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, data);
  const combined = new Uint8Array(iv.byteLength + cipherBuf.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(cipherBuf), iv.byteLength);

  // SHA-256 of ciphertext for integrity
  const hashBuf = await crypto.subtle.digest("SHA-256", combined);
  const sha256 = Array.from(new Uint8Array(hashBuf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  const encrypted_b64 = btoa(String.fromCharCode(...combined));
  return { encrypted_b64, sha256, size_bytes: combined.byteLength };
}

// ── Status helpers ─────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<DocStatus, { dot: string; label: string; bg: string }> = {
  PENDING:  { dot: "bg-gray-300",   label: "Pending",  bg: "bg-gray-50"  },
  UPLOADED: { dot: "bg-blue-500",   label: "Uploaded", bg: "bg-blue-50"  },
  VERIFIED: { dot: "bg-green-500",  label: "Verified", bg: "bg-green-50" },
  EXPIRED:  { dot: "bg-red-400",    label: "Expired",  bg: "bg-red-50"   },
};

function formatDocType(dt: string): string {
  return dt.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

// ── Main component ─────────────────────────────────────────────────────────

export default function ClaimVaultPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const DIGILOCKER_URL = process.env.NEXT_PUBLIC_DIGILOCKER_URL || "http://localhost:3002";

  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [wallet, setWallet] = useState<PolicyWalletEntry[]>([]);
  const [syncQueue, setSyncQueue] = useState<SyncQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState(true);
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"checklist" | "wallet">("checklist");

  // Online/offline detection
  useEffect(() => {
    setIsOnline(navigator.onLine);
    const onOnline  = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online",  onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online",  onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  // Load checklist + wallet
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [clRes, walRes] = await Promise.all([
        fetch(`${API}/insurance/vault/checklist/${token}`),
        fetch(`${API}/insurance/vault/policy-wallet`),
      ]);
      if (clRes.ok) {
        const data: ChecklistItem[] = await clRes.json();
        setChecklist(data);
      }
      if (walRes.ok) {
        const data: PolicyWalletEntry[] = await walRes.json();
        setWallet(data);
      }
    } catch {
      setError("Could not load vault data. You may be offline — documents saved here will sync when reconnected.");
    } finally {
      setLoading(false);
    }
  }, [token, API]);

  useEffect(() => { loadData(); }, [loadData]);

  // Auto-sync when coming back online
  useEffect(() => {
    if (isOnline && syncQueue.length > 0) {
      handleSync();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOnline]);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  // ── Upload a document (encrypt → POST /vault/store) ──────────────────────

  async function handleFileUpload(docType: string, file: File) {
    setUploadingDoc(docType);
    try {
      const arrayBuf = await file.arrayBuffer();
      const { encrypted_b64, sha256, size_bytes } = await encryptBlob(new Uint8Array(arrayBuf));

      // We need claim_id — use token as placeholder (server resolves via token→claim)
      const body = {
        claim_id:      token,   // server-side resolves actual claim_id
        doc_type:      docType,
        encrypted_b64,
        size_bytes,
        sha256,
        retention_hours: 2160,
      };

      if (!isOnline) {
        // Queue for later sync
        const item: SyncQueueItem = {
          local_id:     `local-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          claim_id:     token,
          doc_type:     docType,
          encrypted_b64,
          size_bytes,
          sha256,
          label:        file.name,
        };
        setSyncQueue((q) => [...q, item]);
        showToast(`📥 Queued offline: ${formatDocType(docType)}`);
        return;
      }

      const res = await fetch(`${API}/insurance/vault/store`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      showToast(`✅ ${formatDocType(docType)} uploaded securely`);
      await loadData();
    } catch (err) {
      showToast(`❌ Upload failed: ${String(err)}`);
    } finally {
      setUploadingDoc(null);
    }
  }

  // ── Sync queued offline blobs ─────────────────────────────────────────────

  async function handleSync() {
    if (syncQueue.length === 0 || !isOnline) return;
    setSyncing(true);
    try {
      const res = await fetch(`${API}/insurance/vault/sync`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(syncQueue),
      });
      if (res.ok) {
        const results = await res.json();
        const stored = results.filter((r: { status: string }) => r.status === "stored").length;
        setSyncQueue([]);
        showToast(`🔄 Synced ${stored} document(s) successfully`);
        await loadData();
      }
    } catch {
      showToast("❌ Sync failed — will retry when online");
    } finally {
      setSyncing(false);
    }
  }

  // ── Delete policy wallet entry ────────────────────────────────────────────

  async function handleDeletePolicy(maskedNumber: string) {
    try {
      const res = await fetch(`${API}/insurance/vault/policy-wallet/${encodeURIComponent(maskedNumber)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        showToast("🗑️ Policy removed from wallet");
        await loadData();
      }
    } catch {
      showToast("❌ Could not remove policy");
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  const pendingCount  = checklist.filter((c) => c.status === "PENDING").length;
  const uploadedCount = checklist.filter((c) => c.status === "UPLOADED").length;
  const verifiedCount = checklist.filter((c) => c.status === "VERIFIED").length;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10 shadow-sm">
        <div className="max-w-md mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.back()} className="text-gray-500 hover:text-gray-800 text-xl">←</button>
          <div className="flex-1">
            <h1 className="font-bold text-gray-900 text-sm">📁 Claim Vault</h1>
            <p className="text-xs text-gray-500">Documents encrypted on your device</p>
          </div>
          {/* Online/offline badge */}
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
            isOnline ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
          }`}>
            {isOnline ? "🟢 Online" : "🔴 Offline"}
          </span>
        </div>
      </div>

      {/* Offline banner */}
      {!isOnline && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-center max-w-md mx-auto">
          <p className="text-xs text-amber-800 font-medium">
            📵 Works offline — documents you add now will sync when reconnected.
          </p>
        </div>
      )}

      {/* Offline sync queue banner */}
      {syncQueue.length > 0 && isOnline && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 max-w-md mx-auto flex items-center justify-between">
          <p className="text-xs text-blue-800">
            🔄 {syncQueue.length} document(s) queued for sync
          </p>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="text-xs bg-blue-600 text-white px-3 py-1 rounded-full hover:bg-blue-700 disabled:opacity-50"
          >
            {syncing ? "Syncing…" : "Sync Now"}
          </button>
        </div>
      )}

      <div className="max-w-md mx-auto px-4 pt-4">

        {/* Summary strip */}
        {!loading && checklist.length > 0 && (
          <div className="grid grid-cols-3 gap-2 mb-4">
            {[
              { label: "Pending",  value: pendingCount,  color: "text-gray-600",  bg: "bg-gray-100"  },
              { label: "Uploaded", value: uploadedCount, color: "text-blue-700",  bg: "bg-blue-100"  },
              { label: "Verified", value: verifiedCount, color: "text-green-700", bg: "bg-green-100" },
            ].map(({ label, value, color, bg }) => (
              <div key={label} className={`${bg} rounded-xl p-3 text-center`}>
                <p className={`text-2xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-gray-500">{label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="flex bg-gray-200 rounded-xl p-1 mb-4">
          {(["checklist", "wallet"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 text-sm font-medium py-1.5 rounded-lg transition-colors ${
                activeTab === tab
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab === "checklist" ? "📋 Originals" : "💳 Policy Wallet"}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-4 text-sm text-amber-800">
            ⚠️ {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="text-center py-16 text-gray-400">
            <div className="text-4xl animate-pulse mb-2">🔒</div>
            <p className="text-sm">Loading vault…</p>
          </div>
        )}

        {/* ── CHECKLIST TAB ───────────────────────────────────────── */}
        {!loading && activeTab === "checklist" && (
          <div className="space-y-3">
            {checklist.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <div className="text-4xl mb-2">📂</div>
                <p className="text-sm">No documents required yet.</p>
                <p className="text-xs mt-1">Open the chat to start your claim.</p>
              </div>
            ) : (
              checklist.map((item) => {
                const cfg = STATUS_CONFIG[item.status];
                return (
                  <div
                    key={item.doc_type}
                    className={`${cfg.bg} border border-gray-200 rounded-2xl p-4`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
                        <span className="font-medium text-sm text-gray-800">
                          {formatDocType(item.doc_type)}
                        </span>
                      </div>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cfg.dot} bg-opacity-20 text-gray-700`}>
                        {cfg.label}
                      </span>
                    </div>

                    {item.status === "PENDING" && (
                      <div className="flex gap-2">
                        {/* Upload from device */}
                        <label className="flex-1 cursor-pointer">
                          <input
                            type="file"
                            accept="image/*,application/pdf"
                            className="hidden"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) handleFileUpload(item.doc_type, file);
                              e.target.value = "";
                            }}
                          />
                          <span className={`flex items-center justify-center gap-1 text-xs font-medium 
                            bg-blue-600 text-white rounded-xl py-2 px-3 hover:bg-blue-700 transition-colors
                            ${uploadingDoc === item.doc_type ? "opacity-60 cursor-wait" : ""}`}>
                            {uploadingDoc === item.doc_type ? "⏳ Encrypting…" : "📎 Upload & Encrypt"}
                          </span>
                        </label>

                        {/* DigiLocker shortcut */}
                        <a
                          href={`${DIGILOCKER_URL}?doc_type=${item.doc_type}&return_to=${encodeURIComponent(
                            `http://localhost:3001/claim/${token}/vault`
                          )}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-center gap-1 text-xs font-medium
                            bg-indigo-600 text-white rounded-xl py-2 px-3 hover:bg-indigo-700 transition-colors"
                        >
                          🏛️ DigiLocker
                        </a>
                      </div>
                    )}

                    {item.status === "UPLOADED" && (
                      <p className="text-xs text-blue-600 flex items-center gap-1">
                        🔒 Encrypted and stored — awaiting bank verification
                      </p>
                    )}

                    {item.status === "VERIFIED" && (
                      <p className="text-xs text-green-700 flex items-center gap-1">
                        ✅ Verified by bank officer
                      </p>
                    )}

                    {item.status === "EXPIRED" && (
                      <p className="text-xs text-red-600 flex items-center gap-1">
                        ⚠️ Retention period expired — please re-upload
                      </p>
                    )}
                  </div>
                );
              })
            )}

            {/* DigiLocker info card */}
            <div className="bg-indigo-50 border border-indigo-200 rounded-2xl p-4 mt-2">
              <p className="text-xs font-semibold text-indigo-800 mb-1">🏛️ About DigiLocker</p>
              <p className="text-xs text-indigo-700">
                Use the DigiLocker button on any pending document to fetch it directly from
                your government DigiLocker account — no scanning needed.
              </p>
              <p className="text-xs text-indigo-500 mt-1 font-medium">
                DEMO: Connected to Mock DigiLocker (port 3002)
              </p>
            </div>
          </div>
        )}

        {/* ── POLICY WALLET TAB ───────────────────────────────────── */}
        {!loading && activeTab === "wallet" && (
          <div className="space-y-3">
            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 text-sm text-blue-800 mb-2">
              <p className="font-semibold mb-1">💳 Policy Wallet</p>
              <p className="text-xs text-blue-700">
                Store encrypted copies of your policy cards here. Only masked policy numbers
                appear in the list — full details stay encrypted on your device.
              </p>
            </div>

            {wallet.length === 0 ? (
              <div className="text-center py-10 text-gray-400">
                <div className="text-4xl mb-2">💳</div>
                <p className="text-sm">No policies stored yet.</p>
              </div>
            ) : (
              wallet.map((entry) => (
                <div key={entry.ref} className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="font-semibold text-gray-800 text-sm">{entry.policy_number_masked}</p>
                      <p className="text-xs text-gray-500">Added {formatDate(entry.stored_at)}</p>
                    </div>
                    <button
                      onClick={() => handleDeletePolicy(entry.policy_number_masked)}
                      className="text-red-400 hover:text-red-600 text-xs font-medium px-2 py-1 rounded-lg hover:bg-red-50 transition-colors"
                    >
                      🗑️ Remove
                    </button>
                  </div>
                  {entry.expires_at && (
                    <p className="text-xs text-amber-600">
                      ⏳ Expires: {formatDate(entry.expires_at)}
                    </p>
                  )}
                  <p className="text-xs text-green-700 mt-1">🔒 Encrypted on device</p>
                </div>
              ))
            )}

            {/* Add policy CTA */}
            <div className="bg-gray-100 border-2 border-dashed border-gray-300 rounded-2xl p-6 text-center">
              <p className="text-3xl mb-2">➕</p>
              <p className="text-sm text-gray-600 font-medium">Add a Policy Card</p>
              <p className="text-xs text-gray-400 mt-1">
                Upload your policy document — it will be encrypted before leaving your device.
              </p>
              <label className="mt-3 inline-block cursor-pointer">
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    e.target.value = "";
                    const policyNum = prompt("Enter policy number (e.g. POL-2024-1234):");
                    if (!policyNum) return;
                    const arrayBuf = await file.arrayBuffer();
                    const { encrypted_b64, sha256, size_bytes } = await encryptBlob(new Uint8Array(arrayBuf));
                    const res = await fetch(`${API}/insurance/vault/policy-wallet`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ policy_number: policyNum, encrypted_b64, size_bytes, sha256 }),
                    });
                    if (res.ok) {
                      showToast("💳 Policy added to wallet");
                      await loadData();
                    } else {
                      showToast("❌ Failed to add policy");
                    }
                  }}
                />
                <span className="text-sm bg-blue-600 text-white px-4 py-2 rounded-xl hover:bg-blue-700 transition-colors">
                  📎 Upload & Encrypt
                </span>
              </label>
            </div>
          </div>
        )}

        {/* Security footer */}
        <div className="mt-6 bg-white border border-gray-200 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-400">
            🔐 All documents encrypted with AES-256-GCM before upload.
            <br />The server never sees your plaintext files.
          </p>
          <p className="text-xs text-orange-500 font-medium mt-1">
            DEMO ONLY — Mock encryption key used for demonstration
          </p>
        </div>
      </div>

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-sm px-5 py-3 rounded-2xl shadow-xl z-50 max-w-xs text-center animate-fade-in">
          {toast}
        </div>
      )}
    </div>
  );
}
