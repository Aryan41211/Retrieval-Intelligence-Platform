/**
 * Persistent storage for auth tokens.
 *
 * Kept separate from the axios instance so the request interceptor, the refresh
 * flow and the auth context all read the same source of truth without importing
 * each other (which would create a cycle).
 *
 * Tokens live in localStorage so a reload keeps the session. Every access is
 * wrapped because storage throws in private-mode and sandboxed contexts.
 */

const ACCESS_TOKEN_KEY = 'rip.accessToken';
const REFRESH_TOKEN_KEY = 'rip.refreshToken';

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

function safeGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable - session becomes memory-only */
  }
}

function safeRemove(key: string): void {
  try {
    window.localStorage.removeItem(key);
  } catch {
    /* storage unavailable */
  }
}

export const tokenStore = {
  getAccessToken: (): string | null => safeGet(ACCESS_TOKEN_KEY),
  getRefreshToken: (): string | null => safeGet(REFRESH_TOKEN_KEY),

  setTokens: ({ accessToken, refreshToken }: StoredTokens): void => {
    safeSet(ACCESS_TOKEN_KEY, accessToken);
    safeSet(REFRESH_TOKEN_KEY, refreshToken);
  },

  clear: (): void => {
    safeRemove(ACCESS_TOKEN_KEY);
    safeRemove(REFRESH_TOKEN_KEY);
  },

  hasSession: (): boolean => Boolean(safeGet(ACCESS_TOKEN_KEY)),
};

/**
 * Decode a JWT payload without verifying it.
 *
 * Used only to read a non-authoritative expiry for proactive refresh; the
 * server remains the sole authority on validity.
 */
export function decodeTokenPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payload] = token.split('.');
    if (!payload) return null;
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(normalized)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** Return true when the access token is missing or within `skewSeconds` of expiry. */
export function isAccessTokenExpiring(skewSeconds = 30): boolean {
  const token = tokenStore.getAccessToken();
  if (!token) return true;
  const payload = decodeTokenPayload(token);
  const exp = payload?.exp;
  if (typeof exp !== 'number') return false;
  return Date.now() / 1000 >= exp - skewSeconds;
}
