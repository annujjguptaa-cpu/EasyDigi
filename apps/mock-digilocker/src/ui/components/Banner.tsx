import React from 'react';

interface BannerProps {
  type?: 'demo' | 'consent' | 'info';
  children?: React.ReactNode;
  requester?: string;
  purpose?: string;
  expiry?: string;
}

export const Banner: React.FC<BannerProps> = ({
  type = 'demo',
  children,
  requester,
  purpose,
  expiry,
}) => {
  if (type === 'demo') {
    return (
      <div className="w-full bg-status-flagged/10 border-b border-status-flagged/30 px-4 py-2.5 flex items-center justify-center gap-2 text-ink text-xs font-mono">
        <span className="font-bold text-status-flagged border border-status-flagged px-1.5 py-0.2 rounded-[2px]">
          DEMO ONLY
        </span>
        <span>Not the real DigiLocker / Aggregator. No real numbers or OTPs are ever collected.</span>
      </div>
    );
  }

  if (type === 'consent') {
    return (
      <div className="border border-hairline bg-surface p-4 rounded-[2px] mb-6 space-y-2">
        <div className="font-mono text-xs text-ink-muted uppercase tracking-wider border-b border-hairline pb-1">
          CONSENT SPECIFICATION
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-sans text-xs">
          <div>
            <span className="text-ink-muted block font-mono text-[10px]">WHO IS ASKING</span>
            <span className="font-semibold text-ink">{requester || 'Apex Mutual Bank'}</span>
          </div>
          <div>
            <span className="text-ink-muted block font-mono text-[10px]">PURPOSE</span>
            <span className="font-semibold text-ink">{purpose || 'Lending Underwriting & KYC Verification'}</span>
          </div>
          <div>
            <span className="text-ink-muted block font-mono text-[10px]">VALID UNTIL</span>
            <span className="font-semibold text-ink">{expiry || '7 Days (Auto-Revoked)'}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-hairline bg-surface px-4 py-2.5 rounded-[2px] text-xs font-sans text-ink">
      {children}
    </div>
  );
};
