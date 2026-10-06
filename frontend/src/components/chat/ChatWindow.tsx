import { useEffect } from 'react';
import { ChatRoom } from '../../types';
import { useChatStore } from '../../stores/chatStore';
import { useAuthStore } from '../../stores/authStore';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { TypingIndicator } from './TypingIndicator';
import { useRoomCapability } from '../../hooks/useRoomCapability';
import { ChecklistPanel } from '../checklist/ChecklistPanel';
import { ChecklistStrip } from '../checklist/ChecklistStrip';

import { checklistApi } from '../../api/checklist';
import { useChecklistStore } from '../../stores/checklistStore';
import { CatchUpBanner } from './CatchUpBanner';

interface ChatWindowProps {
  room: ChatRoom;
}

export function ChatWindow({ room }: ChatWindowProps) {
  const { messages, typingUsers } = useChatStore();
  const user = useAuthStore((state) => state.user);
  const roomMessages = messages[room.id] || [];
  const roomTypingUsers = typingUsers[room.id] || [];

  const storeHasChecklist = useRoomCapability(String(room.id), 'checklist');
  const storeHasCatchUp = useRoomCapability(String(room.id), 'catch_me_up');
  const hasChecklist = storeHasChecklist || (room.capabilities?.includes('checklist') ?? false);
  const hasCatchUp = storeHasCatchUp || (room.capabilities?.includes('catch_me_up') ?? false);
  const isDM = room.room_type === 'direct';

  const setRoomItems = useChecklistStore(s => s.setRoomItems);

  // Fetch checklist items for the active room
  useEffect(() => {
    if (hasChecklist) {
      checklistApi.getItems(room.id.toString()).then(items => {
        setRoomItems(room.id.toString(), items);
      }).catch(console.error);
    }
  }, [room.id, hasChecklist, setRoomItems]);

  // Filter out current user from typing users
  const othersTyping = roomTypingUsers.filter((t) => t.userId !== user?.id);

  // Auto-clear stale typing indicators after 3 seconds
  const { setUserTyping } = useChatStore();
  useEffect(() => {
    if (othersTyping.length === 0) return;
    const interval = setInterval(() => {
      const now = Date.now();
      othersTyping.forEach((t) => {
        if (now - t.timestamp > 3000) {
          setUserTyping(room.id, t.userId, t.username, false);
        }
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [othersTyping, room.id, setUserTyping]);

  return (
    <div className="flex-1 flex h-full overflow-hidden">
      <div className="relative flex-1 flex flex-col bg-gray-900 overflow-hidden">
        <ChatHeader room={room} />
        {hasCatchUp && <CatchUpBanner room={room} />}
        
        {hasChecklist && isDM && <ChecklistStrip roomId={room.id} />}

        <div className="flex-1 flex flex-col overflow-hidden">
          <MessageList messages={roomMessages} />

          {othersTyping.length > 0 && (
            <TypingIndicator users={othersTyping} />
          )}
        </div>

        <MessageInput roomId={room.id} />
      </div>

       {hasChecklist && !isDM && <ChecklistPanel roomId={room.id} participants={room.participants_info || []} />}
    </div>
  );
}
