import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input, Label } from '../components/ui/input';
import { FileUp, Download, Search, Filter, FolderOpen } from 'lucide-react';
import { materialService } from '../services/materials';
import { getUser } from '../lib/api';

export default function MaterialsPage() {
  const user = getUser();
  const [materials, setMaterials] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadData, setUploadData] = useState({
    title: '',
    description: '',
    subject_id: '',
    semester: user?.semester || 1,
    sections: [],
    tags: [],
  });

  // Fetch materials
  const fetchMaterials = async () => {
    setLoading(true);
    try {
      const params = {};
      if (searchQuery) params.query = searchQuery;
      const data = await materialService.list(params);
      setMaterials(data.materials || []);
    } catch (err) {
      // Error handled silently
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMaterials();
  }, [searchQuery]);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setUploadData(prev => ({ ...prev, title: file.name.split('.')[0] }));
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('metadata', JSON.stringify({
        ...uploadData,
        faculty_id: user?.id,
      }));

      await materialService.upload(formData);
      alert('Material uploaded successfully!');
      setSelectedFile(null);
      setUploadData({
        title: '',
        description: '',
        subject_id: '',
        semester: user?.semester || 1,
        sections: [],
        tags: [],
      });
      fetchMaterials();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = (material) => {
    materialService.download(material.id);
  };

  const handleDelete = async (materialId) => {
    if (!confirm('Are you sure you want to delete this material?')) return;

    try {
      await materialService.delete(materialId);
      fetchMaterials();
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  const getFileIcon = (fileName) => {
    const ext = fileName.split('.').pop().toLowerCase();
    const icons = {
      pdf: '📄',
      doc: '📝',
      docx: '📝',
      ppt: '📊',
      pptx: '📊',
      zip: '📦',
      rar: '📦',
      txt: '📃',
    };
    return icons[ext] || '📄';
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Study Materials</h1>
          <p className="text-muted-foreground">
            Access lecture notes, assignments, and resources
          </p>
        </div>
        {user?.role === 'faculty' && (
          <Button onClick={() => document.getElementById('upload-section').scrollIntoView({ behavior: 'smooth' })}>
            <FileUp className="h-4 w-4 mr-2" />
            Upload Material
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="flex items-center space-x-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search materials..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Upload Section (Faculty only) */}
      {user?.role === 'faculty' && (
        <Card id="upload-section">
          <CardHeader>
            <CardTitle>Upload Material</CardTitle>
            <CardDescription>
              Share lecture notes, assignments, or other resources with students
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>File</Label>
                <div className="flex items-center space-x-2">
                  <Input
                    type="file"
                    onChange={handleFileSelect}
                    accept=".pdf,.doc,.docx,.ppt,.pptx,.zip"
                    disabled={uploading}
                    className="flex-1"
                  />
                </div>
                {selectedFile && (
                  <p className="text-sm text-muted-foreground">
                    Selected: {selectedFile.name} ({formatFileSize(selectedFile.size)})
                </p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Title</Label>
                <Input
                  placeholder="Lecture notes title"
                  value={uploadData.title}
                  onChange={(e) => setUploadData({ ...uploadData, title: e.target.value })}
                  disabled={uploading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Description</Label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder="Brief description of the material..."
                value={uploadData.description}
                onChange={(e) => setUploadData({ ...uploadData, description: e.target.value })}
                disabled={uploading}
              />
            </div>

            <Button onClick={handleUpload} disabled={uploading || !selectedFile} className="w-full">
              {uploading ? 'Uploading...' : 'Upload Material'}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Materials List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {materials.map((material) => (
          <Card key={material.id} className="hover:shadow-md transition-shadow">
            <CardContent className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{getFileIcon(material.file_name)}</span>
                  <div>
                    <h3 className="font-semibold leading-tight">{material.title}</h3>
                    <p className="text-sm text-muted-foreground">{material.subject_id}</p>
                  </div>
                </div>
              </div>

              {material.description && (
                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                  {material.description}
                </p>
              )}

              <div className="flex items-center justify-between text-xs text-muted-foreground mb-4">
                <span>{material.file_name}</span>
                <span>{material.file_size_mb} MB</span>
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleDownload(material)}
                  className="flex-1"
                >
                  <Download className="h-3 w-3 mr-1" />
                  Download
                </Button>
                {user?.role === 'faculty' && (
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleDelete(material.id)}
                  >
                    Delete
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {materials.length === 0 && !loading && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground text-center">
              {searchQuery ? 'No materials found matching your search.' : 'No study materials available yet.'}
            </p>
          </CardContent>
        </Card>
      )}

      {loading && (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      )}
    </div>
  );
}
