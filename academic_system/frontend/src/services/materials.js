import { api } from '../lib/api';

export const materialService = {
  create: async (data) => {
    return await api('/materials', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  upload: async (data) => {
    return await materialService.create(data);
  },

  list: async (params = {}) => {
    const searchParams = new URLSearchParams(params);
    return await api(`/materials?${searchParams}`);
  },

  subjects: async (params = {}) => {
    const searchParams = new URLSearchParams(params);
    return await api(`/materials/subjects?${searchParams}`);
  },

  getById: async (id) => {
    return await api(`/materials/${id}`);
  },

  open: async (id) => {
    return await api(`/materials/${id}/access`, {
      method: 'POST',
    });
  },

  delete: async (id) => {
    return await api(`/materials/${id}`, {
      method: 'DELETE',
    });
  },
};
