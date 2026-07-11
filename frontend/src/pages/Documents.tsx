import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { documentsApi } from '@/services';
import { Upload, Trash2, RefreshCw, Search } from 'lucide-react';
import toast from 'react-hot-toast';

export function Documents() {
  const [search, setSearch] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
  });

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => documentsApi.upload(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document uploaded successfully');
    },
    onError: () => {
      toast.error('Failed to upload document');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document deleted');
    },
    onError: () => toast.error('Failed to delete document'),
  });

  const reindexMutation = useMutation({
    mutationFn: (id: string) => documentsApi.reindex(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Re-indexing started');
    },
    onError: () => toast.error('Failed to re-index document'),
  });

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    uploadMutation.mutate(formData);
    e.target.value = '';
  };

  const filteredDocs = documents?.filter((doc: { filename: string }) =>
    doc.filename.toLowerCase().includes(search.toLowerCase())
  );

  const getStatusVariant = (status: string) => {
    switch (status.toLowerCase()) {
      case 'ready':
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'error':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
          <p className="text-muted-foreground">Manage your knowledge base</p>
        </div>
        <input ref={fileInputRef} type="file" className="hidden" onChange={handleUpload} accept=".pdf,.docx,.txt,.md,.markdown" />
        <Button onClick={() => fileInputRef.current?.click()}>
          <Upload className="mr-2 h-4 w-4" />
          Upload
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search documents..."
            className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : filteredDocs && filteredDocs.length > 0 ? (
        <div className="grid gap-4">
          {filteredDocs.map((doc: { document_id: string; filename: string; size_bytes: number; uploaded_at: string; status: string; chunk_count?: number }) => (
            <Card key={doc.document_id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="space-y-1">
                  <h3 className="font-medium">{doc.filename}</h3>
                  <div className="flex items-center gap-3 text-sm text-muted-foreground">
                    <span>{(doc.size_bytes / 1024).toFixed(1)} KB</span>
                    <span>Uploaded {new Date(doc.uploaded_at).toLocaleDateString()}</span>
                    {doc.chunk_count !== undefined && <span>{doc.chunk_count} chunks</span>}
                  </div>
                  <Badge variant={getStatusVariant(doc.status)}>{doc.status}</Badge>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="icon" onClick={() => reindexMutation.mutate(doc.document_id)} disabled={reindexMutation.isPending}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                  <Button variant="destructive" size="icon" onClick={() => deleteMutation.mutate(doc.document_id)} disabled={deleteMutation.isPending}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No documents found"
          description="Upload a document to get started. Supported formats: PDF, DOCX, TXT, MD."
          action={
            <Button onClick={() => fileInputRef.current?.click()}>
              <Upload className="mr-2 h-4 w-4" />
              Upload Document
            </Button>
          }
        />
      )}
    </div>
  );
}
