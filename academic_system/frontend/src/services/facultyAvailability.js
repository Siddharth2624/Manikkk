import { api } from '../lib/api';

export const facultyAvailabilityService = {
  get: async (subjectId, semester, section) => {
    const params = new URLSearchParams({
      subject_id: subjectId,
      semester: semester.toString(),
      section,
    });
    const data = await api(`/faculty/availability?${params.toString()}`);
    // Convert backend format {day, slot} to frontend format "Day-Slot" (title case day)
    const slots = data?.available_slots || [];
    return slots.map(s => {
      // Convert "MON" -> "Mon", "TUE" -> "Tue", etc.
      const dayTitleCase = s.day.charAt(0) + s.day.slice(1).toLowerCase();
      return `${dayTitleCase}-${s.slot}`;
    });
  },

  update: async (data) => {
    // Convert frontend format "Day-Slot" to backend format {day, slot}
    const available_slots = data.available_slots.map(slotKey => {
      const [day, slot] = slotKey.split('-');
      // Capitalize day (e.g., "mon" -> "MON")
      const dayUpper = day.toUpperCase();
      return { day: dayUpper, slot: parseInt(slot, 10) };
    });

    return await api('/faculty/availability', {
      method: 'POST',
      body: JSON.stringify({
        ...data,
        available_slots,
      }),
    });
  },

  getEffective: async (filters) => {
    const params = new URLSearchParams();
    if (filters.facultyId) params.append('faculty_id', filters.facultyId);
    if (filters.day) params.append('day', filters.day);
    if (filters.slot) params.append('slot', filters.slot);
    return await api(`/faculty/availability/effective?${params.toString()}`);
  },

  createOverride: async (data) => {
    return await api('/faculty/availability/overrides', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getOverrides: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.facultyId) params.append('faculty_id', filters.facultyId);
    if (filters.startDate) params.append('start_date', filters.startDate);
    if (filters.endDate) params.append('end_date', filters.endDate);
    return await api(`/faculty/availability/overrides?${params.toString()}`);
  },

  deleteOverride: async (overrideId) => {
    return await api(`/faculty/availability/overrides/${overrideId}`, {
      method: 'DELETE',
    });
  },
};
