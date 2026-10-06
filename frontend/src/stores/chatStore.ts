import { create } from 'zustand';
import { ChatRoom, Message } from '../types';
import { chatApi } from '../api/chat';
import { useAuthStore } from './authStore';
import { useRoomsStore } from './roomsStore';
import { useDigestStore } from './digestStore';
import { apiClient } from '../api/client';
import { useNotificationsStore } from './notificationsStore';

let digestFetchTimeout: ReturnType<typeof setTimeout> | null = null;

interface TypingUser {
  userId: number;
  username: string;
  timestamp: number;
}

interface ChatState {
  rooms: ChatRoom[];
  activeRoom: ChatRoom | null;
  messages: Record<string, Message[]>;
  typingUsers: Record<string, TypingUser[]>;
  onlineUsers: Set<number>;
  isLoading: boolean;

  // Room actions
  fetchRooms: () => Promise<void>;
  setActiveRoom: (room: ChatRoom | null) => void;
  createDirectMessage: (userId: number) => Promise<ChatRoom>;
  updateRoom: (room: ChatRoom) => void;

  // Message actions
  fetchMessages: (roomId: string) => Promise<void>;
  addMessage: (roomId: string, message: Message) => void;
  handleNewMessageAlert: (message: Message) => void;
  updateMessage: (roomId: string, message: Message) => void;
  deleteMessage: (roomId: string, messageId: string) => void;

  // Typing indicators
  setUserTyping: (roomId: string, userId: number, username: string, isTyping: boolean) => void;
  clearTypingUsers: (roomId: string) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  rooms: [],
  activeRoom: null,
  messages: {},
  typingUsers: {},
  onlineUsers: new Set<number>(),
  isLoading: false,

