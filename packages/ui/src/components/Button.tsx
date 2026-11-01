import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  children,
  className = '',
  ...props
}) => {
  // Primary is the single black action button with uppercase mono label
  const baseClasses =
    'min-h-[48px] px-6 py-2.5 font-mono text-xs uppercase tracking-widest font-semibold rounded-[2px] transition-all flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-ink focus:ring-offset-2';

  const variants = {
    primary:
      'bg-ink text-paper hover:opacity-90 active:scale-[0.99] border border-ink disabled:opacity-50',
    secondary:
      'bg-transparent text-ink border border-hairline hover:bg-surface active:bg-paper/80 disabled:opacity-50',
    danger:
      'bg-transparent text-status-error border border-status-error hover:bg-status-error/10 disabled:opacity-50',
  };

  return (
    <button
      className={`${baseClasses} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
