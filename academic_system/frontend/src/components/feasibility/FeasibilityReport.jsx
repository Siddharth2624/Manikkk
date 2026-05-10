import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { CheckCircle, AlertTriangle, XCircle, Activity } from 'lucide-react';

// Status badge component with distinctive styling
const StatusBadge = ({ status }) => {
  const config = {
    pass: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/30',
      border: 'border-emerald-200 dark:border-emerald-800',
      text: 'text-emerald-700 dark:text-emerald-400',
      icon: CheckCircle,
      label: 'FEASIBLE'
    },
    warning: {
      bg: 'bg-amber-50 dark:bg-amber-950/30',
      border: 'border-amber-200 dark:border-amber-800',
      text: 'text-amber-700 dark:text-amber-400',
      icon: AlertTriangle,
      label: 'CAUTION'
    },
    fail: {
      bg: 'bg-rose-50 dark:bg-rose-950/30',
      border: 'border-rose-200 dark:border-rose-800',
      text: 'text-rose-700 dark:text-rose-400',
      icon: XCircle,
      label: 'NOT FEASIBLE'
    }
  };

  const style = config[status?.toLowerCase()] || config.pass;
  const Icon = style.icon;

  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border-2 ${style.bg} ${style.border} ${style.text} font-mono font-bold tracking-wider`}>
      <Icon className="h-5 w-5" />
      <span>{style.label}</span>
    </div>
  );
};

// Confidence meter with circular progress
const ConfidenceMeter = ({ score, recoverability }) => {
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  const getColor = (score) => {
    if (score >= 80) return '#10b981';
    if (score >= 50) return '#f59e0b';
    return '#ef4444';
  };

  const getRecoverabilityColor = (r) => {
    switch (r?.toLowerCase()) {
      case 'recoverable': return 'text-emerald-600 dark:text-emerald-400';
      case 'difficult': return 'text-amber-600 dark:text-amber-400';
      case 'near_impossible': return 'text-rose-600 dark:text-rose-400';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="flex items-center gap-6">
      {/* Circular progress */}
      <div className="relative w-36 h-36">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          {/* Background circle */}
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-gray-200 dark:text-gray-800"
          />
          {/* Progress circle */}
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={getColor(score)}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-black tabular-nums">{score}</span>
          <span className="text-xs text-gray-500 font-medium">CONFIDENCE</span>
        </div>
      </div>

      {/* Recoverability indicator */}
      <div className="flex flex-col gap-2">
        <div className="text-xs text-gray-500 uppercase tracking-widest font-medium">Generation Difficulty</div>
        <div className={`text-xl font-bold uppercase tracking-wider ${getRecoverabilityColor(recoverability)}`}>
          {recoverability?.replace('_', ' ') || 'UNKNOWN'}
        </div>
      </div>
    </div>
  );
};

// Error list display
const ErrorList = ({ errors }) => {
  if (!errors || errors.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-semibold text-rose-600 dark:text-rose-400 uppercase tracking-wider">
        <XCircle className="h-4 w-4" />
        <span>Blocking Issues ({errors.length})</span>
      </div>
      {errors.map((error, i) => (
        <div
          key={i}
          className="flex items-start gap-3 p-3 bg-rose-50 dark:bg-rose-950/20 border-l-4 border-rose-500 rounded"
        >
          <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-rose-100 dark:bg-rose-900/50 text-rose-600 dark:text-rose-400 text-xs font-bold rounded">
            {i + 1}
          </span>
          <p className="text-sm text-rose-800 dark:text-rose-300">{error}</p>
        </div>
      ))}
    </div>
  );
};

// Main report card
export function FeasibilityReport({ report, onDismiss }) {
  if (!report) return null;

  return (
    <Card className="border-2 shadow-lg overflow-hidden">
      {/* Header with status */}
      <CardHeader className={`border-b ${report.status === 'fail' ? 'bg-rose-50/50 dark:bg-rose-950/10' : report.status === 'warning' ? 'bg-amber-50/50 dark:bg-amber-950/10' : 'bg-emerald-50/50 dark:bg-emerald-950/10'}`}>
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <CardTitle className="text-2xl">Feasibility Analysis</CardTitle>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Pre-generation constraint analysis completed
            </p>
          </div>
          <StatusBadge status={report.status} />
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-6">
        {/* Confidence & Recoverability */}
        <ConfidenceMeter
          score={report.confidence_score || 0}
          recoverability={report.recoverability}
        />

        {/* Errors */}
        <ErrorList errors={report.errors} />

        {/* Action buttons */}
        {onDismiss && report.status !== 'fail' && (
          <div className="flex gap-3 pt-4 border-t">
            <button
              onClick={onDismiss}
              className="flex-1 px-4 py-3 bg-gray-900 hover:bg-gray-800 text-white font-semibold rounded-lg transition-colors"
            >
              Proceed with Generation
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
