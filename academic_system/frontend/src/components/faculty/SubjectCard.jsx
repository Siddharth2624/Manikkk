import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { ChevronDown, ChevronUp, Clock, Users, BookOpen, Check, X, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { SlotGrid } from '../shared/SlotGrid';

export function SubjectCard({
  subject,
  semester,
  section,
  initialSlots = [],
  onSave,
  readonly = false,
  minSlotsOverride,
}) {
  const [expanded, setExpanded] = useState(false);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [savedSlots, setSavedSlots] = useState([]); // Tracks last successfully saved slots
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const loadingRef = useRef(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const subjectId = subject?.id || subject?._id;
  const subjectCredits = subject?.credits || 3;
  const minSlots = minSlotsOverride ?? subjectCredits;

  // Initialize savedSlots when initialSlots changes (on load)
  useEffect(() => {
    if (initialSlots && initialSlots.length > 0 && !loaded) {
      setSavedSlots([...initialSlots]);
    }
  }, [initialSlots, loaded]);

  useEffect(() => {
    if (!expanded && !readonly) {
      setAvailableSlots([]);
      setLoaded(false);
      setError(null);
      setSuccess(false);
    }
  }, [expanded, readonly]);

  const handleToggleSlot = useCallback((slotKey) => {
    if (readonly) return;

    setAvailableSlots((prev) => {
      const exists = prev.includes(slotKey);
      if (exists) {
        // Allow unchecking freely - validate only on save
        return prev.filter((s) => s !== slotKey);
      } else {
        setError(null);
        return [...prev, slotKey];
      }
    });
  }, [readonly]);

  const loadSlots = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;

    try {
      if (!subjectId) {
        throw new Error('Subject ID is missing. Please refresh the page.');
      }

      setSaving(true);
      const slots = await onSave(subjectId, semester, section, null);
      if (slots) {
        setAvailableSlots(slots);
        setSavedSlots([...slots]); // Also update savedSlots when loading from backend
      } else {
        setAvailableSlots(initialSlots);
        setSavedSlots([...initialSlots]);
      }
      setLoaded(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
      loadingRef.current = false;
    }
  }, [subjectId, semester, section, initialSlots, onSave]);

  const handleExpand = useCallback(async () => {
    setExpanded((prev) => !prev);
    if (!expanded && !readonly && !loaded) {
      await loadSlots();
    }
  }, [expanded, readonly, loaded, loadSlots]);

  const handleSave = useCallback(async () => {
    if (availableSlots.length < minSlots) {
      setError(`Minimum ${minSlots} slots required`);
      setTimeout(() => setError(null), 3000);
      return;
    }

    try {
      if (!subjectId) {
        throw new Error('Subject ID is missing. Please refresh the page.');
      }

      setSaving(true);
      await onSave(subjectId, semester, section, availableSlots);
      // Update savedSlots after successful save
      setSavedSlots([...availableSlots]);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 3000);
    } finally {
      setSaving(false);
    }
  }, [availableSlots, minSlots, subjectId, semester, section, onSave]);

  const hasChanges = useMemo(() => {
    const sortedSaved = [...savedSlots].sort();
    const sortedCurrent = [...availableSlots].sort();
    if (sortedSaved.length !== sortedCurrent.length) return true;
    return sortedSaved.some((slot, i) => slot !== sortedCurrent[i]);
  }, [savedSlots, availableSlots]);

  const isValid = availableSlots.length >= minSlots;

  return (
    <div
      className={cn(
        'border rounded-lg overflow-hidden transition-all duration-200',
        'bg-white dark:bg-gray-950',
        expanded ? 'border-violet-200 dark:border-violet-800 shadow-sm' : 'border-gray-200 dark:border-gray-800',
        readonly && 'opacity-75'
      )}
    >
      <div
        className={cn(
          'flex items-center justify-between p-4 cursor-pointer transition-colors',
          !readonly && 'hover:bg-gray-50 dark:hover:bg-gray-900'
        )}
        onClick={handleExpand}
        tabIndex={readonly ? -1 : 0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleExpand();
          }
        }}
        role={readonly ? undefined : 'button'}
        aria-expanded={expanded}
      >
        <div className="flex items-center space-x-4">
          <div className="h-12 w-12 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
            <BookOpen className="h-6 w-6 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-semibold text-gray-900 dark:text-white">{subject.name}</h3>
              <span className="text-xs text-gray-500 dark:text-gray-400">({subject.code})</span>
            </div>
            <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400 mt-1">
              <span className="flex items-center space-x-1">
                <Users className="h-3 w-3" />
                <span>Sem {semester} - Sec {section}</span>
              </span>
              <span className="flex items-center space-x-1">
                <Clock className="h-3 w-3" />
                <span>{subjectCredits} credits</span>
              </span>
              <span className="text-xs">
                {expanded ? availableSlots.length : savedSlots.length}/{minSlots} slots
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {success && (
            <span className="flex items-center text-green-600 dark:text-green-400 text-sm">
              <Check className="h-4 w-4" />
            </span>
          )}
          {error && !expanded && (
            <span className="flex items-center text-red-600 dark:text-red-400 text-sm">
              <X className="h-4 w-4" />
            </span>
          )}
          {expanded ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-800 p-4 space-y-4">
          {error && (
            <div className="flex items-center space-x-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
              <X className="h-4 w-4" />
              <span>{error}</span>
            </div>
          )}

          {saving && !loaded ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-violet-600" />
            </div>
          ) : (
            <>
              <SlotGrid
                availableSlots={availableSlots}
                onToggle={handleToggleSlot}
                readonly={readonly}
              />

              {/* Slot Legend */}
              <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400 mb-3">
                <span className="flex items-center gap-1">
                  <span className="w-4 h-4 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 flex items-center justify-center">
                    <Check className="h-3 w-3" aria-hidden="true" />
                  </span>
                  Available
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-4 h-4 rounded bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 flex items-center justify-center">-</span>
                  Unavailable
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  <span className={cn(isValid ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400')}>
                    {availableSlots.length} available slots
                  </span>
                  <span className="mx-2">-</span>
                  <span>Min: {minSlots} - Timetable will schedule {subjectCredits} class{subjectCredits > 1 ? 'es' : ''}/week</span>
                </div>

                {!readonly && (
                  <div className="flex items-center space-x-2">
                    {hasChanges && (
                      <span className="text-xs text-orange-600 dark:text-orange-400">Unsaved changes</span>
                    )}
                    <button
                      onClick={handleSave}
                      disabled={!hasChanges || saving || !isValid}
                      className={cn(
                        'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                        'focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2',
                        hasChanges && !saving && isValid
                          ? 'bg-violet-600 text-white hover:bg-violet-700 cursor-pointer'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
                      )}
                    >
                      {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save Changes'}
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default SubjectCard;
