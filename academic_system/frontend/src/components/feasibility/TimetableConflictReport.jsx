import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  Lightbulb,
  Users,
  Zap,
} from 'lucide-react';
import { useState } from 'react';

const DAY_LABELS = {
  MON: 'Monday',
  TUE: 'Tuesday',
  WED: 'Wednesday',
  THU: 'Thursday',
  FRI: 'Friday',
  SAT: 'Saturday',
};

function cleanText(value = '') {
  return value.trim().replace(/\.$/, '');
}

function parseAvailability(raw = '') {
  if (!raw || raw.trim().toLowerCase() === 'none') return [];

  const matches = [...raw.replace(/\.$/, '').matchAll(/([A-Z]+)\[([^\]]*)\]/g)];
  return matches.map((match) => ({
    day: match[1],
    slots: match[2]
      .split(',')
      .map((slot) => slot.trim())
      .filter(Boolean),
  }));
}

function parseAssignedSlots(raw = '') {
  if (!raw || raw.trim().toLowerCase() === 'none') return [];

  const matches = [...raw.matchAll(/([A-Z]+)-(\d+)(?:\s*\(([^)]+)\))?/g)];
  return matches.map((match) => ({
    day: match[1],
    slot: match[2],
    time: match[3] || '',
  }));
}

function getReasonLabel(reason = '') {
  const lower = reason.toLowerCase();

  if (lower.includes('no available slots')) {
    return 'No usable free slot remains for this subject.';
  }
  if (lower.includes('no 2 consecutive')) {
    return 'No two consecutive slots are available for this lab.';
  }
  if (lower.includes('has only')) {
    return 'The faculty has fewer available slots than this subject requires.';
  }
  if (lower.includes('needs') && lower.includes('available')) {
    return 'The faculty workload needs more available slots.';
  }

  return cleanText(reason) || 'The generator could not find a valid slot.';
}

function parseCompactConflict(message) {
  if (!message?.startsWith('Conflict:')) return null;

  const text = message.replace(/^Conflict:\s*/, '').trim();

  const missingFacultyMatch = text.match(/^No faculty assigned to(?: lab)? subject:\s*(.+)$/);
  if (missingFacultyMatch) {
    return {
      type: 'missing-faculty',
      title: 'Faculty assignment missing',
      subjectName: cleanText(missingFacultyMatch[1]),
      reason: 'No faculty is assigned to this subject.',
      suggestions: [
        'Assign a faculty member to this subject for the selected semester and section.',
        'Return to Faculty Assignments and verify the subject appears in the assignment list.',
      ],
    };
  }

  const facultyLoadMatch = text.match(/^Faculty\s+(.+?)\s+teaching\s+(.+?)\s+needs\s+(\d+)\s+total slots,\s+but only has\s+(\d+)\s+available slots\.\s+Please add\s+(\d+)\s+more slots/i);
  if (facultyLoadMatch) {
    return {
      type: 'faculty-load',
      title: 'Faculty availability is insufficient',
      facultyName: facultyLoadMatch[1],
      subjectName: facultyLoadMatch[2],
      requiredSlots: facultyLoadMatch[3],
      availableSlotCount: facultyLoadMatch[4],
      shortage: facultyLoadMatch[5],
      reason: `${facultyLoadMatch[1]} needs ${facultyLoadMatch[3]} total teaching slots, but only ${facultyLoadMatch[4]} are available.`,
      suggestions: [
        `Add at least ${facultyLoadMatch[5]} more available slot(s) for this faculty.`,
        'If the faculty cannot add slots, reassign one subject to another faculty member.',
        'Regenerate the timetable after updating availability or assignments.',
      ],
    };
  }

  const subjectMatch = text.match(/^Cannot schedule(?:\s+(lab))?\s+'([^']+)'\s+\(([^)]+)\)(?:\s+-\s+slot\s+(\d+)\/(\d+))?\.\s*(.*)$/i);
  if (!subjectMatch) return null;

  const [, labKeyword, subjectName, subjectCode, currentSlot, requiredSlots, rest] = subjectMatch;
  const isLab = Boolean(labKeyword);
  const facultyMatch = rest.match(/^Faculty\s+(.+?)\s+((?:has|needs|is|teaching)\b.*)$/i);
  const facultyName = facultyMatch?.[1] || '';
  const detailText = facultyMatch?.[2] || rest;
  const assignedMatch = detailText.match(/Already assigned:\s*(.*?)(?:\.\s*Faculty availability:|$)/i);
  const availabilityMatch = detailText.match(/(?:Faculty availability|Available slots|Available):\s*(.*?)(?:\.\s*(?:Please|Labs)|$)/i);
  const availableNeedsMatch = detailText.match(/has only\s+(\d+)\s+available slot\(s\),\s+but needs\s+(\d+)/i);

  let reason = detailText
    .replace(/\s*Already assigned:.*$/i, '')
    .replace(/\s*(?:Faculty availability|Available slots|Available):.*$/i, '')
    .replace(/\s*Please add more availability\.?$/i, '')
    .trim();

  if (facultyName && reason.toLowerCase().startsWith(facultyName.toLowerCase())) {
    reason = reason.slice(facultyName.length).trim();
  }

  const assignedSlots = parseAssignedSlots(assignedMatch?.[1] || '');
  const availability = parseAvailability(availabilityMatch?.[1] || '');
  const shortage = availableNeedsMatch
    ? Math.max(Number(availableNeedsMatch[2]) - Number(availableNeedsMatch[1]), 0)
    : null;

  const suggestions = [];
  if (isLab || reason.toLowerCase().includes('consecutive')) {
    suggestions.push('Add at least one pair of consecutive slots for this faculty, such as slots 1-2, 3-4, or 7-8.');
    suggestions.push('Use an admin override only if the faculty can teach during those consecutive periods.');
  } else if (shortage) {
    suggestions.push(`Add at least ${shortage} more available slot(s) for this faculty and subject.`);
  } else {
    suggestions.push('Add more faculty availability for this subject, preferably on different days.');
  }
  suggestions.push('If availability cannot be expanded, reassign the subject to another faculty member.');
  suggestions.push('Regenerate the timetable after making the change.');

  return {
    type: 'subject',
    title: isLab ? 'Lab could not be scheduled' : 'Subject could not be scheduled',
    subjectName,
    subjectCode,
    facultyName,
    slotProgress: currentSlot && requiredSlots ? `${currentSlot} of ${requiredSlots}` : '',
    requiredSlots,
    availableSlotCount: availableNeedsMatch?.[1],
    reason: getReasonLabel(reason),
    originalReason: cleanText(reason),
    assignedSlots,
    availability,
    suggestions,
  };
}

