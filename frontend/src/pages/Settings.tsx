import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { settingsApi } from '@/services';
import toast from 'react-hot-toast';

export function Settings() {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.get,
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => settingsApi.update(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      toast.success('Settings saved');
    },
    onError: () => toast.error('Failed to save settings'),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Configure your RAG pipeline</p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>LLM Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium">LLM Provider</label>
              <Input
                defaultValue={settings?.llm_provider?.name as string || 'fake'}
                onBlur={(e) => updateMutation.mutate({ llm_provider: { name: e.target.value } })}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Model</label>
              <Input
                defaultValue={settings?.llm_provider?.model as string || 'fake-model'}
                onBlur={(e) => updateMutation.mutate({ llm_provider: { model: e.target.value } })}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Temperature</label>
              <Input
                type="number"
                step="0.1"
                min="0"
                max="2"
                defaultValue={settings?.temperature ?? 0.2}
                onBlur={(e) => updateMutation.mutate({ temperature: parseFloat(e.target.value) })}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Retrieval Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Top-K</label>
              <Input
                type="number"
                min={1}
                max={100}
                defaultValue={settings?.top_k ?? 10}
                onBlur={(e) => updateMutation.mutate({ top_k: parseInt(e.target.value) })}
              />
            </div>
            <div className="grid gap-2">
              <label className="text-sm font-medium">Retrieval Strategy</label>
              <Input
                defaultValue={settings?.retrieval_strategy?.name as string || 'hybrid'}
                onBlur={(e) => updateMutation.mutate({ retrieval_strategy: { name: e.target.value } })}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Embedding Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium">Embedding Model</label>
              <Input
                defaultValue={settings?.embedding_model?.name as string || 'all-MiniLM-L6-v2'}
                onBlur={(e) => updateMutation.mutate({ embedding_model: { name: e.target.value } })}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
