import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input, Label } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { CheckCircle, XCircle, Calendar, UserCheck, AlertCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { attendanceService } from '../services/attendance';
import { adminService } from '../services/admin';
import { facultyAssignmentService } from '../services/facultyAssignment';
import { getUser } from '../lib/api';
import { cn } from '../lib/utils';
import { format } from 'date-fns';

const ACADEMIC_YEAR = '2024-2025';
const normalizeAttendanceStatus = (status) => (status === 'present' ? 'present' : 'absent');

export default function AttendancePage() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);

  // Role-based state
  const [view, setView] = useState('loading'); // 'loading', 'faculty', 'student'
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [selectedSection, setSelectedSection] = useState(null);

  // Faculty marking state
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [students, setStudents] = useState([]);
  const [attendance, setAttendance] = useState({});
  const [loading, setLoading] = useState(false);
  const [markingAttendance, setMarkingAttendance] = useState(false);
  const [existingAttendance, setExistingAttendance] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Student summary state
  const [attendanceSummary, setAttendanceSummary] = useState([]);
  const [selectedStudentSubject, setSelectedStudentSubject] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [expandedSubjects, setExpandedSubjects] = useState({});

  // Initialize user once on mount
  useEffect(() => {
    const user = getUser();
    setCurrentUser(user);

    if (!user) {
      navigate('/login');
      return;
    }

    if (user.role === 'admin') {
      // Admin should not access attendance
      navigate('/dashboard');
      return;
    }

    // Set initial section from user data
    setSelectedSection(user?.section || 'A');
  }, []); // Run only once on mount

  // Fetch data based on role (after user is set)
  useEffect(() => {
    if (!currentUser) return;

    if (currentUser.role === 'faculty') {
      setView('faculty');
      fetchFacultySubjects();
    } else if (currentUser.role === 'student') {
      setView('student');
      fetchMyAttendanceSummary();
    }
  }, [currentUser]); // Run when currentUser is set

  // Faculty: Fetch assigned subjects
  const fetchFacultySubjects = async () => {
    setLoading(true);
    try {
      const assignments = await facultyAssignmentService.getMySubjects();
      console.log('Fetched assignments:', assignments);

      // Group by subject.id to collect all sections for each subject
      const subjectMap = new Map();
      assignments.forEach(assignment => {
        const subjectId = assignment.subject?.id;
        if (!subjectId) return;

        if (!subjectMap.has(subjectId)) {
          subjectMap.set(subjectId, {
            id: subjectId,
            name: assignment.subject?.name || 'Unknown Subject',
            code: assignment.subject?.code || 'N/A',
            semester: assignment.semester,
            sections: new Set([assignment.section])
          });
        } else {
          subjectMap.get(subjectId).sections.add(assignment.section);
        }
      });

      const subjectsList = Array.from(subjectMap.values());
      console.log('Processed subjects:', subjectsList);
      setSubjects(subjectsList);

      // Auto-select first subject and its first section if available
      if (subjectsList.length > 0 && !selectedSubject) {
        const firstSubject = subjectsList[0];
        setSelectedSubject(firstSubject.id);
        const firstSection = Array.from(firstSubject.sections)[0];
        setSelectedSection(firstSection);
      }
    } catch (err) {
      console.error('Failed to fetch subjects:', err);
    } finally {
      setLoading(false);
    }
  };

  // Faculty: Fetch students for selected subject and section
  useEffect(() => {
    if (selectedSubject && selectedSection && view === 'faculty') {
      fetchStudents();
      // Check if attendance already exists for this date
      checkExistingAttendance();
    }
  }, [selectedSubject, selectedSection, date, view]);

  const fetchStudents = async () => {
    setLoading(true);
    try {
      // Get students by semester and section (faculty-accessible endpoint)
      const subject = subjects.find(s => s.id === selectedSubject);
      const data = await adminService.getStudentsByClass(
        subject?.semester || 1,
        selectedSection
      );

      setStudents(data.users || []);

      // Initialize attendance - default to present for all
      const initialAttendance = {};
      (data.users || []).forEach(s => {
        initialAttendance[s.id] = 'present';
      });
      setAttendance(initialAttendance);
    } catch (err) {
      console.error('Failed to fetch students:', err);
      setStudents([]);
    } finally {
      setLoading(false);
    }
  };

  const checkExistingAttendance = async () => {
    try {
      const data = await attendanceService.getDaily(selectedSubject, date);
      if (data.records && data.records.length > 0) {
        // Load existing attendance
        const existing = {};
        data.records.forEach(record => {
          existing[record.student_id] = normalizeAttendanceStatus(record.status);
        });
        setAttendance(existing);
        setExistingAttendance(data.records);
      } else {
        setExistingAttendance(null);
        // Reset to default present
        const defaultAttendance = {};
        students.forEach(s => {
          defaultAttendance[s.id] = 'present';
        });
        setAttendance(defaultAttendance);
      }
    } catch (err) {
      setExistingAttendance(null);
    }
  };

  // Student: Fetch attendance summary
  const fetchMyAttendanceSummary = async () => {
    setSummaryLoading(true);
    try {
      const data = await attendanceService.getMySummary();
      const summaries = data.summaries || [];
      setAttendanceSummary(summaries);
      setSelectedStudentSubject((currentSubjectId) => {
        const stillAvailable = summaries.some((summary) => summary.subject_id === currentSubjectId);
        return stillAvailable ? currentSubjectId : summaries[0]?.subject_id || '';
      });
    } catch (err) {
      console.error('Failed to fetch attendance summary:', err);
      setAttendanceSummary([]);
      setSelectedStudentSubject('');
    } finally {
      setSummaryLoading(false);
    }
  };

  // Faculty: Mark attendance
  const handleMarkAttendance = async () => {
    setMarkingAttendance(true);
    setSuccessMessage(null);
    try {
      const attendanceData = Object.entries(attendance).map(([studentId, status]) => ({
        student_id: studentId,
        status: normalizeAttendanceStatus(status),
        remarks: '',
      }));

      const subject = subjects.find(s => s.id === selectedSubject);

      await attendanceService.mark({
        subject_id: selectedSubject,
        semester: subject?.semester || 1,
        section: selectedSection,
        academic_year: ACADEMIC_YEAR,
        attendance_date: date,
        attendance: attendanceData,
      });

      setSuccessMessage(`Attendance marked for ${attendanceData.length} students`);
      // Refresh existing attendance
      checkExistingAttendance();

      // Clear message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Failed to mark attendance:', err);
      alert('Failed to mark attendance: ' + (err.message || 'Unknown error'));
    } finally {
      setMarkingAttendance(false);
    }
  };

  const setAttendanceStatus = (studentId, status) => {
    setAttendance(prev => ({
      ...prev,
      [studentId]: normalizeAttendanceStatus(status),
    }));
  };

  const toggleSubjectExpanded = (subjectId) => {
    setExpandedSubjects(prev => ({
      ...prev,
      [subjectId]: !(prev[subjectId] ?? true)
    }));
  };

  // Calculate stats for faculty view
  const presentCount = Object.values(attendance).filter(s => s === 'present').length;
  const absentCount = Object.values(attendance).filter(s => s === 'absent').length;

  // ==================== FACULTY VIEW ====================
  if (view === 'faculty') {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Mark Attendance</h1>
          <p className="text-muted-foreground">
            Record student attendance for your classes
          </p>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
            <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
            <p className="text-sm text-green-800 dark:text-green-300">{successMessage}</p>
          </div>
        )}

        {/* Subject and Date Selection */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">Select Class</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Subject</Label>
                {loading ? (
                  <div className="flex items-center justify-center h-10">
                    <Loader2 className="h-5 w-5 animate-spin text-violet-600" />
                  </div>
                ) : (
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={selectedSubject || ''}
                    onChange={(e) => {
                      const newSubjectId = e.target.value;
                      setSelectedSubject(newSubjectId);
                      setExistingAttendance(null);

                      // Auto-select first section of the chosen subject
                      const subject = subjects.find(s => s.id === newSubjectId);
                      if (subject && subject.sections) {
                        const sectionsArray = Array.from(subject.sections);
                        if (sectionsArray.length > 0) {
                          setSelectedSection(sectionsArray[0]);
                        }
                      }
                    }}
                  >
                    <option value="">Select a subject...</option>
                    {subjects.map((subject) => {
                      const sectionsArray = Array.from(subject.sections || []);
                      return (
                        <option key={subject.id} value={subject.id}>
                          {subject.code} - {subject.name} (Sem {subject.semester})
                          {sectionsArray.length > 1 ? ` - Sec: ${sectionsArray.join(', ')}` : ''}
                          </option>
                      );
                    })}
                  </select>
                )}
              </div>

              {selectedSubject && (
                <div className="space-y-2">
                  <Label>Section</Label>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={selectedSection}
                    onChange={(e) => {
                      setSelectedSection(e.target.value);
                      setExistingAttendance(null);
                    }}
                  >
                    {(() => {
                      const subject = subjects.find(s => s.id === selectedSubject);
                      const sectionsArray = subject ? Array.from(subject.sections || []) : [];
                      return sectionsArray.map((section) => (
                        <option key={section} value={section}>Section {section}</option>
                      ));
                    })()}
                  </select>
                </div>
              )}

              <div className="space-y-2">
                <Label>Date</Label>
                <Input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  max={format(new Date(), 'yyyy-MM-dd')}
                />
              </div>

              {existingAttendance && (
                <div className="flex items-center gap-2 p-2 rounded bg-blue-50 dark:bg-blue-900/20 text-sm text-blue-700 dark:text-blue-300">
                  <Calendar className="h-4 w-4" />
                  <span>Attendance already marked for this date</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Stats Card */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg">Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Present</span>
                <span className="text-lg font-bold text-green-600">{presentCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Absent</span>
                <span className="text-lg font-bold text-red-600">{absentCount}</span>
              </div>
              <div className="pt-2 border-t">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Total</span>
                  <span className="text-lg font-bold">{students.length}</span>
                </div>
              </div>
              <Button
                onClick={handleMarkAttendance}
                disabled={!selectedSubject || students.length === 0 || markingAttendance}
                className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700"
              >
                {markingAttendance ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Marking...
                  </>
                ) : (
                  <>
                    <UserCheck className="h-4 w-4 mr-2" />
                    {existingAttendance ? 'Update Attendance' : 'Mark Attendance'}
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => {
                  const allPresent = {};
                  students.forEach(s => allPresent[s.id] = 'present');
                  setAttendance(allPresent);
                }}
                disabled={students.length === 0}
              >
                <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                Mark All Present
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => {
                  const allAbsent = {};
                  students.forEach(s => allAbsent[s.id] = 'absent');
                  setAttendance(allAbsent);
                }}
                disabled={students.length === 0}
              >
                <XCircle className="h-4 w-4 mr-2 text-red-600" />
                Mark All Absent
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Student List */}
        {selectedSubject && !loading && students.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <span>
                  {students.length} Students - {subjects.find(s => s.id === selectedSubject)?.name}
                </span>
                <span className="text-sm font-normal text-muted-foreground">
                  Section {selectedSection}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {students.map((student) => {
                  const status = normalizeAttendanceStatus(attendance[student.id] || 'present');
                  return (
                    <div
                      key={student.id}
                      className={cn(
                        "flex items-center justify-between p-4 rounded-lg border transition-all",
                        status === 'present' && "bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800",
                        status === 'absent' && "bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800"
                      )}
                    >
                      <div className="flex items-center space-x-4">
                        <div className={cn(
                          status === 'present' && 'text-green-600',
                          status === 'absent' && 'text-red-600'
                        )}>
                          {status === 'present' && <CheckCircle className="h-5 w-5" />}
                          {status === 'absent' && <XCircle className="h-5 w-5" />}
                        </div>
                        <div>
                          <p className="font-medium">{student.full_name}</p>
                          <p className="text-sm text-muted-foreground">{student.roll_number}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        {['present', 'absent'].map((s) => (
                          <button
                            key={s}
                            onClick={() => setAttendanceStatus(student.id, s)}
                            className={cn(
                              "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                              status === s
                                ? s === 'present' ? "bg-green-600 text-white"
                                  : "bg-red-600 text-white"
                                : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400"
                            )}
                          >
                            {s.charAt(0).toUpperCase() + s.slice(1)}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {selectedSubject && !loading && students.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <UserCheck className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No students found for Section {selectedSection}</p>
            </CardContent>
          </Card>
        )}

        {!selectedSubject && !loading && subjects.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No subjects assigned to you yet.</p>
              <p className="text-sm text-muted-foreground mt-2">Contact admin to get subjects assigned.</p>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  // ==================== STUDENT VIEW ====================
  if (view === 'student') {
    const selectedSummary = attendanceSummary.find(
      (summary) => summary.subject_id === selectedStudentSubject
    ) || attendanceSummary[0] || null;
    const selectedSubjectName = selectedSummary?.subject?.name || selectedSummary?.subject_name || 'Unknown Subject';
    const selectedSubjectCode = selectedSummary?.subject?.code || selectedSummary?.subject_code || 'N/A';
    const selectedPercentage = selectedSummary?.percentage || 0;
    const selectedTotalClasses = selectedSummary?.total_classes || 0;
    const selectedPresent = selectedSummary?.present || 0;
    const selectedAbsent = selectedSummary?.absent || 0;
    const selectedBelowThreshold = Boolean(selectedSummary?.is_below_threshold);

    return (
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">My Attendance</h1>
          <p className="text-muted-foreground">
            Select a subject to view your attendance for Semester {currentUser?.semester || '-'}, Section {currentUser?.section || '-'}
          </p>
        </div>

        {summaryLoading ? (
          <Card>
            <CardContent className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
            </CardContent>
          </Card>
        ) : attendanceSummary.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Calendar className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No subjects found for your semester and section.</p>
              <p className="text-sm text-muted-foreground mt-2">Attendance will appear here once subjects are assigned and faculty starts marking.</p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Subject Selector */}
            <div className="grid gap-4 lg:grid-cols-[1fr_220px]">
              <Card>
                <CardHeader className="pb-4">
                  <CardTitle className="text-lg">Select Subject</CardTitle>
                </CardHeader>
                <CardContent>
                  <Select
                    value={selectedSummary?.subject_id || ''}
                    onChange={(event) => setSelectedStudentSubject(event.target.value)}
                  >
                    {attendanceSummary.map((summary) => {
                      const subjectName = summary.subject?.name || summary.subject_name || 'Unknown Subject';
                      const subjectCode = summary.subject?.code || summary.subject_code || 'N/A';
                      return (
                        <option key={summary.subject_id} value={summary.subject_id}>
                          {subjectCode} - {subjectName}
                        </option>
                      );
                    })}
                  </Select>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-4">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Subjects</CardTitle>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl font-bold">{attendanceSummary.length}</span>
                  <p className="text-xs text-muted-foreground mt-1">in your semester</p>
                </CardContent>
              </Card>
            </div>

            {/* Selected Subject Stats */}
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="pb-4">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Attendance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-end gap-2">
                    <span className={cn(
                      "text-3xl font-bold",
                      selectedTotalClasses === 0 ? "text-gray-600" :
                      selectedPercentage >= 75 ? "text-green-600" :
                      selectedPercentage >= 60 ? "text-yellow-600" : "text-red-600"
                    )}>
                      {selectedPercentage}%
                    </span>
                    <span className="text-sm text-muted-foreground mb-1">selected subject</span>
                  </div>
                  {selectedBelowThreshold && (
                    <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      Below 75%
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-4">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Present</CardTitle>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl font-bold text-green-600">{selectedPresent}</span>
                  <p className="text-xs text-muted-foreground mt-1">classes attended</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-4">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Absent</CardTitle>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl font-bold text-red-600">{selectedAbsent}</span>
                  <p className="text-xs text-muted-foreground mt-1">classes missed</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-4">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Total Classes</CardTitle>
                </CardHeader>
                <CardContent>
                  <span className="text-3xl font-bold">{selectedTotalClasses}</span>
                  <p className="text-xs text-muted-foreground mt-1">marked so far</p>
                </CardContent>
              </Card>
            </div>

            {/* Selected Subject Details */}
            <Card>
              <CardHeader>
                <CardTitle className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <span>Selected Subject Attendance</span>
                  <span className="text-sm font-normal text-muted-foreground">
                    {selectedSubjectCode} - {selectedSubjectName}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[selectedSummary].filter(Boolean).map((subject) => {
                    const isExpanded = expandedSubjects[subject.subject_id] ?? true;
                    const percentage = subject.percentage || 0;
                    const isBelowThreshold = subject.is_below_threshold;
                    const subjectName = subject.subject?.name || subject.subject_name || 'Unknown Subject';

                    return (
                      <div
                        key={subject.subject_id}
                        className="border rounded-lg overflow-hidden"
                      >
                        <button
                          onClick={() => toggleSubjectExpanded(subject.subject_id)}
                          className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                        >
                          <div className="flex items-center gap-4 flex-1">
                            <div className={cn(
                              "w-12 h-12 rounded-lg flex items-center justify-center font-bold",
                              percentage >= 75 ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
                              percentage >= 60 ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
                              "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                            )}>
                              {percentage}%
                            </div>
                            <div className="flex-1 text-left">
                              <p className="font-medium">{subjectName}</p>
                              <p className="text-sm text-muted-foreground">
                                {subject.total_classes} classes • {subject.present} present
                              </p>
                            </div>
                            {isBelowThreshold && (
                              <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded-md flex items-center gap-1">
                                <AlertCircle className="h-3 w-3" />
                                Low
                              </span>
                            )}
                          </div>
                          {isExpanded ? (
                            <ChevronUp className="h-5 w-5 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-5 w-5 text-muted-foreground" />
                          )}
                        </button>

                        {/* Progress Bar */}
                        <div className="h-2 bg-gray-100 dark:bg-gray-800">
                          <div
                            className={cn(
                              "h-full transition-all",
                              percentage >= 75 ? "bg-green-500" :
                              percentage >= 60 ? "bg-yellow-500" : "bg-red-500"
                            )}
                            style={{ width: `${Math.min(percentage, 100)}%` }}
                          />
                        </div>

                        {/* Expanded Details */}
                        {isExpanded && (
                          <div className="p-4 border-t bg-gray-50 dark:bg-gray-800/50 grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">Present</p>
                              <p className="text-lg font-bold text-green-600">{subject.present}</p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">Absent</p>
                              <p className="text-lg font-bold text-red-600">{subject.absent}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Warning if below threshold */}
            {selectedBelowThreshold && (
              <div className="flex items-start gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-800 dark:text-red-300">
                    Attendance Warning
                  </p>
                  <p className="text-xs text-red-700 dark:text-red-400 mt-1">
                    Your attendance is below 75% in {selectedSubjectName}. Please attend classes regularly to meet the attendance requirement.
                  </p>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  return null;
}
