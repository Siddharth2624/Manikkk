import { api } from '../lib/api';

export const facultyAssignmentService = {
  getMySubjects: async () => {
    const data = await api('/faculty/my-subjects');
    return data || [];
  },

  assign: async (data) => {
    return await api('/faculty/assignments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getAll: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.semester) params.append('semester', filters.semester);
    if (filters.section) params.append('section', filters.section);
    if (filters.subjectId) params.append('subject_id', filters.subjectId);
    if (filters.facultyId) params.append('faculty_id', filters.facultyId);
    const data = await api(`/faculty/assignments?${params.toString()}`);
    return data.assignments || [];
  },

  delete: async (assignmentId) => {
    return await api(`/faculty/assignments/${assignmentId}`, {
      method: 'DELETE',
    });
  },
};
