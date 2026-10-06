import { useState, useRef, useEffect, useCallback } from 'react';
import { wsService } from '../../services/websocket';
import { useChatStore } from '../../stores/chatStore';
import { usePresenceStore } from '../../stores/presenceStore';
import { useAuthStore } from '../../stores/authStore';
import { Send, Paperclip, Smile, X } from 'lucide-react';
import clsx from 'clsx';

interface MessageInputProps {
  roomId: string;
  replyTo?: { id: string; content: string; sender: string } | null;
  onCancelReply?: () => void;
}

export function MessageInput({ roomId, replyTo, onCancelReply }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [scheduleChoiceVisible, setScheduleChoiceVisible] = useState(false);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionStart, setMentionStart] = useState<number | null>(null);
  const [mentionIndex, setMentionIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const currentUser = useAuthStore(s => s.user);
  const room = useChatStore(s => s.rooms.find(r => r.id === roomId));
  const otherParticipant = room?.room_type === 'direct'
    ? room.participants_info?.find((p) => p.user.id !== currentUser?.id)?.user
    : null;
  const recipientId = otherParticipant?.id;
  const mentionCandidates = room?.room_type === 'group' && mentionQuery !== null
    ? (room.participants_info || [])
      .map((participant) => participant.user)
      .filter((participant) => participant.id !== currentUser?.id)
      .filter((participant) => participant.username.toLowerCase().includes(mentionQuery.toLowerCase()))
      .slice(0, 6)
    : [];
  const recipientDeepWork = usePresenceStore(s => 
    recipientId ? s.onlineUsers[recipientId]?.deepWork : null
  );

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [message]);

  const updateMentionState = (value: string, cursorPosition: number) => {
    if (room?.room_type !== 'group') {
      setMentionQuery(null);
      setMentionStart(null);
      return;
    }

    const textBeforeCursor = value.slice(0, cursorPosition);
    const match = textBeforeCursor.match(/(?:^|\s)@([A-Za-z0-9_.-]*)$/);
    if (!match) {
      setMentionQuery(null);
      setMentionStart(null);
      return;
    }

    setMentionQuery(match[1]);
    setMentionStart(cursorPosition - match[1].length - 1);
    setMentionIndex(0);
  };

  const selectMention = (username: string) => {
    if (mentionStart === null) return;

    const cursorPosition = textareaRef.current?.selectionStart ?? message.length;
    const nextMessage = `${message.slice(0, mentionStart)}@${username} ${message.slice(cursorPosition)}`;
    const nextCursorPosition = mentionStart + username.length + 2;
    setMessage(nextMessage);
    setMentionQuery(null);
    setMentionStart(null);
    setMentionIndex(0);

    window.requestAnimationFrame(() => {
      textareaRef.current?.focus();
      textareaRef.current?.setSelectionRange(nextCursorPosition, nextCursorPosition);
    });
  };

  // Handle typing indicator
  const handleTyping = useCallback(() => {
    if (!isTyping) {
      setIsTyping(true);
      wsService.sendTyping(true);
    }

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout to stop typing indicator
    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      wsService.sendTyping(false);
    }, 2000);
  }, [isTyping]);

  // Cleanup typing timeout on unmount
  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      if (isTyping) {
        wsService.sendTyping(false);
      }
    };
  }, [isTyping]);

  const sendCurrentMessage = (visibleFrom?: string) => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage) return;

    wsService.sendMessage(trimmedMessage, replyTo?.id, visibleFrom);
    setMessage('');
    setScheduleChoiceVisible(false);

    if (isTyping) {
      setIsTyping(false);
      wsService.sendTyping(false);
    }
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    onCancelReply?.();
    textareaRef.current?.focus();
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmedMessage = message.trim();

    if (!trimmedMessage) return;

    if (recipientDeepWork?.active && recipientDeepWork.endsAt && new Date(recipientDeepWork.endsAt).getTime() > Date.now()) {
      setScheduleChoiceVisible(true);
      return;
    }

    sendCurrentMessage();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (mentionCandidates.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setMentionIndex((index) => (index + 1) % mentionCandidates.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setMentionIndex((index) => (index - 1 + mentionCandidates.length) % mentionCandidates.length);
        return;
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        selectMention(mentionCandidates[mentionIndex].username);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setMentionQuery(null);
        setMentionStart(null);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-gray-700 bg-gray-800 p-4">
      {/* Reply Preview */}
      {replyTo && (
        <div className="mb-3 flex items-center justify-between px-3 py-2 bg-gray-700 rounded-lg">
          <div className="flex-1 min-w-0">
            <p className="text-xs text-primary-400">Replying to {replyTo.sender}</p>
            <p className="text-sm text-gray-300 truncate">{replyTo.content}</p>
          </div>
          <button
            onClick={onCancelReply}
            className="ml-2 p-1 rounded hover:bg-gray-600 text-gray-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Deep Work Warning Banner */}
      {recipientDeepWork?.active && recipientDeepWork.endsAt && (
        <div className="flex items-center gap-2 mb-2 rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
          <span>🎧</span>
          <span>
            Cette personne est actuellement concentrée (jusqu'à {new Date(recipientDeepWork.endsAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }).replace(':', 'h')}). 
            Votre message lui sera remis silencieusement.
          </span>
          {scheduleChoiceVisible && (
            <div className="ml-auto flex shrink-0 gap-1">
              <button type="button" onClick={() => sendCurrentMessage()} className="rounded-md bg-amber-600 px-2 py-1 text-white hover:bg-amber-700">
                Maintenant
              </button>
              <button type="button" onClick={() => sendCurrentMessage(recipientDeepWork.endsAt || undefined)} className="rounded-md bg-indigo-600 px-2 py-1 text-white hover:bg-indigo-700">
                Programmer
              </button>
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end space-x-3">
        {/* Attachment Button */}
        <button
          type="button"
          className="p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
        >
          <Paperclip className="w-5 h-5" />
        </button>

        {/* Input Area */}
         <div className="flex-1 relative">
           {mentionCandidates.length > 0 && (
             <div className="absolute bottom-full left-0 z-30 mb-2 w-64 overflow-hidden rounded-lg border border-gray-600 bg-gray-800 shadow-xl">
               <p className="border-b border-gray-700 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                 Mentionner un membre
               </p>
               {mentionCandidates.map((participant, index) => (
                 <button
                   key={participant.id}
                   type="button"
                   onMouseDown={(event) => event.preventDefault()}
                   onClick={() => selectMention(participant.username)}
                   className={clsx(
                     'flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-200 transition-colors',
                     index === mentionIndex ? 'bg-primary-600 text-white' : 'hover:bg-gray-700',
                   )}
                 >
                   <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-500/30 text-xs font-semibold">
                     {participant.username.charAt(0).toUpperCase()}
                   </span>
                   <span>
                     <span className="font-medium">@{participant.username}</span>
                     {participant.display_name && participant.display_name !== participant.username && (
                       <span className="ml-2 text-xs text-gray-400">{participant.display_name}</span>
                     )}
                   </span>
                 </button>
               ))}
             </div>
           )}
           <textarea
            ref={textareaRef}
             value={message}
             onChange={(e) => {
               const nextMessage = e.target.value;
               setMessage(nextMessage);
               updateMentionState(nextMessage, e.target.selectionStart ?? nextMessage.length);
               handleTyping();
             }}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-gray-100 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            style={{ maxHeight: '150px' }}
          />
        </div>

        {/* Emoji Button */}
        <button
          type="button"
          className="p-2 rounded-lg hover:bg-gray-700 transition-colors text-gray-400 hover:text-white"
        >
          <Smile className="w-5 h-5" />
        </button>

        {/* Send Button */}
        <button
          type="submit"
          disabled={!message.trim()}
          className={clsx(
            'p-3 rounded-xl transition-all duration-200',
            message.trim()
              ? 'bg-primary-600 hover:bg-primary-700 text-white'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
          )}
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      <p className="mt-2 text-xs text-gray-500 text-center">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
