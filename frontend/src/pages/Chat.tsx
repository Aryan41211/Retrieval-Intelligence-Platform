import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';
import { CitationLink } from '@/components/common/CitationLink';
import { chatApi } from '@/services';
import { Send, Trash2, User } from 'lucide-react';
import toast from 'react-hot-toast';

export function Chat() {
  const [query, setQuery] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: messages, isLoading } = useQuery({
    queryKey: ['chat-history', conversationId],
    queryFn: () => chatApi.history(conversationId),
  });

  const sendMutation = useMutation({
    mutationFn: (q: string) => chatApi.send({ query: q, conversation_id: conversationId }),
    onSuccess: (data) => {
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id);
      }
      setQuery('');
      queryClient.invalidateQueries({ queryKey: ['chat-history'] });
    },
    onError: () => {
      toast.error('Failed to send message');
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => chatApi.clear(conversationId || ''),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chat-history'] });
      toast.success('Chat cleared');
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || sendMutation.isPending) return;
    sendMutation.mutate(query);
  };

  const renderContent = () => {
    if (isLoading) return <Spinner />;
    if (!messages || messages.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="mb-4 text-4xl">💬</div>
          <h3 className="mb-2 text-lg font-semibold">Start a conversation</h3>
          <p className="max-w-md text-sm text-muted-foreground">
            Ask questions about your documents. The AI will retrieve relevant context and provide grounded answers with citations.
          </p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {messages.map((msg: { role: string; content: string; timestamp?: string; retrieved_chunks?: Array<{ chunk_id: string; document_id: string; content: string; similarity_score: number }>; citations?: Array<{ doc_index: number; chunk_id: string }> }, idx: number) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                AI
              </div>
            )}
            <div className={`max-w-[80%] rounded-lg px-4 py-3 ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
              <div className="prose dark:prose-invert max-w-none text-sm">
                <MarkdownRenderer content={msg.content} />
              </div>
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.citations.map((citation, cIdx) => (
                    <CitationLink key={cIdx} {...citation} />
                  ))}
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}
        {sendMutation.isPending && (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
              AI
            </div>
            <div className="rounded-lg bg-muted px-4 py-3">
              <Spinner size="sm" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
    );
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <Card className="flex h-full flex-col">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>AI Chat</CardTitle>
          <Button variant="outline" size="sm" onClick={() => clearMutation.mutate()} disabled={!conversationId}>
            <Trash2 className="mr-2 h-4 w-4" />
            Clear chat
          </Button>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-4 overflow-hidden p-0">
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {renderContent()}
          </div>
          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border p-4">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              disabled={sendMutation.isPending}
            />
            <Button type="submit" disabled={!query.trim() || sendMutation.isPending}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
