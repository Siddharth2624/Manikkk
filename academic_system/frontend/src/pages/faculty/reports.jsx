import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Select } from '../../components/ui/select';
import { FileText, Loader2, Users, UserCheck, UserX, AlertCircle, Search, BookOpen, Download } from 'lucide-react';
import { facultyAssignmentService } from '../../services/facultyAssignment';
import { attendanceService } from '../../services/attendance';
import { getUser } from '../../lib/api';
import { cn } from '../../lib/utils';

const ACADEMIC_YEAR = '2024-2025';
const THRESHOLD_PERCENTAGE = 75;

function getAssignmentSubject(assignment) {
  const subject = assignment.subject || {};
  return {
    ...subject,
    id: subject.id || assignment.subject_id,
    name: subject.name || assignment.subject_name || 'Unknown Subject',
    code: subject.code || assignment.subject_code || 'N/A',
  };
}

function getAssignmentKey(assignment) {
  const subject = getAssignmentSubject(assignment);
  return `${subject.id}-${assignment.semester}-${assignment.section}`;
}

function normalizeStudents(reportData) {
  if (Array.isArray(reportData?.students)) {
    return reportData.students;
  }

  return (reportData?.attendance || []).map((row) => ({
    student_id: row.student?.id,
    student_name: row.student?.name || 'Unknown Student',
    roll_number: row.student?.roll_number || 'N/A',
    total_classes: row.summary?.total || 0,
    present: row.summary?.present || 0,
    absent: row.summary?.absent || 0,
    percentage: row.summary?.percentage || 0,
    is_below_threshold: row.summary?.is_below_threshold || false,
  }));
}

function calculateStats(students) {
  const totalStudents = students.length;
  const present = students.reduce((sum, student) => sum + (student.present || 0), 0);
  const absent = students.reduce((sum, student) => sum + (student.absent || 0), 0);
  const totalClasses = students.reduce((sum, student) => sum + (student.total_classes || 0), 0);
  const belowThreshold = students.filter(
    (student) => (student.total_classes || 0) > 0 && (student.percentage || 0) < THRESHOLD_PERCENTAGE
  ).length;
  const percentage = totalClasses > 0 ? Math.round((present / totalClasses) * 100) : 0;

  return { totalStudents, present, absent, totalClasses, belowThreshold, percentage };
}

const CRC_TABLE = (() => {
  const table = [];
  for (let i = 0; i < 256; i += 1) {
    let value = i;
    for (let j = 0; j < 8; j += 1) {
      value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    }
    table[i] = value >>> 0;
  }
  return table;
})();

function escapeXml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function sanitizeFileName(value) {
  return String(value || 'attendance-report')
    .replace(/[^a-z0-9._-]+/gi, '_')
    .replace(/^_+|_+$/g, '') || 'attendance-report';
}

