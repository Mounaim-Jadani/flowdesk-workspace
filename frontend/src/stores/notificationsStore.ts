import { create } from 'zustand';
import { apiClient } from '../api/client';

export interface NotificationItem {
  id: string;
  kind: string;
  payload: any;
  created_at: string;
  is_read: boolean;
}

interface NotificationsState {
  items: NotificationItem[];
  unreadCount: number;
  push: (item: NotificationItem) => void;
  load: () => Promise<void>;
  markRead: (id: string) => void;
  markAllRead: () => Promise<void>;
  clearMessageNotifications: (roomId: string) => void;
}

export const useNotificationsStore = create<NotificationsState>((set) => ({
  items: [],
  unreadCount: 0,
  push: (item) => set((state) => {
    if (state.items.some((existing) => existing.id === item.id)) {
      return state;
    }
    return {
      items: [item, ...state.items],
      unreadCount: state.unreadCount + (item.is_read ? 0 : 1),
    };
  }),
  load: async () => {
    try {
      const response = await apiClient.get('/notifications/');
      const items = response.data as NotificationItem[];
      set({ items, unreadCount: items.filter((item) => !item.is_read).length });
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  },
  markRead: (id) => {
    void apiClient.post(`/notifications/${id}/read/`).catch(() => {});
    set((state) => {
    const newItems = state.items.map(item =>
      item.id === id ? { ...item, is_read: true } : item
    );
    return {
      items: newItems,
      unreadCount: newItems.filter(item => !item.is_read).length
    };
    });
  },
  markAllRead: async () => {
    await apiClient.post('/notifications/read-all/');
    set((state) => ({
      items: state.items.map((item) => ({ ...item, is_read: true })),
      unreadCount: 0,
    }));
  },
  clearMessageNotifications: (roomId) => set((state) => {
    const newItems = state.items.filter((item) => !(
      item.kind === 'message' && String(item.payload?.room_id) === String(roomId)
    ));
    return {
      items: newItems,
      unreadCount: newItems.filter((item) => !item.is_read).length,
    };
  }),
}));
