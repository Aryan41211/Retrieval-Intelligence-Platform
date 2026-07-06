import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell } from '@/components/layout/AppShell';
import { Dashboard } from '@/pages/Dashboard';
import { Chat } from '@/pages/Chat';
import { Documents } from '@/pages/Documents';
import { RetrievalInspector } from '@/pages/RetrievalInspector';
import { ContextViewer } from '@/pages/ContextViewer';
import { CitationExplorer } from '@/pages/CitationExplorer';
import { EvaluationDashboard } from '@/pages/EvaluationDashboard';
import { Experiments } from '@/pages/Experiments';
import { Settings } from '@/pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/retrieval" element={<RetrievalInspector />} />
            <Route path="/context" element={<ContextViewer />} />
            <Route path="/citations" element={<CitationExplorer />} />
            <Route path="/evaluation" element={<EvaluationDashboard />} />
            <Route path="/experiments" element={<Experiments />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
