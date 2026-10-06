import { apiClient } from './client';

export const presenceApi = {
  startDeepWork: async (durationMinutes: number) => {
    const response = await apiClient.post('/presence/deep-work/start/', { duration_minutes: durationMinutes });
    return response.data;
  },
  stopDeepWork: async () => {
    const response = await apiClient.post('/presence/deep-work/stop/');
    return response.data;
  }
};
