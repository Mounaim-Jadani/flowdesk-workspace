import { useEffect, useRef } from 'react';
import { format, isToday, isYesterday } from 'date-fns';
import clsx from 'clsx';
import { Message } from '../../types';
import { useAuthStore } from '../../stores/authStore';
import { Avatar } from '../ui/Avatar';
import { CheckCheck, Edit2, Trash2 } from 'lucide-react';
import { CommitmentChip } from '../checklist/CommitmentChip';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const user = useAuthStore((state) => state.user);

  // Reliable auto-scroll using ResizeObserver
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Function to scroll to bottom
    const scrollToBottom = () => {
      container.scrollTop = container.scrollHeight;
    };

    // Scroll immediately on mount or message length change
    scrollToBottom();
    // Also use a small timeout for any delayed renders
    setTimeout(scrollToBottom, 150);

    // Observe changes in the container's size (e.g. when textarea shrinks)
    const resizeObserver = new ResizeObserver(() => {
      scrollToBottom();
    });
    
    // Observe changes to the children (e.g. DOM nodes added/removed)
    const mutationObserver = new MutationObserver(() => {
      scrollToBottom();
    });

    resizeObserver.observe(container);
    mutationObserver.observe(container, { childList: true, subtree: true });

    return () => {
      resizeObserver.disconnect();
      mutationObserver.disconnect();
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
}

function MessageBubble({ message, isOwn, showAvatar }: MessageBubbleProps) {
  const time = format(new Date(message.created_at), 'HH:mm');

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
      <div className={clsx('group max-w-[70%]', isOwn ? 'items-end' : 'items-start')}>
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

        {/* Actions */}
        {isOwn && (
          <div className="hidden group-hover:flex mt-1 space-x-1 justify-end">
            <button className="p-1 rounded hover:bg-gray-700 text-gray-500 hover:text-gray-300">
              <Edit2 className="w-3 h-3" />
            </button>
            <button className="p-1 rounded hover:bg-gray-700 text-gray-500 hover:text-red-400">
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        )}
        
        {/* Commitment Chip Injection */}
        {isOwn && <CommitmentChip messageId={message.id} />}
      </div>
    </div>
  );
}
