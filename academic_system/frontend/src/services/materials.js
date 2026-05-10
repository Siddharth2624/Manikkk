import { api } from '../lib/api';

export const materialService = {
  upload: async (formData) => {
    const token = localStorage.getItem('access_token');
    const response = await fetch('/api/v1/materials/upload', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });
    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  },

  list: async (params = {}) => {
    const searchParams = new URLSearchParams(params);
    return await api(`/materials?${searchParams}`);
  },

  getById: async (id) => {
    return await api(`/materials/${id}`);
  },

  download: async (id) => {
    const token = localStorage.getItem('access_token');
    window.open(`/api/v1/materials/${id}/download?token=${token}`, '_blank');
  },

  delete: async (id) => {
    return await api(`/materials/${id}`, {
      method: 'DELETE',
    });
  },
};
