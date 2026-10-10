import { create } from 'zustand';
import apiClient from '../api/client';

export interface KarmaBadge {
  kind: string;
  period_key?: string | null;
  awarded_at: string;
}

export interface KarmaEvent {
  id: string;
  kind: string;
  score: number;
  room_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface KarmaLeaderboardEntry {
  user_id: number;
  username: string;
  score: number;
  badges: string[];
}

interface KarmaState {
  myKarma: { total: number; monthly: number; rank: number | null; badges: KarmaBadge[]; recent_events: KarmaEvent[] } | null;
  leaderboard: KarmaLeaderboardEntry[];
  loading: boolean;
  load: (roomId?: string) => Promise<void>;
  applyUpdate: (userId: number, delta: number, newTotal: number, monthlyTotal: number, badges: string[], isCurrentUser: boolean) => void;
}

export const useKarmaStore = create<KarmaState>((set) => ({
  myKarma: null,
  leaderboard: [],
  loading: false,
  load: async (roomId) => {
    set({ loading: true });
    try {
      const [meResponse, leaderboardResponse] = await Promise.all([
        apiClient.get(`/karma/me/${roomId ? `?room_id=${encodeURIComponent(roomId)}` : ''}`),
        apiClient.get(`/karma/leaderboard/?scope=month${roomId ? `&room_id=${encodeURIComponent(roomId)}` : ''}`),
      ]);
      set({ myKarma: meResponse.data, leaderboard: leaderboardResponse.data, loading: false });
    } catch (error) {
      console.error('Failed to load Karma:', error);
      set({ loading: false });
    }
  },
  applyUpdate: (userId, _delta, newTotal, monthlyTotal, badges, isCurrentUser) => set((state) => ({
    myKarma: isCurrentUser && state.myKarma
      ? {
          ...state.myKarma,
          total: newTotal,
          monthly: monthlyTotal,
          badges: [
            ...state.myKarma.badges,
            ...badges.filter((kind) => !state.myKarma!.badges.some((badge) => badge.kind === kind)).map((kind) => ({
              kind,
              awarded_at: new Date().toISOString(),
            })),
          ],
        }
      : state.myKarma,
    leaderboard: state.leaderboard
      .map((entry) => entry.user_id === userId
        ? { ...entry, score: monthlyTotal, badges: [...new Set([...entry.badges, ...badges])] }
        : entry)
      .sort((left, right) => right.score - left.score),
  })),
}));
