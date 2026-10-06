import { useEffect } from 'react';
import { wsService } from '../services/websocket';
import { useChatStore } from '../stores/chatStore';
import { useChecklistStore } from '../stores/checklistStore';
import toast from 'react-hot-toast';

export function useChecklistSync() {
  const { setPendingProposal, upsertItem } = useChecklistStore();

  useEffect(() => {
    const handleMessage = (data: any) => {
      // 1. Détection d'un engagement (proposition de checklist)
      if (data.type === 'commitment_detected') {
        const roomId = data.room_id || useChatStore.getState().activeRoom?.id;
        if (roomId) {
          setPendingProposal({ 
            roomId: String(roomId),
            payload: data 
          });
        }
      }

      // 2. Événement de diffusion (création, update, toggle)
      if (data.type === 'checklist' || (data.type === 'relay_event' && data.payload?.type === 'checklist_event')) {
        const payload = data.type === 'relay_event'
          ? { ...data.payload, type: undefined }
          : data.payload;
        if (payload.kind === 'item_created' || payload.kind === 'item_updated') {
          if (payload.item && payload.item.room_id) {
            upsertItem(String(payload.item.room_id), payload.item);
          }
        } else if (payload.kind === 'item_toggled') {
          const { itemsByRoom } = useChecklistStore.getState();
          for (const [roomIdStr, items] of Object.entries(itemsByRoom)) {
            const item = items.find(i => i.id === payload.item_id);
            if (item) {
              upsertItem(roomIdStr, {
                ...item,
                status: payload.done ? 'done' : 'open',
                _optimistic: false
              } as any);
              break;
            }
          }
        }
      }

      // 3. Notification personnelle d'assignation
      if (data.type === 'notification' && data.payload?.kind === 'assignment') {
        const payload = data.payload.payload;
        toast(`Nouvelle action assignée par @${payload.actor_username} : "${payload.description}"`, {
          icon: '📋'
        });
        
        // Si l'item complet est dans data.payload.item, on l'upsert
        if (data.payload.item) {
           // Si room est dispo
           const roomId = data.payload.item.room || data.payload.room_id;
           if (roomId) upsertItem(String(roomId), data.payload.item);
        }
      }
    };

    const cleanup = wsService.onMessage(handleMessage);
    return () => {
      cleanup();
    };
  }, [setPendingProposal, upsertItem]);
}
