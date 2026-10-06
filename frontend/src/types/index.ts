// User types
export interface User {
  id: number;
  username: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  bio?: string;
  is_online: boolean;
  last_seen?: string;
  created_at?: string;
  deep_work?: { active: boolean; ends_at: string } | null;
}

export interface UserMinimal {
  id: number;
  username: string;
  display_name: string;
  avatar_url: string | null;
  is_online: boolean;
  deep_work?: { active: boolean; ends_at: string } | null;
}

// Auth types
export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  password_confirm: string;
  display_name?: string;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

// Chat types
export interface Message {
  id: string;
  room: string;
  sender: UserMinimal;
  content: string;
  message_type: 'text' | 'image' | 'file' | 'system';
  attachment?: string;
  reply_to?: string;
  reply_to_preview?: {
    id: string;
    content: string;
    sender: string;
  };
  is_edited: boolean;
  edited_at?: string;
  is_deleted: boolean;
  created_at: string;
  visible_from?: string | null;
  is_own_message?: boolean;
}

export interface RoomParticipant {
  user: UserMinimal;
  role: 'member' | 'admin' | 'owner';
  joined_at: string;
  is_typing: boolean;
  is_muted: boolean;
}

export interface ChatRoom {
  id: string;
  name: string;
  room_type: 'direct' | 'group';
  description?: string;
  avatar?: string;
  capabilities?: string[];
  participants_info: RoomParticipant[];
  last_message?: {
    id: string;
    content: string;
    sender: string;
    created_at: string;
    message_type: string;
  };
  unread_count: number;
  display_name: string;
  display_avatar?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatRoomDetail extends ChatRoom {
  messages: Message[];
}

// Catch-Me-Up / digest types
export interface DigestKeyPoint {
  text: string;
  message_id: string;
  ts: string;
  username: string;
}

export interface DigestMention {
  message_id: string;
  preview: string;
  username: string;
  ts: string;
}

export interface DigestStats {
  message_count: number;
  participants: number;
  decisions_count?: number;
  open_items?: number;
}

export interface DigestData {
  since: string;
  until: string;
  summary: string;
  key_points: DigestKeyPoint[];
  mentions: DigestMention[];
  stats: DigestStats;
  summary_language?: string;
}

// WebSocket message types
export interface WSMessage {
  type: 'message' | 'typing' | 'read' | 'edit' | 'delete' | 'user_join' | 'user_leave' | 'status';
  message?: Message;
  user_id?: number;
  username?: string;
  is_typing?: boolean;
  is_online?: boolean;
  message_id?: string;
  read_at?: string;
}

// API Response types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
