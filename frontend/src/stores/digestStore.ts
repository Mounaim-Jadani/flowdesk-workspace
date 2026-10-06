import { create } from 'zustand';
import { apiClient } from '../api/client';
import { DigestData } from '../types';

interface DigestState {
  digestByRoom: Record<string, DigestData | null>;
  loadingRooms: Record<string, boolean>;
  openRooms: string[];             // rooms avec bandeau affiché
  setLoading: (roomId: string, loading: boolean) => void;
  setDigest: (roomId: string, d: DigestData | null) => void;
  dismiss: (roomId: string) => void;   // fermé sans consommer
  consume: (roomId: string) => void;   // fermé + POST consume
  regenerate: (roomId: string, langPref: string) => Promise<void>;
}

export const useDigestStore = create<DigestState>((set) => ({
  digestByRoom: {},
  loadingRooms: {},
  openRooms: [],
  setLoading: (roomId, loading) => set((s) => ({
    loadingRooms: { ...s.loadingRooms, [roomId]: loading },
    openRooms: loading ? [...new Set([...s.openRooms, roomId])] : s.openRooms
  })),
  setDigest: (roomId, d) => set((s) => ({ 
    digestByRoom: { ...s.digestByRoom, [roomId]: d },
    loadingRooms: { ...s.loadingRooms, [roomId]: false },
    openRooms: d ? [...new Set([...s.openRooms, roomId])] : s.openRooms
  })),
  dismiss: (roomId) => set((s) => ({
    openRooms: s.openRooms.filter(id => id !== roomId)
  })),
  consume: (roomId) => {
    // Déclencher l'appel API POST
    apiClient.post(`/digest/rooms/${roomId}/consume/`).catch(console.error);
    
    set((s) => ({
      openRooms: s.openRooms.filter(id => id !== roomId),
      digestByRoom: { ...s.digestByRoom, [roomId]: null }
    }));
  },
  regenerate: async (roomId, langPref) => {
    set((s) => ({ loadingRooms: { ...s.loadingRooms, [roomId]: true } }));
    try {
      const res = await apiClient.get(`/digest/rooms/${roomId}/?force=true&lang_pref=${langPref}`);
      set((s) => ({
        digestByRoom: { ...s.digestByRoom, [roomId]: res.data },
        loadingRooms: { ...s.loadingRooms, [roomId]: false }
      }));
    } catch (err) {
      console.error('Failed to regenerate digest:', err);
      set((s) => ({ loadingRooms: { ...s.loadingRooms, [roomId]: false } }));
    }
  }
}));
