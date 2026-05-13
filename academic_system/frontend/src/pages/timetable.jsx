import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { timetableService } from '../services/timetable';
import { getUser } from '../lib/api';
import { Clock, Loader2, Edit, FileDown } from 'lucide-react';

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

const escapeHtml = (value = '') =>
  String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  })[char]);

const getSlotContentFromTimetable = (timetableData, dayIndex, slot) => {
  if (!timetableData?.schedule) return null;

  const dayData =
    timetableData.schedule[dayIndex] ||
    timetableData.schedule.find((day) => day.day === DAY_SHORT[dayIndex] || day.day === DAYS[dayIndex]);
  if (!dayData) return null;

  const slotData = dayData.slots?.find((item) => item.slot === slot) || dayData.slots?.[slot - 1];
  if (!slotData) return null;

  if (slotData.room === 'LUNCH') {
    return {
      isLunch: true,
      label: 'Lunch Break'
    };
  }

  if (!slotData.subject_id) return null;

  return {
    subject: slotData.subject?.name || slotData.subject_id,
    faculty: slotData.faculty?.name || ''
  };
};

const buildTimetableTableHtml = (timetableData) => {
  const headerCells = TIME_SLOTS.map((slot) => `<th>${escapeHtml(slot.time)}</th>`).join('');
  const bodyRows = DAYS.map((day, dayIndex) => {
    const cells = TIME_SLOTS.map((slot) => {
      const content = getSlotContentFromTimetable(timetableData, dayIndex, slot.slot);

      if (content?.isLunch) {
        return '<td><div class="cell lunch">Lunch Break</div></td>';
      }

      if (content) {
        return `
          <td>
            <div class="cell class-cell">
              <strong>${escapeHtml(content.subject)}</strong>
              ${content.faculty ? `<span>${escapeHtml(content.faculty)}</span>` : ''}
            </div>
          </td>
        `;
      }

      return '<td><div class="cell free">Free</div></td>';
    }).join('');

    return `<tr><th class="day-cell">${escapeHtml(DAY_SHORT[dayIndex] || day)}</th>${cells}</tr>`;
  }).join('');

  return `
    <table>
      <thead>
        <tr>
          <th class="day-cell">Day</th>
          ${headerCells}
        </tr>
      </thead>
      <tbody>
        ${bodyRows}
      </tbody>
    </table>
  `;
};

const buildTimetableSectionHtml = (timetableData) => {
  const title = `Semester ${timetableData.semester} - Section ${timetableData.section}`;
  return `
    <section class="timetable-section">
      <h2>${escapeHtml(title)}</h2>
      ${buildTimetableTableHtml(timetableData)}
    </section>
  `;
};

const createPrintWindow = () => {
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('Please allow popups to download the timetable PDF.');
    return null;
  }

  printWindow.document.write(`
    <!doctype html>
    <html>
      <head>
        <title>Preparing PDF</title>
        <style>
          body {
            align-items: center;
            color: #111827;
            display: flex;
            font-family: "Segoe UI", Arial, sans-serif;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
          }
        </style>
      </head>
      <body>
        Preparing timetable PDF...
      </body>
    </html>
  `);
  printWindow.document.close();
  return printWindow;
};

