import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { evaluationApi } from '@/services';
import { BarChart3 } from 'lucide-react';

export function EvaluationDashboard() {
  const { data: evaluations, isLoading } = useQuery({
    queryKey: ['evaluations'],
    queryFn: evaluationApi.list,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const metrics = [
    { label: 'Overall Score', value: evaluations?.overall_score?.toFixed(2) ?? 'N/A' },
    { label: 'Total Evaluations', value: evaluations?.length ?? 0 },
    { label: 'Last Run', value: evaluations?.length ? 'Recent' : 'Never' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Evaluation Dashboard</h1>
        <p className="text-muted-foreground">Monitor RAG quality metrics and performance</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{metric.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metric.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {evaluations && evaluations.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Recent Evaluations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {evaluations.map((eval_: { evaluation_id: string; evaluation_type: string; score: number; timestamp: string }, idx: number) => (
                <div key={eval_.evaluation_id || idx} className="flex items-center justify-between rounded-lg border border-border p-4">
                  <div>
                    <div className="font-medium">{eval_.evaluation_type}</div>
                    <div className="text-sm text-muted-foreground">{new Date(eval_.timestamp).toLocaleString()}</div>
                  </div>
                  <div className="text-xl font-bold">{(eval_.score * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <EmptyState
          icon={<BarChart3 className="h-12 w-12" />}
          title="No evaluations yet"
          description="Run an evaluation to see RAGAS and DeepEval metrics here."
        />
      )}
    </div>
  );
}
