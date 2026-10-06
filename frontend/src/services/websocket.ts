/// <reference types="vite/client" />
import { useAuthStore } from '../stores/authStore';
import { useChatStore } from '../stores/chatStore';
import { WSMessage } from '../types';
import toast from 'react-hot-toast';
import { routeEvent } from './notificationRouter';
import { useNotificationsStore } from '../stores/notificationsStore';

type MessageHandler = (data: WSMessage) => void;

class WebSocketService {
  private socket: WebSocket | null = null;
  private statusSocket: WebSocket | null = null;
  private roomId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private heartbeatInterval: ReturnType<typeof setTimeout> | null = null;
  private statusReconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private statusReconnectEnabled = true;
  private messageHandlers: MessageHandler[] = [];

  private getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || window.location.host;
    return `${protocol}//${host}`;
  }

  connectToRoom(roomId: string): void {
    if (this.socket?.readyState === WebSocket.OPEN && this.roomId === roomId) {
      return;
    }

    this.disconnectFromRoom();
    this.roomId = roomId;

    const token = useAuthStore.getState().tokens?.access;
    if (!token) {
      console.error('No auth token available');
      return;
    }

    const url = `${this.getWsUrl()}/ws/chat/${roomId}/?token=${token}`;
    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log(`Connected to room ${roomId}`);
      this.reconnectAttempts = 0;
    };

    this.socket.onmessage = (event) => {
      try {
        const data: WSMessage = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.socket.onclose = (event) => {
      console.log(`Disconnected from room ${roomId}`, event.code);
      if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect();
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnectFromRoom(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }

    this.roomId = null;
    this.reconnectAttempts = 0;
  }

  connectToStatus(): void {
    this.statusReconnectEnabled = true;
    if (this.statusSocket?.readyState === WebSocket.OPEN) {
      return;
    }

    const token = useAuthStore.getState().tokens?.access;
    if (!token) return;

    const url = `${this.getWsUrl()}/ws/status/?token=${token}`;
    this.statusSocket = new WebSocket(url);

    this.statusSocket.onopen = () => {
      console.log('Connected to status updates');
      this.startHeartbeat();
    };

    this.statusSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message_alert') {
          const deliverAlert = () => this.deliverNewMessageAlert(data.message);
          const visibleAt = data.message?.visible_from ? new Date(data.message.visible_from).getTime() : 0;
          const isOwnMessage = data.message?.sender?.id === useAuthStore.getState().user?.id;
          if (visibleAt > Date.now() && !isOwnMessage) {
            window.setTimeout(deliverAlert, visibleAt - Date.now());
          } else {
            deliverAlert();
          }
        }

        // Notify external handlers of all events on the personal/status channel
        this.messageHandlers.forEach(handler => handler(data));
      } catch (error) {
        console.error('Failed to parse status message:', error);
      }
    };

    this.statusSocket.onclose = () => {
      console.log('Disconnected from status updates');
      this.stopHeartbeat();
      if (this.statusReconnectEnabled && useAuthStore.getState().tokens?.access) {
        this.statusReconnectTimeout = window.setTimeout(() => {
          this.statusReconnectTimeout = null;
          this.connectToStatus();
        }, 1500);
      }
    };
  }

  private deliverNewMessageAlert(message: any): void {
    if (!message) return;
          // Toujours mettre à jour le compteur non-lu
          useChatStore.getState().handleNewMessageAlert(message);

          const currentActiveRoomId = useChatStore.getState().activeRoom?.id || null;
          const routing = routeEvent(
            { type: 'message', room_id: String(message.room), content: message.content },
            { activeRoomId: currentActiveRoomId ? String(currentActiveRoomId) : null }
          );

           if (routing.delivered === 'immediate') {
             // Only messages from another room become notifications. A
             // message already being read in the active room must not remain
             // in the bell after the conversation is opened.
             useNotificationsStore.getState().push({
               id: `message-${message.id}`,
               kind: 'message',
               payload: {
                 room_id: String(message.room),
                 preview: `Message de ${message.sender.username}: ${message.content.substring(0, 50)}...`,
               },
               created_at: new Date().toISOString(),
               is_read: false,
             });
             toast.success(`Nouveau message de ${message.sender.username}`);
           }
  }

  disconnectFromStatus(): void {
    this.statusReconnectEnabled = false;
    this.stopHeartbeat();
    if (this.statusReconnectTimeout) {
      clearTimeout(this.statusReconnectTimeout);
      this.statusReconnectTimeout = null;
    }
    if (this.statusSocket) {
      this.statusSocket.close();
      this.statusSocket = null;
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.statusSocket?.readyState === WebSocket.OPEN) {
        this.statusSocket.send(JSON.stringify({ type: 'heartbeat' }));
      }
    }, 30000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private handleMessage(data: WSMessage): void {
    const chatStore = useChatStore.getState();

    switch (data.type) {
      case 'message':
        if (data.message && this.roomId) {
          chatStore.addMessage(this.roomId, data.message);
        }
        break;

      case 'typing':
        if (this.roomId && data.user_id && data.username) {
          chatStore.setUserTyping(
            this.roomId,
            data.user_id,
            data.username,
            data.is_typing || false
          );
        }
        break;

      case 'edit':
        if (data.message && this.roomId) {
          chatStore.updateMessage(this.roomId, data.message);
        }
        break;

      case 'delete':
        if (data.message_id && this.roomId) {
          chatStore.deleteMessage(this.roomId, data.message_id);
        }
        break;

      case 'user_join':
      case 'user_leave':
        // Could show notifications
        break;

      case 'read':
        // Could update read receipts
        break;
    }

    // Notify external handlers
    this.messageHandlers.forEach((handler) => handler(data));
  }

  sendMessage(content: string, replyTo?: string, visibleFrom?: string): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          type: 'message',
          content,
          reply_to: replyTo,
          visible_from: visibleFrom,
        })
      );
    }
  }

  sendTyping(isTyping: boolean): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          type: 'typing',
          is_typing: isTyping,
        })
      );
    }
  }

  sendRead(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: 'read' }));
    }
  }

  editMessage(messageId: string, content: string): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          type: 'edit',
          message_id: messageId,
          content,
        })
      );
    }
  }

  deleteMessage(messageId: string): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(
        JSON.stringify({
          type: 'delete',
          message_id: messageId,
        })
      );
    }
  }

  public sendPersonalAck(_payload: Record<string, any>): void {
    // NOOP v1 — réservé EPIC 7 (acquittement notification)
  }

  send(data: any): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
    };
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimeout = setTimeout(() => {
      if (this.roomId) {
        this.connectToRoom(this.roomId);
      }
    }, delay);
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }
}

export const wsService = new WebSocketService();
