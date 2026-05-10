import { api } from '../lib/api';

export const adminAssignmentService = {
  // Get all subject assignments
  getAll: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.semester) params.append('semester', filters.semester);
    if (filters.section) params.append('section', filters.section);
    if (filters.subjectId) params.append('subject_id', filters.subjectId);
    if (filters.facultyId) params.append('faculty_id', filters.facultyId);
    return await api(`/admin/subject-assignments?${params.toString()}`);
  },

  // Create new subject assignment
  create: async (data) => {
    return await api('/admin/subject-assignments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Delete assignment
  delete: async (assignmentId) => {
    return await api(`/admin/subject-assignments/${assignmentId}`, {
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
    if (filters.subjectId) params.append('subject_id', filters.facultyId);
    if (filters.fromDate) params.append('from_date', filters.fromDate);
    return await api(`/admin/override-log?${params.toString()}`);
  },

  // Delete override
  deleteOverride: async (overrideId) => {
    return await api(`/admin/override-log/${overrideId}`, {
      method: 'DELETE',
    });
  },
};
