import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RequireAuth, RequireRole } from './RequireAuth';
import { AuthProvider } from '@/contexts/AuthContext';
import { tokenStore } from '@/services/tokenStore';

const me = vi.hoisted(() => vi.fn());

vi.mock('@/services/enterprise', () => ({
  enterpriseApi: {
    me,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  },
}));

function renderApp(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<div>Login page</div>} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <div>Protected content</div>
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth>
                <RequireRole roles={['admin']}>
                  <div>Admin content</div>
                </RequireRole>
              </RequireAuth>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('RequireAuth', () => {
  beforeEach(() => {
    window.localStorage.clear();
    me.mockReset();
  });

  it('redirects to login when there is no session', async () => {
    renderApp();
    expect(await screen.findByText('Login page')).toBeInTheDocument();
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument();
  });

  it('renders protected content for an authenticated user', async () => {
    tokenStore.setTokens({ accessToken: 'a', refreshToken: 'r' });
    me.mockResolvedValue({
      id: '1',
      email: 'a@b.com',
      username: 'alice',
      full_name: '',
      role: 'member',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
    });

    renderApp();
    expect(await screen.findByText('Protected content')).toBeInTheDocument();
  });

  it('redirects to login when the stored token is rejected', async () => {
    tokenStore.setTokens({ accessToken: 'stale', refreshToken: 'stale' });
    me.mockRejectedValue(new Error('401'));

    renderApp();
    expect(await screen.findByText('Login page')).toBeInTheDocument();
    // The unusable tokens must not be left behind.
    await waitFor(() => expect(tokenStore.hasSession()).toBe(false));
  });
});

describe('RequireRole', () => {
  beforeEach(() => {
    window.localStorage.clear();
    me.mockReset();
  });

  it('keeps a non-admin out of an admin route', async () => {
    tokenStore.setTokens({ accessToken: 'a', refreshToken: 'r' });
    me.mockResolvedValue({
      id: '1',
      email: 'a@b.com',
      username: 'alice',
      full_name: '',
      role: 'member',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
    });

    renderApp('/admin');
    // Redirected to "/" (the protected dashboard), not shown admin content.
    expect(await screen.findByText('Protected content')).toBeInTheDocument();
    expect(screen.queryByText('Admin content')).not.toBeInTheDocument();
  });

  it('admits an admin', async () => {
    tokenStore.setTokens({ accessToken: 'a', refreshToken: 'r' });
    me.mockResolvedValue({
      id: '1',
      email: 'a@b.com',
      username: 'root',
      full_name: '',
      role: 'admin',
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
    });

    renderApp('/admin');
    expect(await screen.findByText('Admin content')).toBeInTheDocument();
  });
});
