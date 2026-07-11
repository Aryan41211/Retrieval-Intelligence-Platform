import { useQuery } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { experimentsApi } from '@/services';
import { FlaskConical } from 'lucide-react';

export function Experiments() {
  const { data: experiments, isLoading } = useQuery({
    queryKey: ['experiments'],
    queryFn: experimentsApi.list,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Experiments</h1>
          <p className="text-muted-foreground">Compare retrieval strategies, embedding models, and prompts</p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : experiments && experiments.length > 0 ? (
        <div className="grid gap-4">
          {experiments.map((exp: { experiment_id: string; name: string; status: string; created_at: string }) => (
            <Card key={exp.experiment_id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="space-y-1">
                  <h3 className="font-medium">{exp.name}</h3>
                  <div className="flex items-center gap-3 text-sm text-muted-foreground">
                    <span>ID: {exp.experiment_id}</span>
                    <span>Created {new Date(exp.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <Badge variant={exp.status === 'completed' ? 'success' : 'secondary'}>{exp.status}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<FlaskConical className="h-12 w-12" />}
          title="No experiments yet"
          description="Create an experiment to compare different RAG configurations and strategies."
        />
      )}
    </div>
  );
}
