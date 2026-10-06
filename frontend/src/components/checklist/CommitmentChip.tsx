import { useState, useEffect } from 'react';
import { useChecklistStore } from '../../stores/checklistStore';
import { useChatStore } from '../../stores/chatStore';
import { apiClient } from '../../api/client';
import clsx from 'clsx';
import toast from 'react-hot-toast';

interface CommitmentChipProps {
  messageId: string;
}

export function CommitmentChip({ messageId }: CommitmentChipProps) {
  const proposal = useChecklistStore((s) => s.pendingProposal);
  const setPendingProposal = useChecklistStore((s) => s.setPendingProposal);
  
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  
  const activeRoom = useChatStore((s) => s.activeRoom);

  const [description, setDescription] = useState('');
  const [assigneeId, setAssigneeId] = useState<string>('');
  const [dueAt, setDueAt] = useState('');

  useEffect(() => {
    const dismissed = JSON.parse(sessionStorage.getItem('dismissed_proposals') || '[]');
    if (dismissed.includes(messageId)) {
      setIsDismissed(true);
    }
  }, [messageId]);

  useEffect(() => {
    if (proposal?.payload?.message_id === messageId) {
      setDescription(proposal.payload.suggested_description || '');
      setDueAt(proposal.payload.suggested_due_at ? proposal.payload.suggested_due_at.substring(0, 10) : '');
      setAssigneeId(proposal.payload.suggested_assignee?.id?.toString() || '');
    }
  }, [proposal, messageId]);

  if (proposal?.payload?.message_id !== messageId || isDismissed) {
    return null;
  }

  const handleDismiss = () => {
    const dismissed = JSON.parse(sessionStorage.getItem('dismissed_proposals') || '[]');
    dismissed.push(messageId);
    sessionStorage.setItem('dismissed_proposals', JSON.stringify(dismissed));
    setIsDismissed(true);
    setPendingProposal(null);
  };

  const handleCreate = async () => {
    if (!activeRoom) return;
    
    // Formatage strict du payload
    const payload = {
      room_id: activeRoom.id,
      message_id: messageId,
      description: description,
      // Extraire UNIQUEMENT l'ID entier, pas l'objet complet
      assignee_id: assigneeId ? Number(assigneeId) : null,
      // CRITIQUE : Si la date est vide (""), envoyer null. Django plantera avec "".
      due_at: dueAt ? new Date(dueAt).toISOString() : null,
    };

    try {
      await apiClient.post('/checklist/items/', payload);
      toast.success('Action créée avec succès !');
      setPendingProposal(null);
    } catch (error: any) {
      toast.error(`Erreur : ${JSON.stringify(error.response?.data) || 'Erreur inconnue'}`);
    }
  };

  if (!isExpanded) {
    return (
      <div className="mt-2 ml-12">
        <button
          onClick={() => setIsExpanded(true)}
          className="inline-flex items-center gap-2 rounded-full border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950 px-3 py-1 text-xs text-violet-700 dark:text-violet-300 hover:bg-violet-100 dark:hover:bg-violet-900 transition-colors"
        >
          ✅ Engagement détecté — en faire une action ?
        </button>
      </div>
    );
  }

  const isDM = activeRoom?.room_type === 'direct';

  return (
    <div className="mt-2 ml-12 p-3 rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-950/50 shadow-sm flex flex-col gap-2 w-fit">
      <div className="text-xs font-semibold text-violet-800 dark:text-violet-300 mb-1">Créer une action</div>
      
      <input 
        type="text" 
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        className="w-56 rounded-md border border-slate-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1 text-xs text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500"
        placeholder="Description de l'action"
      />
      
      <select
        value={assigneeId}
        onChange={(e) => setAssigneeId(e.target.value)}
        disabled={isDM}
        className={clsx(
          "w-56 rounded-md border border-slate-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1 text-xs text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500",
          isDM && "opacity-75 bg-slate-100 dark:bg-gray-900 cursor-not-allowed"
        )}
      >
        <option value="">-- Sans assigné --</option>
        {activeRoom?.participants_info?.map((p) => (
          <option key={p.user.id} value={p.user.id}>
            {p.user.username}
          </option>
        ))}
      </select>

      <input 
        type="date"
        value={dueAt}
        onChange={(e) => setDueAt(e.target.value)}
        className="w-56 rounded-md border border-slate-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-2 py-1 text-xs text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-violet-500"
      />

      <div className="flex gap-2 mt-1">
        <button 
          onClick={handleCreate}
          className="px-3 py-1 rounded bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium transition-colors"
        >
          Créer
        </button>
        <button 
          onClick={handleDismiss}
          className="px-3 py-1 rounded bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 text-xs font-medium transition-colors"
        >
          Ignorer
        </button>
      </div>
    </div>
  );
}
