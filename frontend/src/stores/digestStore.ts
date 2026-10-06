import { create } from 'zustand';
import { apiClient } from '../api/client';
import { DigestData } from '../types';

interface DigestState {
  digestByRoom: Record<string, DigestData | null>;
  loadingRooms: Record<string, boolean>;
  errorByRoom: Record<string, string | null>;
  openRooms: string[];             // rooms avec bandeau affiché
  setLoading: (roomId: string, loading: boolean) => void;
  setDigest: (roomId: string, d: DigestData | null) => void;
  setError: (roomId: string, error: string | null) => void;
  completeConsume: (roomId: string) => void;
  dismiss: (roomId: string) => void;   // fermé sans consommer
  regenerate: (roomId: string, langPref: string) => Promise<void>;
}

export const useDigestStore = create<DigestState>((set) => ({
  digestByRoom: {},
  loadingRooms: {},
  errorByRoom: {},
  openRooms: [],
  setLoading: (roomId, loading) => set((s) => ({
    loadingRooms: { ...s.loadingRooms, [roomId]: loading },
    errorByRoom: { ...s.errorByRoom, [roomId]: null },
    openRooms: loading ? [...new Set([...s.openRooms, roomId])] : s.openRooms
  })),
  setDigest: (roomId, d) => set((s) => ({ 
    digestByRoom: { ...s.digestByRoom, [roomId]: d },
    loadingRooms: { ...s.loadingRooms, [roomId]: false },
    errorByRoom: { ...s.errorByRoom, [roomId]: null },
    openRooms: d
      ? [...new Set([...s.openRooms, roomId])]
      : s.openRooms.filter((id) => id !== roomId),
  })),
  setError: (roomId, error) => set((s) => ({
    loadingRooms: { ...s.loadingRooms, [roomId]: false },
    errorByRoom: { ...s.errorByRoom, [roomId]: error },
    openRooms: [...new Set([...s.openRooms, roomId])],
  })),
  completeConsume: (roomId) => set((s) => ({
    openRooms: s.openRooms.filter(id => id !== roomId),
    digestByRoom: { ...s.digestByRoom, [roomId]: null },
    errorByRoom: { ...s.errorByRoom, [roomId]: null },
    loadingRooms: { ...s.loadingRooms, [roomId]: false },
  })),
  dismiss: (roomId) => set((s) => ({
    openRooms: s.openRooms.filter(id => id !== roomId)
  })),
  regenerate: async (roomId, langPref) => {
    set((s) => ({
      loadingRooms: { ...s.loadingRooms, [roomId]: true },
      errorByRoom: { ...s.errorByRoom, [roomId]: null },
      openRooms: [...new Set([...s.openRooms, roomId])],
    }));
    try {
      const languageQuery = langPref ? `&lang_pref=${encodeURIComponent(langPref)}` : '';
      const res = await apiClient.get(`/digest/rooms/${roomId}/?force=true${languageQuery}`);
      if (res.status === 204 || !res.data) {
        set((s) => ({
          digestByRoom: { ...s.digestByRoom, [roomId]: null },
          loadingRooms: { ...s.loadingRooms, [roomId]: false },
          errorByRoom: { ...s.errorByRoom, [roomId]: null },
          openRooms: s.openRooms.filter((id) => id !== roomId),
        }));
        return;
      }
      set((s) => ({
        digestByRoom: { ...s.digestByRoom, [roomId]: res.data },
        loadingRooms: { ...s.loadingRooms, [roomId]: false },
        errorByRoom: { ...s.errorByRoom, [roomId]: null },
      }));
    } catch (err) {
      console.error('Failed to regenerate digest:', err);
      set((s) => ({
        loadingRooms: { ...s.loadingRooms, [roomId]: false },
        errorByRoom: {
          ...s.errorByRoom,
          [roomId]: 'Impossible de générer le rattrapage. Vérifiez votre connexion puis réessayez.',
        },
        openRooms: [...new Set([...s.openRooms, roomId])],
      }));
    }
  }
}));
