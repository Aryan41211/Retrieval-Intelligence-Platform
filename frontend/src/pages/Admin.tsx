/**
 * Admin dashboard: platform statistics and the audit trail.
 *
 * Reachable only through RequireRole; the backend independently enforces the
 * `view_analytics` permission, so this guard is convenience, not security.
 */

import { useQuery } from '@tanstack/react-query';
import { enterpriseApi } from '@/services/enterprise';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';

interface StatTileProps {
  label: string;
  value: number | undefined;
}

function StatTile({ label, value }: StatTileProps) {
  return (
    <Card className="p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value ?? '—'}</p>
    </Card>
  );
}

export function Admin() {
  const stats = useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: enterpriseApi.dashboard,
  });

  const audit = useQuery({
    queryKey: ['admin', 'audit'],
    queryFn: () => enterpriseApi.auditLogs(25, 0),
  });

  if (stats.isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (stats.isError) {
    return (
      <ErrorState
        title="Could not load admin data"
        description="You may not have permission to view analytics."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Admin</h1>
        <p className="text-sm text-muted-foreground">Platform usage and activity</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <StatTile label="Total users" value={stats.data?.total_users} />
        <StatTile label="Active users" value={stats.data?.active_users} />
        <StatTile label="Workspaces" value={stats.data?.total_workspaces} />
        <StatTile label="Conversations" value={stats.data?.total_conversations} />
        <StatTile label="Messages" value={stats.data?.total_messages} />
        <StatTile label="Audit records" value={stats.data?.recent_audit_count} />
      </div>

      <Card className="p-4">
        <h2 className="mb-3 text-lg font-medium">Recent activity</h2>
        {audit.isLoading ? (
          <Spinner />
        ) : audit.isError ? (
          <ErrorState title="Could not load the audit log" description="Please try again." />
        ) : !audit.data?.length ? (
          <EmptyState title="No activity yet" description="Audit records will appear here." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Action</th>
                  <th className="py-2 pr-4 font-medium">Resource</th>
                  <th className="py-2 pr-4 font-medium">IP</th>
                  <th className="py-2 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.map((entry) => (
                  <tr key={entry.id} className="border-b border-border/50">
                    <td className="py-2 pr-4">{entry.action}</td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {entry.resource_type ?? '—'}
                    </td>
                    <td className="py-2 pr-4 text-muted-foreground">
                      {entry.ip_address ?? '—'}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
