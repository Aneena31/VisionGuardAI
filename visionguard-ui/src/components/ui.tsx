import React from 'react';
import { motion, HTMLMotionProps } from 'motion/react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { RiskLevel } from '../types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface CardProps extends HTMLMotionProps<'div'> {}

export const GlassCard = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={cn(
          'bg-slate-900/40 border border-slate-800 backdrop-blur-xl rounded-2xl p-6 shadow-[0_0_20px_rgba(0,0,0,0.5)]',
          className
        )}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);
GlassCard.displayName = 'GlassCard';

export const RiskBadge = ({ level, className }: { level: RiskLevel | string; className?: string }) => {
  const styles = {
    Low: 'bg-green-500/10 text-green-500 border-green-500/20',
    Medium: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    High: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    Critical: 'bg-red-500/10 text-red-500 border-red-500/20 shadow-[0_0_10px_rgba(239,68,68,0.3)]',
  };

  const currentStyle = styles[level as keyof typeof styles] || styles.Low;

  return (
    <span className={cn('px-2 py-1 rounded text-[10px] font-bold border uppercase tracking-wider', currentStyle, className)}>
      {level}
    </span>
  );
};
