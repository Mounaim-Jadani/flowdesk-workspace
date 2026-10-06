import { create } from 'zustand';

interface RoomsState {
  capabilities: Record<string, string[]>;   // roomId -> capabilities
  setCapabilities: (roomId: string, caps: string[]) => void;
  hasCapability: (roomId: string, cap: string) => boolean;
}

export const useRoomsStore = create<RoomsState>((set, get) => ({
  capabilities: {},
  setCapabilities: (roomId, caps) => set((s) => ({ 
      capabilities: { ...s.capabilities, [roomId]: caps } 
  })),
  hasCapability: (roomId, cap) => (get().capabilities[roomId] ?? []).includes(cap),
}));
