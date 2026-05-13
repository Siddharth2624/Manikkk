import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input, Label } from '../components/ui/input';
import {
  BookOpen,
  CalendarDays,
  ExternalLink,
  FileUp,
  FolderOpen,
  Link as LinkIcon,
  Loader2,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import { materialService } from '../services/materials';
import { getUser } from '../lib/api';

const today = () => new Date().toISOString().slice(0, 10);

const formatDate = (value) => {
  if (!value) return 'No date';
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
};

const buildSubjectKey = (item) => `${item.subject_id}-${item.semester}`;

export default function MaterialsPage() {
  const user = getUser();
  const [materials, setMaterials] = useState([]);
  const [subjectOptions, setSubjectOptions] = useState([]);
  const [selectedSubjectKey, setSelectedSubjectKey] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingSubjects, setLoadingSubjects] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showAddMaterial, setShowAddMaterial] = useState(false);
  const [error, setError] = useState(null);
  const [uploadData, setUploadData] = useState({
    title: '',
    description: '',
    material_url: '',
    material_date: today(),
    subject_key: '',
    sections: [],
  });

  const selectedSubject = subjectOptions.find((item) => buildSubjectKey(item) === selectedSubjectKey);
  const selectedUploadSubject = subjectOptions.find((item) => buildSubjectKey(item) === uploadData.subject_key);

  const fetchSubjects = async () => {
    setLoadingSubjects(true);
    try {
      const data = await materialService.subjects();
      const options = data.subjects || [];
      setSubjectOptions(options);
      if (options.length > 0) {
        const firstKey = buildSubjectKey(options[0]);
        setUploadData((prev) => ({
          ...prev,
          subject_key: prev.subject_key || firstKey,
          sections: prev.sections.length > 0 ? prev.sections : options[0].sections || [],
        }));
      }
    } catch (err) {
      setError(err.message || 'Failed to load subjects');
    } finally {
      setLoadingSubjects(false);
    }
  };

  const fetchMaterials = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (searchQuery.trim()) params.query = searchQuery.trim();
      if (selectedSubject) {
        params.subject_id = selectedSubject.subject_id;
        params.semester = selectedSubject.semester;
      }
      const data = await materialService.list(params);
      setMaterials(data.materials || []);
    } catch (err) {
      setError(err.message || 'Failed to load materials');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubjects();
  }, []);

  useEffect(() => {
    fetchMaterials();
  }, [searchQuery, selectedSubjectKey]);

  const handleUploadSubjectChange = (subjectKey) => {
    const option = subjectOptions.find((item) => buildSubjectKey(item) === subjectKey);
    setUploadData((prev) => ({
      ...prev,
      subject_key: subjectKey,
      sections: option?.sections || [],
    }));
  };

  const toggleSection = (section) => {
    setUploadData((prev) => {
      const exists = prev.sections.includes(section);
      return {
        ...prev,
        sections: exists
          ? prev.sections.filter((item) => item !== section)
          : [...prev.sections, section],
      };
    });
  };

  const handleCreateMaterial = async () => {
    if (!selectedUploadSubject) {
      setError('Please select a subject');
      return;
    }

    if (!uploadData.title.trim() || !uploadData.material_url.trim() || !uploadData.material_date) {
      setError('Please provide title, material link, and date');
      return;
    }

    if ((selectedUploadSubject.sections || []).length > 0 && uploadData.sections.length === 0) {
      setError('Please select at least one section');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await materialService.create({
        title: uploadData.title.trim(),
        description: uploadData.description.trim() || null,
        material_url: uploadData.material_url.trim(),
        material_date: uploadData.material_date,
        subject_id: selectedUploadSubject.subject_id,
        semester: selectedUploadSubject.semester,
        sections: uploadData.sections,
      });

      setUploadData({
        title: '',
        description: '',
        material_url: '',
        material_date: today(),
        subject_key: uploadData.subject_key,
        sections: selectedUploadSubject.sections || [],
      });
      setShowAddMaterial(false);
      await fetchMaterials();
    } catch (err) {
      setError(err.message || 'Failed to save material link');
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenMaterial = async (material) => {
    const linkWindow = window.open('', '_blank');
    try {
      const data = await materialService.open(material.id);
      if (linkWindow) {
        linkWindow.location.href = data.material_url;
      } else {
        window.open(data.material_url, '_blank', 'noopener,noreferrer');
      }
      fetchMaterials();
    } catch (err) {
      if (linkWindow) linkWindow.close();
      setError(err.message || 'Failed to open material');
    }
  };

  const handleDelete = async (materialId) => {
    if (!confirm('Are you sure you want to delete this material?')) return;

    try {
      await materialService.delete(materialId);
      fetchMaterials();
    } catch (err) {
      setError(err.message || 'Delete failed');
    }
  };

  const groupedMaterials = useMemo(() => {
    return materials.reduce((groups, material) => {
      const dateKey = material.material_date || 'undated';
      if (!groups[dateKey]) groups[dateKey] = [];
      groups[dateKey].push(material);
      return groups;
    }, {});
  }, [materials]);

  const sortedDateGroups = Object.entries(groupedMaterials).sort(([a], [b]) => b.localeCompare(a));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Study Materials</h1>
          <p className="text-muted-foreground">
            Subject-wise links organized by class date
          </p>
        </div>
        {user?.role === 'faculty' && (
          <Button onClick={() => setShowAddMaterial(true)}>
            <FileUp className="mr-2 h-4 w-4" />
            Add Material Link
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
          {error}
        </div>
      )}

      <Card>
        <CardContent className="p-4">
          <div className="grid gap-3 md:grid-cols-[minmax(220px,280px)_1fr]">
            <div className="space-y-2">
              <Label>Subject</Label>
              <select
                value={selectedSubjectKey}
                onChange={(event) => setSelectedSubjectKey(event.target.value)}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                disabled={loadingSubjects}
              >
                <option value="">All subjects</option>
                {subjectOptions.map((item) => (
                  <option key={buildSubjectKey(item)} value={buildSubjectKey(item)}>
                    {item.subject?.code} - {item.subject?.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by title or description..."
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {user?.role === 'faculty' && showAddMaterial && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="max-h-[90vh] w-full max-w-2xl overflow-y-auto">
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle>Add Material Link</CardTitle>
                  <CardDescription>
                    Select one of your assigned subjects and save a day-wise Drive/material link.
                  </CardDescription>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAddMaterial(false)}
                  disabled={submitting}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Subject</Label>
                  <select
                    value={uploadData.subject_key}
                    onChange={(event) => handleUploadSubjectChange(event.target.value)}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    disabled={submitting || loadingSubjects}
                  >
                    <option value="">Select subject...</option>
                    {subjectOptions.map((item) => (
                      <option key={buildSubjectKey(item)} value={buildSubjectKey(item)}>
                        {item.subject?.code} - {item.subject?.name} (Sem {item.semester})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label>Material Date</Label>
                  <Input
                    type="date"
                    value={uploadData.material_date}
                    onChange={(event) => setUploadData({ ...uploadData, material_date: event.target.value })}
                    disabled={submitting}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input
                    placeholder="Example: Lecture 5 - Normalization"
                    value={uploadData.title}
                    onChange={(event) => setUploadData({ ...uploadData, title: event.target.value })}
                    disabled={submitting}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Drive / Material Link</Label>
                  <div className="relative">
                    <LinkIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      type="url"
                      placeholder="https://drive.google.com/..."
                      value={uploadData.material_url}
                      onChange={(event) => setUploadData({ ...uploadData, material_url: event.target.value })}
                      disabled={submitting}
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              {selectedUploadSubject?.sections?.length > 0 && (
                <div className="space-y-2">
                  <Label>Visible To Sections</Label>
                  <div className="flex flex-wrap gap-2">
                    {selectedUploadSubject.sections.map((section) => (
                      <button
                        key={section}
                        type="button"
                        onClick={() => toggleSection(section)}
                        disabled={submitting}
                        className={`rounded-full border px-3 py-1 text-sm transition-colors ${
                          uploadData.sections.includes(section)
                            ? 'border-violet-500 bg-violet-50 text-violet-700 dark:bg-violet-900/20 dark:text-violet-300'
                            : 'border-gray-200 text-muted-foreground dark:border-gray-800'
                        }`}
                      >
                        Section {section}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label>Description <span className="text-xs text-muted-foreground">(optional)</span></Label>
                <textarea
                  className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="Short note for students..."
                  value={uploadData.description}
                  onChange={(event) => setUploadData({ ...uploadData, description: event.target.value })}
                  disabled={submitting}
                />
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleCreateMaterial}
                  disabled={submitting || !uploadData.subject_key}
                  className="flex-1"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Material Link'
                  )}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowAddMaterial(false)}
                  disabled={submitting}
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
        </div>
      ) : sortedDateGroups.length > 0 ? (
        <Card className="border-gray-200 dark:border-gray-800">
          <CardHeader>
            <CardTitle>Materials List</CardTitle>
            <CardDescription>
              {materials.length} material link(s) {selectedSubject ? `for ${selectedSubject.subject?.code}` : 'available'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-5">
              {sortedDateGroups.map(([dateKey, dateMaterials]) => (
                <section key={dateKey} className="space-y-2">
                  <div className="flex items-center gap-2 px-1">
                    <CalendarDays className="h-4 w-4 text-violet-600" />
                    <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                      {formatDate(dateKey)}
                    </h2>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                      {dateMaterials.length}
                    </span>
                  </div>

                  <div className="space-y-2">
                    {dateMaterials.map((material) => (
                      <div
                        key={material.id}
                        className="flex flex-col gap-4 rounded-lg border border-gray-200 p-4 transition-all hover:border-violet-300 hover:bg-gray-50 dark:border-gray-800 dark:hover:border-violet-700 dark:hover:bg-gray-900/50 lg:flex-row lg:items-center lg:justify-between"
                      >
                        <div className="flex min-w-0 items-start gap-4">
                          <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-lg bg-violet-50 text-violet-600 dark:bg-violet-900/20 dark:text-violet-300">
                            <LinkIcon className="h-5 w-5" />
                          </div>

                          <div className="min-w-0 space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h3 className="font-medium text-gray-900 dark:text-white">
                                {material.title}
                              </h3>
                              <span className="inline-flex items-center gap-1 rounded-full bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700 dark:bg-violet-900/20 dark:text-violet-300">
                                <BookOpen className="h-3 w-3" />
                                {material.subject?.code || 'Subject'}
                              </span>
                            </div>

                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {material.subject?.name || material.subject_id}
                            </p>

                            {material.description && (
                              <p className="max-w-3xl text-sm text-muted-foreground">
                                {material.description}
                              </p>
                            )}

                            <div className="text-xs text-gray-500 dark:text-gray-400">
                              Faculty: {material.faculty_name || 'Faculty'}
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-shrink-0 items-center gap-2 lg:justify-end">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleOpenMaterial(material)}
                          >
                            <ExternalLink className="mr-1 h-3.5 w-3.5" />
                            Open Link
                          </Button>
                          {user?.role === 'faculty' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDelete(material.id)}
                              className="text-red-600 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-900/20"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FolderOpen className="mb-4 h-12 w-12 text-muted-foreground" />
            <p className="text-center text-muted-foreground">
              {searchQuery ? 'No materials found matching your search.' : 'No study materials available yet.'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