function getColumnName(index) {
  let name = '';
  let current = index + 1;

  while (current > 0) {
    const remainder = (current - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    current = Math.floor((current - 1) / 26);
  }

  return name;
}

function getCrc32(bytes) {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i += 1) {
    crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function createZip(files) {
  const encoder = new TextEncoder();
  const localChunks = [];
  const centralChunks = [];
  const records = [];
  let offset = 0;

  files.forEach((file) => {
    const nameBytes = encoder.encode(file.name);
    const dataBytes = encoder.encode(file.content);
    const crc = getCrc32(dataBytes);
    const header = new Uint8Array(30 + nameBytes.length);
    const view = new DataView(header.buffer);

    view.setUint32(0, 0x04034b50, true);
    view.setUint16(4, 20, true);
    view.setUint16(6, 0x0800, true);
    view.setUint16(8, 0, true);
    view.setUint16(10, 0, true);
    view.setUint16(12, 0, true);
    view.setUint32(14, crc, true);
    view.setUint32(18, dataBytes.length, true);
    view.setUint32(22, dataBytes.length, true);
    view.setUint16(26, nameBytes.length, true);
    view.setUint16(28, 0, true);
    header.set(nameBytes, 30);

    localChunks.push(header, dataBytes);
    records.push({
      nameBytes,
      crc,
      size: dataBytes.length,
      offset,
    });
    offset += header.length + dataBytes.length;
  });

  const centralOffset = offset;
  let centralSize = 0;

  records.forEach((record) => {
    const header = new Uint8Array(46 + record.nameBytes.length);
    const view = new DataView(header.buffer);

    view.setUint32(0, 0x02014b50, true);
    view.setUint16(4, 20, true);
    view.setUint16(6, 20, true);
    view.setUint16(8, 0x0800, true);
    view.setUint16(10, 0, true);
    view.setUint16(12, 0, true);
    view.setUint16(14, 0, true);
    view.setUint32(16, record.crc, true);
    view.setUint32(20, record.size, true);
    view.setUint32(24, record.size, true);
    view.setUint16(28, record.nameBytes.length, true);
    view.setUint16(30, 0, true);
    view.setUint16(32, 0, true);
    view.setUint16(34, 0, true);
    view.setUint16(36, 0, true);
    view.setUint32(38, 0, true);
    view.setUint32(42, record.offset, true);
    header.set(record.nameBytes, 46);

    centralChunks.push(header);
    centralSize += header.length;
  });

  const end = new Uint8Array(22);
  const endView = new DataView(end.buffer);
  endView.setUint32(0, 0x06054b50, true);
  endView.setUint16(8, records.length, true);
  endView.setUint16(10, records.length, true);
  endView.setUint32(12, centralSize, true);
  endView.setUint32(16, centralOffset, true);

  return new Blob([...localChunks, ...centralChunks, end], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
}

function buildWorksheetXml(rows) {
  const sheetRows = rows.map((row, rowIndex) => {
    const rowNumber = rowIndex + 1;
    const cells = row.map((cell, columnIndex) => {
      const cellData = typeof cell === 'object' && cell !== null ? cell : { value: cell };
      const reference = `${getColumnName(columnIndex)}${rowNumber}`;
      const style = cellData.style ?? 2;

      if (typeof cellData.value === 'number' && Number.isFinite(cellData.value)) {
        return `<c r="${reference}" s="${style}"><v>${cellData.value}</v></c>`;
      }

      return `<c r="${reference}" t="inlineStr" s="${style}"><is><t>${escapeXml(cellData.value)}</t></is></c>`;
    }).join('');

    return `<row r="${rowNumber}">${cells}</row>`;
  }).join('');

  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <cols>
    <col min="1" max="1" width="8" customWidth="1"/>
    <col min="2" max="2" width="18" customWidth="1"/>
    <col min="3" max="3" width="30" customWidth="1"/>
    <col min="4" max="8" width="16" customWidth="1"/>
  </cols>
  <sheetData>${sheetRows}</sheetData>
</worksheet>`;
}

function createAttendanceWorkbook(rows) {
  return createZip([
    {
      name: '[Content_Types].xml',
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>`,
    },
    {
      name: '_rels/.rels',
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>`,
    },
    {
      name: 'xl/workbook.xml',
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Attendance" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>`,
    },
    {
      name: 'xl/_rels/workbook.xml.rels',
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>`,
    },
    {
      name: 'xl/styles.xml',
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE8EEF8"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color auto="1"/></left>
      <right style="thin"><color auto="1"/></right>
      <top style="thin"><color auto="1"/></top>
      <bottom style="thin"><color auto="1"/></bottom>
      <diagonal/>
    </border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" applyFont="1" applyFill="1" applyBorder="1"/>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" applyBorder="1"/>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
  <dxfs count="0"/>
  <tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/>
</styleSheet>`,
    },
    {
      name: 'xl/worksheets/sheet1.xml',
      content: buildWorksheetXml(rows),
    },
  ]);
}

