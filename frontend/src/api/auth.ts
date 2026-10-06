import apiClient from './client';
import { LoginCredentials, RegisterData, AuthResponse, User, UserMinimal } from '../types';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/login/', credentials);
    return {
      user: response.data.user,
      tokens: {
        access: response.data.access,
        refresh: response.data.refresh,
      },
    };
  },

  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/register/', data);
    return response.data;
  },

  logout: async (refreshToken: string): Promise<void> => {
    await apiClient.post('/auth/logout/', { refresh: refreshToken });
  },

  getProfile: async (): Promise<User> => {
    const response = await apiClient.get('/auth/profile/');
    return response.data;
  },

  updateProfile: async (data: Partial<User>): Promise<User> => {
    const response = await apiClient.patch('/auth/profile/', data);
    return response.data;
  },

  changePassword: async (data: {
    current_password: string;
    new_password: string;
    new_password_confirm: string;
  }): Promise<void> => {
    await apiClient.post('/auth/password/change/', data);
  },

  searchUsers: async (query: string): Promise<User[]> => {
    const response = await apiClient.get(`/auth/users/?search=${query}`);
    return response.data;
  },

  getOnlineUsers: async (): Promise<UserMinimal[]> => {
    const response = await apiClient.get('/auth/users/online/');
    return response.data;
  },
};
