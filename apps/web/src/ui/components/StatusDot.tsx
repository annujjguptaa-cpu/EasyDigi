import React from 'react';

export type StatusType = 'verified' | 'flagged' | 'missing' | 'error' | 'success';

interface StatusDotProps {
  state: StatusType;
  label?: string;
  showIcon?: boolean;
}

export const StatusDot: React.FC<StatusDotProps> = ({ state, label, showIcon = true }) => {
  const configs: Record<StatusType, { colorClass: string; icon: string; defaultLabel: string }> = {
    verified: {
      colorClass: 'bg-status-verified text-status-verified',
      icon: '✓',
      defaultLabel: 'VERIFIED',
    },
    flagged: {
      colorClass: 'bg-status-flagged text-status-flagged',
      icon: '!',
      defaultLabel: 'FLAGGED',
    },
    missing: {
      colorClass: 'bg-status-missing text-status-missing',
      icon: '○',
      defaultLabel: 'MISSING',
    },
    error: {
      colorClass: 'bg-status-error text-status-error',
      icon: '✕',
      defaultLabel: 'ERROR',
    },
    success: {
      colorClass: 'bg-status-success text-status-success',
      icon: '✓',
      defaultLabel: 'READY',
    },
  };

  const config = configs[state] || configs.missing;
  const displayLabel = label || config.defaultLabel;

  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-xs tracking-wider">
      <span className={`w-2 h-2 rounded-full inline-block ${config.colorClass.split(' ')[0]}`} />
      {showIcon && <span className="font-bold">{config.icon}</span>}
      <span className="uppercase text-ink">{displayLabel}</span>
    </span>
  );
};