  fetchRooms: async () => {
    set({ isLoading: true });
    try {
      const rooms = await chatApi.getRooms();
      rooms.forEach((r: ChatRoom) => {
        if (r.capabilities) {
          useRoomsStore.getState().setCapabilities(r.id, r.capabilities);
        }
      });
      set({ rooms, isLoading: false });

      // (Le pré-chargement en arrière-plan a été retiré à la demande du client)
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  setActiveRoom: (room: ChatRoom | null) => {
    if (digestFetchTimeout) {
      clearTimeout(digestFetchTimeout);
      digestFetchTimeout = null;
    }

    // Interception of unread count before zeroing
    const unreadCount = room?.unread_count || 0;

    if (room && unreadCount >= 8) {
      // Afficher le bandeau IMMÉDIATEMENT avec spinner
      useDigestStore.getState().setLoading(room.id, true);

      // Debounce the request so rapidly switching rooms does not create
      // unnecessary digest generations.
      digestFetchTimeout = setTimeout(() => {
        digestFetchTimeout = null;
          const language = window.localStorage.getItem('flowdesk-digest-language') || '';
          const languageQuery = language ? `?lang_pref=${encodeURIComponent(language)}` : '';
          apiClient.get(`/digest/rooms/${room.id}/${languageQuery}`)
          .then(res => {
            useDigestStore.getState().setDigest(room.id, res.data);
          })
          .catch(err => {
            console.error('Failed to fetch digest:', err);
            useDigestStore.getState().setDigest(room.id, null);
          })
          .finally(() => {
            chatApi.markAsRead(room.id).catch(() => {});
          });
      }, 500);
    }

    set((state) => {
      const needsRoomsUpdate = room && state.rooms.some(r => r.id === room.id && (r.unread_count || 0) > 0);
      return {
        activeRoom: room,
        rooms: needsRoomsUpdate
          ? state.rooms.map(r => (r.id === room!.id) ? { ...r, unread_count: 0 } : r)
          : state.rooms
      };
    });

    if (room) {
      // Opening a room means its message notifications have been read.
      useNotificationsStore.getState().clearMessageNotifications(String(room.id));
      if (unreadCount >= 8) {
        // Le markAsRead est géré après la récupération du digest pour éviter la race condition backend
      } else {
        chatApi.markAsRead(room.id).catch(() => {});
      }
    }
  },

  createDirectMessage: async (userId: number) => {
    const room = await chatApi.createDirectMessage(userId);
    const rooms = get().rooms;
    const existingIndex = rooms.findIndex((r) => r.id === room.id);
    if (existingIndex === -1) {
      set({ rooms: [room, ...rooms] });
    }
    return room;
  },

  updateRoom: (room: ChatRoom) => {
    set((state) => ({
      rooms: state.rooms.map((r) => (r.id === room.id ? room : r)),
      activeRoom: state.activeRoom?.id === room.id ? room : state.activeRoom,
    }));
  },

  fetchMessages: async (roomId: string) => {
    try {
      const response = await chatApi.getMessages(roomId);
      const messages = response.results || response;
      set((state) => ({
        messages: {
          ...state.messages,
          [roomId]: Array.isArray(messages) ? messages.reverse() : [],
        },
      }));
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  },

  addMessage: (roomId: string, message: Message) => {
    set((state) => {
      const roomMessages = state.messages[roomId] || [];
      // Avoid duplicates
      if (roomMessages.some((m) => m.id === message.id)) {
        return state;
      }
      return {
        messages: {
          ...state.messages,
          [roomId]: [...roomMessages, message],
        },
        // Update room's last message
        rooms: state.rooms.map((room) =>
          room.id === roomId
            ? {
                ...room,
                last_message: {
                  id: message.id,
                  content: message.content,
                  sender: message.sender.username,
                  created_at: message.created_at,
                  message_type: message.message_type,
                },
                 unread_count: (state.activeRoom?.id === roomId)
                   ? 0
                   : (room.unread_count || 0),
              }
            : room
        ),
      };
    });
  },

  handleNewMessageAlert: (message: Message) => {
    set((state) => {
      // Use useAuthStore to check if own message
      const currentUser = useAuthStore.getState().user;
      const isOwnMessage = currentUser?.id === message.sender.id;
      const roomId = message.room;
      const hasRoom = state.rooms.some((room) => String(room.id) === String(roomId));

      const nextState = {
        rooms: state.rooms.map((room) =>
          String(room.id) === String(roomId)
            ? {
                ...room,
                last_message: {
                  id: message.id,
                  content: message.content,
                  sender: message.sender.username,
                  created_at: message.created_at,
                  message_type: message.message_type,
                },
                unread_count: (state.activeRoom?.id === roomId || isOwnMessage)
                  ? (room.unread_count || 0)
                  : (room.unread_count || 0) + 1,
              }
            : room
        ),
      };
      if (!hasRoom) {
        void get().fetchRooms().catch(() => {});
      }
      return nextState;
    });
  },

  updateMessage: (roomId: string, message: Message) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [roomId]: (state.messages[roomId] || []).map((m) =>
          m.id === message.id ? message : m
        ),
      },
    }));
  },

  deleteMessage: (roomId: string, messageId: string) => {
    set((state) => ({
      messages: {
        ...state.messages,
        [roomId]: (state.messages[roomId] || []).map((m) =>
          m.id === messageId
            ? { ...m, is_deleted: true, content: 'This message has been deleted' }
            : m
        ),
      },
    }));
  },

  setUserTyping: (roomId: string, userId: number, username: string, isTyping: boolean) => {
    set((state) => {
      const roomTyping = state.typingUsers[roomId] || [];

      if (isTyping) {
        // Add or update typing user
        const existing = roomTyping.find((t) => t.userId === userId);
        if (existing) {
          return {
            typingUsers: {
              ...state.typingUsers,
              [roomId]: roomTyping.map((t) =>
                t.userId === userId ? { ...t, timestamp: Date.now() } : t
              ),
            },
          };
        }
        return {
          typingUsers: {
            ...state.typingUsers,
            [roomId]: [...roomTyping, { userId, username, timestamp: Date.now() }],
          },
        };
      } else {
        // Remove typing user
        return {
          typingUsers: {
            ...state.typingUsers,
            [roomId]: roomTyping.filter((t) => t.userId !== userId),
          },
        };
      }
    });
  },

  clearTypingUsers: (roomId: string) => {
    set((state) => ({
      typingUsers: {
        ...state.typingUsers,
        [roomId]: [],
      },
    }));
  },
}));
