import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, AuthTokens, LoginCredentials, RegisterData } from '../types';
import { authApi } from '../api/auth';

interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isLoading: boolean;
  isAuthenticated: boolean;

  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  setTokens: (tokens: AuthTokens) => void;
  setUser: (user: User) => void;
  fetchProfile: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      tokens: null,
      isLoading: false,
      isAuthenticated: false,

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true });
        try {
          const response = await authApi.login(credentials);
          set({
            user: response.user,
            tokens: response.tokens,
            isAuthenticated: true,
            isLoading: false,
          });
          
          import('./presenceStore').then(module => {
            const deepWorkInfo = response.user.deep_work 
              ? { active: response.user.deep_work.active, endsAt: response.user.deep_work.ends_at } 
              : null;
            module.usePresenceStore.getState().setMySession(deepWorkInfo);
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (data: RegisterData) => {
        set({ isLoading: true });
        try {
          const response = await authApi.register(data);
          set({
            user: response.user,
            tokens: response.tokens,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: async () => {
        const tokens = get().tokens;
        try {
          if (tokens?.refresh) {
            await authApi.logout(tokens.refresh);
          }
        } finally {
          set({
            user: null,
            tokens: null,
            isAuthenticated: false,
          });
        }
      },

      setTokens: (tokens: AuthTokens) => {
        set({ tokens });
      },

      setUser: (user: User) => {
        set({ user });
      },

      fetchProfile: async () => {
        try {
          const user = await authApi.getProfile();
          set({ user });
          
          // Mettre à jour mySession si l'utilisateur a une session deep work active
          import('./presenceStore').then(module => {
            const deepWorkInfo = user.deep_work 
              ? { active: user.deep_work.active, endsAt: user.deep_work.ends_at } 
              : null;
            module.usePresenceStore.getState().setMySession(deepWorkInfo);
          });
        } catch {
          // Silent fail - user might be logged out
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        tokens: state.tokens,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
