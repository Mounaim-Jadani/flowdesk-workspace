import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { format, isToday, isYesterday } from 'date-fns';
import clsx from 'clsx';
import { Message } from '../../types';
import { wsService } from '../../services/websocket';
import { chatApi } from '../../api/chat';
import { useAuthStore } from '../../stores/authStore';
import { Avatar } from '../ui/Avatar';
import { CheckCheck, Edit2, Plus, Reply, Trash2 } from 'lucide-react';
import { CommitmentChip } from '../checklist/CommitmentChip';

const REACTION_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🙏'];

interface MessageListProps {
  messages: Message[];
  onReply?: (message: Message) => void;
  roomId?: string;
}

export function MessageList({ messages, onReply, roomId }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const user = useAuthStore((state) => state.user);
  const initialScrollDone = useRef(false);

  // Scroll on initial load and new messages only when the user is already at
  // the bottom. Reaction updates must never move the user away from the
  // message they are interacting with.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const isNearBottom = () => (
      container.scrollHeight - container.scrollTop - container.clientHeight < 120
    );
    const scrollToBottom = () => {
      container.scrollTop = container.scrollHeight;
    };

    const shouldScroll = !initialScrollDone.current || isNearBottom();
    initialScrollDone.current = true;
    let frame: number | undefined;
    let timeout: number | undefined;
    if (shouldScroll) {
      frame = requestAnimationFrame(scrollToBottom);
      timeout = window.setTimeout(scrollToBottom, 150);
    }

    // Observe changes in the container itself, but preserve the user's
    // position when they are reading older messages.
    const resizeObserver = new ResizeObserver(() => {
      if (isNearBottom()) scrollToBottom();
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (frame !== undefined) cancelAnimationFrame(frame);
      if (timeout !== undefined) window.clearTimeout(timeout);
    };
  }, [messages.length]);

  const formatMessageDate = (date: Date): string => {
    if (isToday(date)) return 'Today';
    if (isYesterday(date)) return 'Yesterday';
    return format(date, 'MMMM d, yyyy');
  };

  // Group messages by date
  const groupedMessages: { date: string; messages: Message[] }[] = [];
  let currentGroup: { date: string; messages: Message[] } | null = null;

  messages.forEach((message) => {
    const messageDate = new Date(message.created_at);
    const dateString = formatMessageDate(messageDate);

    if (!currentGroup || currentGroup.date !== dateString) {
      currentGroup = { date: dateString, messages: [] };
      groupedMessages.push(currentGroup);
    }
    currentGroup.messages.push(message);
  });

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto px-4 py-4 flex flex-col space-y-4">
      {/* Spacer to push messages to the bottom when there are few */}
      <div className="flex-1"></div>
      
      {groupedMessages.map((group, groupIndex) => (
        <div key={groupIndex}>
          {/* Date Separator */}
          <div className="flex items-center justify-center my-4">
            <div className="px-3 py-1 rounded-full bg-gray-800 text-xs text-gray-400">
              {group.date}
            </div>
          </div>

          {/* Messages */}
          <div className="space-y-2">
            {group.messages.map((message, index) => {
              const isOwn = message.sender?.id === user?.id;
              const showAvatar = !isOwn && (
                index === 0 ||
                group.messages[index - 1]?.sender?.id !== message.sender?.id
              );

              return (
                <MessageBubble
                  key={message.id}
                    message={message}
                    isOwn={isOwn}
                    showAvatar={showAvatar}
                    onReply={onReply}
                    roomId={roomId}
                />
              );
            })}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}

interface MessageBubbleProps {
  message: Message;
  isOwn: boolean;
  showAvatar: boolean;
  onReply?: (message: Message) => void;
  roomId?: string;
}

function MessageBubble({ message, isOwn, showAvatar, onReply, roomId }: MessageBubbleProps) {
  const time = format(new Date(message.created_at), 'HH:mm');
  const [reactionPickerOpen, setReactionPickerOpen] = useState(false);
  const [reactionPickerPosition, setReactionPickerPosition] = useState<{ left: number; top: number } | null>(null);
  const reactionButtonRef = useRef<HTMLButtonElement>(null);
  const reactionPickerRef = useRef<HTMLDivElement>(null);
  const pickerCloseTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelPickerClose = useCallback(() => {
    if (pickerCloseTimeout.current !== null) {
      clearTimeout(pickerCloseTimeout.current);
      pickerCloseTimeout.current = null;
    }
  }, []);

  const closeReactionPicker = useCallback(() => {
    cancelPickerClose();
    setReactionPickerOpen(false);
  }, [cancelPickerClose]);

  const schedulePickerClose = () => {
    if (!reactionPickerOpen) return;
    cancelPickerClose();
    // Allow crossing the small gap between the message and the floating palette.
    pickerCloseTimeout.current = setTimeout(closeReactionPicker, 300);
  };

  useEffect(() => {
    if (!reactionPickerOpen) return;

    const anchorRect = reactionButtonRef.current?.getBoundingClientRect();
    const dismissOutside = (event: Event) => {
      if (!(event.target instanceof Node)) return;
      if (reactionButtonRef.current?.contains(event.target) || reactionPickerRef.current?.contains(event.target)) return;
      closeReactionPicker();
    };
    const dismissOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      closeReactionPicker();
      reactionButtonRef.current?.focus({ preventScroll: true });
    };
    const dismissOnScroll = () => {
      const rect = reactionButtonRef.current?.getBoundingClientRect();
      // Ignore a queued scroll event from bringing the button into view before
      // opening. Close only when its anchor has actually moved since opening.
      if (!rect || !anchorRect || rect.top !== anchorRect.top || rect.left !== anchorRect.left) {
        closeReactionPicker();
      }
    };

    document.addEventListener('pointerdown', dismissOutside);
    document.addEventListener('focusin', dismissOutside);
    document.addEventListener('keydown', dismissOnEscape);
    window.addEventListener('scroll', dismissOnScroll, true);
    window.addEventListener('resize', closeReactionPicker);
    window.addEventListener('blur', closeReactionPicker);
    return () => {
      cancelPickerClose();
      document.removeEventListener('pointerdown', dismissOutside);
      document.removeEventListener('focusin', dismissOutside);
      document.removeEventListener('keydown', dismissOnEscape);
      window.removeEventListener('scroll', dismissOnScroll, true);
      window.removeEventListener('resize', closeReactionPicker);
      window.removeEventListener('blur', closeReactionPicker);
    };
  }, [reactionPickerOpen, cancelPickerClose, closeReactionPicker]);

  const toggleReaction = (emoji: string) => {
    if (!roomId) return;
    const existingReaction = message.reactions?.find((reaction) => reaction.emoji === emoji);
    const hasReacted = Boolean(existingReaction?.reacted);
    const request = hasReacted
      ? chatApi.removeReaction(roomId, message.id, emoji)
      : chatApi.addReaction(roomId, message.id, emoji);

    void request.catch(() => {
      // Keep WebSocket as a fallback when the REST request is unavailable.
      wsService.send({
        type: hasReacted ? 'reaction_remove' : 'reaction_add',
        message_id: message.id,
        emoji,
      });
    });
    closeReactionPicker();
  };

  const toggleReactionPicker = () => {
    if (reactionPickerOpen) {
      closeReactionPicker();
      return;
    }
    const button = reactionButtonRef.current;
    if (!button) return;
    const rect = button.getBoundingClientRect();
    const pickerWidth = Math.min(248, window.innerWidth - 16);
    const pickerHeight = 48;
    const left = Math.min(
      Math.max(8, rect.right - pickerWidth),
      Math.max(8, window.innerWidth - pickerWidth - 8),
    );
    const top = rect.bottom + pickerHeight + 4 <= window.innerHeight
      ? rect.bottom + 4
      : Math.max(8, rect.top - pickerHeight - 4);
    setReactionPickerPosition({ left, top });
    setReactionPickerOpen(true);
  };

  if (message.is_deleted) {
    return (
      <div
        data-message-id={message.id}
        className={clsx('flex', isOwn ? 'justify-end' : 'justify-start')}
      >
        <div className="px-4 py-2 rounded-2xl bg-gray-800/50 text-gray-500 italic text-sm">
          This message has been deleted
        </div>
      </div>
    );
  }

  return (
    <div
      data-message-id={message.id}
      className={clsx('flex items-end space-x-2', isOwn ? 'flex-row-reverse space-x-reverse' : '')}
    >
      {/* Avatar */}
      <div className="w-8 flex-shrink-0">
        {showAvatar && !isOwn && message.sender && (
          <Avatar
            name={message.sender.display_name || message.sender.username}
            src={message.sender.avatar_url}
            size="sm"
          />
        )}
      </div>

      {/* Message */}
      <div
        className={clsx('group max-w-[70%]', isOwn ? 'items-end' : 'items-start')}
        onPointerEnter={cancelPickerClose}
        onPointerLeave={(event) => {
          if (event.pointerType === 'mouse') schedulePickerClose();
        }}
      >
        {/* Sender name for others */}
        {showAvatar && !isOwn && message.sender && (
          <p className="text-xs text-gray-500 mb-1 ml-1">
            {message.sender.display_name || message.sender.username}
          </p>
        )}

        <div
          className={clsx(
            'relative px-4 py-2 rounded-2xl',
            isOwn
              ? 'bg-primary-600 text-white rounded-br-md'
              : 'bg-gray-700 text-gray-100 rounded-bl-md'
          )}
        >
          {/* Reply preview */}
          {message.reply_to_preview && (
            <div className={clsx(
              'mb-2 p-2 rounded-lg text-xs border-l-2',
              isOwn ? 'bg-primary-700 border-primary-400' : 'bg-gray-600 border-gray-400'
            )}>
              <p className="font-medium">{message.reply_to_preview.sender}</p>
              <p className="truncate opacity-75">{message.reply_to_preview.content}</p>
            </div>
          )}

          {/* Content */}
          <p className="whitespace-pre-wrap break-words">{message.content}</p>

          {/* Footer */}
          <div className={clsx(
            'flex items-center mt-1 space-x-1 text-xs',
            isOwn ? 'text-primary-200' : 'text-gray-400'
          )}>
            <span>{time}</span>
            {message.is_edited && (
              <span className="italic">(edited)</span>
            )}
            {isOwn && (
              <CheckCheck className="w-4 h-4" />
            )}
          </div>
        </div>

        {message.reactions && message.reactions.length > 0 && (
          <div className={clsx('mt-1 flex flex-wrap gap-1', isOwn ? 'justify-end' : 'justify-start')}>
            {message.reactions.map((reaction) => (
              <button
                key={reaction.emoji}
                type="button"
                onClick={() => toggleReaction(reaction.emoji)}
                className={clsx(
                  'rounded-full border px-2 py-0.5 text-xs transition-colors',
                  reaction.reacted
                    ? 'border-primary-400 bg-primary-900/60 text-primary-100'
                    : 'border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-500',
                )}
                title={reaction.reacted ? 'Retirer la réaction' : 'Réagir'}
              >
                {reaction.emoji} {reaction.count}
              </button>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className={clsx(
          'mt-1 flex space-x-1 justify-end',
          reactionPickerOpen
            ? 'opacity-100'
            : 'pointer-events-none opacity-0 group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100',
        )}>
          {onReply && (
            <button
              type="button"
              onClick={() => onReply(message)}
              className="inline-flex items-center gap-1 rounded px-1.5 py-1 text-xs text-gray-500 hover:bg-gray-700 hover:text-gray-300"
              title="Répondre"
            >
              <Reply className="h-3 w-3" />
              Répondre
            </button>
          )}
          {roomId && (
            <div className="relative">
              <button
                type="button"
                ref={reactionButtonRef}
                onClick={toggleReactionPicker}
                className="inline-flex items-center gap-1 rounded px-1.5 py-1 text-xs text-gray-500 hover:bg-gray-700 hover:text-gray-300"
                aria-label="Ajouter une réaction"
                aria-expanded={reactionPickerOpen}
                aria-controls={reactionPickerOpen ? `reactions-${message.id}` : undefined}
              >
                <Plus className="h-3 w-3" />
              </button>
              {reactionPickerOpen && createPortal(
                <div
                  ref={reactionPickerRef}
                  id={`reactions-${message.id}`}
                  role="group"
                  aria-label="Choisir une réaction"
                  className="fixed z-50 grid w-[248px] max-w-[calc(100vw-16px)] grid-cols-6 gap-1 rounded-lg border border-gray-700 bg-gray-900 p-1.5 shadow-xl"
                  style={reactionPickerPosition || undefined}
                  onPointerEnter={cancelPickerClose}
                  onPointerLeave={(event) => {
                    if (event.pointerType === 'mouse') schedulePickerClose();
                  }}
                >
                  {REACTION_EMOJIS.map((emoji) => (
                    <button
                      key={emoji}
                      type="button"
                      onClick={() => toggleReaction(emoji)}
                      className="flex h-8 min-w-0 items-center justify-center rounded text-base hover:bg-gray-700 focus-visible:bg-gray-700"
                      aria-label={`Réagir avec ${emoji}`}
                      aria-pressed={Boolean(message.reactions?.find((reaction) => reaction.emoji === emoji)?.reacted)}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>,
                document.body,
              )}
            </div>
          )}
          {isOwn && (
            <>
            <button className="p-1 rounded hover:bg-gray-700 text-gray-500 hover:text-gray-300">
              <Edit2 className="w-3 h-3" />
            </button>
            <button className="p-1 rounded hover:bg-gray-700 text-gray-500 hover:text-red-400">
              <Trash2 className="w-3 h-3" />
            </button>
            </>
          )}
        </div>
        
        {/* Commitment Chip Injection */}
        {isOwn && <CommitmentChip messageId={message.id} />}
      </div>
    </div>
  );
}
