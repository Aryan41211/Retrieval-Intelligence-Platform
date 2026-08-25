import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AppShell } from '@/components/layout/AppShell';
import { AuthProvider } from '@/contexts/AuthContext';
import { RequireAuth, RequireRole } from '@/components/auth/RequireAuth';
import { Dashboard } from '@/pages/Dashboard';
import { Chat } from '@/pages/Chat';
import { Documents } from '@/pages/Documents';
import { RetrievalInspector } from '@/pages/RetrievalInspector';
import { ContextViewer } from '@/pages/ContextViewer';
import { CitationExplorer } from '@/pages/CitationExplorer';
import { EvaluationDashboard } from '@/pages/EvaluationDashboard';
import { Experiments } from '@/pages/Experiments';
import { Settings } from '@/pages/Settings';
import { Login } from '@/pages/Login';
import { Admin } from '@/pages/Admin';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/** Application routes that require an authenticated session. */
function ProtectedRoutes() {
  return (
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
        <Route
          path="/admin"
          element={
            <RequireRole roles={['admin']}>
              <Admin />
            </RequireRole>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Toaster
            position="top-right"
            toastOptions={{ className: 'dark:bg-slate-800 dark:text-white' }}
          />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/*"
              element={
                <RequireAuth>
                  <ProtectedRoutes />
                </RequireAuth>
              }
            />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
