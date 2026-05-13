import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input, Label } from '../../components/ui/input';
import {
  UserPlus,
  Trash2,
  Search,
  BookOpen,
  Users,
  Check,
  X,
  Loader2,
  AlertCircle,
  ChevronDown,
  Info,
  Calendar,
  Plus,
} from 'lucide-react';
import { adminAssignmentService } from '../../services/adminAssignment';
import { adminService } from '../../services/admin';

const SEMESTERS = [1, 2, 3, 4, 5, 6, 7, 8];
const SECTIONS = ['A', 'B'];
const BOTH_SECTIONS = 'BOTH';
const ASSIGNMENT_SECTION_OPTIONS = [
  ...SECTIONS.map((section) => ({ value: section, label: section })),
  { value: BOTH_SECTIONS, label: 'Both A & B' },
];

export default function AdminAssignmentsPage() {
  const [assignments, setAssignments] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [showSubjectForm, setShowSubjectForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [subjectSubmitting, setSubjectSubmitting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [filters, setFilters] = useState({ semester: '', section: '' });

  const [formData, setFormData] = useState({
    faculty_id: '',
    subject_id: '',
    semester: '1',
    section: 'A',
  });
  const [subjectFormData, setSubjectFormData] = useState({
    code: '',
    name: '',
    semester: '1',
    subject_type: 'theory',
    credits: '3',
    classes_per_week: '3',
  });

  const fetchAssignments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (filters.semester) params.semester = filters.semester;
      if (filters.section) params.section = filters.section;
      const data = await adminAssignmentService.getAll(params);
      setAssignments(data.assignments || []);
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 5000);
    } finally {
      setLoading(false);
    }
  }, [filters.semester, filters.section]);

  const fetchSubjectsAndFaculty = useCallback(async () => {
    try {
      const subjectsData = await adminService.getSubjects();
      setSubjects(subjectsData.subjects || []);

      const usersData = await adminService.getUsers({ role: 'faculty' });
      setFaculty(usersData.users || []);
    } catch (err) {
      console.error('Failed to load reference data:', err);
    }
  }, []);

  useEffect(() => {
    fetchAssignments();
    fetchSubjectsAndFaculty();
  }, [fetchAssignments, fetchSubjectsAndFaculty]);

  const resetForm = () => {
    setFormData({
      faculty_id: '',
      subject_id: '',
      semester: '1',
      section: 'A',
    });
  };

  const resetSubjectForm = () => {
    setSubjectFormData({
      code: '',
      name: '',
      semester: '1',
      subject_type: 'theory',
      credits: '3',
      classes_per_week: '3',
    });
  };

  const openAddForm = () => {
    resetForm();
    setShowAddForm(true);
  };

  const closeForm = () => {
    setShowAddForm(false);
    resetForm();
    setError(null);
  };

  const closeSubjectForm = () => {
    setShowSubjectForm(false);
    resetSubjectForm();
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const targetSections = formData.section === BOTH_SECTIONS ? SECTIONS : [formData.section];
      const results = [];

      for (const section of targetSections) {
        try {
          await adminAssignmentService.create({
            ...formData,
            section,
          });
          results.push({ section, success: true });
        } catch (err) {
          results.push({
            section,
            success: false,
            message: err.message || 'Failed to create assignment',
          });
        }
      }

      const failed = results.filter((result) => !result.success);
      const createdSections = results
        .filter((result) => result.success)
        .map((result) => result.section);

      if (failed.length > 0) {
        const failedText = failed
          .map((result) => `Section ${result.section}: ${result.message}`)
          .join(' ');

        if (createdSections.length > 0) {
          setSuccess(`Created assignment for section ${createdSections.join(', ')}.`);
          setTimeout(() => setSuccess(null), 3000);
          await fetchAssignments();
        }

        throw new Error(failedText);
      }

      setSuccess(
        targetSections.length > 1
          ? `Assignments created for sections ${targetSections.join(' and ')}!`
          : 'Assignment created successfully!'
      );
      setTimeout(() => setSuccess(null), 3000);
      closeForm();
      await fetchAssignments();
    } catch (err) {
      setError(err.message || 'Failed to create assignment');
      setTimeout(() => setError(null), 5000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubjectTypeChange = (subjectType) => {
    setSubjectFormData((prev) => ({
      ...prev,
      subject_type: subjectType,
      credits: subjectType === 'lab' ? '2' : prev.credits || '3',
      classes_per_week: subjectType === 'lab' ? '2' : prev.classes_per_week || prev.credits || '3',
    }));
  };

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    setSubjectSubmitting(true);
    setError(null);

    const isLab = subjectFormData.subject_type === 'lab';
    const payload = {
      code: subjectFormData.code.trim(),
      name: subjectFormData.name.trim(),
      semester: parseInt(subjectFormData.semester, 10),
      subject_type: subjectFormData.subject_type,
      credits: isLab ? 2 : parseInt(subjectFormData.credits, 10),
      classes_per_week: isLab ? 2 : parseInt(subjectFormData.classes_per_week, 10),
    };

    try {
      const created = await adminService.createSubject(payload);
      setSuccess(`${created.code} created successfully!`);
      setTimeout(() => setSuccess(null), 3000);
      closeSubjectForm();
      await fetchSubjectsAndFaculty();
      if (created.id) {
        setFormData((prev) => ({ ...prev, subject_id: created.id }));
      }
    } catch (err) {
      setError(err.message || 'Failed to create subject');
      setTimeout(() => setError(null), 5000);
    } finally {
      setSubjectSubmitting(false);
    }
  };

  const confirmDelete = (assignment) => {
    setDeleteConfirm(assignment);
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;

    try {
      await adminAssignmentService.delete(deleteConfirm.id);
      setSuccess('Assignment deleted successfully!');
      setTimeout(() => setSuccess(null), 3000);
      setDeleteConfirm(null);
      fetchAssignments();
    } catch (err) {
      setError(err.message || 'Failed to delete assignment');
      setTimeout(() => setError(null), 5000);
    }
  };

  const getSubject = (subjectId) => subjects.find(s => s.id === subjectId);
  const getFacultyMember = (facultyId) => faculty.find(f => f.id === facultyId);

  const filteredAssignments = assignments.filter((assignment) => {
    if (!searchQuery) return true;
    const subj = getSubject(assignment.subject_id);
    const fac = getFacultyMember(assignment.faculty_id);
    const searchLower = searchQuery.toLowerCase();

    return (
      subj?.name?.toLowerCase().includes(searchLower) ||
      subj?.code?.toLowerCase().includes(searchLower) ||
      fac?.full_name?.toLowerCase().includes(searchLower) ||
      fac?.email?.toLowerCase().includes(searchLower)
    );
  });

  const stats = {
    total: assignments.length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Faculty Assignments
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage subject assignments to faculty members
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => {
              resetSubjectForm();
              setShowSubjectForm(true);
            }}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            New Subject
          </Button>
          <Button
            onClick={openAddForm}
            className="gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
          >
            <UserPlus className="h-4 w-4" />
            New Assignment
          </Button>
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

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-violet-50 dark:bg-violet-900/20">
                <BookOpen className="h-5 w-5 text-violet-600 dark:text-violet-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Assignments</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
                <Users className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{faculty.length}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Total Faculty</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="border-gray-200 dark:border-gray-800">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex items-center gap-2">
              <Label>Semester:</Label>
              <select
                value={filters.semester}
                onChange={(e) => setFilters({ ...filters, semester: e.target.value })}
                className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                <option value="">All</option>
                {SEMESTERS.map((s) => (
                  <option key={s} value={s.toString()}>Sem {s}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <Label>Section:</Label>
              <select
                value={filters.section}
                onChange={(e) => setFilters({ ...filters, section: e.target.value })}
                className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-950 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                <option value="">All</option>
                {SECTIONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
              <Input
                placeholder="Search by subject, faculty name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 h-10"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Add Subject Modal */}
      {showSubjectForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle>Create New Subject</CardTitle>
                  <CardDescription>
                    Add a subject to the catalog.
                  </CardDescription>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={closeSubjectForm}
                  disabled={subjectSubmitting}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreateSubject} className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Subject Code</Label>
                    <Input
                      value={subjectFormData.code}
                      onChange={(e) => setSubjectFormData({ ...subjectFormData, code: e.target.value.toUpperCase() })}
                      placeholder="CS101"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Subject Name</Label>
                    <Input
                      value={subjectFormData.name}
                      onChange={(e) => setSubjectFormData({ ...subjectFormData, name: e.target.value })}
                      placeholder="Data Structures"
                      required
                    />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-2">
                    <Label>Semester</Label>
                    <select
                      value={subjectFormData.semester}
                      onChange={(e) => setSubjectFormData({ ...subjectFormData, semester: e.target.value })}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
                      required
                    >
                      {SEMESTERS.map((s) => (
                        <option key={s} value={s.toString()}>Sem {s}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2 sm:col-span-2">
                    <Label>Subject Type</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => handleSubjectTypeChange('theory')}
                        className={`rounded-lg border-2 p-3 text-left transition-all ${
                          subjectFormData.subject_type === 'theory'
                            ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20'
                            : 'border-gray-200 hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600'
                        }`}
                      >
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">Theory</p>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSubjectTypeChange('lab')}
                        className={`rounded-lg border-2 p-3 text-left transition-all ${
                          subjectFormData.subject_type === 'lab'
                            ? 'border-violet-500 bg-violet-50 dark:bg-violet-900/20'
                            : 'border-gray-200 hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600'
                        }`}
                      >
                        <p className="text-sm font-semibold text-gray-900 dark:text-white">Lab</p>
                      </button>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Credits</Label>
                    <Input
                      type="number"
                      min="1"
                      max="6"
                      value={subjectFormData.subject_type === 'lab' ? '2' : subjectFormData.credits}
                      onChange={(e) => setSubjectFormData({ ...subjectFormData, credits: e.target.value })}
                      disabled={subjectFormData.subject_type === 'lab'}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Classes Per Week</Label>
                    <Input
                      type="number"
                      min="1"
                      max="10"
                      value={subjectFormData.subject_type === 'lab' ? '2' : subjectFormData.classes_per_week}
                      onChange={(e) => setSubjectFormData({ ...subjectFormData, classes_per_week: e.target.value })}
                      disabled={subjectFormData.subject_type === 'lab'}
                      required
                    />
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button
                    type="submit"
                    disabled={subjectSubmitting}
                    className="flex-1 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
                  >
                    {subjectSubmitting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      'Create Subject'
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={closeSubjectForm}
                    disabled={subjectSubmitting}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Add Assignment Modal */}
      {showAddForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <Card className="w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>Create New Assignment</CardTitle>
              <CardDescription>
                Assign a subject to a faculty member for a specific semester and section
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label>Faculty Member</Label>
                  <select
                    value={formData.faculty_id}
                    onChange={(e) => setFormData({ ...formData, faculty_id: e.target.value })}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
                    required
                  >
                    <option value="">Select faculty...</option>
                    {faculty.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.full_name} ({f.email})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label>Subject</Label>
                  <select
                    value={formData.subject_id}
                    onChange={(e) => setFormData({ ...formData, subject_id: e.target.value })}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
                    required
                  >
                    <option value="">Select subject...</option>
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.code} - {s.name} ({s.subject_type === 'lab' ? 'Lab, 2 consecutive slots' : `${s.credits} credits`})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Semester</Label>
                    <select
                      value={formData.semester}
                      onChange={(e) => setFormData({ ...formData, semester: e.target.value })}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
                      required
                    >
                      {SEMESTERS.map((s) => (
                        <option key={s} value={s.toString()}>Sem {s}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label>Section</Label>
                    <select
                      value={formData.section}
                      onChange={(e) => setFormData({ ...formData, section: e.target.value })}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
                      required
                    >
                      {ASSIGNMENT_SECTION_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-blue-700 dark:text-blue-300">
                    <strong>Note:</strong> One faculty can be assigned to one theory subject and one lab subject per semester.
                    Choose Both A & B to create separate assignments for both sections. A blank availability record will be created automatically.
                  </p>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      formData.section === BOTH_SECTIONS ? 'Create Assignments' : 'Create Assignment'
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={closeForm}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <Card className="w-full max-w-sm">
            <CardHeader>
              <CardTitle>Confirm Delete</CardTitle>
              <CardDescription>
                Are you sure you want to delete this assignment?
                This will also remove the associated availability record.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  onClick={handleDelete}
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

      {/* Assignments List */}
      <Card className="border-gray-200 dark:border-gray-800">
        <CardHeader>
          <CardTitle>All Assignments</CardTitle>
          <CardDescription>
            {filteredAssignments.length} assignment{filteredAssignments.length !== 1 ? 's' : ''} found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
            </div>
          ) : (
            <div className="space-y-2">
              {filteredAssignments.map((assignment) => {
                const subj = getSubject(assignment.subject_id);
                const fac = getFacultyMember(assignment.faculty_id);
                const subjectName = subj?.name || assignment.subject_name || 'Unknown Subject';
                const subjectCode = subj?.code || assignment.subject_code || 'N/A';
                const facultyName = fac?.full_name || assignment.faculty_name || 'Unknown Faculty';

                return (
                  <div
                    key={assignment.id}
                    className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:border-violet-300 dark:hover:border-violet-700 hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-all cursor-pointer"
                    onClick={() => window.location.href = `/admin/faculty-availability?faculty_id=${assignment.faculty_id}&subject_id=${assignment.subject_id}&semester=${assignment.semester}&section=${assignment.section}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-semibold">
                        {subjectCode.substring(0, 3)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-gray-900 dark:text-white">
                            {subjectName}
                          </p>
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                            {subjectCode}
                          </span>
                          {subj?.subject_type === 'lab' && (
                            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                              Lab - 2 consecutive slots
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {facultyName}
                          </span>
                          <span>-</span>
                          <span>Sem {assignment.semester} - Sec {assignment.section}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          window.location.href = `/admin/faculty-availability?faculty_id=${assignment.faculty_id}&subject_id=${assignment.subject_id}&semester=${assignment.semester}&section=${assignment.section}`;
                        }}
                        className="cursor-pointer"
                      >
                        <Calendar className="h-4 w-4 mr-1" />
                        Availability
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          confirmDelete(assignment);
                        }}
                        className="cursor-pointer text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {!loading && filteredAssignments.length === 0 && (
            <div className="text-center py-12">
              <BookOpen className="h-12 w-12 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400">
                {searchQuery || filters.semester || filters.section
                  ? 'No assignments found matching your filters.'
                  : 'No assignments yet. Create one to get started.'}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
