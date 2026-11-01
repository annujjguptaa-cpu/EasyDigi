import React from 'react';

interface PanelProps {
  caption?: string;
  children: React.ReactNode;
  className?: string;
  badge?: React.ReactNode;
}

export const Panel: React.FC<PanelProps> = ({
  caption,
  children,
  className = '',
  badge,
}) => {
  return (
    <div
      className={`border border-hairline bg-surface rounded-[2px] transition-colors ${className}`}
    >
      {(caption || badge) && (
        <div className="flex items-center justify-between border-b border-hairline px-3 py-1.5 bg-paper/50">
          {caption && (
            <span className="font-mono text-[11px] text-ink-muted uppercase tracking-wider">
              {caption}
            </span>
          )}
          {badge && <div>{badge}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
};
