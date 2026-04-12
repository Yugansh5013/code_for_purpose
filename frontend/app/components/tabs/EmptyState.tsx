interface EmptyStateProps {
  children: string;
}

export function EmptyState({ children }: EmptyStateProps) {
  return (
    <div className="flex h-full items-center justify-center px-4 text-center font-mono text-[10px] text-text-3">
      {children}
    </div>
  );
}
