import { useState, useEffect, useCallback } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { ErrorBoundary } from '../../components/ErrorBoundary';
import { SubjectCard } from '../../components/faculty/SubjectCard';
import { facultyAssignmentService } from '../../services/facultyAssignment';
import { facultyAvailabilityService } from '../../services/facultyAvailability';

export default function FacultySubjectsPage() {
  const [subjects, setSubjects] = useState([]);
  const [occupiedSlotsMap, setOccupiedSlotsMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savingSubject, setSavingSubject] = useState(null);

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

      // Fetch occupied slots for each unique semester/section combination
      const uniqueSemSections = [...new Set(processedData.map(a => `${a.semester}-${a.section}`))];
      const occupiedMap = {};

      for (const semSec of uniqueSemSections) {
        const [semester, section] = semSec.split('-');
        try {
          const occupied = await facultyAvailabilityService.getOccupiedSlots(parseInt(semester), section);
          occupiedMap[semSec] = occupied;
        } catch (err) {
          console.warn(`Failed to fetch occupied slots for ${semSec}:`, err);
          occupiedMap[semSec] = [];
        }
      }

      setOccupiedSlotsMap(occupiedMap);
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
    const subjectKey = `${subjectId}-${semester}-${section}`;
    setSavingSubject(subjectKey);

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

      // Refresh occupied slots after successful save
      const semSec = `${semester}-${section}`;
      try {
        const occupied = await facultyAvailabilityService.getOccupiedSlots(semester, section);
        setOccupiedSlotsMap(prev => ({
          ...prev,
          [semSec]: occupied
        }));
      } catch (err) {
        console.warn('Failed to refresh occupied slots:', err);
      }

      return slots;
    } catch (err) {
      throw new Error(err.message || 'Failed to save availability');
    } finally {
      setSavingSubject(null);
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
          <p className="text-xs text-orange-600 dark:text-orange-400 mt-1">
            Note: Slots already selected by other faculty for the same semester/section are shown as unavailable
          </p>
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
            // Get occupied slots for this semester/section from backend
            const semSec = `${assignment.semester}-${assignment.section}`;
            const occupiedSlots = occupiedSlotsMap[semSec] || [];

            return (
              <ErrorBoundary key={`${assignment.subject._id}-${assignment.semester}-${assignment.section}`}>
                <SubjectCard
                  subject={assignment.subject}
                  semester={assignment.semester}
                  section={assignment.section}
                  initialSlots={assignment.available_slots || []}
                  onSave={handleSaveAvailability}
                  saving={savingSubject === `${assignment.subject._id}-${assignment.semester}-${assignment.section}`}
                  bookedSlots={occupiedSlots}
                />
              </ErrorBoundary>
            );
          })}
        </div>
      )}
    </div>
  );
}
