import { api } from './api';

export const experimentsApi = {
  list: async () => {
    const { data } = await api.get('/experiments');
    return data;
  },
  create: async (payload: { name: string; description?: string; configuration: Record<string, unknown>; dataset_id?: string }) => {
    const { data } = await api.post('/experiments', payload);
    return data;
  },
};
