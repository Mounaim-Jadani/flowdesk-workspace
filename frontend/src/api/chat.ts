import apiClient from './client';
import { ChatRoom, ChatRoomDetail, Message, PaginatedResponse } from '../types';

export const chatApi = {
  getRooms: async (): Promise<ChatRoom[]> => {
    const response = await apiClient.get('/chat/rooms/');
    return response.data.results || response.data;
  },

  getRoom: async (roomId: string): Promise<ChatRoomDetail> => {
    const response = await apiClient.get(`/chat/rooms/${roomId}/`);
    return response.data;
  },

  createRoom: async (data: {
    name?: string;
    room_type: 'direct' | 'group';
    participant_ids: number[];
    description?: string;
  }): Promise<ChatRoom> => {
    const response = await apiClient.post('/chat/rooms/', data);
    return response.data;
  },

  createDirectMessage: async (userId: number): Promise<ChatRoom> => {
    const response = await apiClient.post('/chat/direct/', { user_id: userId });
    return response.data;
  },

  getMessages: async (
    roomId: string,
    page = 1
  ): Promise<PaginatedResponse<Message>> => {
    const response = await apiClient.get(`/chat/rooms/${roomId}/messages/?page=${page}`);
    return response.data;
  },

  sendMessage: async (
    roomId: string,
    content: string,
    replyTo?: string
  ): Promise<Message> => {
    const response = await apiClient.post(`/chat/rooms/${roomId}/messages/`, {
      content,
      reply_to: replyTo,
    });
    return response.data;
  },

  editMessage: async (
    roomId: string,
    messageId: string,
    content: string
  ): Promise<Message> => {
    const response = await apiClient.patch(
      `/chat/rooms/${roomId}/messages/${messageId}/`,
      { content }
    );
    return response.data;
  },

  deleteMessage: async (roomId: string, messageId: string): Promise<void> => {
    await apiClient.delete(`/chat/rooms/${roomId}/messages/${messageId}/`);
  },

  markAsRead: async (roomId: string): Promise<void> => {
    await apiClient.post(`/chat/rooms/${roomId}/read/`);
  },

  updateTypingStatus: async (roomId: string, isTyping: boolean): Promise<void> => {
    await apiClient.post(`/chat/rooms/${roomId}/typing/`, { is_typing: isTyping });
  },
};
