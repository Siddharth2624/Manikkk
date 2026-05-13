import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { AlertTriangle, Clock, Users, BookOpen } from 'lucide-react';

/**
 * Simple slot-wise conflict display
 * Shows which faculties and subjects are conflicting for each time slot
 */
export function ConflictReport({ warnings, assignments = [], onDismiss }) {
  if (!warnings || (!warnings.local?.length && !warnings.global?.length)) {
    return null;
  }

  const facultyNameById = new Map();
  const subjectLabelById = new Map();

  assignments.forEach((assignment) => {
    if (assignment.faculty_id && assignment.faculty_name) {
      facultyNameById.set(assignment.faculty_id, assignment.faculty_name);
    }
    if (assignment.subject_id) {
      const subjectLabel = assignment.subject_code
        ? `${assignment.subject_code} - ${assignment.subject_name || 'Subject'}`
        : assignment.subject_name;
      if (subjectLabel) {
        subjectLabelById.set(assignment.subject_id, subjectLabel);
      }
    }
  });

  const facultyLabel = (facultyIdOrName) =>
    facultyNameById.get(facultyIdOrName) || facultyIdOrName;

  const subjectLabel = (subjectIdOrName) =>
    subjectLabelById.get(subjectIdOrName) || subjectIdOrName;

  // Group conflicts by slot
  const conflictsBySlot = {};

  // Process local warnings (faculty-specific conflicts)
  warnings.local?.forEach(warning => {
    // Local warnings may not have slot info, create a "General" category
    if (!conflictsBySlot['General']) {
      conflictsBySlot['General'] = { faculties: new Set(), subjects: new Set() };
    }
    conflictsBySlot['General'].faculties.add(warning.faculty_name || facultyLabel(warning.faculty_id));
    conflictsBySlot['General'].subjects.add(subjectLabel(warning.subject_id) || warning.subject_name);
  });

  // Process global warnings (slot-specific conflicts)
  warnings.global?.forEach(warning => {
    const slotKey = `Slot ${warning.slot_number} (${warning.time_range})`;
    if (!conflictsBySlot[slotKey]) {
      conflictsBySlot[slotKey] = { faculties: new Set(), subjects: new Set(), competing_faculty: [] };
    }
    // Store competing faculty and subjects for this slot
    conflictsBySlot[slotKey].faculties = new Set(
      warning.competing_faculty_names?.length
        ? warning.competing_faculty_names
        : (warning.competing_faculty || []).map(facultyLabel)
    );
    conflictsBySlot[slotKey].subjects = new Set(
      warning.competing_subject_names?.length
        ? warning.competing_subject_names
        : (warning.competing_subjects || []).map(subjectLabel)
    );
  });

  return (
    <Card className="border-2 border-rose-200 dark:border-rose-900 shadow-lg bg-rose-50/50 dark:bg-rose-950/20">
      <CardHeader className="border-b bg-rose-100/50 dark:bg-rose-900/30">
        <CardTitle className="flex items-center gap-3 text-rose-800 dark:text-rose-300">
          <AlertTriangle className="h-6 w-6" />
          <span>Scheduling Risks Detected</span>
        </CardTitle>
        <p className="text-sm text-rose-700 dark:text-rose-400 mt-1">
          These slots are highly contested. They may block generation unless availability is diversified.
        </p>
      </CardHeader>

      <CardContent className="pt-6">
        <div className="space-y-4">
          {Object.entries(conflictsBySlot).map(([slot, data]) => (
            <div
              key={slot}
              className="p-4 rounded-lg bg-white dark:bg-gray-900 border border-rose-200 dark:border-rose-900"
            >
              {/* Slot Header */}
              <div className="flex items-center gap-2 mb-3">
                {slot === 'General' ? (
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                ) : (
                  <Clock className="h-5 w-5 text-rose-500" />
                )}
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                  {slot}
                </h3>
              </div>

              {/* Conflicting Faculties */}
              {data.faculties.size > 0 && (
                <div className="mb-2">
                  <div className="flex items-center gap-2 text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                    <Users className="h-3 w-3" />
                    Conflicting Faculties
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Array.from(data.faculties).map((faculty) => (
                      <span
                        key={faculty}
                        className="px-2 py-1 text-xs bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-300 rounded"
                      >
                        {faculty}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Conflicting Subjects */}
              {data.subjects.size > 0 && (
                <div>
                  <div className="flex items-center gap-2 text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wide mb-1">
                    <BookOpen className="h-3 w-3" />
                    Conflicting Subjects
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Array.from(data.subjects).map((subject) => (
                      <span
                        key={subject}
                        className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 rounded"
                      >
                        {subject}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Action button */}
        {onDismiss && (
          <div className="flex justify-end mt-6">
            <button
              onClick={onDismiss}
              className="px-4 py-2 text-sm bg-rose-600 hover:bg-rose-700 text-white rounded-lg transition-colors"
            >
              Dismiss
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
