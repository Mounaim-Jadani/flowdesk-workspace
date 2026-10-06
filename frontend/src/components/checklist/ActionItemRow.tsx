import { clsx } from 'clsx';
import { ActionItem, useChecklistStore } from '../../stores/checklistStore';

interface ActionItemRowProps {
  roomId: string;
  item: ActionItem;
}

export function ActionItemRow({ roomId, item }: ActionItemRowProps) {
  const toggleItem = useChecklistStore((s) => s.toggleItem);

  const isDone = item.status === 'done';

  const getDueColor = (dueAt: string | null) => {
    if (!dueAt) return 'text-slate-500';
    const due = new Date(dueAt).getTime();
    const now = Date.now();
    const diff = due - now;

    if (diff < 0) return 'text-rose-600';
    if (diff < 24 * 60 * 60 * 1000) return 'text-amber-600';
    return 'text-slate-500';
  };

  const getDueText = (dueAt: string | null) => {
    if (!dueAt) return 'Pas d\'échéance';
    const date = new Date(dueAt);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={clsx("flex items-start gap-3 py-3", isDone && "opacity-60")}>
      <input
        type="checkbox"
        checked={isDone}
        onChange={() => toggleItem(roomId, item.id, !isDone)}
        className="mt-1 h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500 cursor-pointer"
      />
      <div className="flex-1 flex flex-col gap-1">
        <span className={clsx("text-sm text-slate-800 dark:text-slate-200", isDone && "line-through")}>
          {item.description}
        </span>
        <div className="flex items-center gap-4 text-xs">
          {item.assignee ? (
            <div className="flex items-center gap-1 text-slate-500">
              <div className="w-4 h-4 rounded-full bg-violet-200 dark:bg-violet-800 flex items-center justify-center text-[10px] text-violet-700 dark:text-violet-300">
                {item.assignee.username.charAt(0).toUpperCase()}
              </div>
              <span>{item.assignee.username}</span>
            </div>
          ) : (
            <span className="text-slate-400 italic">Non assigné</span>
          )}
          
          <span className={getDueColor(item.due_at)}>
            📅 {getDueText(item.due_at)}
          </span>
        </div>
      </div>
    </div>
  );
}
