import { api } from './api';

export const evaluationApi = {
  list: async () => {
    const { data } = await api.get('/evaluation/history');
    return data;
  },
  run: async (payload: { dataset_id?: string; dataset?: Array<Record<string, unknown>>; evaluation_types?: string[]; metrics?: Record<string, unknown> }) => {
    const { data } = await api.post('/evaluation/run', payload);
    return data;
  },
};
