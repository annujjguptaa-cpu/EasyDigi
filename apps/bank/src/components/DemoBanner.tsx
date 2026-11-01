import React from 'react';

interface DemoBannerProps {
  customMessage?: string;
}

export const DemoBanner: React.FC<DemoBannerProps> = ({ 
  customMessage = "DEMO ONLY, not the real DigiLocker / Aggregator. No real Aadhaar or OTP is ever collected." 
}) => {
  return (
    <div className="bg-amber-500 text-amber-950 px-4 py-2 text-center text-xs sm:text-sm font-semibold shadow-md flex items-center justify-center gap-2 border-b-2 border-amber-600">
      <span className="bg-amber-900 text-amber-100 uppercase text-[10px] px-1.5 py-0.5 rounded tracking-wider font-bold">
        DEMO ONLY
      </span>
      <span>{customMessage}</span>
    </div>
  );
};
