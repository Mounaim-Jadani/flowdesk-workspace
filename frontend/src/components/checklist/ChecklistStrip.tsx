import { useEffect, useState } from 'react';
import { useChecklistStore } from '../../stores/checklistStore';
import { ActionItemRow } from './ActionItemRow';
import { clsx } from 'clsx';
import { useAuthStore } from '../../stores/authStore';

interface ChecklistStripProps {
  roomId: string;
}

export function ChecklistStrip({ roomId }: ChecklistStripProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const items = useChecklistStore((s) => s.itemsByRoom[roomId] || []);
  const currentUser = useAuthStore((s) => s.user);

  useEffect(() => {
    const key = `flowdesk-open-checklist-${roomId}`;
    setIsExpanded(sessionStorage.getItem(key) === 'true');
    sessionStorage.removeItem(key);
    const openChecklist = (event: Event) => {
      if ((event as CustomEvent<string>).detail === String(roomId)) {
        setIsExpanded(true);
        sessionStorage.removeItem(key);
      }
    };
    window.addEventListener('flowdesk-open-checklist', openChecklist);
    return () => window.removeEventListener('flowdesk-open-checklist', openChecklist);
  }, [roomId]);
  
  // if (items.length === 0) return null;

  const activeCount = items.filter(i => i.status !== 'done').length;
  const myActiveCount = items.filter(i => i.status !== 'done' && i.assignee?.id === currentUser?.id).length;

  return (
    <div className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shrink-0">
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs transition-colors"
      >
        <div className="flex items-center gap-2 font-medium text-slate-700 dark:text-slate-300">
          <span className="text-violet-600">☑</span>
          {activeCount} action{activeCount !== 1 ? 's' : ''} en cours · {myActiveCount} pour toi
        </div>
        <div className={clsx(
          "text-slate-400 transition-transform duration-200",
          isExpanded ? "rotate-180" : ""
        )}>
          ▼
        </div>
      </button>

      {isExpanded && (
        <div className="max-h-64 overflow-y-auto px-4 divide-y divide-slate-100 dark:divide-slate-800">
          {items.map(item => (
            <ActionItemRow key={item.id} roomId={roomId} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
