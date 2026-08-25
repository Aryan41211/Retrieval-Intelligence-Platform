import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import toast from 'react-hot-toast';
import { tokenStore } from './tokenStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/** Endpoints that must not carry (or retry with) a bearer token. */
const PUBLIC_PATHS = [
  '/auth/login',
  '/auth/register',
  '/auth/refresh',
  '/auth/password-reset',
  '/auth/email/verify',
];

function isPublicPath(url: string | undefined): boolean {
  if (!url) return false;
  return PUBLIC_PATHS.some((path) => url.includes(path));
}

/**
 * Attach the access token to every request.
 *
 * Every data-plane router on the backend requires a bearer JWT. Without this
 * interceptor the entire frontend received 401 on every call.
 */
api.interceptors.request.use((config) => {
  const token = tokenStore.getAccessToken();
  if (token && !isPublicPath(config.url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/** Callback invoked when the session can no longer be recovered. */
let onSessionExpired: (() => void) | null = null;

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

// A single in-flight refresh shared by all queued requests, so a burst of
// concurrent 401s triggers one refresh rather than one per request.
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) throw new Error('No refresh token');

  // Bare axios: the shared instance would recurse through this interceptor.
  const { data } = await axios.post(
    `${API_BASE_URL}/auth/refresh`,
    { refresh_token: refreshToken },
    { headers: { 'Content-Type': 'application/json' } }
  );
  tokenStore.setTokens({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
  });
  return data.access_token as string;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string; message?: string }>) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;

    // On a 401, try exactly one transparent refresh + replay.
    if (
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !isPublicPath(original.url) &&
      tokenStore.getRefreshToken()
    ) {
      original._retried = true;
      try {
        refreshPromise = refreshPromise ?? refreshAccessToken();
        const token = await refreshPromise;
        refreshPromise = null;
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        refreshPromise = null;
        tokenStore.clear();
        onSessionExpired?.();
        toast.error('Your session expired. Please sign in again.');
        return Promise.reject(error);
      }
    }

    if (error.response?.status === 401 && !isPublicPath(original?.url)) {
      tokenStore.clear();
      onSessionExpired?.();
    }

    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred';
    toast.error(message);
    return Promise.reject(error);
  }
);

export type {
  Document,
  DocumentUploadRequest,
  DocumentUploadResponse,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  RetrievalResult,
  RetrievalRequest,
  RetrievalResponse,
  RetrievalInspectResponse,
  EvaluationResult,
  EvaluationRequest,
  EvaluationResponse,
  ExperimentResult,
  ExperimentRequest,
  ExperimentResponse,
  SettingsResponse,
  Theme,
} from '@/types';
