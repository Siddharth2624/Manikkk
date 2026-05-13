import { api, clearAuthSession } from '../lib/api';

export const authService = {
  login: async (email, password) => {
    const data = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    return data;
  },

  register: async (userData) => {
    const data = await api('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    return data;
  },

  logout: async () => {
    clearAuthSession();
  },

  getCurrentUser: async () => {
    return await api('/auth/me');
  },

  changePassword: async (currentPassword, newPassword) => {
    return await api('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
  },
};
