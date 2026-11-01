import React from 'react';

interface Step {
  index: string;
  label: string;
  status: 'completed' | 'current' | 'pending';
}

interface StepperProps {
  steps: Step[];
  nextDeadline?: string;
}

export const Stepper: React.FC<StepperProps> = ({ steps, nextDeadline }) => {
  return (
    <div className="w-full border-b border-hairline pb-4 mb-6">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-2">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full">
          {steps.map((step, i) => (
            <React.Fragment key={step.index}>
              <div className="flex items-center gap-2">
                <span
                  className={`font-mono text-xs px-2 py-0.5 rounded-[2px] border ${
                    step.status === 'completed'
                      ? 'border-status-verified text-status-verified bg-status-verified/5'
                      : step.status === 'current'
                      ? 'border-ink text-paper bg-ink'
                      : 'border-hairline text-ink-muted bg-surface'
                  }`}
                >
                  {step.index}
                </span>
                <span
                  className={`font-sans text-xs uppercase tracking-wider font-semibold whitespace-nowrap ${
                    step.status === 'current' ? 'text-ink' : 'text-ink-muted'
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {i < steps.length - 1 && (
                <span className="w-4 h-[1px] bg-hairline shrink-0" />
              )}
            </React.Fragment>
          ))}
        </div>
        {nextDeadline && (
          <div className="font-mono text-[11px] text-ink-muted uppercase">
            NEXT DEADLINE: <span className="text-ink font-semibold">{nextDeadline}</span>
          </div>
        )}
      </div>
    </div>
  );
};
