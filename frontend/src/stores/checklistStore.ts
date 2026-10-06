import { create } from 'zustand';
import { wsService } from '../services/websocket';
import toast from 'react-hot-toast';

export interface ActionItem {
  id: string;
  description: string;
  due_at: string | null;
  status: 'open' | 'done' | 'dismissed';
  assignee: { id: number; username: string } | null;
  created_by: { id: number; username: string };
  source_message_id: string | null;
}

export interface CommitmentProposal {
  message_id: string;
  preview: string;
  suggested_description: string;
  suggested_assignee: { id: number; username: string } | null;
  suggested_due_at: string | null;
}

interface ChecklistState {
  itemsByRoom: Record<string, ActionItem[]>;
  pendingProposal: { roomId: string; payload: CommitmentProposal } | null;
  setRoomItems: (roomId: string, items: ActionItem[]) => void;
  upsertItem: (roomId: string, item: ActionItem) => void;
  setPendingProposal: (p: ChecklistState['pendingProposal']) => void;
  toggleItem: (roomId: string, itemId: string, done: boolean) => void;
}

export const useChecklistStore = create<ChecklistState>((set, get) => ({
  itemsByRoom: {},
  pendingProposal: null,

  setRoomItems: (roomId, items) => {
    set((state) => ({
      itemsByRoom: {
        ...state.itemsByRoom,
        [roomId]: items,
      },
    }));
  },

  upsertItem: (roomId, item) => {
    set((state) => {
      const roomItems = state.itemsByRoom[roomId] || [];
      const index = roomItems.findIndex((i) => i.id === item.id);
      
      const newRoomItems = [...roomItems];
      if (index > -1) {
        newRoomItems[index] = item; // This replaces the optimistic object with the server object
      } else {
        newRoomItems.unshift(item);
      }

      return {
        itemsByRoom: {
          ...state.itemsByRoom,
          [roomId]: newRoomItems,
        },
      };
    });
  },

  setPendingProposal: (p) => set({ pendingProposal: p }),

  toggleItem: (roomId, itemId, done) => {
    const previousState = get().itemsByRoom[roomId] || [];
    const itemIndex = previousState.findIndex(i => i.id === itemId);
    
    if (itemIndex === -1) return;
    
    const originalItem = previousState[itemIndex];

    // Optimistic Update: we add an internal optimistic flag to the object
    set((state) => {
      const roomItems = [...(state.itemsByRoom[roomId] || [])];
      roomItems[itemIndex] = { 
        ...originalItem, 
        status: done ? 'done' : 'open',
        _optimistic: true
      } as ActionItem & { _optimistic?: boolean };
      return {
        itemsByRoom: {
          ...state.itemsByRoom,
          [roomId]: roomItems,
        },
      };
    });

    // Send to WS
    try {
      wsService.send({
        type: 'checklist_toggle',
        item_id: itemId,
        done: done
      });
    } catch (e) {
      // Revert if WS fails immediately
      get().setRoomItems(roomId, previousState);
      toast.error('Erreur de connexion');
      return;
    }

    // Set timeout for rollback
    setTimeout(() => {
      const currentItem = get().itemsByRoom[roomId]?.find(i => i.id === itemId) as ActionItem & { _optimistic?: boolean };
      // If the item still has the _optimistic flag, it means upsertItem was never called by the server event
      if (currentItem && currentItem._optimistic) {
        toast.error('Le serveur n\'a pas répondu. Action annulée.');
        // Revert to original state
        set((state) => {
          const roomItems = [...(state.itemsByRoom[roomId] || [])];
          const idx = roomItems.findIndex(i => i.id === itemId);
          if (idx > -1) {
            roomItems[idx] = originalItem;
          }
          return {
            itemsByRoom: {
              ...state.itemsByRoom,
              [roomId]: roomItems,
            },
          };
        });
      }
    }, 3000);
  },
}));
