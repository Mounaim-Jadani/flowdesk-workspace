import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useChatStore } from '../stores/chatStore';
import { wsService } from '../services/websocket';
import { authApi } from '../api/auth';
import { usePresenceStore } from '../stores/presenceStore';
import { useNotificationsStore } from '../stores/notificationsStore';
import { Sidebar } from '../components/chat/Sidebar';
import { ChatWindow } from '../components/chat/ChatWindow';
import { EmptyState } from '../components/chat/EmptyState';

export function ChatPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const navigate = useNavigate();
  const { activeRoom, setActiveRoom, fetchRooms, rooms, fetchMessages } = useChatStore();
  const setUserPresence = usePresenceStore((state) => state.setUserPresence);
  const clearMessageNotifications = useNotificationsStore((state) => state.clearMessageNotifications);

  // Fetch rooms on mount
  useEffect(() => {
    fetchRooms();
    
    // Fetch initial online users
    authApi.getOnlineUsers().then(users => {
      users.forEach(u => setUserPresence(u.id, { 
        online: true,
        deepWork: u.deep_work ? { active: u.deep_work.active, endsAt: u.deep_work.ends_at } : null
      }));
    }).catch(console.error);

    wsService.connectToStatus();

    // Ensure WebSocket is properly closed when tab closes
    const handleBeforeUnload = () => {
      wsService.disconnectFromStatus();
      wsService.disconnectFromRoom();
    };
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      wsService.disconnectFromStatus();
    };
  }, [fetchRooms, setUserPresence]);

  // Handle WebSocket connection and message fetching
  useEffect(() => {
    if (roomId) {
      fetchMessages(roomId);
      wsService.connectToRoom(roomId);
    } else {
      wsService.disconnectFromRoom();
    }

    return () => {
      if (roomId) {
        wsService.disconnectFromRoom();
      }
    };
  }, [roomId, fetchMessages]);

  // Clear message alerts whenever the route changes, even if the room state
  // was already active and ChatPage does not need to replace activeRoom.
  useEffect(() => {
    if (roomId) {
      clearMessageNotifications(roomId);
    }
  }, [roomId, clearMessageNotifications]);

  // Handle active room state update
  useEffect(() => {
    if (roomId && rooms.length > 0) {
      const room = rooms.find((r) => r.id === roomId);
      if (room && activeRoom?.id !== room.id) {
        setActiveRoom(room);
      }
    } else if (!roomId && activeRoom !== null) {
      setActiveRoom(null);
    }
  }, [roomId, rooms, activeRoom, setActiveRoom]);

  const handleRoomSelect = (room: typeof rooms[0]) => {
    navigate(`/chat/${room.id}`);
  };

  return (
    <div className="h-screen w-full flex bg-gray-900 overflow-hidden">
      {/* Sidebar */}
      <Sidebar onRoomSelect={handleRoomSelect} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {activeRoom ? (
          <ChatWindow room={activeRoom} />
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}
