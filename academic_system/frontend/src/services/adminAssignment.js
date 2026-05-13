import { api } from '../lib/api';

export const adminAssignmentService = {
  // Get all subject assignments
  getAll: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.semester) params.append('semester', filters.semester);
    if (filters.section) params.append('section', filters.section);
    if (filters.subjectId) params.append('subject_id', filters.subjectId);
    if (filters.facultyId) params.append('faculty_id', filters.facultyId);
    const data = await api(`/admin/assignments?${params.toString()}`);
    return { assignments: Array.isArray(data) ? data : (data?.assignments || []) };
  },

  // Create new subject assignment
  create: async (data) => {
    return await api('/admin/assign-subject', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Delete assignment
  delete: async (assignmentId) => {
    return await api(`/admin/assign-subject/${assignmentId}`, {
      method: 'DELETE',
    });
  },

  // Get effective availability for a faculty
  getEffectiveAvailability: async (filters) => {
    const params = new URLSearchParams();
    if (filters.facultyId) params.append('faculty_id', filters.facultyId);
    if (filters.subjectId) params.append('subject_id', filters.subjectId);
    if (filters.semester) params.append('semester', filters.semester);
    if (filters.section) params.append('section', filters.section);
    return await api(`/admin/faculty-availability/effective?${params.toString()}`);
  },

  // Create availability override
  createOverride: async (data) => {
    return await api('/admin/overrides', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Get override audit log
  getOverrides: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.facultyId) params.append('faculty_id', filters.facultyId);
    if (filters.subjectId) params.append('subject_id', filters.subjectId);
    const data = await api(`/admin/overrides?${params.toString()}`);
    return { overrides: Array.isArray(data) ? data : (data?.overrides || []) };
  },

  // Delete override
  deleteOverride: async (overrideId) => {
    return await api(`/admin/overrides/${overrideId}`, {
      method: 'DELETE',
    });
  },
};
