import { api } from './api';

export const chatApi = {
  history: async (conversationId?: string) => {
    const { data } = await api.get('/chat', {
      params: { conversation_id: conversationId },
    });
    return data;
  },
  send: async (payload: { query: string; conversation_id?: string; context?: Record<string, unknown> }, signal?: AbortSignal) => {
    const { data } = await api.post('/chat', payload, { signal });
    return data;
  },
  clear: async (conversationId: string) => {
    const { data } = await api.delete('/chat', { params: { conversation_id: conversationId } });
    return data;
  },
};
