export interface EmptyStateProps {
  message: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="text-center">
      <h2 className="font-bold">{message}</h2>
    </div>
  );
}
