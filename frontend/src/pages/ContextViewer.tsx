import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { CodeBlock } from '@/components/common/CodeBlock';
import { retrievalApi } from '@/services';
import { Search } from 'lucide-react';

export function ContextViewer() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<{ prompt: string; context: string; token_count?: number } | null>(null);

  const searchMutation = useMutation({
    mutationFn: () => retrievalApi.search({ query, top_k: 10 }),
    onSuccess: (data) => {
      const context = data.results?.map((r: { content: string }, i: number) => `[doc_${i + 1}]: ${r.content}`).join('\n\n') || '';
      setResult({
        prompt: `Context:\n${context}\n\nQuestion: ${query}\nAnswer:`,
        context,
        token_count: context.length / 4,
      });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Context Viewer</h1>
        <p className="text-muted-foreground">Inspect the prompt and retrieved context</p>
      </div>

      <Card>
        <CardContent className="flex gap-2 pt-6">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a query to view context..."
            className="flex-1"
            onKeyDown={(e) => e.key === 'Enter' && query.trim() && searchMutation.mutate()}
          />
          <Button onClick={() => query.trim() && searchMutation.mutate()} disabled={searchMutation.isPending || !query.trim()}>
            {searchMutation.isPending ? <Spinner size="sm" /> : <Search className="h-4 w-4" />}
          </Button>
        </CardContent>
      </Card>

      {searchMutation.isPending && (
        <div className="flex justify-center py-12"><Spinner /></div>
      )}

      {result && (
        <div className="grid gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Prompt Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <CodeBlock code={result.prompt} language="markdown" />
              {result.token_count && (
                <p className="mt-2 text-xs text-muted-foreground">~{Math.round(result.token_count)} tokens</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Retrieved Context</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-96 overflow-y-auto">
                <CodeBlock code={result.context} language="markdown" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
