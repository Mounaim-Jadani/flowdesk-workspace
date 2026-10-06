import { useEffect } from 'react';
import { wsService } from '../services/websocket';
import { usePresenceStore } from '../stores/presenceStore';
import { useAuthStore } from '../stores/authStore';
import toast from 'react-hot-toast';

export function usePresenceSync() {
  useEffect(() => {
    // Listen for WebSocket events from the global personal channel
    const unsubscribe = wsService.onMessage((data: any) => {
      const presence = usePresenceStore.getState();
      const currentUser = useAuthStore.getState().user;
      
      // 1. Regular heartbeat event ('status' or 'status_update')
      if (data.type === 'status' || data.type === 'status_update') {
        const deepWorkInfo = data.deep_work 
          ? { active: data.deep_work.active, endsAt: data.deep_work.ends_at } 
          : null;

        presence.setUserPresence(data.user_id, { 
          online: data.is_online, 
          deepWork: deepWorkInfo 
        });
        
        // Ensure mySession is initialized if the status update is for the current user (e.g. after a page refresh)
        if (currentUser && data.user_id === currentUser.id) {
          presence.setMySession(deepWorkInfo);
        }
      }
      
      // 2. Real-time broadcast for deep work start/stop
      // Handle both nested relay_event payload and flat kind based payload
      const isRelay = data.type === 'relay_event' && data.payload?.kind === 'deep_work';
      const isDirect = data.kind === 'deep_work';
      
      if (isRelay || isDirect) {
        const payload = isRelay ? data.payload : data;
        const deepWorkInfo = payload.active 
          ? { active: true, endsAt: payload.ends_at } 
          : null;
          
        // Update global presence state for this user
        presence.setUserPresence(payload.user_id, { 
          deepWork: deepWorkInfo 
        });
        
        if (currentUser && payload.user_id === currentUser.id) {
          presence.setMySession(deepWorkInfo);
        }
      }

      // 3. Fin de session Deep Work par le worker (EPIC 3 - 3.1.8)
      const isEndedRelay = data.type === 'relay_event' && data.payload?.kind === 'deep_work_ended';
      const isEndedDirect = data.kind === 'deep_work_ended';

      if (isEndedRelay || isEndedDirect) {
        const payload = isEndedRelay ? data.payload : data;
        
        // Mettre à jour l'état de présence (fin de deep work)
        presence.setUserPresence(payload.user_id, { deepWork: null });
        
        if (currentUser && payload.user_id === currentUser.id) {
          presence.setMySession(null);
          
          const deferredQueue = usePresenceStore.getState().deferredQueue || [];
          if (deferredQueue.length > 0) {
            toast(`🎧 Session terminée — ${deferredQueue.length} notifications reportées`, {
              icon: '🚀',
              duration: 5000,
            });
            presence.clearDeferred();
          } else {
            toast('🎧 Session terminée — aucune interruption !', {
              icon: '✨',
              duration: 3000,
            });
          }
        }
      }
    });
    
    return () => unsubscribe(); // Cleanup on unmount
  }, []);
}
