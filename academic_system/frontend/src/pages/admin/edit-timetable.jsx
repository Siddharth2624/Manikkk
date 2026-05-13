import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input, Label } from '../../components/ui/input';
import {
  ArrowLeft,
  Save,
  RotateCcw,
  Clock,
  Copy,
  Check,
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
  History,
} from 'lucide-react';
import { timetableService } from '../../services/timetable';
import { adminService } from '../../services/admin';
import { api } from '../../lib/api';

const DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI'];
const TIME_SLOTS = [
  { slot: 1, time: '9:00 - 9:50' },
  { slot: 2, time: '9:50 - 10:40' },
  { slot: 3, time: '10:40 - 11:30' },
  { slot: 4, time: '11:30 - 12:20' },
  { slot: 5, time: '12:20 - 1:10' },
  { slot: 6, time: '1:10 - 2:00' },
  { slot: 7, time: '2:00 - 2:50' },
  { slot: 8, time: '2:50 - 3:40' },
  { slot: 9, time: '3:40 - 4:30' },
  { slot: 10, time: '4:30 - 5:20' },
];

// Helper to get slot number from slot object or number
const getSlotNumber = (slot) => typeof slot === 'object' ? slot.slot : slot;

// Slot time display
const getSlotTime = (slot) => {
  if (typeof slot === 'object') return slot.time;
  const found = TIME_SLOTS.find(s => s.slot === slot);
  return found ? found.time : `Slot ${slot}`;
};

