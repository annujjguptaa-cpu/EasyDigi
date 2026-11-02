"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

export default function ClaimTimelinePage() {
  const params = useParams();
  const token = params?.id as string;

  const [timeline, setTimeline] = useState<any[]>([]);
  const [deadlines, setDeadlines] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [timeRes, deadRes] = await Promise.all([
          fetch(`${API_URL}/insurance/timeline/${token}`),
          fetch(`${API_URL}/insurance/deadlines/${token}`),
        ]);
        if (timeRes.ok) setTimeline(await timeRes.json());
        if (deadRes.ok) setDeadlines(await deadRes.json());
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    if (token) loadData();
  }, [token, API_URL]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white">Claim Timeline & Regulatory SLA Deadlines</h1>
          <p className="text-xs text-slate-400">Claim Token: {token}</p>
        </div>
        <Link href="/insurance" className="text-xs bg-slate-800 text-slate-300 px-3 py-1.5 rounded">
          ← Back to Hub
        </Link>
      </div>

      {/* Deadlines SLA Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-semibold text-white mb-3">Service Level Regulatory Deadlines</h2>
        {deadlines.length === 0 ? (
          <p className="text-xs text-slate-500">No deadlines recorded yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {deadlines.map((dl, idx) => (
              <div key={idx} className="bg-slate-950 border border-slate-800/80 p-3 rounded-lg flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-slate-200 capitalize">{dl.deadline_type.replace(/_/g, " ")}</p>
                  <p className="text-[10px] text-slate-400">Owner: {dl.owner}</p>
                </div>
                <div className="text-right">
                  <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium ${
                    dl.status === "MET" ? "bg-emerald-950 text-emerald-400 border border-emerald-800" :
                    dl.status === "AT_RISK" ? "bg-amber-950 text-amber-400 border border-amber-800" :
                    dl.status === "BREACHED" ? "bg-rose-950 text-rose-400 border border-rose-800" :
                    "bg-blue-950 text-blue-400 border border-blue-800"
                  }`}>
                    {dl.status}
                  </span>
                  {dl.hours_remaining !== null && (
                    <p className="text-[10px] text-slate-500 mt-0.5">{dl.hours_remaining}h remaining</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Unified Timeline List */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-4">Unified Audit Event Log</h2>
        {timeline.length === 0 ? (
          <p className="text-xs text-slate-500">No events found in timeline.</p>
        ) : (
          <div className="space-y-4 border-l-2 border-slate-800 pl-4 ml-2">
            {timeline.map((item, idx) => (
              <div key={idx} className="relative">
                <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-indigo-500 ring-4 ring-slate-900"></span>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-200">{item.label}</span>
                  <span className="text-[10px] text-slate-500 font-mono">{item.timestamp?.slice(0, 19).replace("T", " ")}</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">Actor: {item.actor || "system"}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
