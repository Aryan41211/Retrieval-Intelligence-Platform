import { api } from './api';

export const retrievalApi = {
  search: async (payload: { query: string; top_k?: number; threshold?: number; filters?: Record<string, unknown>; strategy?: string }) => {
    const { data } = await api.post('/retrieval/search', payload);
    return data;
  },
  inspect: async (payload: { query: string; top_k?: number; filters?: Record<string, unknown> }) => {
    const { data } = await api.post('/retrieval/inspect', payload);
    return data;
  },
};
