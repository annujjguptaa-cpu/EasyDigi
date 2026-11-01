import React from 'react';
import { StatusDot, StatusType } from './StatusDot';

interface DocumentRowProps {
  id: string;
  docType: string;
  maskedFields: Record<string, any>;
  status: StatusType;
  source: 'DigiLocker' | 'Upload' | 'Camera';
  action?: React.ReactNode;
}

export const DocumentRow: React.FC<DocumentRowProps> = ({
  id,
  docType,
  maskedFields,
  status,
  source,
  action,
}) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3 border-b border-hairline hover:bg-surface/60 transition-colors gap-3">
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
        <span className="font-mono text-xs text-ink-muted">
          {id}
        </span>
        <span className="font-sans font-semibold text-sm text-ink">
          {docType}
        </span>
        <div className="flex flex-wrap gap-2 text-xs font-mono text-ink-muted">
          {Object.entries(maskedFields).map(([k, v]) => (
            <span key={k} className="bg-paper px-1.5 py-0.5 border border-hairline rounded-[2px]">
              {k}: <span className="text-ink">{String(v)}</span>
            </span>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="font-mono text-[10px] uppercase text-ink-muted border border-hairline px-1.5 py-0.5 rounded-[2px]">
          {source}
        </span>
        <StatusDot state={status} />
        {action}
      </div>
    </div>
  );
};
