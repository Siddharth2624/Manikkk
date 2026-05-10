import { api } from '../lib/api';

export const timetableService = {
  generate: async (data) => {
    return await api('/timetable/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  view: async ({ semester, section, version = null }) => {
    const params = new URLSearchParams({
      semester: semester.toString(),
      section,
    });
    if (version !== null) params.append('version', version.toString());
    return await api(`/timetable?${params.toString()}`);
  },

  updateSlot: async (timetableId, slotData) => {
    return await api(`/timetable/slots/${timetableId}`, {
      method: 'PUT',
      body: JSON.stringify(slotData),
    });
  },

  getTimetable: async (semester, section) => {
    return await api(`/timetable?semester=${semester}&section=${section}`);
  },

  getFacultySchedule: async (facultyId) => {
    return await api(`/timetable/faculty/${facultyId}`);
  },

  listTimetables: async () => {
    return await api('/timetable/list');
  },

  delete: async ({ semester, section }) => {
    return await api(`/timetable/${semester}/${section}`, {
      method: 'DELETE',
    });
  },

  deleteTimetable: async (semester, section) => {
    return await api(`/timetable/${semester}/${section}`, {
      method: 'DELETE',
    });
  },

  getTimeSlots: async () => {
    return await api('/timetable/slots');
  },
};
