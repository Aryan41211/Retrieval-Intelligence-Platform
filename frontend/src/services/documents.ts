import { api } from './api';

export const documentsApi = {
  list: async () => {
    const { data } = await api.get('/documents');
    return data;
  },
  upload: async (payload: FormData) => {
    const { data } = await api.post('/documents/upload', payload, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  delete: async (id: string) => {
    const { data } = await api.delete(`/documents/${id}`);
    return data;
  },
  reindex: async (id: string) => {
    const { data } = await api.post(`/documents/${id}/reindex`);
    return data;
  },
};
