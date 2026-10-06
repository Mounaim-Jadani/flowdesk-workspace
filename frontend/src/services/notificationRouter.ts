import { usePresenceStore } from '../stores/presenceStore';

export type IncomingEvent = 
  | { type: 'message'; room_id: string; content: string; [key: string]: any }
  | { type: 'notification'; kind: string; payload: any; [key: string]: any }
  | { type: string; [key: string]: any };

export type DeliveryStatus = 'immediate' | 'deferred' | 'ignored';

// Liste des événements qui méritent une notification visuelle/sonore
const NOTIFYABLE_EVENTS = new Set(['message', 'notification', 'checklist_assigned', 'decision_pinned']);

/**
 * Extrait un aperçu propre selon le type d'événement
 */
const extractPreview = (event: IncomingEvent): string => {
  if (event.type === 'message' && typeof event.content === 'string') {
    return event.content.substring(0, 100) + (event.content.length > 100 ? '...' : '');
  }
  
  if (event.type === 'notification' && event.payload) {
    if (typeof event.payload.preview === 'string') return event.payload.preview;
    if (typeof event.payload.title === 'string') return event.payload.title;
    return `Nouvelle notification: ${event.payload.kind || 'Action'}`;
  }

  return 'Nouvelle activité';
};

/**
 * Détermine si une notification doit être affichée immédiatement ou différée
 */
export function routeEvent(
  event: IncomingEvent, 
  ctx: { activeRoomId: string | null }
): { delivered: DeliveryStatus } {
  const presence = usePresenceStore.getState();
  
  // Si ce n'est pas un événement notifiable, on le laisse passer silencieusement 
  // (ce n'est pas censé créer un toast de toute façon)
  if (!NOTIFYABLE_EVENTS.has(event.type)) {
    return { delivered: 'immediate' };
  }

  // Règle de politesse Deep Work :
  // On diffère SI ET SEULEMENT SI le Deep Work est actif ET qu'on ne regarde pas déjà la room d'où vient l'événement.
  const isDeepWorkActive = presence.mySession?.active === true;
  const isFromActiveRoom = event.room_id && String(event.room_id) === String(ctx.activeRoomId);

  if (isFromActiveRoom) {
    // Si on regarde déjà la conversation, pas besoin de toast ni de notification différée
    return { delivered: 'ignored' };
  }

  if (isDeepWorkActive) {
    // On met l'événement dans la file d'attente
    presence.deferNotification({ 
      id: crypto.randomUUID(), 
      roomId: (event.room_id as unknown as number) || 0, // Fallback si ce n'est pas lié à une room
      preview: extractPreview(event) 
    });
    
    return { delivered: 'deferred' };
  }
  
  return { delivered: 'immediate' };
}
