"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";

interface Message {
  sender: "agent" | "user";
  text: string;
  time: string;
  action?: string;
  missing?: string[];
}

interface IntakeData {
  claim_number: string;
  claim_type: string;
  claimant_name: string;
  incident_date: string;
  guidance: {
    required_documents: string[];
    optional_documents: string[];
    scenario_guidance: string;
  };
}

export default function ClaimIntakePage() {
  const params = useParams();
  const token = params?.token as string;

  const [loading, setLoading] = useState(true);
  const [intake, setIntake] = useState<IntakeData | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [sending, setSending] = useState(false);
  const [securityNotice, setSecurityNotice] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  useEffect(() => {
    async function fetchIntake() {
      try {
        const res = await fetch(`${API_URL}/insurance/claim/${token}/intake-details`);
        if (res.ok) {
          const data = await res.json();
          setIntake(data);
          // Initial greeting from agent
          setMessages([
            {
              sender: "agent",
              text: `Namaste ${data.claimant_name}. I am your EasyDigi Insurance Claims Assistant for Claim #${data.claim_number} (${data.claim_type.replace(/_/g, " ").toUpperCase()}).\n\n${data.guidance?.scenario_guidance || "I will guide you through evidence capture and document submission."}`,
              time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              missing: data.status?.missing_required_documents
            }
          ]);
        } else {
          setSecurityNotice("This claim link is invalid or has expired. Please contact support.");
        }
      } catch (err) {
        setSecurityNotice("Unable to reach the claims gateway. Please verify network connection.");
      } finally {
        setLoading(false);
      }
    }
    if (token) fetchIntake();
  }, [token, API_URL]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || sending) return;

    const userText = inputText.trim();
    setInputText("");
    const newMsg: Message = {
      sender: "user",
      text: userText,
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    };
    setMessages((prev) => [...prev, newMsg]);
    setSending(true);

    try {
      const res = await fetch(`${API_URL}/insurance/claim/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: token,
          message: userText,
          claimant_name: intake?.claimant_name
        })
      });
      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            sender: "agent",
            text: data.reply,
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            action: data.action,
            missing: data.missing_documents
          }
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "agent",
          text: "Connection interrupted. Please resend your message.",
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500 mx-auto mb-3"></div>
          <p className="text-sm text-slate-400">Verifying secure claim session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col max-w-xl mx-auto shadow-2xl border-x border-slate-800">
      {/* Top Header */}
      <header className="px-4 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between sticky top-0 z-10">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <h1 className="font-semibold text-sm text-white">EasyDigi Claim Intake Assistant</h1>
          </div>
          <p className="text-xs text-slate-400">
            {intake ? `Claim #${intake.claim_number} • ${intake.claim_type}` : "Secure Portal"}
          </p>
        </div>
        <span className="text-[10px] font-mono uppercase bg-emerald-950 text-emerald-400 border border-emerald-800/60 px-2 py-0.5 rounded">
          Client Encrypted
        </span>
      </header>

      {/* Security Disclaimer Banner */}
      <div className="bg-amber-950/40 border-b border-amber-800/50 px-4 py-2 text-[11px] text-amber-300 flex items-center gap-2">
        <span>🔒</span>
        <span>Never type your Aadhaar number or OTP in chat. Documents remain in your device vault.</span>
      </div>

      {securityNotice ? (
        <div className="p-8 text-center my-auto">
          <div className="w-12 h-12 bg-red-950/60 text-red-400 border border-red-800 rounded-full flex items-center justify-center mx-auto mb-4">
            ⚠️
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Notice</h2>
          <p className="text-sm text-slate-400">{securityNotice}</p>
        </div>
      ) : (
        <>
          {/* Messages Area */}
          <main className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed shadow-md whitespace-pre-wrap ${
                    m.sender === "user"
                      ? "bg-emerald-600 text-white rounded-br-none"
                      : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none"
                  }`}
                >
                  {m.text}
                </div>
                <span className="text-[10px] text-slate-500 mt-1 px-1">{m.time}</span>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </main>

          {/* Quick Action Badges */}
          {intake?.guidance?.required_documents && (
            <div className="px-4 py-2 bg-slate-900/60 border-t border-slate-800 flex gap-2 overflow-x-auto text-[11px] no-scrollbar">
              <span className="text-slate-400 self-center whitespace-nowrap">Required:</span>
              {intake.guidance.required_documents.map((d, i) => (
                <span
                  key={i}
                  className="bg-slate-800 border border-slate-700 text-slate-300 px-2 py-0.5 rounded whitespace-nowrap"
                >
                  {d}
                </span>
              ))}
            </div>
          )}

          {/* Chat Input Bar */}
          <form
            onSubmit={handleSendMessage}
            className="p-3 bg-slate-900 border-t border-slate-800 flex items-center gap-2"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask a question or report details..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
            <button
              type="submit"
              disabled={sending || !inputText.trim()}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md flex items-center gap-1"
            >
              <span>Send</span>
              <span>→</span>
            </button>
          </form>
        </>
      )}
    </div>
  );
}
