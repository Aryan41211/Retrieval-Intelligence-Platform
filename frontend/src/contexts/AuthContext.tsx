/**
 * Authentication state for the whole application.
 *
 * Holds the current user, exposes login/register/logout, and restores a session
 * from stored tokens on mount. Every data-plane endpoint requires a bearer JWT,
 * so nothing in the app can load until this has resolved.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { enterpriseApi } from '@/services/enterprise';
import { setSessionExpiredHandler } from '@/services/api';
import { tokenStore } from '@/services/tokenStore';
import type { TokenResponse, User } from '@/types';

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  /** True until the initial session restore completes. */
  isLoading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function storeTokens(tokens: TokenResponse): void {
  tokenStore.setTokens({
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
  });
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  // The axios interceptor cannot import this module (cycle), so it calls back
  // in when a refresh fails and the session is unrecoverable.
  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    return () => setSessionExpiredHandler(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!tokenStore.hasSession()) {
      setUser(null);
      return;
    }
    try {
      setUser(await enterpriseApi.me());
    } catch {
      clearSession();
    }
  }, [clearSession]);

  // Restore any existing session once, on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!tokenStore.hasSession()) {
        if (!cancelled) setIsLoading(false);
        return;
      }
      try {
        const me = await enterpriseApi.me();
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const login = useCallback(async (identifier: string, password: string) => {
    const tokens = await enterpriseApi.login({ identifier, password });
    storeTokens(tokens);
    setUser(await enterpriseApi.me());
  }, []);

  const register = useCallback(
    async (email: string, username: string, password: string) => {
      const tokens = await enterpriseApi.register({ email, username, password });
      storeTokens(tokens);
      setUser(await enterpriseApi.me());
    },
    []
  );

  const logout = useCallback(async () => {
    try {
      await enterpriseApi.logout();
    } catch {
      // Logout is stateless server-side; discarding local tokens is what counts.
    }
    clearSession();
  }, [clearSession]);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, isLoading, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
