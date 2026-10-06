import { useState, useRef, useEffect } from 'react';
import { Bell, Check, Headphones } from 'lucide-react';
import { useNotificationsStore } from '../../stores/notificationsStore';
import { usePresenceStore } from '../../stores/presenceStore';
import { useNavigate } from 'react-router-dom';

export function NotificationsDropdown() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { items, unreadCount, markRead, clearMessageNotifications } = useNotificationsStore();
  const deferredQueue = usePresenceStore((state) => state.deferredQueue);
  const mySession = usePresenceStore((state) => state.mySession);

  // Le nombre total de notifications (standard + différées si en Deep Work)
  const totalUnread = unreadCount + (mySession?.active ? deferredQueue.length : 0);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`relative p-2 rounded-lg transition-colors ${isOpen ? 'bg-gray-600' : 'bg-gray-700 hover:bg-gray-600'}`}
        title="Notifications"
      >
        <Bell className="w-5 h-5 text-gray-300" />
        {totalUnread > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-gray-900">
            {totalUnread > 9 ? '9+' : totalUnread}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-80 rounded-xl bg-gray-800 border border-gray-700 shadow-2xl overflow-hidden z-50 flex flex-col max-h-[24rem]">
          <div className="px-4 py-3 border-b border-gray-700 flex justify-between items-center bg-gray-800/95 backdrop-blur-sm sticky top-0">
            <h3 className="font-semibold text-white">Notifications</h3>
          </div>

          <div className="overflow-y-auto flex-1 p-2 space-y-1">
            {mySession?.active && deferredQueue.length > 0 && (
              <div className="mb-4">
                <div className="px-2 py-1 mb-1 text-xs font-semibold text-amber-500/80 uppercase tracking-wider flex items-center gap-1">
                  <Headphones className="w-3 h-3" /> Différées (Deep Work)
                </div>
                {deferredQueue.map((item, idx) => (
                  <div key={item.id || idx} className="p-3 rounded-lg bg-gray-700/40 border border-gray-700/50 mb-1">
                    <p className="text-sm text-gray-200 line-clamp-2">{item.preview}</p>
                    <p className="text-[10px] text-gray-500 mt-1">
                      {new Date(item.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                ))}
              </div>
            )}

            {items.length === 0 && (!mySession?.active || deferredQueue.length === 0) ? (
              <div className="p-4 text-center text-sm text-gray-500">
                Aucune notification
              </div>
            ) : (
              <>
                {items.length > 0 && (
                  <div className="px-2 py-1 mb-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Récentes
                  </div>
                )}
                {items.map((item) => (
                  <div 
                    key={item.id} 
                    className={`p-3 rounded-lg flex items-start gap-3 transition-colors ${!item.is_read ? 'bg-primary-500/10' : 'hover:bg-gray-700/50'}`}
                  >
                    <div 
                      className="flex-1 min-w-0 cursor-pointer"
                      onClick={() => {
                        if (item.kind === 'assignment' && item.payload?.room_id) {
                          sessionStorage.setItem(
                            `flowdesk-open-checklist-${item.payload.room_id}`,
                            'true',
                          );
                          window.dispatchEvent(new CustomEvent('flowdesk-open-checklist', {
                            detail: String(item.payload.room_id),
                          }));
                          navigate(`/chat/${item.payload.room_id}`);
                          setIsOpen(false);
                          if (!item.is_read) markRead(item.id);
                        } else if (item.kind === 'message' && item.payload?.room_id) {
                          clearMessageNotifications(String(item.payload.room_id));
                          navigate(`/chat/${item.payload.room_id}`);
                          setIsOpen(false);
                        }
                      }}
                    >
                      <p className={`text-sm ${!item.is_read ? 'text-white font-medium' : 'text-gray-300'}`}>
                        {item.kind === 'assignment' 
                          ? `${item.payload?.actor_username} t'a assigné : "${item.payload?.description}"` 
                          : item.payload?.preview || item.kind}
                      </p>
                      <p className="text-[10px] text-gray-500 mt-1">
                        {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    {!item.is_read && (
                      <button 
                        onClick={() => markRead(item.id)}
                        className="p-1.5 text-primary-400 hover:bg-primary-500/20 rounded-md transition-colors"
                        title="Marquer comme lu"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