const writePrintDocument = (printWindow, { title, subtitle, sectionsHtml }) => {
  printWindow.document.open();
  printWindow.document.write(`
    <!doctype html>
    <html>
      <head>
        <title>${escapeHtml(title)}</title>
        <style>
          @page {
            size: landscape;
            margin: 12mm;
          }

          * {
            box-sizing: border-box;
          }

          body {
            color: #111827;
            font-family: "Segoe UI", Arial, sans-serif;
            margin: 0;
          }

          .header {
            border-bottom: 2px solid #111827;
            margin-bottom: 18px;
            padding-bottom: 10px;
          }

          h1 {
            font-size: 24px;
            margin: 0 0 4px;
          }

          h2 {
            font-size: 18px;
            margin: 0 0 12px;
          }

          p {
            color: #4b5563;
            font-size: 13px;
            margin: 0;
          }

          table {
            border-collapse: collapse;
            table-layout: fixed;
            width: 100%;
          }

          th,
          td {
            border: 1px solid #d1d5db;
            padding: 7px;
            text-align: center;
            vertical-align: middle;
          }

          th {
            background: #f3f4f6;
            font-size: 11px;
            font-weight: 700;
          }

          .day-cell {
            width: 58px;
          }

          .cell {
            align-items: center;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            gap: 3px;
            justify-content: center;
            min-height: 58px;
            padding: 7px;
          }

          .class-cell {
            background: #f5f3ff;
            border: 1px solid #c4b5fd;
            color: #3b0764;
          }

          .class-cell strong {
            font-size: 12px;
            line-height: 1.25;
          }

          .class-cell span {
            color: #6d28d9;
            font-size: 10px;
            line-height: 1.25;
          }

          .lunch {
            background: #fffbeb;
            border: 1px solid #fbbf24;
            color: #92400e;
            font-size: 12px;
            font-weight: 700;
          }

          .free {
            background: #f9fafb;
            color: #9ca3af;
            font-size: 12px;
          }

          .timetable-section {
            break-after: page;
            page-break-after: always;
          }

          .timetable-section:last-child {
            break-after: auto;
            page-break-after: auto;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>${escapeHtml(title)}</h1>
          <p>${escapeHtml(subtitle)}</p>
        </div>
        ${sectionsHtml}
      </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.focus();
  window.setTimeout(() => printWindow.print(), 250);
};

export default function TimetablePage() {
  const navigate = useNavigate();
  const user = getUser();
  const [timetable, setTimetable] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloadingAll, setDownloadingAll] = useState(false);
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
    return getSlotContentFromTimetable(timetable, dayIndex, slot);
  };

  const handleDownloadPdf = () => {
    if (!timetable?.schedule) return;

    const title = `Semester ${currentSemester} - Section ${currentSection} Timetable`;
    const printWindow = createPrintWindow();
    if (!printWindow) return;

    writePrintDocument(printWindow, {
      title,
      subtitle: 'Generated from Academic System',
      sectionsHtml: buildTimetableSectionHtml({
        ...timetable,
        semester: currentSemester,
        section: currentSection
      })
    });
  };

  const handleDownloadAllPdf = async () => {
    if (downloadingAll) return;

    const printWindow = createPrintWindow();
    if (!printWindow) return;

    setDownloadingAll(true);
    try {
      const response = await timetableService.listTimetables();
      const timetableItems = (response.timetables || [])
        .slice()
        .sort((a, b) => a.semester - b.semester || a.section.localeCompare(b.section));

      if (timetableItems.length === 0) {
        printWindow.close();
        alert('No generated timetables found.');
        return;
      }

      const loadedTimetables = await Promise.all(
        timetableItems.map(async (item) => {
          try {
            const data = await timetableService.getTimetable(item.semester, item.section);
            return {
              ...data,
              semester: item.semester,
              section: item.section,
            };
          } catch (err) {
            if (err.status === 401) throw err;
            console.error(`Failed to load timetable for semester ${item.semester}, section ${item.section}:`, err);
            return null;
          }
        })
      );

      const printableTimetables = loadedTimetables.filter((item) => item?.schedule);
      if (printableTimetables.length === 0) {
        printWindow.close();
        alert('No printable timetables found.');
        return;
      }

      writePrintDocument(printWindow, {
        title: 'All Semester Timetables',
        subtitle: `${printableTimetables.length} timetable(s) generated from Academic System`,
        sectionsHtml: printableTimetables.map(buildTimetableSectionHtml).join('')
      });
    } catch (err) {
      printWindow.close();
      if (err.status !== 401) {
        alert(err.message || 'Failed to prepare all timetables PDF.');
      }
    } finally {
      setDownloadingAll(false);
    }
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
        <div className="flex flex-wrap items-center gap-3">
          {user?.role === 'admin' && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleDownloadAllPdf}
              disabled={downloadingAll}
              className="gap-1"
            >
              {downloadingAll ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileDown className="h-4 w-4" />
              )}
              All Semesters PDF
            </Button>
          )}

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
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleDownloadPdf}
                  className="gap-1"
                >
                  <FileDown className="h-4 w-4" />
                  Download PDF
                </Button>
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
