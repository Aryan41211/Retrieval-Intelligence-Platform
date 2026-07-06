import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { retrievalApi } from '@/services';

export function RetrievalInspector() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(10);

  const inspectMutation = useMutation({
    mutationFn: () => retrievalApi.inspect({ query, top_k: topK }),
  });

  const candidates = inspectMutation.data?.candidates || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Retrieval Inspector</h1>
        <p className="text-muted-foreground">Inspect how documents are retrieved and ranked</p>
      </div>

      <Card>
        <CardContent className="flex gap-2 pt-6">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a query to inspect retrieval..."
            className="flex-1"
            onKeyDown={(e) => e.key === 'Enter' && query.trim() && inspectMutation.mutate()}
          />
          <Input
            type="number"
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value) || 10)}
            className="w-20"
            min={1}
            max={50}
          />
          <Button onClick={() => query.trim() && inspectMutation.mutate()} disabled={inspectMutation.isPending || !query.trim()}>
            {inspectMutation.isPending ? <Spinner size="sm" /> : 'Inspect'}
          </Button>
        </CardContent>
      </Card>

      {inspectMutation.isPending && (
        <div className="flex justify-center py-12"><Spinner /></div>
      )}

      {!inspectMutation.isPending && candidates.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Method: {inspectMutation.data?.fusion_method || 'hybrid'}</span>
            <span>·</span>
            <span>Reranker: {inspectMutation.data?.reranker_used ? 'Yes' : 'No'}</span>
            <span>·</span>
            <span>{candidates.length} candidates</span>
          </div>
          {candidates.map((c: { chunk_id: string; document_id: string; content: string; similarity_score: number; rank: number; source_filename?: string; dense_score?: number; bm25_score?: number; rrf_score?: number; rerank_score?: number; final_score?: number }, idx: number) => (
            <Card key={`${c.chunk_id}-${idx}`}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">#{c.rank}</Badge>
                      <span className="text-sm font-medium">{c.source_filename || `Doc ${c.document_id}`}</span>
                      {c.chunk_id && <span className="text-xs text-muted-foreground">{c.chunk_id}</span>}
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-3">{c.content}</p>
                  </div>
                  <div className="flex flex-col gap-1 text-right text-xs">
                    {c.dense_score !== undefined && <span>Dense: {c.dense_score.toFixed(4)}</span>}
                    {c.bm25_score !== undefined && <span>BM25: {c.bm25_score.toFixed(4)}</span>}
                    {c.rrf_score !== undefined && <span>RRF: {c.rrf_score.toFixed(4)}</span>}
                    {c.rerank_score !== undefined && <span>Rerank: {c.rerank_score.toFixed(4)}</span>}
                    {c.final_score !== undefined && <span className="font-semibold">Final: {c.final_score.toFixed(4)}</span>}
                    {c.similarity_score > 0 && <span>Sim: {c.similarity_score.toFixed(4)}</span>}
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
