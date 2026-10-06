import { create } from 'zustand';

export interface DeepWorkInfo { active: boolean; endsAt: string | null; }

export interface PresenceState {
  onlineUsers: Record<number, { online: boolean; deepWork: DeepWorkInfo | null }>;
  mySession: DeepWorkInfo | null;
  deferredQueue: Array<{ id: string; roomId: number; preview: string; at: string }>;
  
  setUserPresence: (userId: number, p: Partial<{ online: boolean; deepWork: DeepWorkInfo | null }>) => void;
  setMySession: (s: DeepWorkInfo | null) => void;
  deferNotification: (item: { id: string; roomId: number; preview: string }) => void;
  clearDeferred: () => void;
}

export const usePresenceStore = create<PresenceState>((set) => ({
  onlineUsers: {},
  mySession: null,
  deferredQueue: [],
  
  setUserPresence: (userId, p) => set((s) => ({
    onlineUsers: { 
      ...s.onlineUsers, 
      [userId]: { ...{ online: false, deepWork: null }, ...s.onlineUsers[userId], ...p } 
    }
  })),
  setMySession: (mySession) => set({ mySession }),
  deferNotification: (item) => set((s) => ({ 
    deferredQueue: [...s.deferredQueue, { ...item, at: new Date().toISOString() }] 
  })),
  clearDeferred: () => set({ deferredQueue: [] }),
}));
