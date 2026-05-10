import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { AlertTriangle, Clock, Users, BookOpen, Zap, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

/**
 * Display slot-wise conflict report for failed timetable generation.
 *
 * Shows for each time slot (day + time):
 * - Which faculty are available
 * - What subjects each faculty teaches
 * - Highlights multiple faculty competing for same slot
 */
export function TimetableConflictReport({ errorMessage, onDismiss }) {
  const [collapsedDays, setCollapsedDays] = useState({});

  if (!errorMessage) {
    return null;
  }

  // Check if this is a detailed conflict report
  const isConflictReport = errorMessage.includes('CONFLICT ANALYSIS REPORT');

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
