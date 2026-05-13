import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Label } from '../../components/ui/input';
import {
  ArrowLeft,
  Clock,
  Shield,
  Trash2,
  Plus,
  Check,
  AlertCircle,
  Loader2,
  Info,
  History,
  X,
} from 'lucide-react';
import { adminAssignmentService } from '../../services/adminAssignment';
import { adminService } from '../../services/admin';

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

export default function AdminFacultyAvailabilityPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Get URL params for pre-selection
  const urlFacultyId = searchParams.get('faculty_id');
  const urlSubjectId = searchParams.get('subject_id');
  const urlSemester = searchParams.get('semester');
  const urlSection = searchParams.get('section');

  const [allFaculty, setAllFaculty] = useState([]);
  const [allSubjects, setAllSubjects] = useState([]);
  const [selectedFaculty, setSelectedFaculty] = useState(urlFacultyId || '');
  const [selectedSubject, setSelectedSubject] = useState(urlSubjectId || '');
  const [selectedSemester, setSelectedSemester] = useState(urlSemester || '1');
  const [selectedSection, setSelectedSection] = useState(urlSection || 'A');

  const [effectiveSlots, setEffectiveSlots] = useState([]);
  const [baseSlots, setBaseSlots] = useState([]);
  const [overrides, setOverrides] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Override form state
  const [showOverrideForm, setShowOverrideForm] = useState(false);
  const [overrideData, setOverrideData] = useState({
    override_type: 'persistent',
    slots: [],
  });
  const [submittingOverride, setSubmittingOverride] = useState(false);

  const [deleteConfirm, setDeleteConfirm] = useState(null);

  // Fetch faculty and subjects on mount
  useEffect(() => {
    const fetchReferenceData = async () => {
      try {
        const facultyData = await adminService.getUsers({ role: 'faculty' });
        setAllFaculty(facultyData.users || []);

        const subjectsData = await adminService.getSubjects();
        setAllSubjects(subjectsData.subjects || []);
      } catch (err) {
        console.error('Failed to load reference data:', err);
      }
    };
    fetchReferenceData();
  }, []);

  // Fetch availability data when selection changes
  const fetchAvailabilityData = useCallback(async () => {
    if (!selectedFaculty || !selectedSubject || !selectedSemester || !selectedSection) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      // Fetch effective availability
      const effectiveData = await adminAssignmentService.getEffectiveAvailability({
        facultyId: selectedFaculty,
        subjectId: selectedSubject,
        semester: selectedSemester,
        section: selectedSection,
      });

      setBaseSlots(effectiveData.base_slots || []);
      setEffectiveSlots(effectiveData.effective_slots || []);

      // Fetch overrides
      const overridesData = await adminAssignmentService.getOverrides({
        facultyId: selectedFaculty,
        subjectId: selectedSubject,
      });
      setOverrides(overridesData.overrides || []);
    } catch (err) {
      setError(err.message || 'Failed to load availability data');
      setTimeout(() => setError(null), 5000);
    } finally {
      setLoading(false);
    }
  }, [selectedFaculty, selectedSubject, selectedSemester, selectedSection, ]);

  useEffect(() => {
    if (urlFacultyId && urlSubjectId) {
      fetchAvailabilityData();
    }
  }, [fetchAvailabilityData, urlFacultyId, urlSubjectId]);

  const handleRefresh = () => {
    fetchAvailabilityData();
  };

  const handleSlotAction = (day, slot, action) => {
    setOverrideData((prev) => {
      const existingIndex = prev.slots.findIndex((s) => s.day === day && s.slot === slot);
      if (existingIndex >= 0) {
        const existing = prev.slots[existingIndex];
        const updated = [...prev.slots];
        if (existing.action === action) {
          updated.splice(existingIndex, 1);
        } else {
          updated[existingIndex] = { day, slot, action };
        }
        return { ...prev, slots: updated };
      }
      return {
        ...prev,
        slots: [...prev.slots, { day, slot, action }],
      };
    });
  };

  const handleSubmitOverride = async (e) => {
    e.preventDefault();
    if (overrideData.slots.length === 0) {
      setError('Please select at least one slot for the override');
      setTimeout(() => setError(null), 3000);
      return;
    }

    setSubmittingOverride(true);
    setError(null);

    try {
      await adminAssignmentService.createOverride({
        faculty_id: selectedFaculty,
        subject_id: selectedSubject,
        semester: parseInt(selectedSemester),
        section: selectedSection,
        override_type: overrideData.override_type,
        slots: overrideData.slots,
      });

      setSuccess(`Override created successfully! (${overrideData.override_type})`);
      setTimeout(() => setSuccess(null), 3000);

      // Reset form and refresh data
      setOverrideData({ override_type: 'persistent', slots: [] });
      setShowOverrideForm(false);
      fetchAvailabilityData();
    } catch (err) {
      setError(err.message || 'Failed to create override');
      setTimeout(() => setError(null), 5000);
    } finally {
      setSubmittingOverride(false);
    }
  };

  const handleDeleteOverride = async (overrideId) => {
    try {
      await adminAssignmentService.deleteOverride(overrideId);
      setSuccess('Override deleted successfully');
      setTimeout(() => setSuccess(null), 3000);
      setDeleteConfirm(null);
      fetchAvailabilityData();
    } catch (err) {
      setError(err.message || 'Failed to delete override');
      setTimeout(() => setError(null), 5000);
    }
  };

  // Get selected faculty and subject details
  const selectedFacultyDetails = allFaculty.find((f) => f.id === selectedFaculty);
  const selectedSubjectDetails = allSubjects.find((s) => s.id === selectedSubject);

  // Check if a slot is available in effective availability
  const isSlotAvailable = (day, slot) => {
    return effectiveSlots.some((s) => s.day === day && s.slot === slot);
  };

  // Check if a slot is in base availability
  const isInBase = (day, slot) => {
    return baseSlots.some((s) => s.day === day && s.slot === slot);
  };

  // Check if a slot is affected by an override
  const getSlotOverrideStatus = (day, slot) => {
    for (const override of overrides) {
      const slotOverride = override.slots.find((s) => s.day === day && s.slot === slot);
      if (slotOverride) {
        return {
          action: slotOverride.action,
          type: override.override_type,
        };
      }
    }
    return null;
  };

  const getPendingSlotAction = (day, slot) => {
    return overrideData.slots.find((s) => s.day === day && s.slot === slot)?.action || null;
  };

  const selectedAddCount = overrideData.slots.filter((slot) => slot.action === 'add').length;
  const selectedRemoveCount = overrideData.slots.filter((slot) => slot.action === 'remove').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/admin/assignments')}
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Assignments
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Faculty Availability
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            View and manage faculty availability with admin overrides
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

      {/* Selection Card */}
      <Card className="border-gray-200 dark:border-gray-800">
        <CardHeader>
          <CardTitle>Select Assignment</CardTitle>
          <CardDescription>Choose faculty and subject to view availability</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-2">
              <Label>Faculty Member</Label>
              <select
                value={selectedFaculty}
                onChange={(e) => setSelectedFaculty(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                <option value="">Select faculty...</option>
                {allFaculty.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.full_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Subject</Label>
              <select
                value={selectedSubject}
                onChange={(e) => setSelectedSubject(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                <option value="">Select subject...</option>
                {allSubjects.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.code} - {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Semester</Label>
              <select
                value={selectedSemester}
                onChange={(e) => setSelectedSemester(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={s.toString()}>
                    Semester {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Section</Label>
              <select
                value={selectedSection}
                onChange={(e) => setSelectedSection(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                {['A', 'B'].map((s) => (
                  <option key={s} value={s}>
                    Section {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <Button
                onClick={handleRefresh}
                disabled={!selectedFaculty || !selectedSubject || loading}
                className="w-full gap-2"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Clock className="h-4 w-4" />
                )}
                View Availability
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Availability Display */}
      {selectedFacultyDetails && selectedSubjectDetails && (
        <>
          {/* Summary Cards */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold">
                    {selectedFacultyDetails.full_name?.charAt(0) || 'U'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {selectedFacultyDetails.full_name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                      {selectedFacultyDetails.email}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-sm">
                    {selectedSubjectDetails.code?.substring(0, 3) || 'SUB'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {selectedSubjectDetails.name}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {selectedSubjectDetails.code} - {selectedSubjectDetails.credits} credits
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-gray-200 dark:border-gray-800">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-green-50 dark:bg-green-900/20">
                      <Clock className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <p className="text-lg font-bold text-gray-900 dark:text-white">
                        {effectiveSlots.length}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Available Slots</p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowOverrideForm(!showOverrideForm)}
                    className="gap-1 cursor-pointer"
                  >
                    <Plus className="h-4 w-4" />
                    Override
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Legend */}
          <Card className="border-gray-200 dark:border-gray-800">
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700"></div>
                  <span className="text-gray-600 dark:text-gray-400">Faculty Preference</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-blue-100 dark:bg-blue-900/30 border border-blue-300 dark:border-blue-700"></div>
                  <span className="text-gray-600 dark:text-gray-400">Added by Override</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700"></div>
                  <span className="text-gray-600 dark:text-gray-400">Removed by Override</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700"></div>
                  <span className="text-gray-600 dark:text-gray-400">Unavailable</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Override Form */}
          {showOverrideForm && (
            <Card className="border-violet-200 dark:border-violet-800">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Create Availability Override</CardTitle>
                    <CardDescription>
                      Add or remove specific slots from faculty availability
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowOverrideForm(false)}
                    className="cursor-pointer"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmitOverride} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Override Type</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setOverrideData({ ...overrideData, override_type: 'persistent' })}
                        className={`p-3 rounded-lg border-2 transition-all text-left ${
                          overrideData.override_type === 'persistent'
                            ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                          <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-white">Persistent</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">Stays until deleted</p>
                          </div>
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => setOverrideData({ ...overrideData, override_type: 'one_time' })}
                        className={`p-3 rounded-lg border-2 transition-all text-left ${
                          overrideData.override_type === 'one_time'
                            ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20'
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                          <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-white">One-Time</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">Used once, then marked applied</p>
                          </div>
                        </div>
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <Label>Select Slots to Override</Label>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        Click an available slot to make it unavailable. Click an unavailable slot to make it available. Click a selected slot again to undo.
                      </p>
                    </div>
                    <div className="border border-gray-200 dark:border-gray-800 rounded-lg p-4">
                      <div className="overflow-x-auto">
                        <table className="min-w-full">
                          <thead>
                            <tr className="border-b border-gray-200 dark:border-gray-800">
                              <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Day</th>
                              {TIME_SLOTS.map((slot) => (
                                <th key={slot.slot} className="min-w-[105px] px-1 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400">
                                  <span className="block">Slot {slot.slot}</span>
                                  <span className="block font-normal">{slot.time}</span>
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {DAYS.map((day) => (
                              <tr key={day} className="border-b border-gray-100 dark:border-gray-900">
                                <td className="px-2 py-1 text-sm font-medium text-gray-700 dark:text-gray-300">
                                  {day}
                                </td>
                                {TIME_SLOTS.map((slot) => {
                                  const pendingAction = getPendingSlotAction(day, slot.slot);
                                  const available = isSlotAvailable(day, slot.slot);
                                  const inBase = isInBase(day, slot.slot);
                                  const overrideStatus = getSlotOverrideStatus(day, slot.slot);
                                  const nextAction = available ? 'remove' : 'add';

                                  let label = available ? 'Available' : 'Unavailable';
                                  let detail = inBase ? 'Faculty choice' : 'No slot';
                                  let cellClass = available
                                    ? 'border-green-300 bg-green-100 text-green-800 hover:border-green-400 dark:border-green-800 dark:bg-green-900/30 dark:text-green-200'
                                    : 'border-gray-200 bg-gray-100 text-gray-500 hover:border-gray-300 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-500';

                                  if (overrideStatus?.action === 'add') {
                                    detail = 'Existing override';
                                    cellClass = 'border-blue-300 bg-blue-100 text-blue-800 hover:border-blue-400 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-200';
                                  } else if (overrideStatus?.action === 'remove') {
                                    label = 'Unavailable';
                                    detail = 'Existing override';
                                    cellClass = 'border-red-300 bg-red-100 text-red-800 hover:border-red-400 dark:border-red-800 dark:bg-red-900/30 dark:text-red-200';
                                  }

                                  if (pendingAction === 'add') {
                                    label = 'Make available';
                                    detail = 'Selected';
                                    cellClass = 'border-blue-600 bg-blue-600 text-white shadow-sm ring-2 ring-blue-200 dark:ring-blue-900';
                                  } else if (pendingAction === 'remove') {
                                    label = 'Make unavailable';
                                    detail = 'Selected';
                                    cellClass = 'border-red-600 bg-red-600 text-white shadow-sm ring-2 ring-red-200 dark:ring-red-900';
                                  }
                                  return (
                                    <td key={slot.slot} className="px-1 py-1 text-center">
                                      <button
                                        type="button"
                                        onClick={() => handleSlotAction(day, slot.slot, nextAction)}
                                        className={`h-14 w-full rounded-lg border px-2 text-xs transition-all hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-violet-500 ${cellClass}`}
                                        title={pendingAction ? `Undo change: ${day} slot ${slot.slot}` : `${available ? 'Make unavailable' : 'Make available'}: ${day} slot ${slot.slot}`}
                                      >
                                        <span className="flex items-center justify-center gap-1 font-semibold">
                                          {pendingAction === 'remove' || overrideStatus?.action === 'remove' ? (
                                            <X className="h-3.5 w-3.5" />
                                          ) : available || pendingAction === 'add' || overrideStatus?.action === 'add' ? (
                                            <Check className="h-3.5 w-3.5" />
                                          ) : null}
                                          {label}
                                        </span>
                                        <span className="mt-0.5 block text-[10px] opacity-80">{detail}</span>
                                      </button>
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {overrideData.slots.length} slot(s) selected - {selectedAddCount} make available, {selectedRemoveCount} make unavailable
                    </p>
                  </div>

                  <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-blue-700 dark:text-blue-300">
                      Available slots will be saved as unavailable overrides. Unavailable slots will be saved as available overrides.
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      type="submit"
                      disabled={submittingOverride || overrideData.slots.length === 0}
                      className="flex-1 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
                    >
                      {submittingOverride ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        'Create Override'
                      )}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setShowOverrideForm(false);
                        setOverrideData({ override_type: 'persistent', slots: [] });
                      }}
                      disabled={submittingOverride}
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {/* Effective Availability Grid */}
          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <CardTitle>Effective Availability</CardTitle>
              <CardDescription>
                Faculty preferences combined with admin overrides - {effectiveSlots.length} slots available
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
                    <thead className="bg-gray-50 dark:bg-gray-800">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                          Day / Slot
                        </th>
                        {TIME_SLOTS.map((slot) => (
                          <th key={slot.slot} className="px-2 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400">
                            {slot.time}
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
                            const available = isSlotAvailable(day, slot.slot);
                            const inBase = isInBase(day, slot.slot);
                            const overrideStatus = getSlotOverrideStatus(day, slot.slot);

                            let bgClass = 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600';

                            if (available) {
                              if (overrideStatus?.action === 'add') {
                                bgClass = 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400';
                              } else if (overrideStatus?.action === 'remove') {
                                bgClass = 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400';
                              } else if (inBase) {
                                bgClass = 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
                              }
                            } else if (overrideStatus?.action === 'remove' && inBase) {
                              bgClass = 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400';
                            }

                            return (
                              <td key={slot.slot} className="px-1 py-1 text-center">
                                <div className={`w-full h-10 rounded-md flex items-center justify-center text-xs font-medium transition-all duration-150 ${bgClass}`}>
                                  {available ? 'Available' : ''}
                                </div>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Override Audit Log */}
          <Card className="border-gray-200 dark:border-gray-800">
            <CardHeader>
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-gray-500" />
                <CardTitle>Override History</CardTitle>
              </div>
              <CardDescription>Audit log of all admin overrides for this assignment</CardDescription>
            </CardHeader>
            <CardContent>
              {overrides.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Shield className="h-10 w-10 mx-auto mb-2 text-gray-300 dark:text-gray-700" />
                  <p>No overrides created yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {overrides.map((override) => (
                    <div
                      key={override.id}
                      className="p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:border-violet-300 dark:hover:border-violet-700 transition-all"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              override.override_type === 'persistent'
                                ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400'
                                : 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400'
                            }`}>
                              {override.override_type === 'persistent' ? 'Persistent' : 'One-Time'}
                            </span>
                            {override.applied && (
                              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                                Applied
                              </span>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-1 mb-2">
                            {override.slots.map((slot, idx) => (
                              <span
                                key={idx}
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                                  slot.action === 'add'
                                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                                    : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
                                }`}
                              >
                                {slot.action === 'add' ? 'Available' : 'Unavailable'} - {slot.day}({slot.slot})
                              </span>
                            ))}
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            By {override.admin_name || 'Admin'} - {new Date(override.timestamp).toLocaleString()}
                          </p>
                        </div>
                        {!override.applied && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setDeleteConfirm(override)}
                            className="cursor-pointer text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <Card className="w-full max-w-sm">
            <CardHeader>
              <CardTitle>Confirm Delete</CardTitle>
              <CardDescription>
                Are you sure you want to delete this override?
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  onClick={() => handleDeleteOverride(deleteConfirm.id)}
                  className="flex-1"
                >
                  Delete
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setDeleteConfirm(null)}
                  className="flex-1"
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
