import { beforeEach, describe, expect, it, vi } from 'vitest';
import { decodeTokenPayload, isAccessTokenExpiring, tokenStore } from './tokenStore';

/** Build an unsigned JWT with the given payload (signature is never checked here). */
function makeToken(payload: Record<string, unknown>): string {
  const encode = (value: object) =>
    btoa(JSON.stringify(value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  return `${encode({ alg: 'HS256' })}.${encode(payload)}.sig`;
}

describe('tokenStore', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it('round-trips tokens', () => {
    tokenStore.setTokens({ accessToken: 'a1', refreshToken: 'r1' });
    expect(tokenStore.getAccessToken()).toBe('a1');
    expect(tokenStore.getRefreshToken()).toBe('r1');
    expect(tokenStore.hasSession()).toBe(true);
  });

  it('reports no session when empty', () => {
    expect(tokenStore.hasSession()).toBe(false);
    expect(tokenStore.getAccessToken()).toBeNull();
  });

  it('clears both tokens', () => {
    tokenStore.setTokens({ accessToken: 'a1', refreshToken: 'r1' });
    tokenStore.clear();
    expect(tokenStore.getAccessToken()).toBeNull();
    expect(tokenStore.getRefreshToken()).toBeNull();
    expect(tokenStore.hasSession()).toBe(false);
  });

  it('survives storage throwing (private mode / blocked site data)', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied');
    });
    expect(() => tokenStore.setTokens({ accessToken: 'a', refreshToken: 'r' })).not.toThrow();
    expect(tokenStore.getAccessToken()).toBeNull();
    expect(tokenStore.hasSession()).toBe(false);
  });
});

describe('decodeTokenPayload', () => {
  it('decodes a well-formed payload', () => {
    const token = makeToken({ sub: 'user-1', role: 'admin' });
    expect(decodeTokenPayload(token)).toMatchObject({ sub: 'user-1', role: 'admin' });
  });

  it('returns null for malformed input rather than throwing', () => {
    expect(decodeTokenPayload('not-a-jwt')).toBeNull();
    expect(decodeTokenPayload('')).toBeNull();
    expect(decodeTokenPayload('a.!!!.c')).toBeNull();
  });
});

describe('isAccessTokenExpiring', () => {
  beforeEach(() => {
    // Restore first: an earlier test replaces Storage.prototype methods, and
    // that spy would otherwise leak into this suite and make every read null.
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  it('treats a missing token as expiring', () => {
    expect(isAccessTokenExpiring()).toBe(true);
  });

  it('detects an expired token', () => {
    const past = Math.floor(Date.now() / 1000) - 60;
    tokenStore.setTokens({ accessToken: makeToken({ exp: past }), refreshToken: 'r' });
    expect(isAccessTokenExpiring()).toBe(true);
  });

  it('accepts a token that is still comfortably valid', () => {
    const future = Math.floor(Date.now() / 1000) + 3600;
    tokenStore.setTokens({ accessToken: makeToken({ exp: future }), refreshToken: 'r' });
    expect(isAccessTokenExpiring()).toBe(false);
  });

  it('treats a token inside the skew window as expiring', () => {
    const soon = Math.floor(Date.now() / 1000) + 10;
    tokenStore.setTokens({ accessToken: makeToken({ exp: soon }), refreshToken: 'r' });
    expect(isAccessTokenExpiring(30)).toBe(true);
  });
});
