import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Chat } from '@/pages/Chat';

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

describe('Chat', () => {
  it('renders chat heading', () => {
    render(<Chat />, { wrapper: Wrapper });
    expect(screen.getByText('AI Chat')).toBeDefined();
  });

  it('renders empty state message', async () => {
    render(<Chat />, { wrapper: Wrapper });
    await waitFor(() => expect(screen.getByText('Start a conversation')).toBeDefined());
  });

  it('renders input field', async () => {
    render(<Chat />, { wrapper: Wrapper });
    await waitFor(() => expect(screen.getByPlaceholderText(/ask a question/i)).toBeDefined());
  });
});
