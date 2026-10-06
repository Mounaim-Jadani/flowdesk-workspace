import { ChatRoom } from '../../types';
import { useAuthStore } from '../../stores/authStore';
import { usePresenceStore } from '../../stores/presenceStore';
import { Avatar } from '../ui/Avatar';
import { Phone, Video, MoreVertical, Users } from 'lucide-react';
import { DeepWorkBadge } from '../presence/DeepWorkBadge';

interface ChatHeaderProps {
  room: ChatRoom;
}

export function ChatHeader({ room }: ChatHeaderProps) {
  const onlineUsers = usePresenceStore((state) => state.onlineUsers);
  const currentUser = useAuthStore((state) => state.user);

  const otherParticipant = room.room_type === 'direct'
    ? room.participants_info?.find((p) => p.user.id !== currentUser?.id)?.user
    : null;

  const isOtherDeepWork = otherParticipant ? onlineUsers[otherParticipant.id]?.deepWork?.active : false;
  const isOnline = otherParticipant && !isOtherDeepWork ? !!onlineUsers[otherParticipant.id]?.online : false;
  const participantCount = room.participants_info.length;

  return (
    <div className="h-16 px-4 flex items-center justify-between border-b border-gray-700 bg-gray-800">
      <div className="flex items-center space-x-3">
        <Avatar
          name={room.display_name}
          src={room.display_avatar}
          size="md"
          isOnline={room.room_type === 'direct' && !isOtherDeepWork ? isOnline : undefined}
        />
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-semibold text-white">{room.display_name}</h2>
            {room.room_type === 'direct' && otherParticipant && (
              <DeepWorkBadge userId={otherParticipant.id} />
            )}
          </div>
          <p className="text-xs text-gray-400">
            {room.room_type === 'direct' ? (
              isOtherDeepWork ? '' : (isOnline ? 'Online' : 'Offline')
            ) : (
              <span className="flex items-center">
                <Users className="w-3 h-3 mr-1" />
                {participantCount} members
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <button className="p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white">
          <Phone className="w-5 h-5" />
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white">
          <Video className="w-5 h-5" />
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white">
          <MoreVertical className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
