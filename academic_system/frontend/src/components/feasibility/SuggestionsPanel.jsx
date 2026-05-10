import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Lightbulb, Plus, Clock, Minus } from 'lucide-react';

// Suggestion type icons
const SuggestionIcon = ({ type }) => {
  const icons = {
    add_slots: Plus,
    diversify_slots: Minus,
    add_afternoon: Clock,
    add_consecutive: Plus,
    avoid_lunch: Minus
  };

  const Icon = icons[type] || Lightbulb;
  return <Icon className="h-5 w-5" />;
};

// Priority badge
const PriorityBadge = ({ priority }) => {
  const config = {
    low: { bg: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400', label: 'Low' },
    medium: { bg: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', label: 'Medium' },
    high: { bg: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400', label: 'High' }
  };

  const style = config[priority?.toLowerCase()] || config.low;

  return (
    <span className={`px-2 py-1 text-xs font-bold rounded ${style.bg}`}>
      {style.label} Priority
    </span>
  );
};

// Suggestion card
const SuggestionCard = ({ suggestion }) => (
  <div className="group p-4 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-950/20 dark:to-purple-950/20 border border-indigo-100 dark:border-indigo-900 rounded-lg hover:shadow-lg transition-all">
    <div className="flex items-start gap-4">
      {/* Icon */}
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 group-hover:scale-110 transition-transform">
        <SuggestionIcon type={suggestion.suggestion_type} />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="font-semibold text-gray-900 dark:text-gray-100">
              {suggestion.message}
            </div>
            {suggestion.target_subject_id && (
              <div className="text-xs text-gray-500 mt-1">
                For: {suggestion.target_subject_id}
              </div>
            )}
          </div>
          <PriorityBadge priority={suggestion.priority} />
        </div>

        {/* Expected impact */}
        {suggestion.expected_impact && (
          <div className="flex items-center gap-2 text-xs text-indigo-700 dark:text-indigo-400 bg-indigo-100/50 dark:bg-indigo-900/30 px-3 py-2 rounded-full max-w-fit">
            <Lightbulb className="h-3 w-3" />
            <span className="font-medium">{suggestion.expected_impact}</span>
          </div>
        )}
      </div>
    </div>
  </div>
);

// Group suggestions by type
const groupSuggestions = (suggestions) => {
  const groups = {
    add_slots: [],
    diversify_slots: [],
    add_afternoon: [],
    add_consecutive: [],
    avoid_lunch: [],
    other: []
  };

  suggestions.forEach(s => {
    const type = s.suggestion_type || 'other';
    if (groups[type]) {
      groups[type].push(s);
    } else {
      groups.other.push(s);
    }
  });

  return groups;
};

// Main suggestions panel
export function SuggestionsPanel({ suggestions }) {
  if (!suggestions || suggestions.length === 0) return null;

  const groups = groupSuggestions(suggestions);
  const totalCount = suggestions.length;
  const highPriorityCount = suggestions.filter(s => s.priority === 'high').length;

  return (
    <Card className="border-2 border-indigo-200 dark:border-indigo-900 shadow-lg bg-gradient-to-br from-indigo-50/50 to-purple-50/50 dark:from-indigo-950/10 dark:to-purple-950/10">
      <CardHeader className="border-b bg-indigo-100/50 dark:bg-indigo-900/20">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Lightbulb className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
            <span>Recommendations</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">{totalCount} suggestions</span>
            {highPriorityCount > 0 && (
              <span className="px-2 py-1 text-xs bg-rose-500 text-white rounded-full font-bold">
                {highPriorityCount} urgent
              </span>
            )}
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4 pt-6">
        {/* High priority first */}
        {groups.add_slots.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Add Available Slots
            </h4>
            {groups.add_slots.map((s, i) => (
              <SuggestionCard key={i} suggestion={s} />
            ))}
          </div>
        )}

        {groups.diversify_slots.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <Minus className="h-4 w-4" />
              Diversify Slot Selection
            </h4>
            {groups.diversify_slots.map((s, i) => (
              <SuggestionCard key={i} suggestion={s} />
            ))}
          </div>
        )}

        {groups.add_afternoon.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Add Afternoon Availability
            </h4>
            {groups.add_afternoon.map((s, i) => (
              <SuggestionCard key={i} suggestion={s} />
            ))}
          </div>
        )}

        {/* Other suggestions */}
        {groups.other.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
              Other Recommendations
            </h4>
            {groups.other.map((s, i) => (
              <SuggestionCard key={i} suggestion={s} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
