import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input, Label } from '../components/ui/input';
import { ArrowLeft, Loader2, Sparkles, Download } from 'lucide-react';
import { api } from '../lib/api';
import {
  FeasibilityReport,
  WarningsPanel,
  ConstraintScoresPanel,
  SuggestionsPanel
} from '../components/feasibility';

export default function FeasibilityAnalysisPage() {
  const navigate = useNavigate();

  const [semester, setSemester] = useState(1);
  const [section, setSection] = useState('A');
  const [analyzing, setAnalyzing] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);

  // Run analysis
  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    setReport(null);

    try {
      const response = await api('/timetable/analyze', {
        method: 'POST',
        body: JSON.stringify({ semester, section }),
      });
      setReport(response);
    } catch (err) {
      // Check if it's a feasibility error (response has report data)
      if (err.message && err.message.includes('cannot generate')) {
        // The error might be from FeasibilityError
        // Try to parse the error response
        try {
          const errorData = JSON.parse(err.message);
          if (errorData.status === 'fail') {
            setReport(errorData);
            return;
          }
        } catch {
          // Not parseable as report, show error message
        }
      }
      setError(err.message || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  // Proceed to generation
  const handleProceed = () => {
    navigate('/admin/timetable', { state: { semester, section } });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      {/* Animated background pattern */}
      <div className="fixed inset-0 opacity-[0.03] dark:opacity-[0.01] pointer-events-none">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(90deg, #000 1px, transparent 1px),
            linear-gradient(#000 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>

      <div className="relative max-w-5xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(-1)}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            <div>
              <h1 className="text-4xl font-black tracking-tight bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                Feasibility Analysis
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Pre-generation constraint validation and optimization insights
              </p>
            </div>
          </div>
        </div>

        {/* Controls */}
        <Card className="border-2 shadow-lg bg-white/80 dark:bg-gray-900/80 backdrop-blur">
          <CardContent className="pt-6">
            <div className="flex flex-wrap items-end gap-6">
              <div className="space-y-2">
                <Label htmlFor="semester">Semester</Label>
                <select
                  id="semester"
                  value={semester}
                  onChange={(e) => setSemester(Number(e.target.value))}
                  className="px-4 py-2 border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-950 font-mono font-bold focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                    <option key={s} value={s}>Semester {s}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="section">Section</Label>
                <select
                  id="section"
                  value={section}
                  onChange={(e) => setSection(e.target.value)}
                  className="px-4 py-2 border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-950 font-mono font-bold focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                >
                  {['A', 'B', 'C', 'D', 'E', 'F'].map(s => (
                    <option key={s} value={s}>Section {s}</option>
                  ))}
                </select>
              </div>

              <Button
                onClick={handleAnalyze}
                disabled={analyzing}
                size="lg"
                className="gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-5 w-5" />
                    Analyze Feasibility
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Error */}
        {error && (
          <div className="p-4 bg-rose-50 dark:bg-rose-950/30 border-2 border-rose-200 dark:border-rose-900 rounded-lg">
            <p className="text-rose-800 dark:text-rose-300 font-medium">{error}</p>
          </div>
        )}

        {/* Report */}
        {report && (
          <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
            {/* Main report with confidence */}
            <FeasibilityReport
              report={report}
              onDismiss={report.status !== 'fail' ? handleProceed : undefined}
            />

            {/* Constraint scores */}
            {report.constraint_scores && Object.keys(report.constraint_scores).length > 0 && (
              <ConstraintScoresPanel constraintScores={report.constraint_scores} />
            )}

            {/* Warnings */}
            {report.warnings && (
              <WarningsPanel warnings={report.warnings} />
            )}

            {/* Suggestions */}
            {report.suggestions && report.suggestions.length > 0 && (
              <SuggestionsPanel suggestions={report.suggestions} />
            )}

            {/* Telemetry snapshot (for debugging) */}
            {report.telemetry_snapshot && (
              <Card className="border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/50">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-500">
                      Analysis completed at {new Date(report.telemetry_snapshot.analysis_timestamp).toLocaleString()}
                    </div>
                    <Button variant="outline" size="sm" className="gap-2">
                      <Download className="h-4 w-4" />
                      Export Report
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Empty state */}
        {!report && !analyzing && !error && (
          <div className="text-center py-20">
            <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/30 dark:to-purple-900/30 flex items-center justify-center">
              <Sparkles className="h-12 w-12 text-indigo-600 dark:text-indigo-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Ready to Analyze
            </h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
              Select a semester and section to run feasibility analysis before generating the timetable.
              This helps identify potential conflicts and optimization opportunities.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Import Card component
import { Card, CardContent } from '../components/ui/card';
import { Label } from '../components/ui/input';
