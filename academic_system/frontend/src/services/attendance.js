import { api } from '../lib/api';

export const attendanceService = {
  // Faculty: Mark attendance for students
  mark: async (data) => {
    return await api('/attendance/mark', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Student: Get their own attendance summary
  getMySummary: async (subjectId = null) => {
    const params = subjectId ? `?subject_id=${subjectId}` : '';
    return await api(`/attendance/my-summary${params}`);
  },

  // Faculty/Admin: Get attendance report for a subject
  getReport: async (subjectId, params = {}) => {
    const searchParams = new URLSearchParams(params);
    return await api(`/attendance/report/${subjectId}?${searchParams}`);
  },

  // Faculty/Admin: Get daily attendance for a subject
  getDaily: async (subjectId, date) => {
    return await api(`/attendance/daily/${subjectId}?attendance_date=${date}`);
  },
};
