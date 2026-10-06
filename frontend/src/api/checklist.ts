import apiClient from './client';
import { ActionItem } from '../stores/checklistStore';

export const checklistApi = {
  getItems: async (roomId: string): Promise<ActionItem[]> => {
    const response = await apiClient.get(`/checklist/rooms/${roomId}/items/`);
    // API returns PaginatedResponse or list
    return response.data.results || response.data;
  },
  createItem: async (payload: {
    room_id: string;
    description: string;
    assignee_id?: number | null;
    due_at?: string | null;
  }): Promise<ActionItem> => {
    const response = await apiClient.post('/checklist/items/', payload);
    return response.data;
  },
};
