import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { AlertTriangle, Users, Clock, MapPin } from 'lucide-react';

// Severity indicator
const SeverityBadge = ({ severity }) => {
  const config = {
    comfortable: { color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400', label: 'OK' },
    moderate: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', label: 'MODERATE' },
    tight: { color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400', label: 'TIGHT' },
    critical: { color: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400', label: 'CRITICAL' }
  };

  const style = config[severity?.toLowerCase()] || config.comfortable;

  return (
    <span className={`px-2 py-1 text-xs font-bold rounded ${style.color}`}>
      {style.label}
    </span>
  );
};

// Risk level indicator
const RiskIndicator = ({ level }) => {
  const colors = {
    low: 'bg-gray-400',
    medium: 'bg-amber-400',
    high: 'bg-orange-500',
    critical: 'bg-rose-500'
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs uppercase tracking-wider text-gray-500">Risk</span>
      <div className={`w-2 h-2 rounded-full ${colors[level?.toLowerCase()] || colors.low}`} />
      <span className="text-xs font-semibold uppercase">{level || 'LOW'}</span>
    </div>
  );
};

// Local warning card (faculty-specific)
const LocalWarningCard = ({ warning }) => (
  <div className="p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1 space-y-3">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Users className="h-5 w-5 text-blue-500 flex-shrink-0" />
          <div>
            <div className="font-semibold text-gray-900 dark:text-gray-100">{warning.subject_name}</div>
            <div className="text-sm text-gray-500">{warning.faculty_name}</div>
          </div>
        </div>

        {/* Metrics */}
        <div className="flex flex-wrap gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Constraint Score</span>
            <span className="font-mono font-bold text-gray-900 dark:text-gray-100">
              {warning.constraint_score?.toFixed(2) || 'N/A'}
            </span>
          </div>
          <SeverityBadge severity={warning.severity} />
          <RiskIndicator level={warning.risk_level} />
        </div>

        {/* Message */}
        <p className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-950 p-3 rounded border-l-2 border-blue-500">
          {warning.message}
        </p>

        {/* Suggestion */}
        {warning.suggestion && (
          <div className="flex items-start gap-2 text-xs">
            <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
            <span className="text-gray-600 dark:text-gray-400">{warning.suggestion}</span>
          </div>
        )}
      </div>
    </div>
  </div>
);

// Global warning card (section-wide bottleneck)
const GlobalWarningCard = ({ warning }) => (
  <div className="p-4 bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-950/20 dark:to-red-950/20 border border-orange-200 dark:border-orange-900 rounded-lg">
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1 space-y-2">
        {/* Header */}
        <div className="flex items-center gap-3">
          <MapPin className="h-5 w-5 text-orange-500 flex-shrink-0" />
          <div>
            <div className="font-mono text-lg font-bold text-gray-900 dark:text-gray-100">
              {warning.time_range}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Slot {warning.slot_number}</div>
          </div>
        </div>

        {/* Competition info */}
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-gray-500" />
            <span className="text-gray-600 dark:text-gray-400">
              {warning.competing_subjects?.length || 0} subjects competing
            </span>
          </div>
          <div className="px-2 py-1 bg-white dark:bg-gray-900 rounded border border-orange-200 dark:border-orange-900">
            <span className="text-xs font-mono">
              Supply/Demand: {(warning.supply_demand_ratio || 0).toFixed(2)}
            </span>
          </div>
          <RiskIndicator level={warning.risk_level} />
        </div>

        {/* Message */}
        <p className="text-sm text-gray-700 dark:text-gray-300 font-medium">
          {warning.message}
        </p>

        {/* Competing subjects list */}
        {warning.competing_subjects && warning.competing_subjects.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {warning.competing_subjects.map((subject, i) => (
              <span
                key={i}
                className="px-2 py-1 text-xs bg-white dark:bg-gray-900 border border-orange-200 dark:border-orange-900 rounded"
              >
                {subject}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  </div>
);

// Main warnings panel
export function WarningsPanel({ warnings }) {
  if (!warnings) return null;
  const hasLocal = warnings.local && warnings.local.length > 0;
  const hasGlobal = warnings.global && warnings.global.length > 0;

  if (!hasLocal && !hasGlobal) return null;

  return (
    <Card className="border-2 shadow-lg">
      <CardHeader className="border-b bg-amber-50/30 dark:bg-amber-950/10">
        <CardTitle className="flex items-center gap-3">
          <AlertTriangle className="h-6 w-6 text-amber-500" />
          <span>Warnings & Bottlenecks</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-6 pt-6">
        {/* Global warnings (bottlenecks) */}
        {hasGlobal && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-orange-500" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
                Section-Wide Bottlenecks ({warnings.global.length})
              </h3>
            </div>
            <div className="space-y-3">
              {warnings.global.map((warning, i) => (
                <GlobalWarningCard key={i} warning={warning} />
              ))}
            </div>
          </div>
        )}

        {/* Local warnings (faculty-specific) */}
        {hasLocal && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
                Faculty-Specific Issues ({warnings.local.length})
              </h3>
            </div>
            <div className="space-y-3">
              {warnings.local.map((warning, i) => (
                <LocalWarningCard key={i} warning={warning} />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
