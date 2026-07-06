import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Dashboard } from '@/pages/Dashboard';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );
}

describe('Dashboard', () => {
  it('renders dashboard heading', () => {
    render(<Dashboard />, { wrapper: Wrapper });
    expect(screen.getByText('Dashboard')).toBeDefined();
  });

  it('renders stat cards', () => {
    render(<Dashboard />, { wrapper: Wrapper });
    expect(screen.getByText('Documents')).toBeDefined();
    expect(screen.getByText('Conversations')).toBeDefined();
    expect(screen.getByText('Evaluations')).toBeDefined();
    expect(screen.getByText('System')).toBeDefined();
  });
});
