import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';

import { useAuthStore } from './stores/authStore';
import { wsService } from './services/websocket';
import { useNotificationsStore } from './stores/notificationsStore';
import { usePresenceSync } from './hooks/usePresenceSync';
import { useChecklistSync } from './hooks/useChecklistSync';
import { useChatStore } from './stores/chatStore';
import { routeEvent } from './services/notificationRouter';
import toast from 'react-hot-toast';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ChatPage } from './pages/ChatPage';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  
  usePresenceSync();
  useChecklistSync();

  useEffect(() => {
    if (isAuthenticated) {
      void useNotificationsStore.getState().load();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    // Listen to personal channel messages for notifications
    const cleanup = wsService.onMessage((data: any) => {
      if (data.kind === 'notification') {
        const notifItem = {
          id: data.id || Date.now().toString(),
          kind: data.notification_kind || data.payload?.kind || 'notification',
          payload: data.payload,
          created_at: new Date().toISOString(),
          is_read: false
        };
        // Toujours ajouter au store (et incrémenter le compteur)
        useNotificationsStore.getState().push(notifItem);
        
        const currentActiveRoomId = useChatStore.getState().activeRoom?.id || null;
        const routing = routeEvent(
          { type: 'notification', kind: notifItem.kind, payload: notifItem.payload }, 
          { activeRoomId: currentActiveRoomId ? String(currentActiveRoomId) : null }
        );
        
        if (routing.delivered === 'immediate') {
          toast(`Notification: ${notifItem.kind}`, { icon: '🔔' });
        }
      }
    });
    return cleanup;
  }, []);

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/chat" replace /> : <LoginPage />}
      />
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to="/chat" replace /> : <RegisterPage />}
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/chat/:roomId"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to={isAuthenticated ? '/chat' : '/login'} replace />} />
    </Routes>
  );
}

export default App;
