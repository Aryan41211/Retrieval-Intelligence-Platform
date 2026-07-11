import { useQuery } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { chatApi } from '@/services';
import { Quote } from 'lucide-react';

export function CitationExplorer() {
  const { data: messages, isLoading } = useQuery({
    queryKey: ['chat-history'],
    queryFn: () => chatApi.history(),
  });

  const citations = messages?.flatMap((msg: { citations?: Array<{ doc_index: number; chunk_id: string; document_id: string; confidence: number }> }) => msg.citations || []) || [];

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Citation Explorer</h1>
        <p className="text-muted-foreground">Explore citations and source references</p>
      </div>

      {citations.length === 0 ? (
        <EmptyState
          icon={<Quote className="h-12 w-12" />}
          title="No citations yet"
          description="Start a conversation in AI Chat to generate citations from retrieved documents."
        />
      ) : (
        <div className="grid gap-4">
          {citations.map((citation: { doc_index: number; chunk_id: string; document_id: string; confidence: number }, idx: number) => (
            <Card key={`${citation.document_id}-${citation.chunk_id}-${idx}`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Citation [{citation.doc_index}]</span>
                      <span className="text-xs text-muted-foreground">Chunk: {citation.chunk_id}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">Document: {citation.document_id}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">Confidence</div>
                    <div className="text-lg font-bold">{(citation.confidence * 100).toFixed(0)}%</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
