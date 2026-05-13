import { useState, useEffect, useCallback } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { ErrorBoundary } from '../../components/ErrorBoundary';
import { SubjectCard } from '../../components/faculty/SubjectCard';
import { facultyAssignmentService } from '../../services/facultyAssignment';
import { facultyAvailabilityService } from '../../services/facultyAvailability';

export default function FacultySubjectsPage() {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSubjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await facultyAssignmentService.getMySubjects();
      // Convert available_slots from [{day, slot}] to ["Day-Slot"] format (title case)
      const processedData = data.map(assignment => ({
        ...assignment,
        available_slots: (assignment.available_slots || []).map(slot =>
          typeof slot === 'object' ? `${slot.day.charAt(0)}${slot.day.slice(1).toLowerCase()}-${slot.slot}` : slot
        )
      }));
      setSubjects(processedData);
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 5000);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSubjects();
  }, [fetchSubjects]);

  const handleSaveAvailability = useCallback(async (subjectId, semester, section, slots) => {
    try {
      if (slots === null) {
        return await facultyAvailabilityService.get(subjectId, semester, section);
      }

      await facultyAvailabilityService.update({
        subject_id: subjectId,
        semester,
        section,
        available_slots: slots,
      });

      return slots;
    } catch (err) {
      throw new Error(err.message || 'Failed to save availability');
    }
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-violet-600 mx-auto" />
          <p className="text-muted-foreground">Loading your subjects...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">My Subjects</h1>
          <p className="text-muted-foreground mt-1">Manage your availability for assigned subjects</p>
        </div>
      </div>

      {error && (
        <div className="mb-6 flex items-center space-x-2 p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {subjects.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
          <p className="text-muted-foreground">No subjects assigned</p>
        </div>
      ) : (
        <div className="space-y-4">
          {subjects.map((assignment) => {
            const subjectId = assignment.subject?.id || assignment.subject?._id;

            return (
              <ErrorBoundary key={`${subjectId}-${assignment.semester}-${assignment.section}`}>
                <SubjectCard
                  subject={assignment.subject}
                  semester={assignment.semester}
                  section={assignment.section}
                  initialSlots={assignment.available_slots || []}
                  onSave={handleSaveAvailability}
                />
              </ErrorBoundary>
            );
          })}
        </div>
      )}
    </div>
  );
}
