/**
 * Knowledge base management.
 *
 * Uploads files (PDF, DOCX, Markdown, plain text) or pasted text into either the
 * user's private knowledge base or a workspace they can write to, and lists what
 * is currently indexed.
 */

import { useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Loader2, Search, Trash2, Upload } from 'lucide-react';
import toast from 'react-hot-toast';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Badge } from '@/components/ui/Badge';
import { documentsApi, type DocumentSummary } from '@/services/documents';
import { enterpriseApi } from '@/services/enterprise';

export function Documents() {
  const [search, setSearch] = useState('');
  const [workspaceId, setWorkspaceId] = useState<string>('');
  const [progress, setProgress] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const documents = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
  });

  const formats = useQuery({
    queryKey: ['documents', 'formats'],
    queryFn: documentsApi.supportedFormats,
  });

  const workspaces = useQuery({
    queryKey: ['workspaces'],
    queryFn: () => enterpriseApi.myWorkspaces(),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      documentsApi.uploadFile(file, workspaceId || undefined, setProgress),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success(`Indexed ${result.chunks_indexed} chunk(s) from ${result.filename}`);
    },
    onError: () => {
      // The interceptor already surfaced the server's message.
    },
    onSettled: () => setProgress(null),
  });

  const deleteMutation = useMutation({
    mutationFn: (doc: DocumentSummary) =>
      documentsApi.remove(
        doc.document_id,
        doc.namespace.startsWith('workspace:') ? doc.namespace.split(':')[1] : undefined
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document removed');
    },
  });

  const accept = useMemo(
    () => formats.data?.extensions.join(',') ?? '.txt,.md,.pdf,.docx',
    [formats.data]
  );

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) uploadMutation.mutate(file);
    event.target.value = '';
  };

  const filtered = (documents.data ?? []).filter((doc) =>
    doc.filename.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Documents</h1>
        <p className="text-sm text-muted-foreground">
          Upload documents to make them retrievable in chat.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label htmlFor="workspace" className="mb-1 block text-sm font-medium">
                Destination
              </label>
              <select
                id="workspace"
                value={workspaceId}
                onChange={(e) => setWorkspaceId(e.target.value)}
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">My knowledge base (private)</option>
                {(workspaces.data ?? []).map((ws) => (
                  <option key={ws.id} value={ws.id}>
                    {ws.name} (shared)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept={accept}
                onChange={handleFileChange}
                className="hidden"
                data-testid="file-input"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadMutation.isPending}
              >
                {uploadMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Upload file
              </Button>
            </div>
          </div>

          {progress !== null && (
            <div
              className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          )}

          {formats.data && (
            <p className="text-xs text-muted-foreground">
              Accepts {formats.data.extensions.join(', ')} up to{' '}
              {formats.data.max_file_size_mb} MB.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter documents"
          className="pl-9"
          aria-label="Filter documents"
        />
      </div>

      {documents.isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : documents.isError ? (
        <ErrorState
          title="Could not load documents"
          description="Please try again."
          onRetry={() => documents.refetch()}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-8 w-8" />}
          title={search ? 'No matching documents' : 'No documents yet'}
          description={
            search
              ? 'Try a different filter.'
              : 'Upload a document to make it retrievable in chat.'
          }
        />
      ) : (
        <div className="space-y-2">
          {filtered.map((doc) => (
            <Card key={`${doc.namespace}:${doc.document_id}`}>
              <CardContent className="flex items-center justify-between gap-4 p-4">
                <div className="min-w-0">
                  <p className="truncate font-medium">{doc.filename}</p>
                  <p className="text-xs text-muted-foreground">
                    {doc.chunk_count} chunk{doc.chunk_count === 1 ? '' : 's'} ·{' '}
                    {doc.namespace.startsWith('workspace:') ? 'Shared' : 'Private'}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge variant="success">{doc.status}</Badge>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove ${doc.filename}`}
                    onClick={() => deleteMutation.mutate(doc)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
