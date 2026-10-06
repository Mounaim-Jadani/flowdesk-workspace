interface TypingUser {
  userId: number;
  username: string;
  timestamp: number;
}

interface TypingIndicatorProps {
  users: TypingUser[];
}

export function TypingIndicator({ users }: TypingIndicatorProps) {
  if (users.length === 0) return null;

  const getTypingText = () => {
    if (users.length === 1) {
      return `${users[0].username} is typing`;
    } else if (users.length === 2) {
      return `${users[0].username} and ${users[1].username} are typing`;
    } else {
      return `${users[0].username} and ${users.length - 1} others are typing`;
    }
  };

  return (
    <div className="px-4 py-2 flex items-center space-x-2">
      <div className="typing-indicator">
        <span />
        <span />
        <span />
      </div>
      <span className="text-sm text-gray-400">{getTypingText()}</span>
    </div>
  );
}
