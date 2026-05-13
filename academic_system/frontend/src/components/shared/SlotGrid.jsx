import { useCallback, useEffect, useMemo, useState } from 'react';
import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
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

// Helper to get slot number from slot object
export const getSlotNumber = (slot) => typeof slot === 'object' ? slot.slot : slot;

// Helper to get slot time from slot object or number
export const getSlotTime = (slot) => {
  if (typeof slot === 'object') return slot.time;
  const found = TIME_SLOTS.find(s => s.slot === slot);
  return found ? found.time : `${slot}`;
};

// Export slot numbers array for backward compatibility
export const SLOT_NUMBERS = TIME_SLOTS.map(s => s.slot);

// Hook for academic year persistence
export function useAcademicYear() {
  const [year, setYear] = useState(() => {
    const stored = localStorage.getItem('academicYear');
    if (stored) return stored;

    const currentYear = new Date().getFullYear();
    const month = new Date().getMonth();
    return month >= 3 ? `${currentYear}-${currentYear + 1}` : `${currentYear - 1}-${currentYear}`;
  });

  useEffect(() => {
    localStorage.setItem('academicYear', year);
  }, [year]);

  return [year, setYear];
}

export function SlotGrid({
  availableSlots = [],
  onToggle,
  readonly = false,
  days = DAYS,
  slots = TIME_SLOTS,
  className,
}) {
  const [focusedSlot, setFocusedSlot] = useState(null);

  const slotSet = useMemo(() => new Set(availableSlots), [availableSlots]);

  // Helper to get slot number from slot object or number
  const getSlotNum = useCallback((slot) => {
    return typeof slot === 'object' ? slot.slot : slot;
  }, []);

  // Helper to get slot time from slot object or number
  const getSlotTimeDisplay = useCallback((slot) => {
    return typeof slot === 'object' ? slot.time : `Slot ${slot}`;
  }, []);

  const getSlotKey = useCallback((day, slot) => {
    const slotNum = getSlotNum(slot);
    return `${day}-${slotNum}`;
  }, [getSlotNum]);

  const isAvailable = useCallback((day, slot) => slotSet.has(getSlotKey(day, slot)), [slotSet, getSlotKey]);

  const handleToggle = useCallback(
    (day, slot) => {
      if (readonly) return;
      onToggle?.(getSlotKey(day, slot));
    },
    [readonly, onToggle, getSlotKey]
  );

  const handleKeyDown = useCallback(
    (e, dayIndex, slotIndex) => {
      if (readonly) return;

      switch (e.key) {
        case 'Enter':
        case ' ':
          e.preventDefault();
          handleToggle(days[dayIndex], slots[slotIndex]);
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (slotIndex < slots.length - 1) {
            setFocusedSlot({ dayIndex, slotIndex: slotIndex + 1 });
          }
          break;
        case 'ArrowLeft':
          e.preventDefault();
          if (slotIndex > 0) {
            setFocusedSlot({ dayIndex, slotIndex: slotIndex - 1 });
          }
          break;
        case 'ArrowDown':
          e.preventDefault();
          if (dayIndex < days.length - 1) {
            setFocusedSlot({ dayIndex: dayIndex + 1, slotIndex });
          }
          break;
        case 'ArrowUp':
          e.preventDefault();
          if (dayIndex > 0) {
            setFocusedSlot({ dayIndex: dayIndex - 1, slotIndex });
          }
          break;
      }
    },
    [readonly, days, slots, handleToggle]
  );

  return (
    <div className={cn('overflow-x-auto', className)}>
      <div className="inline-block min-w-full border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700" role="grid">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-32">
                Day / Time
              </th>
              {slots.map((slot) => (
                <th key={getSlotNum(slot)} className="px-2 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider min-w-[100px]">
                  {getSlotTimeDisplay(slot)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-950 divide-y divide-gray-200 dark:divide-gray-700">
            {days.map((day, dayIndex) => (
              <tr key={day}>
                <td className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap">
                  {day}
                </td>
                {slots.map((slot, slotIndex) => {
                  const available = isAvailable(day, slot);
                  const slotNum = getSlotNum(slot);
                  const isFocused = focusedSlot?.dayIndex === dayIndex && focusedSlot?.slotIndex === slotIndex;

                  return (
                    <td key={slotNum} className="px-1 py-1 text-center">
                      <button
                        type="button"
                        role="gridcell"
                        aria-pressed={available}
                        aria-label={`${day} slot ${slotNum} ${available ? 'available' : 'unavailable'}`}
                        tabIndex={isFocused ? 0 : -1}
                        onFocus={() => setFocusedSlot({ dayIndex, slotIndex })}
                        onClick={() => handleToggle(day, slot)}
                        onKeyDown={(e) => handleKeyDown(e, dayIndex, slotIndex)}
                        disabled={readonly}
                        className={cn(
                          'w-full h-10 rounded-md transition-all duration-150 text-xs font-medium',
                          'focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-2',
                          available
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600',
                          readonly
                            ? 'cursor-not-allowed opacity-60'
                            : 'cursor-pointer hover:scale-105 active:scale-95'
                        )}
                      >
                        {available ? (
                          <Check className="mx-auto h-4 w-4" aria-hidden="true" />
                        ) : (
                          '-'
                        )}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default SlotGrid;
