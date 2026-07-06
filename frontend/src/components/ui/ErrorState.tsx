import { cn } from '@/utils/cn';

interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export function ErrorState({ className, title = 'Something went wrong', description, onRetry, ...props }: ErrorStateProps) {
  return (
    <div
      className={cn('flex flex-col items-center justify-center rounded-lg border border-destructive/20 bg-destructive/5 p-12 text-center', className)}
      {...props}
    >
      <h3 className="mb-2 text-lg font-semibold text-destructive">{title}</h3>
      {description && (
        <p className="mb-6 max-w-sm text-sm text-muted-foreground">{description}</p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Try again
        </button>
      )}
    </div>
  );
}
