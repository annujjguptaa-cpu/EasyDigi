import React from 'react';
import Link from 'next/link';
import './globals.css';

export const metadata = {
  title: 'Mock DigiLocker — Sandbox',
  description: 'Simulated DigiLocker sandbox environment for demonstration purposes.',
};

export default function MockDigiLockerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F0F4F8] text-[#1E293B] font-sans">
        {/* Universal DEMO ONLY Watermark Header on EVERY PAGE */}
        <div className="bg-[#DC2626] text-white text-center py-2 px-4 font-mono text-xs font-bold tracking-wider uppercase flex items-center justify-center gap-2">
          <span>⚠ DEMO ONLY, NOT THE REAL DIGILOCKER</span>
          <span className="hidden sm:inline text-[10px] font-normal lowercase opacity-90">
            (Simulated sandbox — no real data or OTP is ever collected)
          </span>
        </div>

        {/* DigiLocker Brand Bar */}
        <header className="bg-white border-b border-[#CBD5E1] px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-xl font-black tracking-tight text-[#0284C7]">DigiLocker</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-[#E0F2FE] text-[#0284C7] font-bold rounded">
                SANDBOX
              </span>
            </Link>
          </div>

          <nav className="flex items-center gap-6 text-xs font-semibold text-[#475569]">
            <Link href="/" className="hover:text-[#0284C7]">
              Issued Documents
            </Link>
            <Link href="/activity" className="hover:text-[#0284C7]">
              Activity Log
            </Link>
            <Link href="/signin" className="hover:text-[#0284C7]">
              Switch Profile
            </Link>
          </nav>
        </header>

        {/* Main Content */}
        <main className="max-w-4xl mx-auto p-6">{children}</main>
      </body>
    </html>
  );
}
