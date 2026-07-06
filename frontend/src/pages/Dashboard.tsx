import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { documentsApi, chatApi, evaluationApi } from '@/services';

export function Dashboard() {
  const { data: documents, isLoading: loadingDocs } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
  });

  const { data: chatHistory } = useQuery({
    queryKey: ['chat-history'],
    queryFn: () => chatApi.history(),
  });

  const { data: evaluations } = useQuery({
    queryKey: ['evaluations'],
    queryFn: evaluationApi.list,
  });

  const stats = [
    { label: 'Documents', value: documents?.length ?? 0, loading: loadingDocs },
    { label: 'Conversations', value: chatHistory?.length ?? 0, loading: false },
    { label: 'Evaluations', value: evaluations?.length ?? 0, loading: false },
    { label: 'System', value: 'Online', loading: false },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your Retrieval Intelligence Platform</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.label}</CardTitle>
            </CardHeader>
            <CardContent>
              {stat.loading ? (
                <Spinner size="sm" />
              ) : (
                <div className="text-2xl font-bold">{stat.value}</div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
