import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input, Label } from '../components/ui/input';
import { ArrowLeft, CheckCircle, AlertCircle, Loader2, Edit, Users, BookOpen, Sparkles } from 'lucide-react';
import { api } from '../lib/api';
import { ConflictReport, TimetableConflictReport } from '../components/feasibility';

export default function AdminTimetablePage() {
  const navigate = useNavigate();

  const [semester, setSemester] = useState(1);
  const [section, setSection] = useState('A');
  const [assignments, setAssignments] = useState([]);
  const [loadingAssignments, setLoadingAssignments] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [bulkGenerating, setBulkGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [bulkResult, setBulkResult] = useState(null);
  const [error, setError] = useState(null);
  const [feasibilityReport, setFeasibilityReport] = useState(null);
  const [generationConflictReport, setGenerationConflictReport] = useState(null);

  // Fetch assignments when semester/section changes
  useEffect(() => {
    const fetchAssignments = async () => {
      setLoadingAssignments(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          semester: semester.toString(),
          section,
        });
        const data = await api(`/timetable/assignments/preview?${params.toString()}`);
        setAssignments(data.assignments || []);
      } catch (err) {
        setError(err.message || 'Failed to load assignments');
        setAssignments([]);
      } finally {
        setLoadingAssignments(false);
      }
    };

    fetchAssignments();
  }, [semester, section]);

  // Handle generate with feasibility error handling
  const handleGenerate = async () => {
    if (assignments.length === 0) {
      setError('No subject assignments found for this semester/section. Please assign subjects to faculty first.');
      return;
    }

    setGenerating(true);
    setError(null);
    setResult(null);
    setBulkResult(null);
    setFeasibilityReport(null);
    setGenerationConflictReport(null);

    try {
      const data = await api('/timetable/generate/simple', {
        method: 'POST',
        body: JSON.stringify({ semester, section }),
      });

      setResult(data);
    } catch (err) {
      const data = err.data;
      if (data?.status === 'generation_conflict') {
        setGenerationConflictReport(data);
        return;
      }

      // Check if it's a feasibility error (has report structure)
      if (data?.status && (data.status === 'fail' || data.status === 'warning')) {
        setFeasibilityReport(data);
        return;
      }

      setError(err.message || 'Failed to generate timetable');
    } finally {
      setGenerating(false);
    }
  };

  // Handle bulk generate for all sections
  const handleBulkGenerate = async () => {
    setBulkGenerating(true);
    setError(null);
    setResult(null);
    setBulkResult(null);
    setGenerationConflictReport(null);

    try {
      const response = await api(`/timetable/generate/bulk?semester=${semester}`, {
        method: 'POST',
      });
      setBulkResult(response);
    } catch (err) {
      setError(err.message || 'Failed to generate timetables for all sections');
    } finally {
      setBulkGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/timetable')}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Generate Timetable</h1>
            <p className="text-muted-foreground">
              Auto-detects subjects and faculty from assignments
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/admin/timetable/edit')}
          className="gap-2"
        >
          <Edit className="h-4 w-4" />
          Edit Existing
        </Button>
      </div>

      {/* Timetable Conflict Report (detailed error from backend) */}
      {error && !feasibilityReport && (
        <TimetableConflictReport
          errorMessage={error}
          assignments={assignments}
          semester={semester}
          section={section}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Structured Generation Conflict Report */}
      {generationConflictReport && (
        <TimetableConflictReport
          conflictReport={generationConflictReport}
          assignments={assignments}
          semester={semester}
          section={section}
          onDismiss={() => setGenerationConflictReport(null)}
        />
      )}

      {/* Feasibility Conflict Report */}
      {feasibilityReport?.errors?.length > 0 && (
        <Card className="border-2 border-red-200 bg-red-50/60 dark:border-red-900 dark:bg-red-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-900 dark:text-red-200">
              <AlertCircle className="h-5 w-5" />
              Timetable generation is blocked
            </CardTitle>
            <CardDescription className="text-red-700 dark:text-red-300">
              Resolve these availability issues, then generate again.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              {feasibilityReport.errors.map((message, index) => (
                <div
                  key={`${message}-${index}`}
                  className="rounded-lg border border-red-200 bg-white px-3 py-2 text-sm text-red-900 dark:border-red-900 dark:bg-gray-950 dark:text-red-200"
                >
                  {message}
                </div>
              ))}
            </div>
            {feasibilityReport.suggestions?.length > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/30">
                <p className="mb-2 text-sm font-semibold text-amber-900 dark:text-amber-100">Suggested fixes</p>
                <div className="space-y-1">
                  {feasibilityReport.suggestions.slice(0, 4).map((suggestion, index) => (
                    <p key={`${suggestion.message}-${index}`} className="text-sm text-amber-800 dark:text-amber-100">
                      {suggestion.message}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {feasibilityReport && feasibilityReport.warnings && (
        <ConflictReport
          warnings={feasibilityReport.warnings}
          assignments={assignments}
          onDismiss={() => setFeasibilityReport(null)}
        />
      )}

      {/* Success */}
      {result && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-green-800 dark:text-green-300">
              Timetable generated successfully!
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 mt-0.5">
              Semester {semester}, Section {section}, Version {result.timetable?.version}
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => navigate('/timetable')}
          >
            View Timetable
          </Button>
        </div>
      )}

      {/* Bulk Generation Success */}
      {bulkResult && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <CheckCircle className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
              Bulk generation completed!
            </p>
            <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
              Semester {semester}: {bulkResult.successful} sections successful, {bulkResult.failed} failed
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => navigate('/timetable')}
          >
            View Timetables
          </Button>
        </div>
      )}

      {/* Configuration Form */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Basic Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Settings</CardTitle>
            <CardDescription>Select semester and section</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Semester</Label>
              <select
                value={semester}
                onChange={(e) => setSemester(parseInt(e.target.value))}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                  <option key={s} value={s}>Semester {s}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Section</Label>
              <select
                value={section}
                onChange={(e) => setSection(e.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {['A', 'B'].map(s => (
                  <option key={s} value={s}>Section {s}</option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Detected Assignments Preview */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Detected Subject Assignments</CardTitle>
            <CardDescription>
              {assignments.length} subject(s) assigned to faculty for this semester/section
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingAssignments ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-violet-600" />
              </div>
            ) : assignments.length === 0 ? (
              <div className="text-center py-8 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                <BookOpen className="h-10 w-10 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">
                  No subject assignments found for Semester {semester}, Section {section}.
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Please assign subjects to faculty first.
                </p>
              </div>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {assignments.map((assignment, index) => (
                  <div
                    key={`${assignment.subject_id}-${assignment.faculty_id}-${index}`}
                    className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800"
                  >
                    <div className="h-10 w-10 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
                      <BookOpen className="h-5 w-5 text-violet-600 dark:text-violet-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {assignment.subject_name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {assignment.subject_code} - {assignment.credits} credit(s)
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-gray-400" />
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {assignment.faculty_name}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Info Card */}
      <Card className="bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <CheckCircle className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800 dark:text-blue-300">
              <p className="font-medium mb-1">Automatic Timetable Generation</p>
              <p className="text-blue-600 dark:text-blue-400">
                The system will automatically detect all subject assignments for the selected semester and section,
                along with faculty availability data. Click "Generate Timetable" to create the schedule.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Generate Buttons */}
      <div className="flex justify-end gap-3">
        <Button
          onClick={handleGenerate}
          disabled={generating || assignments.length === 0 || bulkGenerating}
          className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 gap-2"
        >
          {generating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <CheckCircle className="h-4 w-4" />
              Generate for Section {section}
            </>
          )}
        </Button>
        <Button
          onClick={handleBulkGenerate}
          disabled={bulkGenerating || generating}
          variant="outline"
          className="gap-2"
        >
          {bulkGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating All...
            </>
          ) : (
            <>
              <CheckCircle className="h-4 w-4" />
              Generate All Sections
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
