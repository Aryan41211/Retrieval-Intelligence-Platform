import { cn } from '@/utils/cn';

interface CitationLinkProps {
  docIndex: number;
  chunkId: string;
  documentId: string;
  confidence?: number;
  className?: string;
  onClick?: () => void;
}

export function CitationLink({ docIndex, chunkId, documentId, confidence, className, onClick }: CitationLinkProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'inline-flex items-center rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary hover:bg-primary/20',
        className
      )}
      title={`Chunk ${chunkId} (doc ${documentId})${confidence ? `, confidence: ${(confidence * 100).toFixed(0)}%` : ''}`}
    >
      [{docIndex}]
    </button>
  );
}
