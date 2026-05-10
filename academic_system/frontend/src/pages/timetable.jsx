import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { timetableService } from '../services/timetable';
import { getUser } from '../lib/api';
import { Clock, Loader2, Edit } from 'lucide-react';

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

const DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY'];
const DAY_SHORT = ['MON', 'TUE', 'WED', 'THU', 'FRI'];

export default function TimetablePage() {
  const navigate = useNavigate();
  const user = getUser();
  const [timetable, setTimetable] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentSemester, setCurrentSemester] = useState(user?.semester || 1);
  const [currentSection, setCurrentSection] = useState(user?.section || 'A');

  const fetchTimetable = async () => {
    setLoading(true);
    try {
      const data = await timetableService.getTimetable(currentSemester, currentSection);
      console.log('Timetable data:', data);
      setTimetable(data);
    } catch (err) {
      console.error('Failed to fetch timetable:', err);
      setTimetable(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimetable();
  }, [currentSemester, currentSection]);

  const getSlotContent = (dayIndex, slot) => {
    if (!timetable?.schedule) return null;

    const dayData = timetable.schedule[dayIndex];
    if (!dayData) return null;

    const slotData = dayData.slots?.[slot - 1];
    if (!slotData) return null;

    // Check for lunch break (marked by room="LUNCH")
    if (slotData.room === 'LUNCH') {
      return {
        isLunch: true,
        label: 'Lunch Break'
      };
    }

    if (!slotData.subject_id) return null;

    // Backend returns enriched data with subject and faculty embedded in slot
    return {
      subject: slotData.subject?.name || slotData.subject_id,
      faculty: slotData.faculty?.name || '',
      room: slotData.room || 'TBA'
    };
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Timetable</h1>
          <p className="text-muted-foreground">
            View your class schedule
          </p>
        </div>

        {/* Semester/Section Selector */}
        <div className="flex items-center space-x-4">
          <select
            value={currentSemester}
            onChange={(e) => setCurrentSemester(parseInt(e.target.value))}
            className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
              <option key={sem} value={sem}>
                Semester {sem}
              </option>
            ))}
          </select>

          <select
            value={currentSection}
            onChange={(e) => setCurrentSection(e.target.value)}
            className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {['A', 'B'].map((sec) => (
              <option key={sec} value={sec}>
                Section {sec}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Timetable Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
        </div>
      ) : timetable?.schedule ? (
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center justify-between">
              <span>Semester {currentSemester} - Section {currentSection}</span>
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-muted-foreground" />
                {user?.role === 'admin' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigate(`/admin/timetable/edit?semester=${currentSemester}&section=${currentSection}&year=2024-2025`)}
                    className="gap-1"
                  >
                    <Edit className="h-4 w-4" />
                    Edit
                  </Button>
                )}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b">
                    <th className="p-3 text-left text-sm font-medium text-muted-foreground">Day</th>
                    {TIME_SLOTS.map((slot) => (
                      <th key={slot.slot} className="p-3 text-center text-sm font-medium">
                        {slot.time}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {DAYS.map((day, dayIndex) => (
                    <tr key={day} className="border-b">
                      <td className="p-3 text-sm font-semibold text-muted-foreground whitespace-nowrap">
                        {DAY_SHORT[dayIndex]}
                      </td>
                      {TIME_SLOTS.map((slot) => {
                        const content = getSlotContent(dayIndex, slot.slot);

                        return (
                          <td key={slot.slot} className="p-2">
                            {content ? (
                              content.isLunch ? (
                                <div className="p-3 rounded-lg text-center text-sm font-medium bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                                  <div className="font-semibold text-amber-800 dark:text-amber-200">
                                    {content.label}
                                  </div>
                                </div>
                              ) : (
                                <div className="p-3 rounded-lg text-center text-sm font-medium border bg-violet-50 dark:bg-violet-900/20 border-violet-200 dark:border-violet-800 hover:scale-105 transition-transform">
                                  <div className="font-semibold text-violet-900 dark:text-violet-100">
                                    {content.subject}
                                  </div>
                                  {content.faculty && (
                                    <div className="text-xs text-violet-700 dark:text-violet-300 mt-1">
                                      {content.faculty}
                                    </div>
                                  )}
                                  {content.room && (
                                    <div className="text-xs text-muted-foreground mt-1">
                                      Room: {content.room}
                                    </div>
                                  )}
                                </div>
                              )
                            ) : (
                              <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-center text-gray-400 dark:text-gray-600 text-sm">
                                Free
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Clock className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground text-center">
              No timetable generated for Semester {currentSemester} - Section {currentSection} yet.
            </p>
            {user?.role === 'admin' && (
              <Button className="mt-4" onClick={() => navigate('/admin/timetable')}>
                Generate Timetable
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
