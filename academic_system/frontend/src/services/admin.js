import { api } from '../lib/api';

export const adminService = {
  // Get current user info
  getMe: async () => {
    return await api('/auth/me');
  },

  // Get public stats (no auth required for testing)
  getPublicStats: async () => {
    return await api('/admin/stats/public');
  },

  // Get admin-only stats
  getStats: async () => {
    return await api('/admin/stats');
  },

  // Get users list
  getUsers: async (params = {}) => {
    const searchParams = new URLSearchParams(params);
    return await api(`/admin/users?${searchParams}`);
  },

  // Get students by class (faculty/admin accessible)
  getStudentsByClass: async (semester, section) => {
    return await api(`/admin/students/by-class?semester=${semester}&section=${section}`);
  },

  // Get subjects list
  getSubjects: async (params = {}) => {
    const searchParams = new URLSearchParams(params);
    return await api(`/admin/subjects?${searchParams}`);
  },

  // Create new subject
  createSubject: async (subjectData) => {
    return await api('/admin/subjects', {
      method: 'POST',
      body: JSON.stringify(subjectData),
    });
  },

  // Create new user
  createUser: async (userData) => {
    return await api('/admin/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },

  // Update user
  updateUser: async (userId, userData) => {
    return await api(`/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
  },

  // Delete user
  deleteUser: async (userId) => {
    return await api(`/admin/users/${userId}`, {
      method: 'DELETE',
    });
  },

  // Test admin endpoint
  testAdmin: async () => {
    return await api('/admin/test');
  },
};
