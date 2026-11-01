import React from 'react';
import { StatusDot, StatusType } from './StatusDot';

interface SectionProps {
  index: string; // e.g. "01", "02"
  title: string;
  status?: StatusType;
  children: React.ReactNode;
  caption?: string;
  className?: string;
}

export const Section: React.FC<SectionProps> = ({
  index,
  title,
  status,
  children,
  caption,
  className = '',
}) => {
  return (
    <section className={`border-b border-hairline pb-6 mb-6 ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hairline pb-2 mb-4">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-ink-muted tracking-widest font-bold">
            {index}
          </span>
          <h2 className="font-serif text-lg md:text-xl font-normal tracking-tight text-ink">
            {title}
          </h2>
        </div>
        {status && <StatusDot state={status} />}
      </div>
      {caption && (
        <p className="font-mono text-xs text-ink-muted mb-4 uppercase tracking-wide">
          {caption}
        </p>
      )}
      <div>{children}</div>
    </section>
  );
};