function findMatchingAssignment(conflict, assignments = []) {
  if (!conflict) return null;

  const subjectCode = conflict.subjectCode || conflict.subject_code;
  const subjectName = conflict.subjectName || conflict.subject_name;
  const facultyName = conflict.facultyName || conflict.faculty_name;
  const subjectId = conflict.subject_id || conflict.subjectId;
  const facultyId = conflict.faculty_id || conflict.facultyId;

  return assignments.find((assignment) => {
    const sameSubject =
      (subjectId && assignment.subject_id === subjectId) ||
      (subjectCode && assignment.subject_code === subjectCode) ||
      (subjectName && assignment.subject_name === subjectName);
    const sameFaculty =
      !facultyId && !facultyName ||
      (facultyId && assignment.faculty_id === facultyId) ||
      (facultyName && assignment.faculty_name === facultyName) ||
      (facultyName && assignment.faculty_name && facultyName.includes(assignment.faculty_name));

    return sameSubject && sameFaculty;
  });
}

function formatConflictType(type = '') {
  if (!type) return 'Scheduling conflict';
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getStructuredConflictTitle(conflict) {
  const type = conflict.type || '';

  if (type.includes('missing_faculty')) return 'Faculty assignment missing';
  if (type.includes('consecutive')) return 'Lab needs consecutive slots';
  if (type.includes('total_shortage')) return 'Faculty workload exceeds availability';
  if (type.includes('lab')) return 'Lab could not be scheduled';
  if (type.includes('theory')) return 'Subject could not be scheduled';
  if (type.includes('insufficient')) return 'Availability is insufficient';

  return 'Scheduling issue';
}

function formatSlot(slot) {
  if (!slot) return '';
  const day = DAY_LABELS[slot.day] || slot.day;
  return `${day} slot ${slot.slot}${slot.time ? ` (${slot.time})` : ''}`;
}

function formatSlotPair(pair) {
  if (!pair) return '';
  const day = DAY_LABELS[pair.day] || pair.day;
  return `${day} slots ${pair.start_slot}-${pair.end_slot}`;
}

function buildAvailabilityHref(conflict, matchedAssignment, semester, section, conflictReport) {
  const facultyId = conflict.faculty_id || matchedAssignment?.faculty_id;
  const subjectId = conflict.subject_id || matchedAssignment?.subject_id;

  if (!facultyId || !subjectId) return null;

  const targetSemester = conflictReport?.semester || semester || matchedAssignment?.semester;
  const targetSection = conflictReport?.section || section || matchedAssignment?.section;

  return `/admin/faculty-availability?faculty_id=${facultyId}&subject_id=${subjectId}&semester=${targetSemester}&section=${targetSection}`;
}

function MetricCard({ label, value, tone = 'gray' }) {
  const toneClass = {
    gray: 'border-gray-200 bg-gray-50 text-gray-900 dark:border-gray-800 dark:bg-gray-900/60 dark:text-white',
    red: 'border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/30 dark:text-red-100',
    blue: 'border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-100',
    amber: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100',
  }[tone];

  return (
    <div className={`rounded-xl border p-3 ${toneClass}`}>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 text-lg font-bold">{value ?? '-'}</p>
    </div>
  );
}

/**
 * Display slot-wise conflict report for failed timetable generation.
 *
 * Shows for each time slot (day + time):
 * - Which faculty are available
 * - What subjects each faculty teaches
 * - Highlights multiple faculty competing for same slot
 */
export function TimetableConflictReport({ errorMessage, conflictReport, assignments = [], semester, section, onDismiss }) {
  const [collapsedDays, setCollapsedDays] = useState({});
  const structuredConflicts = conflictReport?.conflicts || [];

  if (structuredConflicts.length > 0) {
    const reportSemester = conflictReport.semester || semester;
    const reportSection = conflictReport.section || section;
    const totalMissingSlots = structuredConflicts.reduce(
      (total, conflict) => total + Number(conflict.missing_slots || 0),
      0
    );

    return (
      <Card className="border border-red-200 dark:border-red-900 shadow-sm bg-white dark:bg-gray-950 overflow-hidden">
        <CardHeader className="border-b border-red-100 dark:border-red-900/70 bg-red-50 dark:bg-red-950/30">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <CardTitle className="flex items-center gap-3 text-red-900 dark:text-red-200">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/60">
                  <AlertTriangle className="h-5 w-5 text-red-700 dark:text-red-300" />
                </span>
                Timetable generation needs admin action
              </CardTitle>
              <p className="text-sm text-red-800 dark:text-red-300">
                {conflictReport.summary || `${structuredConflicts.length} issue(s) must be resolved before generation can continue.`}
              </p>
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-sm font-medium text-red-700 dark:text-red-300 hover:underline"
              >
                Dismiss
              </button>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-5 pt-5">
          <div className="grid gap-3 md:grid-cols-3">
            <MetricCard
              label="Generation target"
              value={`Sem ${reportSemester}, Section ${reportSection}`}
              tone="gray"
            />
            <MetricCard
              label="Blocking issues"
              value={structuredConflicts.length}
              tone="red"
            />
            <MetricCard
              label="Missing slots"
              value={totalMissingSlots}
              tone={totalMissingSlots > 0 ? 'amber' : 'blue'}
            />
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/30">
            <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-blue-950 dark:text-blue-200">
              <Lightbulb className="h-4 w-4" />
              How to resolve this
            </h3>
            <p className="text-sm text-blue-900 dark:text-blue-200">
              Review each blocking issue below. Open Faculty Availability when the fix is to add or remove slots, or Review Assignments when the faculty assignment itself needs to change.
            </p>
          </div>

          <div className="space-y-4">
            {structuredConflicts.map((conflict, index) => {
              const matchedAssignment = findMatchingAssignment(conflict, assignments);
              const availabilityHref = buildAvailabilityHref(
                conflict,
                matchedAssignment,
                reportSemester,
                reportSection,
                conflictReport
              );
              const subjectName = conflict.subject_name || matchedAssignment?.subject_name || 'Multiple subjects';
              const subjectCode = conflict.subject_code || matchedAssignment?.subject_code;
              const facultyName = conflict.faculty_name || matchedAssignment?.faculty_name || 'Not assigned';
              const availableSlots = conflict.available_slots || [];
              const consecutivePairs = conflict.available_consecutive_pairs || [];
              const usableConsecutivePairs = conflict.usable_consecutive_pairs;
              const displayedLabPairs = Array.isArray(usableConsecutivePairs)
                ? usableConsecutivePairs
                : consecutivePairs;
              const assignedSlots = conflict.assigned_slots || [];
              const blockedSlots = conflict.blocked_slots || [];
              const isLabConflict = ['lab', 'consecutive'].some((keyword) =>
                String(conflict.type || '').toLowerCase().includes(keyword)
              );
              const suggestions = conflict.suggestions?.length ? conflict.suggestions : [conflict.recommendation].filter(Boolean);

              return (
                <div
                  key={`${conflict.type}-${conflict.subject_id || facultyName}-${index}`}
                  className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-950"
                >
                  <div className="flex flex-col gap-3 border-b border-gray-100 pb-4 dark:border-gray-800 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-100 text-sm font-bold text-red-800 dark:bg-red-900/50 dark:text-red-200">
                        {index + 1}
                      </span>
                      <div>
                        <p className="text-base font-semibold text-gray-950 dark:text-white">
                          {getStructuredConflictTitle(conflict)}
                        </p>
                        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                          {subjectName}
                          {subjectCode ? ` (${subjectCode})` : ''} with {facultyName}
                        </p>
                      </div>
                    </div>
                    <span className="w-fit rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700 dark:bg-gray-900 dark:text-gray-300">
                      {formatConflictType(conflict.type)}
                    </span>
                  </div>

                  <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
                    <div className="rounded-xl border border-red-200 bg-red-50/70 p-4 dark:border-red-900 dark:bg-red-950/30">
                      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-red-950 dark:text-red-100">
                        <AlertTriangle className="h-4 w-4" />
                        Blocking issue
                      </div>
                      <p className="text-sm text-red-900 dark:text-red-200">
                        {conflict.issue || 'The generator could not place this assignment.'}
                      </p>
                      {conflict.recommendation && (
                        <p className="mt-2 text-sm font-medium text-red-950 dark:text-red-100">
                          Recommended: {conflict.recommendation}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <MetricCard label="Required" value={conflict.required_slots ?? '-'} tone="gray" />
                      <MetricCard label="Scheduled" value={conflict.scheduled_slots ?? 0} tone="blue" />
                      <MetricCard label="Missing" value={conflict.missing_slots ?? '-'} tone="red" />
                      <MetricCard label="Available" value={conflict.available_slot_count ?? availableSlots.length} tone="amber" />
                    </div>
                  </div>

                  {(availableSlots.length > 0 || assignedSlots.length > 0 || blockedSlots.length > 0 || isLabConflict) && (
                    <div className={`mt-4 grid gap-4 ${isLabConflict ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}>
                      <div className="rounded-xl border border-gray-200 p-4 dark:border-gray-800">
                        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
                          <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                          Available slots
                        </h4>
                        {availableSlots.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {availableSlots.map((slot, slotIndex) => (
                              <span
                                key={`${slot.day}-${slot.slot}-${slotIndex}`}
                                className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-800 ring-1 ring-blue-200 dark:bg-blue-950/40 dark:text-blue-200 dark:ring-blue-900"
                              >
                                {formatSlot(slot)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400">No available slots were found.</p>
                        )}
                      </div>

                      {isLabConflict && (
                        <div className="rounded-xl border border-gray-200 p-4 dark:border-gray-800">
                          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
                            <CalendarClock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                            Free lab pairs
                          </h4>
                          {displayedLabPairs.length > 0 ? (
                            <>
                              <div className="flex flex-wrap gap-2">
                                {displayedLabPairs.map((pair, pairIndex) => (
                                  <span
                                    key={`${pair.day}-${pair.start_slot}-${pair.end_slot}-${pairIndex}`}
                                    className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800 ring-1 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:ring-emerald-900"
                                  >
                                    {formatSlotPair(pair)}
                                  </span>
                                ))}
                              </div>
                              {Array.isArray(usableConsecutivePairs) && consecutivePairs.length > displayedLabPairs.length && (
                                <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                                  Faculty availability has {consecutivePairs.length} pair(s), but only the pairs above are free after classroom and lunch constraints.
                                </p>
                              )}
                            </>
                          ) : Array.isArray(usableConsecutivePairs) && consecutivePairs.length > 0 ? (
                            <div className="space-y-2">
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                No free lab pair remains. Faculty availability includes:
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {consecutivePairs.map((pair, pairIndex) => (
                                  <span
                                    key={`${pair.day}-${pair.start_slot}-${pair.end_slot}-${pairIndex}`}
                                    className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800 ring-1 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-900"
                                  >
                                    {formatSlotPair(pair)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              No same-day consecutive pair is available.
                            </p>
                          )}
                        </div>
                      )}

                      <div className="rounded-xl border border-gray-200 p-4 dark:border-gray-800">
                        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
                          <CalendarClock className="h-4 w-4 text-red-600 dark:text-red-400" />
                          Occupied candidate slots
                        </h4>
                        {blockedSlots.length > 0 ? (
                          <div className="space-y-2">
                            {blockedSlots.map((slot, slotIndex) => (
                              <div
                                key={`${slot.day}-${slot.slot}-${slotIndex}`}
                                className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-900 ring-1 ring-red-200 dark:bg-red-950/40 dark:text-red-200 dark:ring-red-900"
                              >
                                <p className="font-semibold">{formatSlot(slot)}</p>
                                <p className="mt-0.5">
                                  {slot.subject_code || slot.subject_name || 'Occupied'}
                                  {slot.faculty_name ? ` with ${slot.faculty_name}` : ''}
                                  {slot.source_label ? ` (${slot.source_label})` : ''}
                                </p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400">No occupied candidate slots were reported.</p>
                        )}
                      </div>

                      <div className="rounded-xl border border-gray-200 p-4 dark:border-gray-800">
                        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                          Already placed in this attempt
                        </h4>
                        {assignedSlots.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {assignedSlots.map((slot, slotIndex) => (
                              <span
                                key={`${slot.day}-${slot.slot}-${slotIndex}`}
                                className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800 ring-1 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:ring-emerald-900"
                              >
                                {formatSlot(slot)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500 dark:text-gray-400">Nothing was placed before this issue appeared.</p>
                        )}
                      </div>
                    </div>
                  )}

                  {suggestions.length > 0 && (
                    <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
                      <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-950 dark:text-amber-200">
                        <Zap className="h-4 w-4" />
                        Suggested fix
                      </h4>
                      <div className="space-y-2">
                        {suggestions.map((suggestion, suggestionIndex) => (
                          <div key={`${suggestion}-${suggestionIndex}`} className="flex gap-2 text-sm text-amber-900 dark:text-amber-100">
                            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-200 text-xs font-bold text-amber-900 dark:bg-amber-900 dark:text-amber-100">
                              {suggestionIndex + 1}
                            </span>
                            <span>{suggestion}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-4 flex flex-col gap-3 border-t border-gray-100 pt-4 dark:border-gray-800 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Resolve this issue, then generate Semester {reportSemester}, Section {reportSection} again.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {availabilityHref && (
                        <button
                          onClick={() => {
                            window.location.href = availabilityHref;
                          }}
                          className="inline-flex items-center gap-2 rounded-lg bg-gray-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-800 dark:bg-white dark:text-gray-950 dark:hover:bg-gray-200"
                        >
                          Open Faculty Availability
                          <ExternalLink className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => {
                          window.location.href = '/admin/assignments';
                        }}
                        className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-900"
                      >
                        Review Assignments
                        <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!errorMessage) {
    return null;
  }

  // Check if this is a detailed conflict report
  const isConflictReport = errorMessage.includes('CONFLICT ANALYSIS REPORT');
  const compactConflict = parseCompactConflict(errorMessage);

  if (compactConflict && !isConflictReport) {
    const matchedAssignment = findMatchingAssignment(compactConflict, assignments);
    const canOpenAvailability = matchedAssignment?.faculty_id && matchedAssignment?.subject_id;
    const availabilityHref = canOpenAvailability
      ? `/admin/faculty-availability?faculty_id=${matchedAssignment.faculty_id}&subject_id=${matchedAssignment.subject_id}&semester=${semester || matchedAssignment.semester}&section=${section || matchedAssignment.section}`
      : null;

    return (
      <Card className="border border-red-200 dark:border-red-900 shadow-sm bg-white dark:bg-gray-950 overflow-hidden">
        <CardHeader className="border-b border-red-100 dark:border-red-900/70 bg-red-50 dark:bg-red-950/30">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <CardTitle className="flex items-center gap-3 text-red-900 dark:text-red-200">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/60">
                  <AlertTriangle className="h-5 w-5 text-red-700 dark:text-red-300" />
                </span>
                Timetable generation needs your attention
              </CardTitle>
              <p className="text-sm text-red-800 dark:text-red-300">
                The generator stopped because one assignment cannot be placed without violating faculty availability.
              </p>
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-sm font-medium text-red-700 dark:text-red-300 hover:underline"
              >
                Dismiss
              </button>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-5 pt-5">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/60 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                <BookOpen className="h-4 w-4" />
                Subject
              </div>
              <p className="font-semibold text-gray-950 dark:text-white">
                {compactConflict.subjectName || 'Not specified'}
              </p>
              {compactConflict.subjectCode && (
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{compactConflict.subjectCode}</p>
              )}
            </div>

            <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/60 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                <Users className="h-4 w-4" />
                Faculty
              </div>
              <p className="font-semibold text-gray-950 dark:text-white">
                {compactConflict.facultyName || 'Not assigned'}
              </p>
              {compactConflict.slotProgress && (
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  Failed while placing slot {compactConflict.slotProgress}
                </p>
              )}
            </div>

            <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50/70 dark:bg-red-950/30 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-red-600 dark:text-red-300">
                <CalendarClock className="h-4 w-4" />
                Main Issue
              </div>
              <p className="font-semibold text-red-950 dark:text-red-100">
                {compactConflict.reason}
              </p>
              {compactConflict.originalReason && compactConflict.originalReason !== compactConflict.reason && (
                <p className="mt-1 text-sm text-red-700 dark:text-red-300">{compactConflict.originalReason}</p>
              )}
            </div>
          </div>

          {(compactConflict.assignedSlots?.length > 0 || compactConflict.availability?.length > 0) && (
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-gray-200 dark:border-gray-800 p-4">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  Already placed
                </h3>
                {compactConflict.assignedSlots?.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {compactConflict.assignedSlots.map((slot, index) => (
                      <span
                        key={`${slot.day}-${slot.slot}-${index}`}
                        className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-800 ring-1 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:ring-emerald-900"
                      >
                        {DAY_LABELS[slot.day] || slot.day} slot {slot.slot}
                        {slot.time ? ` (${slot.time})` : ''}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No slots have been placed for this assignment yet.</p>
                )}
              </div>

              <div className="rounded-xl border border-gray-200 dark:border-gray-800 p-4">
                <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
                  <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  Faculty availability submitted
                </h3>
                {compactConflict.availability?.length > 0 ? (
                  <div className="space-y-2">
                    {compactConflict.availability.map((day) => (
                      <div key={day.day} className="flex flex-wrap items-center gap-2">
                        <span className="w-24 text-sm font-medium text-gray-700 dark:text-gray-300">
                          {DAY_LABELS[day.day] || day.day}
                        </span>
                        {day.slots.map((slot) => (
                          <span
                            key={`${day.day}-${slot}`}
                            className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-800 ring-1 ring-blue-200 dark:bg-blue-950/40 dark:text-blue-200 dark:ring-blue-900"
                          >
                            Slot {slot}
                          </span>
                        ))}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No availability was found for this faculty assignment.</p>
                )}
              </div>
            </div>
          )}

          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-amber-950 dark:text-amber-200">
              <Lightbulb className="h-4 w-4" />
              Recommended resolution
            </h3>
            <div className="space-y-2">
              {compactConflict.suggestions.map((suggestion, index) => (
                <div key={suggestion} className="flex gap-2 text-sm text-amber-900 dark:text-amber-100">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-200 text-xs font-bold text-amber-900 dark:bg-amber-900 dark:text-amber-100">
                    {index + 1}
                  </span>
                  <span>{suggestion}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 border-t border-gray-100 pt-4 dark:border-gray-800 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              After updating availability or assignments, run generation again for Semester {semester}, Section {section}.
            </p>
            <div className="flex flex-wrap gap-2">
              {availabilityHref && (
                <button
                  onClick={() => {
                    window.location.href = availabilityHref;
                  }}
                  className="inline-flex items-center gap-2 rounded-lg bg-gray-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-800 dark:bg-white dark:text-gray-950 dark:hover:bg-gray-200"
                >
                  Open Faculty Availability
                  <ExternalLink className="h-4 w-4" />
                </button>
              )}
              <button
                onClick={() => {
                  window.location.href = '/admin/assignments';
                }}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-800 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-900"
              >
                Review Assignments
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!isConflictReport) {
    // Not a conflict report, show as simple error
    return (
      <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
        <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0" />
        <p className="text-sm text-red-800 dark:text-red-300 whitespace-pre-wrap">{errorMessage}</p>
        {onDismiss && (
          <button onClick={onDismiss} className="text-red-600 hover:text-red-800 text-sm underline">
            Dismiss
          </button>
        )}
      </div>
    );
  }

  // Parse the message to extract slot-wise conflicts
  // Backend format:
  // 1. MON Slot 1 (09:00 - 09:50)
  //    Type: SINGLE_FACULTY
  //    Faculty Faculty_1234 available for: CS101, CS102
  //    Competing faculty: Faculty_1234
  //    Competing subjects: CS101, CS102
  const parseSlotConflicts = (message) => {
    const lines = message.split('\n');
    const suggestions = [];
    const slotConflicts = [];

    let inSuggestions = false;
    let currentSlot = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // Empty line or separator - end current slot
      if (!line || line.startsWith('=')) {
        if (currentSlot && currentSlot.faculty.length > 0) {
          slotConflicts.push(currentSlot);
        }
        currentSlot = null;
        continue;
      }

      if (line.includes('### SUGGESTIONS TO RESOLVE')) {
        if (currentSlot && currentSlot.faculty.length > 0) {
          slotConflicts.push(currentSlot);
        }
        currentSlot = null;
        inSuggestions = true;
        continue;
      }

      if (inSuggestions) {
        if (line.match(/^\d+\./)) {
          suggestions.push(line.replace(/^\d+\.\s*/, ''));
        } else if (line.startsWith('- ')) {
          suggestions.push(line.substring(2));
        } else if (line) {
          suggestions.push(line);
        }
        continue;
      }

      // Skip section headers
      if (line.startsWith('###')) {
        continue;
      }

      // Parse slot header: "1. MON Slot 1 (09:00 - 09:50)"
      const cleanedLine = line.replace(/^\d+\.\s*/, '');
      const slotMatch = cleanedLine.match(/^([A-Z]+)\s+Slot\s+(\d+)\s+\((.+)\)/);
      if (slotMatch) {
        // Save previous slot if exists
        if (currentSlot && currentSlot.faculty.length > 0) {
          slotConflicts.push(currentSlot);
        }

        currentSlot = {
          day: slotMatch[1],
          slot: slotMatch[2],
          timeRange: slotMatch[3],
          faculty: [],
          description: '',
          conflictType: ''
        };
        continue;
      }

      // Parse slot details
      if (currentSlot) {
        // Type line
        if (line.startsWith('Type:')) {
          currentSlot.conflictType = line.replace('Type:', '').trim();
        }
        // Description line with faculty info
        else if (line.includes('Faculty') || line.includes('available for:')) {
          currentSlot.description = line.replace(/^\d+\.\s*/, '').trim();
          // Extract faculty name from description
          const facultyMatch = line.match(/Faculty\s+(\S+)\s+available/);
          if (facultyMatch) {
            const facultyName = facultyMatch[1];
            // Extract subjects
            const subjectsMatch = line.match(/available for:\s*(.+)/);
            if (subjectsMatch) {
              const subjectsStr = subjectsMatch[1];
              const subjects = subjectsStr.split(',').map(s => {
                const parts = s.trim().split(/\s+/);
                const code = parts[0] || s.trim();
                return {
                  subject_code: code,
                  subject_name: code,
                  subject_type: 'THEORY' // Default, will be refined
                };
              });
              currentSlot.faculty.push({
                faculty_name: facultyName,
                subjects: subjects
              });
            }
          }
        }
        // Competing subjects line - parse to get subject types
        else if (line.startsWith('Competing subjects:')) {
          const subjectsStr = line.replace('Competing subjects:', '').trim();
          const subjectCodes = subjectsStr.split(',').map(s => s.trim());
          // Update existing faculty subjects with more info
          if (currentSlot.faculty.length > 0) {
            currentSlot.faculty[0].subjects = subjectCodes.map(code => ({
              subject_code: code,
              subject_name: code,
              subject_type: 'THEORY'
            }));
          }
        }
        // Competing faculty line
        else if (line.startsWith('Competing faculty:')) {
          const facultyStr = line.replace('Competing faculty:', '').trim();
          const facultyNames = facultyStr.split(',').map(f => f.trim());
          // Update faculty list if needed
          if (currentSlot.faculty.length === 0 && facultyNames.length > 0) {
            currentSlot.faculty = facultyNames.map(name => ({
              faculty_name: name,
              subjects: []
            }));
          }
        }
      }
    }

    // Don't forget the last slot
    if (currentSlot && currentSlot.faculty.length > 0) {
      slotConflicts.push(currentSlot);
    }

    return { slotConflicts, suggestions };
  };

  const { slotConflicts, suggestions } = parseSlotConflicts(errorMessage);

  // Group slots by day
  const groupedByDay = {};
  for (const slot of slotConflicts) {
    if (!groupedByDay[slot.day]) {
      groupedByDay[slot.day] = [];
    }
    groupedByDay[slot.day].push(slot);
  }

  // Day order
  const dayOrder = ['MON', 'TUE', 'WED', 'THU', 'FRI'];

  // Toggle day collapse
  const toggleDay = (day) => {
    setCollapsedDays(prev => ({
      ...prev,
      [day]: !prev[day]
    }));
  };

  return (
    <Card className="border-2 border-rose-200 dark:border-rose-900 shadow-lg bg-rose-50/50 dark:bg-rose-950/20">
      <CardHeader className="border-b bg-rose-100/50 dark:bg-rose-900/30">
        <CardTitle className="flex items-center gap-3 text-rose-800 dark:text-rose-300">
          <AlertTriangle className="h-6 w-6" />
          <span>Timetable Generation Failed - Slot-Wise Conflict Analysis</span>
        </CardTitle>
        <p className="text-sm text-rose-700 dark:text-rose-400 mt-1">
          Review faculty availability and subject assignments for each time slot below
        </p>
      </CardHeader>

      <CardContent className="pt-6">
        {/* Summary - Attempt information */}
        {errorMessage.includes('attempted') && (
          <div className="mb-6 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-900">
            <p className="text-sm text-blue-800 dark:text-blue-200">
              {errorMessage.split('\n').find(l => l.includes('attempted'))?.trim()}
            </p>
          </div>
        )}

        {/* Slot-wise conflicts organized by day */}
        <div className="space-y-4">
          {dayOrder.map(day => {
            if (!groupedByDay[day]) return null;

            const isCollapsed = collapsedDays[day];
            const daySlots = groupedByDay[day];

            return (
              <div key={day} className="border border-gray-300 dark:border-gray-700 rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleDay(day)}
                  className="w-full flex items-center justify-between p-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                    <span className="font-semibold text-gray-800 dark:text-gray-200">
                      {day} - {daySlots.length} Time Slot{daySlots.length > 1 ? 's' : ''}
                    </span>
                  </div>
                  {isCollapsed ? (
                    <ChevronDown className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                  ) : (
                    <ChevronUp className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                  )}
                </button>

                {!isCollapsed && (
                  <div className="p-3 space-y-2 bg-white dark:bg-gray-900">
                    {daySlots.map((slot, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                            Slot {slot.slot} ({slot.timeRange})
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-500">
                            {slot.description || ''}
                          </span>
                        </div>

                        {/* Faculty available at this slot */}
                        {slot.faculty && slot.faculty.length > 0 && (
                          <div className="space-y-2">
                            {slot.faculty.map((faculty, fIdx) => (
                              <div
                                key={fIdx}
                                className="p-2 rounded bg-white dark:bg-gray-900 border border-purple-200 dark:border-purple-900"
                              >
                                <div className="flex items-center gap-2 text-xs text-purple-700 dark:text-purple-300 font-medium mb-1">
                                  <Users className="h-3 w-3" />
                                  {faculty.faculty_name}
                                </div>
                                {faculty.subjects && faculty.subjects.length > 0 && (
                                  <div className="flex flex-wrap gap-1">
                                    {faculty.subjects.map((subject, sIdx) => (
                                      <span
                                        key={sIdx}
                                        className={`px-2 py-0.5 text-xs rounded ${
                                          subject.subject_type === 'LAB'
                                            ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                                            : 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                                        }`}
                                      >
                                        {subject.subject_code}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div className="mt-6 p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-900">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-800 dark:text-amber-300 mb-3">
              <Zap className="h-4 w-4" />
              Suggestions to Resolve
            </h3>
            <ul className="space-y-2">
              {suggestions.filter(s => s.trim()).map((suggestion, idx) => (
                <li key={idx} className="text-sm text-amber-900 dark:text-amber-200">
                  {suggestion}
                </li>
              ))}
            </ul>
          </div>
        )}

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
