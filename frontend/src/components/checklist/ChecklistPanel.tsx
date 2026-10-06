import { useEffect, useState } from 'react';
import { useChecklistStore } from '../../stores/checklistStore';
import { ActionItemRow } from './ActionItemRow';
import { checklistApi } from '../../api/checklist';
import { ChatRoom } from '../../types';
import toast from 'react-hot-toast';

interface ChecklistPanelProps {
  roomId: string;
  participants: ChatRoom['participants_info'];
}

export function ChecklistPanel({ roomId, participants }: ChecklistPanelProps) {
  const [isCreating, setIsCreating] = useState(false);
  const [description, setDescription] = useState('');
  const [assigneeId, setAssigneeId] = useState('');
  const [dueAt, setDueAt] = useState('');
  const setRoomItems = useChecklistStore((s) => s.setRoomItems);
  useEffect(() => {
    const key = `flowdesk-open-checklist-${roomId}`;
    sessionStorage.removeItem(key);
    const consumeIntent = (event: Event) => {
      if ((event as CustomEvent<string>).detail === String(roomId)) {
        sessionStorage.removeItem(key);
      }
    };
    window.addEventListener('flowdesk-open-checklist', consumeIntent);
    return () => window.removeEventListener('flowdesk-open-checklist', consumeIntent);
  }, [roomId]);
  const items = useChecklistStore((s) => s.itemsByRoom[roomId] || []);
  
  const doneCount = items.filter(i => i.status === 'done').length;
  const totalCount = items.length;
  const progress = totalCount === 0 ? 0 : (doneCount / totalCount) * 100;

  const createAction = async () => {
    if (!description.trim()) return;
    try {
      await checklistApi.createItem({
        room_id: roomId,
        description: description.trim(),
        assignee_id: assigneeId ? Number(assigneeId) : null,
        due_at: dueAt ? new Date(`${dueAt}T23:59:00`).toISOString() : null,
      });
      setRoomItems(roomId, await checklistApi.getItems(roomId));
      setDescription('');
      setAssigneeId('');
      setDueAt('');
      setIsCreating(false);
      toast.success('Action créée dans le groupe');
    } catch (error) {
      console.error(error);
      toast.error('Impossible de créer l’action');
    }
  };

  return (
    <div className="w-80 border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col h-full shrink-0">
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Actions</h2>
          <button
            type="button"
            onClick={() => setIsCreating((open) => !open)}
            className="rounded-md bg-violet-600 px-2 py-1 text-xs font-medium text-white hover:bg-violet-700"
          >
            {isCreating ? 'Annuler' : '+ Ajouter'}
          </button>
        </div>
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-2">
          <span>{doneCount}/{totalCount} terminées</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
          <div 
            className="h-full bg-violet-600 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {isCreating && (
        <div className="border-b border-slate-200 p-3 dark:border-slate-800">
          <input
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Description de l’action"
            className="mb-2 w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
          <select
            value={assigneeId}
            onChange={(event) => setAssigneeId(event.target.value)}
            className="mb-2 w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          >
            <option value="">Sans assigné</option>
            {participants.map(({ user }) => (
              <option key={user.id} value={user.id}>{user.username}</option>
            ))}
          </select>
          <input
            type="date"
            value={dueAt}
            onChange={(event) => setDueAt(event.target.value)}
            className="mb-2 w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
          <button
            type="button"
            disabled={!description.trim()}
            onClick={createAction}
            className="w-full rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Créer l’action
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4">
        {items.length === 0 ? (
          <div className="text-center text-sm text-slate-500 mt-8">
            Aucune action pour le moment
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.map(item => (
              <ActionItemRow key={item.id} roomId={roomId} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