export default function AdminEditTimetablePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Get URL params for pre-selection
  const urlSemester = searchParams.get('semester');
  const urlSection = searchParams.get('section');

  const [semester, setSemester] = useState(urlSemester || '1');
  const [section, setSection] = useState(urlSection || 'A');

  // Timetable data
  const [timetable, setTimetable] = useState(null);
  const [versions, setVersions] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [faculty, setFaculty] = useState([]);

  // UI state
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [creatingVersion, setCreatingVersion] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Editing state
  const [editingSlot, setEditingSlot] = useState(null); // { day, slot }
  const [slotForm, setSlotForm] = useState({
    subject_id: '',
    faculty_id: '',
    room: '',
  });
  const [showVersions, setShowVersions] = useState(true);

  // Conflict checking
  const [conflicts, setConflicts] = useState({});
  const [checkingConflicts, setCheckingConflicts] = useState({});

  // Fetch timetable
  const fetchTimetable = useCallback(async () => {
    if (!semester || !section) return;

    setLoading(true);
    setError(null);
    try {
      const data = await timetableService.view({
        semester: parseInt(semester),
        section,
      });
      setTimetable(data);
    } catch (err) {
      setError(err.message || 'Failed to load timetable');
      setTimeout(() => setError(null), 5000);
    } finally {
      setLoading(false);
    }
  }, [semester, section, ]);

  // Fetch versions
  const fetchVersions = useCallback(async () => {
    if (!semester || !section) return;

    try {
      const data = await api(`/timetable/versions/${semester}/${section}`);
      setVersions(data.versions || []);
    } catch (err) {
      console.error('Failed to fetch versions:', err);
    }
  }, [semester, section, ]);

  // Fetch subjects and faculty
  const fetchReferenceData = useCallback(async () => {
    try {
      // Fetch subjects
      const subjectsData = await adminService.getSubjects();
      setSubjects(subjectsData.subjects || []);

      // Fetch faculty
      const usersData = await adminService.getUsers({ role: 'faculty' });
      setFaculty(usersData.users || []);
    } catch (err) {
      console.error('Failed to load reference data:', err);
    }
  }, []);

  useEffect(() => {
    fetchTimetable();
    fetchVersions();
    fetchReferenceData();
  }, [fetchTimetable, fetchVersions, fetchReferenceData]);

  // Open edit modal for a slot
  const openEditSlot = (day, slot) => {
    // Find existing slot data
    let existingSlot = null;
    if (timetable?.schedule) {
      const daySchedule = timetable.schedule.find(s => s.day === day);
      if (daySchedule?.slots) {
        existingSlot = daySchedule.slots.find(s => s.slot === slot);
      }
    }

    setSlotForm({
      subject_id: existingSlot?.subject_id || '',
      faculty_id: existingSlot?.faculty_id || '',
      room: existingSlot?.room || '',
    });
    setEditingSlot({ day, slot });
  };

  // Close edit modal
  const closeEditSlot = () => {
    setEditingSlot(null);
    setSlotForm({ subject_id: '', faculty_id: '', room: '' });
    setConflicts({});
  };

  // Check for conflicts before saving
  const checkConflicts = async (facultyId, roomId, day, slot) => {
    const conflicts = {};

    // Check faculty conflicts
    if (facultyId && facultyId !== slotForm.faculty_id) {
      try {
        const data = await api(
          `/timetable/conflicts/faculty/${facultyId}?day=${day}&slot=${slot}&exclude_timetable_id=${timetable?.id || ''}`
        );
        if (data.conflicts?.length > 0) {
          conflicts.faculty = data.conflicts;
        }
      } catch (err) {
        console.error('Failed to check faculty conflicts:', err);
      }
    }

    // Check room conflicts
    if (roomId && roomId !== slotForm.room) {
      try {
        const data = await api(
          `/timetable/conflicts/room/${roomId}?day=${day}&slot=${slot}&exclude_timetable_id=${timetable?.id || ''}`
        );
        if (data.conflicts?.length > 0) {
          conflicts.room = data.conflicts;
        }
      } catch (err) {
        console.error('Failed to check room conflicts:', err);
      }
    }

    return conflicts;
  };

  // Save slot changes
  const saveSlot = async () => {
    if (!timetable?.id) return;

    setSaving(true);
    setError(null);
    setConflicts({});

    // Check conflicts
    const newConflicts = await checkConflicts(
      slotForm.faculty_id,
      slotForm.room,
      editingSlot.day,
      editingSlot.slot
    );

    if (Object.keys(newConflicts).length > 0) {
      setConflicts(newConflicts);
      setSaving(false);
      setError('Conflicts detected. Please review before saving.');
      setTimeout(() => setError(null), 5000);
      return;
    }

    try {
      await timetableService.updateSlot(timetable.id, {
        day: editingSlot.day,
        slot: editingSlot.slot,
        subject_id: slotForm.subject_id || null,
        faculty_id: slotForm.faculty_id || null,
        room: slotForm.room || null,
      });

      setSuccess('Slot updated successfully! New version created.');
      setTimeout(() => setSuccess(null), 3000);
      closeEditSlot();
      fetchTimetable();
      fetchVersions();
    } catch (err) {
      setError(err.message || 'Failed to update slot');
      setTimeout(() => setError(null), 5000);
    } finally {
      setSaving(false);
    }
  };

  // Create new version
  const createNewVersion = async () => {
    if (!semester || !section) return;

    setCreatingVersion(true);
    setError(null);

    try {
      const data = await api('/timetable/versions/create', {
        method: 'POST',
        body: JSON.stringify({
          semester: parseInt(semester),
          section,
        }),
      });
      setSuccess(`New version ${data.timetable.version} created!`);
      setTimeout(() => setSuccess(null), 3000);
      fetchTimetable();
      fetchVersions();
    } catch (err) {
      setError(err.message || 'Failed to create version');
      setTimeout(() => setError(null), 5000);
    } finally {
      setCreatingVersion(false);
    }
  };

  // Activate a version
  const activateVersion = async (timetableId) => {
    if (!semester || !section) return;

    try {
      await api(`/timetable/versions/activate/${timetableId}?semester=${semester}&section=${section}`, {
        method: 'POST',
      });
      setSuccess('Version activated successfully!');
      setTimeout(() => setSuccess(null), 3000);
      fetchTimetable();
      fetchVersions();
    } catch (err) {
      setError(err.message || 'Failed to activate version');
      setTimeout(() => setError(null), 5000);
    }
  };

  // Delete timetable
  const deleteTimetable = async () => {
    if (!confirm('Are you sure you want to delete ALL versions of this timetable? This cannot be undone.')) {
      return;
    }

    try {
      await timetableService.delete({
        semester: parseInt(semester),
        section,
      });

      setSuccess('Timetable deleted successfully!');
      setTimeout(() => setSuccess(null), 3000);
      setTimetable(null);
      setVersions([]);
    } catch (err) {
      setError(err.message || 'Failed to delete timetable');
      setTimeout(() => setError(null), 5000);
    }
  };

  // Get subject and faculty details
  const getSubject = (subjectId) => subjects.find(s => s.id === subjectId);
  const getFacultyMember = (facultyId) => faculty.find(f => f.id === facultyId);

  // Get slot data for display
  const getSlotData = (day, slot) => {
    if (!timetable?.schedule) return null;
    const daySchedule = timetable.schedule.find(s => s.day === day);
    return daySchedule?.slots?.find(s => s.slot === slot);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/admin/timetable')}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Edit Timetable
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Modify existing timetable with version history
          </p>
        </div>
      </div>

      {/* Success Message */}
      {success && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
          <p className="text-sm text-green-800 dark:text-green-300">{success}</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Configuration */}
      <Card className="border-gray-200 dark:border-gray-800">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Label>Semester:</Label>
              <select
                value={semester}
                onChange={(e) => setSemester(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={s.toString()}>Semester {s}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <Label>Section:</Label>
              <select
                value={section}
                onChange={(e) => setSection(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                {['A', 'B'].map((s) => (
                  <option key={s} value={s}>Section {s}</option>
                ))}
              </select>
            </div>

            <div className="flex-1" />

            <Button
              onClick={fetchTimetable}
              disabled={loading}
              variant="outline"
              className="gap-2"
            >
              <Loader2 className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Load
            </Button>

            {timetable && (
              <>
                <Button
                  onClick={createNewVersion}
                  disabled={creatingVersion}
                  variant="outline"
                  className="gap-2"
                >
                  <Copy className="h-4 w-4" />
                  {creatingVersion ? 'Creating...' : 'New Version'}
                </Button>

                <Button
                  onClick={deleteTimetable}
                  variant="outline"
                  className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete All
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      {timetable ? (
        <div className="grid gap-6 lg:grid-cols-4">
          {/* Timetable Grid */}
          <div className="lg:col-span-3">
            <Card className="border-gray-200 dark:border-gray-800">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>
                      Semester {semester} - Section {section}
                    </CardTitle>
                    <CardDescription>
                      Version {timetable.version || 'N/A'}
                      {timetable.is_active && (
                        <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
                          Active
                        </span>
                      )}
                    </CardDescription>
                  </div>
                  <Button
                    onClick={() => setShowVersions(!showVersions)}
                    variant="outline"
                    size="sm"
                    className="lg:hidden gap-1"
                  >
                    <History className="h-4 w-4" />
                    {showVersions ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="min-w-full border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                          Day / Time
                        </th>
                        {TIME_SLOTS.map((slot) => (
                          <th key={slot.slot} className="px-2 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400">
                            <div className="text-xs">{slot.slot}</div>
                            <div className="text-[10px] text-gray-400">{getSlotTime(slot).split(' - ')[0]}</div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-950 divide-y divide-gray-200 dark:divide-gray-800">
                      {DAYS.map((day) => (
                        <tr key={day}>
                          <td className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-white">
                            {day}
                          </td>
                          {TIME_SLOTS.map((slot) => {
                            const slotData = getSlotData(day, slot);
                            const subject = slotData?.subject_id ? getSubject(slotData.subject_id) : null;
                            const fac = slotData?.faculty_id ? getFacultyMember(slotData.faculty_id) : null;

                            return (
                              <td key={slot.slot} className="px-1 py-1">
                                <button
                                  onClick={() => openEditSlot(day, slot)}
                                  className={`w-full h-16 rounded-lg transition-all duration-200 text-left p-2 cursor-pointer hover:shadow-md hover:scale-105 ${
                                    subject
                                      ? 'bg-gradient-to-br from-violet-50 to-indigo-50 dark:from-violet-900/20 dark:to-indigo-900/20 border border-violet-200 dark:border-violet-800'
                                      : 'bg-gray-50 dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800'
                                  }`}
                                >
                                  {subject ? (
                                    <div className="space-y-0.5">
                                      <p className="text-xs font-medium text-violet-900 dark:text-violet-100 truncate" title={subject.name}>
                                        {subject.code}
                                      </p>
                                      <p className="text-[10px] text-gray-600 dark:text-gray-400 truncate" title={fac?.full_name}>
                                        {fac?.full_name?.split(' ')[0] || '?'}
                                      </p>
                                                                      </div>
                                                                  ) : (
                                                                    <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-600">
                                                                      <Plus className="h-4 w-4" />
                                                                    </div>
                                                                  )}
                                                                </button>
                                                              </td>
                                                            );
                                                          })}
                                                        </tr>
                                                      ))}
                                                    </tbody>
                                                  </table>
                                                </div>
                                              </CardContent>
                                            </Card>
                                          </div>

                          {/* Version History Sidebar */}
                          <div className={`lg:col-span-1 ${showVersions ? 'block' : 'hidden lg:block'}`}>
                            <Card className="border-gray-200 dark:border-gray-800 sticky top-20">
                              <CardHeader>
                                <div className="flex items-center justify-between">
                                  <CardTitle className="text-lg">Version History</CardTitle>
                                  <span className="text-xs text-gray-500">{versions.length} versions</span>
                                </div>
                              </CardHeader>
                              <CardContent>
                                <div className="space-y-2 max-h-96 overflow-y-auto">
                                                                  {versions.length === 0 ? (
                                                                    <p className="text-xs text-gray-500 text-center py-4">No versions</p>
                                                                  ) : (
                                                                    versions.map((version) => (
                                                                      <div
                                                                        key={version.id}
                                                                        className={`p-3 rounded-lg border transition-all cursor-pointer ${
                                                                          version.is_active
                                                                            ? 'border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/20'
                                                                            : 'border-gray-200 dark:border-gray-800 hover:border-violet-300 dark:hover:border-violet-700'
                                                                        }`}
                                                                      >
                                                                        <div className="flex items-center justify-between mb-1">
                                                                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                                                                            v{version.version}
                                                                          </span>
                                                                          {version.is_active ? (
                                                                            <Eye className="h-3 w-3 text-green-600 dark:text-green-400" />
                                                                          ) : (
                                                                            <EyeOff className="h-3 w-3 text-gray-400" />
                                                                          )}
                                                                        </div>
                                                                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                                                                          {new Date(version.created_at).toLocaleString()}
                                                                        </p>
                                                                        {!version.is_active && (
                                                                          <Button
                                                                            size="sm"
                                                                            variant="outline"
                                                                            onClick={(e) => {
                                                                              e.stopPropagation();
                                                                              activateVersion(version.id);
                                                                            }}
                                                                            className="w-full text-xs py-1 gap-1"
                                                                          >
                                                                            <Copy className="h-3 w-3" />
                                                                            Activate
                                                                          </Button>
                                                                        )}
                                                                      </div>
                                                                    ))
                                                                  )}
                                                                </div>
                                                              </CardContent>
                                                            </Card>
                                                          </div>
                                                        </div>
                                                      ) : (
                                                        <Card className="border-gray-200 dark:border-gray-800">
                                                          <CardContent className="p-12 text-center">
                                                            <Clock className="h-12 w-12 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
                                                            <p className="text-gray-500 dark:text-gray-400 mb-4">
                                                              No timetable found for Semester {semester}, Section {section}
                                                            </p>
                                                            <Button
                                                              onClick={() => navigate('/admin/timetable')}
                                                              className="gap-2"
                                                            >
                                                              <Plus className="h-4 w-4" />
                                                              Generate Timetable
                                                            </Button>
                                                          </CardContent>
                                                        </Card>
                                                      )}

                      {/* Edit Slot Modal */}
                      {editingSlot && (
                                                        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
                                                          <Card className="w-full max-w-md">
                                                            <CardHeader>
                                                              <CardTitle>Edit Slot</CardTitle>
                                                              <CardDescription>
                                                                {editingSlot.day} - Slot {editingSlot.slot} ({getSlotTime(editingSlot.slot)})
                                                              </CardDescription>
                                                            </CardHeader>
                                                            <CardContent className="space-y-4">
                                                              {/* Subject */}
                                                              <div className="space-y-2">
                                                                <Label>Subject</Label>
                                                                <select
                                                                  value={slotForm.subject_id}
                                                                  onChange={(e) => setSlotForm({ ...slotForm, subject_id: e.target.value })}
                                                                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
                                                                >
                                                                  <option value="">None (Free slot)</option>
                                                                  {subjects.map((s) => (
                                                                    <option key={s.id} value={s.id}>
                                                                      {s.code} - {s.name}
                                                                    </option>
                                                                  ))}
                                                                </select>
                                                              </div>

                                                              {/* Faculty */}
                                                              <div className="space-y-2">
                                                                <Label>Faculty</Label>
                                                                <select
                                                                  value={slotForm.faculty_id}
                                                                  onChange={(e) => setSlotForm({ ...slotForm, faculty_id: e.target.value })}
                                                                  disabled={!slotForm.subject_id}
                                                                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 disabled:opacity-50"
                                                                >
                                                                  <option value="">Select faculty...</option>
                                                                  {faculty.map((f) => (
                                                                    <option key={f.id} value={f.id}>
                                                                      {f.full_name}
                                                                    </option>
                                                                  ))}
                                                                </select>
                                                              </div>

                                                              {/* Room */}
                                                              <div className="space-y-2">
                                                                <Label>Room</Label>
                                                                <Input
                                                                  value={slotForm.room}
                                                                  onChange={(e) => setSlotForm({ ...slotForm, room: e.target.value })}
                                                                  placeholder="e.g., 101"
                                                                  disabled={!slotForm.subject_id}
                                                                />
                                                              </div>

                                                              {/* Conflicts Warning */}
                                                              {Object.keys(conflicts).length > 0 && (
                                                                <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
                                                                  <p className="text-sm font-medium text-orange-800 dark:text-orange-400 mb-2">
                                                                    ⚠️ Conflicts Detected:
                                                                  </p>
                                                                  {conflicts.faculty && (
                                                                    <p className="text-xs text-orange-700 dark:text-orange-300">
                                                                      • Faculty already booked at this time
                                                                    </p>
                                                                  )}
                                                                  {conflicts.room && (
                                                                    <p className="text-xs text-orange-700 dark:text-orange-300">
                                                                      • Room already booked at this time
                                                                    </p>
                                                                  )}
                                                                </div>
                                                              )}

                                                              {/* Actions */}
                                                              <div className="flex gap-2">
                                                                <Button
                                                                  onClick={saveSlot}
                                                                  disabled={saving || Object.keys(conflicts).length > 0}
                                                                  className="flex-1 gap-2"
                                                                >
                                                                  {saving ? (
                                                                    <>
                                                                      <Loader2 className="h-4 w-4 animate-spin" />
                                                                      Saving...
                                                                    </>
                                                                  ) : (
                                                                    <>
                                                                      <Save className="h-4 w-4" />
                                                                      Save
                                                                    </>
                                                                  )}
                                                                </Button>
                                                                <Button
                                                                  variant="outline"
                                                                  onClick={closeEditSlot}
                                                                  disabled={saving}
                                                                >
                                                                  Cancel
                                                                </Button>
                                                              </div>
                                                            </CardContent>
                                                          </Card>
                                                        </div>
                                                      )}
                                                    </div>
                                                  );
                                                }

// Add the updateSlot and delete methods to the timetable service
// These will need to be added to frontend/src/services/timetable.js
