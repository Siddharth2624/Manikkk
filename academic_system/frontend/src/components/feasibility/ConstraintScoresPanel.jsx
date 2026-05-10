import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { BarChart3, TrendingUp, TrendingDown } from 'lucide-react';

// Visual score bar with severity coloring
const ScoreBar = ({ score, severity }) => {
  const percentage = Math.min(score * 100, 100);
  const colors = {
    comfortable: 'bg-emerald-500',
    moderate: 'bg-blue-500',
    tight: 'bg-amber-500',
    critical: 'bg-rose-500'
  };

  return (
    <div className="space-y-1">
      <div className="h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${colors[severity]} transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="flex justify-between text-xs">
        <span className="text-gray-500">Utilization</span>
        <span className="font-mono font-semibold">{(score * 100).toFixed(1)}%</span>
      </div>
    </div>
  );
};

// Severity badge
const SeverityBadge = ({ severity }) => {
  const config = {
    comfortable: { bg: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400', label: 'Comfortable' },
    moderate: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', label: 'Moderate' },
    tight: { color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', label: 'Tight' },
    critical: { color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400', label: 'Critical' }
  };

  const style = config[severity?.toLowerCase()] || config.comfortable;

  return (
    <span className={`px-2 py-1 text-xs font-bold rounded ${style.color}`}>
      {style.label}
    </span>
  );
};

// Constraint score row
const ConstraintScoreRow = ({ subjectId, score }) => (
  <div className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg hover:shadow-md transition-all">
    <div className="flex items-start gap-4">
      {/* Status icon */}
      <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${
        score.is_tightly_constrained
          ? 'bg-amber-100 dark:bg-amber-900/30'
          : 'bg-emerald-100 dark:bg-emerald-900/30'
      }`}>
        {score.is_tightly_constrained ? (
          <TrendingUp className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        ) : (
          <TrendingDown className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100">{score.subject_name}</h4>
            <p className="text-sm text-gray-500">{score.faculty_name}</p>
          </div>
          <SeverityBadge severity={score.severity} />
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-xs text-gray-500">Required</span>
            <span className="ml-2 font-mono font-bold">{score.required_slots} slots</span>
          </div>
          <div>
            <span className="text-xs text-gray-500">Available</span>
            <span className="ml-2 font-mono font-bold">{score.unique_available_slots} opportunities</span>
          </div>
        </div>

        {/* Score bar */}
        <ScoreBar score={score.score} severity={score.severity} />

        {/* Consecutive pairs (for labs) */}
        {score.consecutive_pairs_available !== undefined && (
          <div className="text-xs text-gray-500">
            Consecutive lab pairs available: <span className="font-mono font-semibold">{score.consecutive_pairs_available}</span>
          </div>
        )}
      </div>
    </div>
  </div>
);

// Summary stats
const SummaryStats = ({ scores }) => {
  const scoreArray = Object.values(scores);
  const critical = scoreArray.filter(s => s.severity === 'critical').length;
  const tight = scoreArray.filter(s => s.severity === 'tight').length;
  const moderate = scoreArray.filter(s => s.severity === 'moderate').length;
  const comfortable = scoreArray.filter(s => s.severity === 'comfortable').length;

  return (
    <div className="grid grid-cols-4 gap-3">
      <div className="text-center p-3 bg-rose-50 dark:bg-rose-950/20 rounded-lg border border-rose-200 dark:border-rose-900">
        <div className="text-2xl font-black text-rose-600 dark:text-rose-400">{critical}</div>
        <div className="text-xs text-rose-700 dark:text-rose-400 uppercase tracking-wider font-medium">Critical</div>
      </div>
      <div className="text-center p-3 bg-amber-50 dark:bg-amber-950/20 rounded-lg border border-amber-200 dark:border-amber-900">
        <div className="text-2xl font-black text-amber-600 dark:text-amber-400">{tight}</div>
        <div className="text-xs text-amber-700 dark:text-amber-400 uppercase tracking-wider font-medium">Tight</div>
      </div>
      <div className="text-center p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-900">
        <div className="text-2xl font-black text-blue-600 dark:text-blue-400">{moderate}</div>
        <div className="text-xs text-blue-700 dark:text-blue-400 uppercase tracking-wider font-medium">Moderate</div>
      </div>
      <div className="text-center p-3 bg-emerald-50 dark:bg-emerald-950/20 rounded-lg border border-emerald-200 dark:border-emerald-900">
        <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">{comfortable}</div>
        <div className="text-xs text-emerald-700 dark:text-emerald-400 uppercase tracking-wider font-medium">OK</div>
      </div>
    </div>
  );
};

// Main constraint scores panel
export function ConstraintScoresPanel({ constraintScores }) {
  if (!constraintScores || Object.keys(constraintScores).length === 0) return null;

  return (
    <Card className="border-2 shadow-lg">
      <CardHeader className="border-b bg-gray-50/50 dark:bg-gray-900/50">
        <CardTitle className="flex items-center gap-3">
          <BarChart3 className="h-6 w-6 text-gray-700 dark:text-gray-300" />
          <span>Constraint Analysis</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6 pt-6">
        {/* Summary stats */}
        <SummaryStats scores={constraintScores} />

        {/* Detailed scores */}
        <div className="space-y-3">
          {Object.entries(constraintScores)
            .sort(([, a], [, b]) => b.score - a.score) // Sort by score descending
            .map(([subjectId, score]) => (
              <ConstraintScoreRow key={subjectId} subjectId={subjectId} score={score} />
            ))}
        </div>
      </CardContent>
    </Card>
  );
}
