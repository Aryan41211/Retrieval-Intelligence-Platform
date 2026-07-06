import { api } from './api';

export const settingsApi = {
  get: async () => {
    const { data } = await api.get('/settings');
    return data;
  },
  update: async (payload: Record<string, unknown>) => {
    const { data } = await api.put('/settings', payload);
    return data;
  },
};
