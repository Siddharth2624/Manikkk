import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { FileText, Loader2, Users, UserCheck, UserX, AlertCircle, Search, ChevronDown } from 'lucide-react';
import { facultyAssignmentService } from '../../services/facultyAssignment';
import { attendanceService } from '../../services/attendance';
import { getUser } from '../../lib/api';
import { cn } from '../../lib/utils';

const ACADEMIC_YEAR = '2024-2025';
const THRESHOLD_PERCENTAGE = 75;

export default function FacultyReportsPage() {
  const navigate = useNavigate();
  const user = getUser();

  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' or 'detailed'
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);

  // Check if user is faculty
  useEffect(() => {
    if (!user || user.role !== 'faculty') {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  // Fetch faculty's assigned subjects
  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    setLoading(true);
    try {
      const data = await facultyAssignmentService.getMySubjects(ACADEMIC_YEAR);
      setAssignments(data.assignments || []);

      // Auto-select first assignment if available
      if (data.assignments && data.assignments.length > 0) {
        const first = data.assignments[0];
        setSelectedAssignment({
          subject_id: first.subject_id,
          semester: first.semester,
          section: first.section,
          subject_name: first.subject?.name || 'Unknown Subject',
          subject_code: first.subject?.code || 'N/A'
        });
      }
    } catch (err) {
      console.error('Failed to fetch assignments:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch report when assignment is selected
  useEffect(() => {
    if (selectedAssignment) {
      fetchReport();
    }
  }, [selectedAssignment]);

  const fetchReport = async () => {
    if (!selectedAssignment) return;

    setReportLoading(true);
    try {
      const data = await attendanceService.getReport(
        selectedAssignment.subject_id,
        {
          semester: selectedAssignment.semester,
          section: selectedAssignment.section,
          academic_year: ACADEMIC_YEAR
        }
      );
      setReportData(data);
    } catch (err) {
      console.error('Failed to fetch report:', err);
      setReportData(null);
    } finally {
      setReportLoading(false);
    }
  };

  const handleAssignmentChange = (e) => {
    const assignmentId = e.target.value;
    const assignment = assignments.find(a => a.id === assignmentId);
    if (assignment) {
      setSelectedAssignment({
        subject_id: assignment.subject_id,
        semester: assignment.semester,
        section: assignment.section,
        subject_name: assignment.subject?.name || 'Unknown Subject',
        subject_code: assignment.subject?.code || 'N/A'
      });
      setSearchQuery('');
      setActiveTab('summary');
    }
  };

  // Computed: Students sorted by percentage (descending)
  const sortedStudents = useMemo(() => {
    if (!reportData?.students) return [];
    return [...reportData.students].sort((a, b) => (b.percentage || 0) - (a.percentage || 0));
  }, [reportData]);

  // Computed: Filtered students by search query
  const filteredStudents = useMemo(() => {
    if (!searchQuery) return sortedStudents;
    const query = searchQuery.toLowerCase();
    return sortedStudents.filter(student =>
      student.student_name?.toLowerCase().includes(query) ||
      student.roll_number?.toLowerCase().includes(query)
    );
  }, [sortedStudents, searchQuery]);

  // Computed: Students below threshold
  const belowThresholdStudents = useMemo(() => {
    return sortedStudents.filter(s => (s.percentage || 0) < THRESHOLD_PERCENTAGE);
  }, [sortedStudents]);

  // Computed: Class statistics
  const classStats = useMemo(() => {
    if (!reportData?.students || reportData.students.length === 0) {
      return { total: 0, present: 0, absent: 0, excused: 0, percentage: 0 };
    }
    const total = reportData.students.length;
    const present = reportData.students.reduce((sum, s) => sum + (s.present || 0), 0);
    const absent = reportData.students.reduce((sum, s) => sum + (s.absent || 0), 0);
    const excused = reportData.students.reduce((sum, s) => sum + (s.excused || 0), 0);
    const totalClasses = reportData.students.reduce((sum, s) => sum + (s.total_classes || 0), 0);
    const percentage = totalClasses > 0 ? Math.round((present / totalClasses) * 100) : 0;

    return { total, present, absent, excused, totalClasses, percentage };
  }, [reportData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Attendance Reports</h1>
        <p className="text-muted-foreground">
          View and analyze attendance for your assigned subjects
        </p>
      </div>

      {/* Empty State - No Subjects */}
      {assignments.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No subjects assigned to you yet.</p>
            <p className="text-sm text-muted-foreground mt-2">Contact admin to get subjects assigned.</p>
          </CardContent>
        </Card>
      )}

      {assignments.length > 0 && (
        <>
          {/* Subject Selector */}
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Select Subject</label>
                <select
                  value={selectedAssignment?.subject_id || ''}
                  onChange={handleAssignmentChange}
                  className="flex h-10 w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {assignments.map((assignment) => (
                    <option key={assignment.id} value={assignment.id}>
                      {assignment.subject?.name || 'Unknown'} (Sem {assignment.semester} - {assignment.section})
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          {/* Report Content */}
          {selectedAssignment && (
            <>
              {/* Report Loading */}
              {reportLoading ? (
                <Card>
                  <CardContent className="flex items-center justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-violet-600 mr-2" />
                    <span className="text-muted-foreground">Loading report...</span>
                  </CardContent>
                </Card>
              ) : !reportData || !reportData.students || reportData.students.length === 0 ? (
                /* Empty State - No Data */
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-12">
                    <Users className="h-12 w-12 text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">
                      No attendance records found for {selectedAssignment.subject_name}
                    </p>
                    <p className="text-sm text-muted-foreground mt-2">
                      Attendance will appear here once you start marking attendance.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                /* Report Display */
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>
                        {selectedAssignment.subject_name} ({selectedAssignment.subject_code})
                      </CardTitle>
                      <span className="text-sm font-normal text-muted-foreground">
                        Sem {selectedAssignment.semester} - Section {selectedAssignment.section}
                      </span>
                    </div>
                    {/* Tabs */}
                    <div className="flex gap-2 mt-4">
                      <button
                        onClick={() => setActiveTab('summary')}
                        className={cn(
                          "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                          activeTab === 'summary'
                            ? "bg-violet-600 text-white"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                        )}
                      >
                        Summary
                      </button>
                      <button
                        onClick={() => setActiveTab('detailed')}
                        className={cn(
                          "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                          activeTab === 'detailed'
                            ? "bg-violet-600 text-white"
                            : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                        )}
                      >
                        Detailed
                      </button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {activeTab === 'summary' && (
                      <div className="space-y-6">
                        {/* Class Stats */}
                        <div className="grid gap-4 md:grid-cols-5">
                          <Card>
                            <CardContent className="pt-6">
                              <p className="text-xs text-muted-foreground mb-1">Overall Attendance</p>
                              <p className={cn(
                                "text-2xl font-bold",
                                classStats.percentage >= 75 ? "text-green-600" :
                                classStats.percentage >= 60 ? "text-yellow-600" : "text-red-600"
                              )}>
                                {classStats.percentage}%
                              </p>
                            </CardContent>
                          </Card>
                          <Card>
                            <CardContent className="pt-6">
                              <p className="text-xs text-muted-foreground mb-1">Total Students</p>
                              <p className="text-2xl font-bold">{classStats.total}</p>
                            </CardContent>
                          </Card>
                          <Card>
                            <CardContent className="pt-6">
                              <p className="text-xs text-muted-foreground mb-1">Present</p>
                              <p className="text-2xl font-bold text-green-600">{classStats.present}</p>
                            </CardContent>
                          </Card>
                          <Card>
                            <CardContent className="pt-6">
                              <p className="text-xs text-muted-foreground mb-1">Absent</p>
                              <p className="text-2xl font-bold text-red-600">{classStats.absent}</p>
                            </CardContent>
                          </Card>
                          <Card>
                            <CardContent className="pt-6">
                              <p className="text-xs text-muted-foreground mb-1">Excused</p>
                              <p className="text-2xl font-bold text-yellow-600">{classStats.excused}</p>
                            </CardContent>
                          </Card>
                        </div>

                        {/* Below Threshold Warning */}
                        {belowThresholdStudents.length > 0 && (
                          <div className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                            <div className="flex items-center gap-2 mb-3">
                              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                              <p className="font-medium text-red-800 dark:text-red-300">
                                Below {THRESHOLD_PERCENTAGE}% Attendance ({belowThresholdStudents.length} students)
                              </p>
                            </div>
                            <div className="space-y-2">
                              {belowThresholdStudents.map((student) => (
                                <div
                                  key={student.student_id}
                                  className="flex items-center justify-between p-2 rounded bg-white dark:bg-gray-800"
                                >
                                  <span className="text-sm">{student.student_name}</span>
                                  <span className="text-sm font-medium text-red-600">
                                    {student.percentage}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {activeTab === 'detailed' && (
                      <div className="space-y-4">
                        {/* Search Bar */}
                        <div className="relative">
                          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                          <input
                            type="text"
                            placeholder="Search by name or roll number..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="flex h-10 w-full max-w-md rounded-md border border-input bg-background pl-10 pr-3 py-2 text-sm"
                          />
                        </div>

                        {/* Students Table */}
                        <div className="border rounded-lg overflow-hidden">
                          <table className="w-full">
                            <thead className="bg-gray-50 dark:bg-gray-800">
                              <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Student</th>
                                <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase">Present</th>
                                <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase">Absent</th>
                                <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase">Excused</th>
                                <th className="px-4 py-3 text-center text-xs font-medium text-muted-foreground uppercase">Percentage</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                              {filteredStudents.map((student) => (
                                <tr key={student.student_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                                  <td className="px-4 py-3">
                                    <div>
                                      <p className="font-medium">{student.student_name}</p>
                                      <p className="text-xs text-muted-foreground">{student.roll_number || 'N/A'}</p>
                                    </div>
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                                      {student.present || 0}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                                      {student.absent || 0}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
                                      {student.excused || 0}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <span className={cn(
                                      "inline-flex items-center px-2 py-1 rounded-full text-xs font-bold",
                                      (student.percentage || 0) >= 75
                                        ? "bg-green-100 text-green-700"
                                        : (student.percentage || 0) >= 60
                                          ? "bg-yellow-100 text-yellow-700"
                                          : "bg-red-100 text-red-700"
                                    )}>
                                      {student.percentage || 0}%
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        {filteredStudents.length === 0 && searchQuery && (
                          <div className="text-center py-8 text-muted-foreground">
                            No students found matching "{searchQuery}"
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
