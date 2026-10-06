import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import { useChatStore } from '../../stores/chatStore';
import { useAuthStore } from '../../stores/authStore';
import { usePresenceStore } from '../../stores/presenceStore';
import { ChatRoom } from '../../types';
import { Avatar } from '../ui/Avatar';
import { NewChatModal } from './NewChatModal';
import { MessageSquare, Plus, LogOut, Settings, Search, Users, Brain } from 'lucide-react';
import toast from 'react-hot-toast';
import { DeepWorkButton } from '../presence/DeepWorkButton';
import { DeepWorkBadge } from '../presence/DeepWorkBadge';
import { NotificationsDropdown } from './NotificationsDropdown';


interface SidebarProps {
  onRoomSelect: (room: ChatRoom) => void;
}

export function Sidebar({ onRoomSelect }: SidebarProps) {
  const navigate = useNavigate();
  const { rooms, activeRoom, isLoading } = useChatStore();
  const { user, logout } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [showNewChat, setShowNewChat] = useState(false);

  const filteredRooms = rooms
    .filter((room) => room.display_name.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      const timeA = a.last_message?.created_at ? new Date(a.last_message.created_at).getTime() : 0;
      const timeB = b.last_message?.created_at ? new Date(b.last_message.created_at).getTime() : 0;
      return timeB - timeA;
    });

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
      toast.success('Logged out successfully');
    } catch {
      toast.error('Failed to logout');
    }
  };

  const mySession = usePresenceStore((state) => state.mySession);

  return (
    <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col h-full z-10 relative">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-primary-600 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">FlowDesk</h1>
              <p className="text-xs text-gray-400">Real-time messaging</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <NotificationsDropdown />
            <button
              onClick={() => setShowNewChat(true)}
              className="p-2 rounded-lg bg-primary-600 hover:bg-primary-700 transition-colors"
              title="New Chat"
            >
              <Plus className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filteredRooms.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-400">
            <Users className="w-8 h-8 mb-2" />
            <p className="text-sm">No conversations yet</p>
            <button
              onClick={() => setShowNewChat(true)}
              className="mt-2 text-primary-400 hover:text-primary-300 text-sm"
            >
              Start a new chat
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-700">
            {filteredRooms.map((room) => (
              <ChatRoomItem
                key={room.id}
                room={room}
                isActive={activeRoom?.id === room.id}
                onClick={() => onRoomSelect(room)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Deep Work Section */}
      <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between bg-gray-800/30">
        <div className="flex items-center gap-2 text-gray-300">
          <Brain className="w-4 h-4 text-indigo-400" />
          <span className="text-sm font-medium">Focus Mode</span>
        </div>
        <DeepWorkButton />
      </div>

      {/* User Section */}
      <div className="p-4 border-t border-gray-700 bg-gray-850">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Avatar
              name={user?.display_name || user?.username || 'U'}
              src={user?.avatar_url}
              size="md"
              isOnline={mySession?.active ? false : true}
            />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white truncate">
                {user?.display_name || user?.username}
              </p>
              <p className="text-xs text-gray-400 truncate">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center space-x-1">
            <button
              className="p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
              title="Settings"
            >
              <Settings className="w-5 h-5" />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-red-400"
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* New Chat Modal */}
      {showNewChat && <NewChatModal onClose={() => setShowNewChat(false)} />}
    </div>
  );
}

interface ChatRoomItemProps {
  room: ChatRoom;
  isActive: boolean;
  onClick: () => void;
}

function ChatRoomItem({ room, isActive, onClick }: ChatRoomItemProps) {
  const onlineUsers = usePresenceStore((state) => state.onlineUsers);
  const currentUser = useAuthStore((state) => state.user);

  // For direct messages, find the OTHER participant and check real-time online status
  const otherParticipant = room.room_type === 'direct'
    ? room.participants_info?.find((p) => p.user.id !== currentUser?.id)?.user
    : undefined;

  const isOtherOnline = otherParticipant 
    ? (onlineUsers[otherParticipant.id]?.deepWork?.active ? undefined : onlineUsers[otherParticipant.id]?.online)
    : undefined;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full p-4 flex items-center space-x-3 hover:bg-gray-700/50 transition-colors text-left',
        isActive && 'bg-gray-700'
      )}
    >
      <Avatar
        name={room.display_name}
        src={room.display_avatar}
        size="lg"
        isOnline={isOtherOnline}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center truncate">
            <span className="font-medium text-white truncate">{room.display_name}</span>
            {room.room_type === 'direct' && otherParticipant && (
              <DeepWorkBadge userId={otherParticipant.id} />
            )}
          </div>
          {room.last_message && (
            <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
              {formatDistanceToNow(new Date(room.last_message.created_at), { addSuffix: false })}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-400 truncate">
            {room.last_message?.content || 'No messages yet'}
          </p>
          {room.unread_count > 0 && (
            <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-primary-600 text-white rounded-full">
              {room.unread_count > 99 ? '99+' : room.unread_count}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
