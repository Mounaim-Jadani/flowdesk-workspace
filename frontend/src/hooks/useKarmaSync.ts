import { useEffect } from 'react';
import toast from 'react-hot-toast';
import { useAuthStore } from '../stores/authStore';
import { useKarmaStore } from '../stores/karmaStore';
import { useChatStore } from '../stores/chatStore';
import { wsService } from '../services/websocket';

export function useKarmaSync() {
  const currentUserId = useAuthStore((state) => state.user?.id);
  const applyUpdate = useKarmaStore((state) => state.applyUpdate);
  const activeRoomId = useChatStore((state) => (
    state.activeRoom?.room_type === 'group' ? state.activeRoom.id : undefined
  ));

  useEffect(() => {
    const unsubscribe = wsService.onMessage((data) => {
      if (data.kind !== 'karma_update') return;
      const badges = Array.isArray(data.badges_unlocked) ? data.badges_unlocked as string[] : [];
      applyUpdate(
        Number(data.user_id),
        Number(data.delta || 0),
        Number(data.new_total || 0),
        Number(data.monthly_total || 0),
        badges,
        Number(data.user_id) === currentUserId,
      );
      // Reload the active scope so users entering/leaving the top ten and
      // changed ranks are reflected without a browser refresh.
      void useKarmaStore.getState().load(activeRoomId);
      if (Number(data.user_id) === currentUserId && Number(data.delta || 0) > 0) {
        toast(`+${data.delta} Karma — ${String(data.event_kind || 'Contribution')}`, { icon: '✨' });
        badges.forEach((badge) => toast(`Nouveau badge : ${badge}`, { icon: '🏅' }));
      }
    });
    return unsubscribe;
  }, [activeRoomId, applyUpdate, currentUserId]);
}