export default function FacultyReportsPage() {
  const navigate = useNavigate();
  const user = getUser();

  const [assignments, setAssignments] = useState([]);
  const [selectedKey, setSelectedKey] = useState('');
  const [report, setReport] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user || user.role !== 'faculty') {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  useEffect(() => {
    fetchAssignments();
  }, []);

  const fetchAssignments = async () => {
    setLoading(true);
    setError(null);
    setReport(null);

    try {
      const data = await facultyAssignmentService.getMySubjects();
      const assignedSubjects = Array.isArray(data) ? data : data.assignments || [];
      setAssignments(assignedSubjects);
      setSelectedKey(assignedSubjects.length > 0 ? getAssignmentKey(assignedSubjects[0]) : '');
    } catch (err) {
      console.error('Failed to fetch assigned subjects:', err);
      setError(err.message || 'Failed to load assigned subjects');
      setAssignments([]);
      setSelectedKey('');
    } finally {
      setLoading(false);
    }
  };

  const selectedAssignment = useMemo(
    () => assignments.find((assignment) => getAssignmentKey(assignment) === selectedKey),
    [assignments, selectedKey]
  );

  useEffect(() => {
    if (!selectedAssignment) {
      setReport(null);
      return;
    }

    fetchSelectedReport(selectedAssignment);
  }, [selectedAssignment]);

  const fetchSelectedReport = async (assignment) => {
    const subject = getAssignmentSubject(assignment);
    setReportLoading(true);
    setError(null);
    setSearchQuery('');

    try {
      const reportData = await attendanceService.getReport(subject.id, {
        semester: assignment.semester,
        section: assignment.section,
        academic_year: ACADEMIC_YEAR,
      });
      const students = normalizeStudents(reportData).sort((a, b) =>
        (a.student_name || '').localeCompare(b.student_name || '')
      );

      setReport({
        key: getAssignmentKey(assignment),
        subject: reportData.subject || subject,
        semester: assignment.semester,
        section: assignment.section,
        students,
        stats: calculateStats(students),
        error: null,
      });
    } catch (err) {
      console.error('Failed to fetch attendance report:', err);
      setReport({
        key: getAssignmentKey(assignment),
        subject,
        semester: assignment.semester,
        section: assignment.section,
        students: [],
        stats: calculateStats([]),
        error: err.message || 'Failed to load report',
      });
    } finally {
      setReportLoading(false);
    }
  };

  const filteredStudents = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!report?.students) return [];
    if (!query) return report.students;

    return report.students.filter((student) =>
      student.student_name?.toLowerCase().includes(query) ||
      student.roll_number?.toLowerCase().includes(query)
    );
  }, [report, searchQuery]);

  const downloadSelectedReport = () => {
    if (!report || report.error) return;

    const subjectName = report.subject?.name || 'Unknown Subject';
    const subjectCode = report.subject?.code || 'N/A';
    const generatedAt = new Date().toLocaleString();
    const workbookRows = [
      [{ value: 'Attendance Report', style: 1 }],
      [{ value: 'Subject', style: 1 }, `${subjectName} (${subjectCode})`],
      [{ value: 'Semester', style: 1 }, report.semester],
      [{ value: 'Section', style: 1 }, report.section],
      [{ value: 'Generated At', style: 1 }, generatedAt],
      [],
      [
        { value: 'S.No', style: 1 },
        { value: 'Roll Number', style: 1 },
        { value: 'Student Name', style: 1 },
        { value: 'Total Classes', style: 1 },
        { value: 'Present', style: 1 },
        { value: 'Absent', style: 1 },
        { value: 'Attendance %', style: 1 },
        { value: 'Status', style: 1 },
      ],
      ...report.students.map((student, index) => {
        const hasClasses = (student.total_classes || 0) > 0;
        const isLow = hasClasses && (student.percentage || 0) < THRESHOLD_PERCENTAGE;
        const status = !hasClasses ? 'No classes' : isLow ? 'Below 75%' : 'Good';

        return [
          index + 1,
          student.roll_number || 'N/A',
          student.student_name || 'Unknown Student',
          student.total_classes || 0,
          student.present || 0,
          student.absent || 0,
          hasClasses ? `${student.percentage || 0}%` : 'No classes',
          status,
        ];
      }),
    ];

    const blob = createAttendanceWorkbook(workbookRows);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${sanitizeFileName(`${subjectCode}_Sem${report.semester}_Section${report.section}_Attendance`)}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Attendance Reports</h1>
        <p className="text-muted-foreground">
          Select one assigned subject to view and download its student attendance
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600 dark:text-red-400" />
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

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
          <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
            <Card>
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground mb-1">Assigned Subjects</p>
                <p className="text-2xl font-bold">{assignments.length}</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                  <div className="w-full space-y-2">
                    <label className="text-sm font-medium">Select Subject</label>
                    <Select
                      value={selectedKey}
                      onChange={(event) => setSelectedKey(event.target.value)}
                    >
                      {assignments.map((assignment) => {
                        const subject = getAssignmentSubject(assignment);
                        return (
                          <option key={getAssignmentKey(assignment)} value={getAssignmentKey(assignment)}>
                            {subject.code} - {subject.name} | Sem {assignment.semester}, Sec {assignment.section}
                          </option>
                        );
                      })}
                    </Select>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={downloadSelectedReport}
                    disabled={!report || reportLoading || Boolean(report.error)}
                    className="gap-2 md:w-auto"
                  >
                    <Download className="h-4 w-4" />
                    Download Excel
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {reportLoading ? (
            <Card>
              <CardContent className="flex items-center justify-center py-16">
                <Loader2 className="h-7 w-7 animate-spin text-violet-600" />
                <span className="ml-3 text-sm text-muted-foreground">Loading selected subject report...</span>
              </CardContent>
            </Card>
          ) : !report ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">Select a subject to view its attendance report.</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="overflow-hidden">
              <CardHeader className="border-b bg-gray-50/70 dark:bg-gray-900/50">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="flex items-start gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
                      <BookOpen className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle>
                        {report.subject?.name || 'Unknown Subject'}
                      </CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {report.subject?.code || 'N/A'} - Semester {report.semester}, Section {report.section}
                      </p>
                    </div>
                  </div>

                  {!report.error && (
                    <div className="w-full sm:w-56">
                      <MiniStat label="Total Students" value={report.stats.totalStudents} />
                    </div>
                  )}
                </div>
              </CardHeader>

              <CardContent className="p-0">
                {report.error ? (
                  <div className="flex items-center gap-2 p-4 text-sm text-red-700 dark:text-red-300">
                    <AlertCircle className="h-4 w-4" />
                    {report.error}
                  </div>
                ) : (
                  <>
                    <div className="border-b p-4">
                      <div className="relative">
                        <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                        <input
                          type="text"
                          placeholder="Search by student name or roll number..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="flex h-10 w-full rounded-md border border-input bg-background pl-10 pr-3 py-2 text-sm"
                        />
                      </div>
                    </div>

                    {report.students.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-10">
                        <Users className="h-10 w-10 text-muted-foreground mb-3" />
                        <p className="text-muted-foreground">
                          No students found for Semester {report.semester}, Section {report.section}.
                        </p>
                      </div>
                    ) : filteredStudents.length === 0 ? (
                      <div className="flex flex-col items-center justify-center py-10">
                        <Search className="h-10 w-10 text-muted-foreground mb-3" />
                        <p className="text-muted-foreground">No students match "{searchQuery}".</p>
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full">
                          <thead className="bg-white dark:bg-gray-950">
                            <tr className="border-b">
                              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-muted-foreground">Student</th>
                              <th className="px-4 py-3 text-center text-xs font-medium uppercase text-muted-foreground">Total</th>
                              <th className="px-4 py-3 text-center text-xs font-medium uppercase text-muted-foreground">Present</th>
                              <th className="px-4 py-3 text-center text-xs font-medium uppercase text-muted-foreground">Absent</th>
                              <th className="px-4 py-3 text-center text-xs font-medium uppercase text-muted-foreground">Attendance</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                            {filteredStudents.map((student) => {
                              const hasClasses = (student.total_classes || 0) > 0;
                              const isLow = hasClasses && (student.percentage || 0) < THRESHOLD_PERCENTAGE;

                              return (
                                <tr
                                  key={`${report.key}-${student.student_id || student.roll_number || student.student_name}`}
                                  className="hover:bg-gray-50 dark:hover:bg-gray-900/60"
                                >
                                  <td className="px-4 py-3">
                                    <div>
                                      <p className="font-medium">{student.student_name || 'Unknown Student'}</p>
                                      <p className="text-xs text-muted-foreground">{student.roll_number || 'N/A'}</p>
                                    </div>
                                  </td>
                                  <td className="px-4 py-3 text-center text-sm">{student.total_classes || 0}</td>
                                  <td className="px-4 py-3 text-center">
                                    <CountBadge icon={UserCheck} value={student.present || 0} tone="green" />
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <CountBadge icon={UserX} value={student.absent || 0} tone="red" />
                                  </td>
                                  <td className="px-4 py-3 text-center">
                                    <span
                                      className={cn(
                                        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold',
                                        !hasClasses && 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
                                        hasClasses && !isLow && 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
                                        isLow && 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                                      )}
                                    >
                                      {hasClasses ? `${student.percentage || 0}%` : 'No classes'}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function MiniStat({ label, value, tone = 'gray' }) {
  const toneClass = {
    gray: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
    green: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    red: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  }[tone];

  return (
    <div className={cn('rounded-lg px-3 py-2 text-center', toneClass)}>
      <p className="text-xs font-medium opacity-80">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

function CountBadge({ icon: Icon, value, tone }) {
  const toneClass = tone === 'green'
    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300';

  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium', toneClass)}>
      <Icon className="h-3 w-3" />
      {value}
    </span>
  );
}
