import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../../api/auth';
import { useChatStore } from '../../stores/chatStore';
import { User } from '../../types';
import { Avatar } from '../ui/Avatar';
import { X, Search, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface NewChatModalProps {
  onClose: () => void;
}

export function NewChatModal({ onClose }: NewChatModalProps) {
  const navigate = useNavigate();
  const { createDirectMessage } = useChatStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    const searchUsers = async () => {
      if (searchQuery.length < 2) {
        setUsers([]);
        return;
      }

      setIsLoading(true);
      try {
        const results = await authApi.searchUsers(searchQuery);
        setUsers(results);
      } catch {
        toast.error('Failed to search users');
      } finally {
        setIsLoading(false);
      }
    };

    const debounce = setTimeout(searchUsers, 300);
    return () => clearTimeout(debounce);
  }, [searchQuery]);

  const handleSelectUser = async (user: User) => {
    setIsCreating(true);
    try {
      const room = await createDirectMessage(user.id);
      onClose();
      navigate(`/chat/${room.id}`);
    } catch {
      toast.error('Failed to create conversation');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md mx-4 bg-gray-800 rounded-2xl shadow-2xl border border-gray-700 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white">New Conversation</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search users by username..."
              className="input pl-10"
              autoFocus
            />
          </div>
        </div>

        {/* User List */}
        <div className="max-h-80 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              {searchQuery.length < 2
                ? 'Type at least 2 characters to search'
                : 'No users found'}
            </div>
          ) : (
            <div className="divide-y divide-gray-700">
              {users.map((user) => (
                <button
                  key={user.id}
                  onClick={() => handleSelectUser(user)}
                  disabled={isCreating}
                  className="w-full p-4 flex items-center space-x-3 hover:bg-gray-700/50 transition-colors text-left disabled:opacity-50"
                >
                  <Avatar
                    name={user.display_name || user.username}
                    src={user.avatar_url}
                    size="md"
                    isOnline={user.is_online}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate">
                      {user.display_name || user.username}
                    </p>
                    <p className="text-sm text-gray-400 truncate">@{user.username}</p>
                  </div>
                  {user.is_online && (
                    <span className="px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded-full">
                      Online
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
