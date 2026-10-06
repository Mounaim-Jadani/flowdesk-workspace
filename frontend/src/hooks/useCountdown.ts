import { useState, useEffect } from 'react';

export function useCountdown(endsAt: string | null): string | null {
  const [timeLeft, setTimeLeft] = useState<string | null>(null);

  useEffect(() => {
    if (!endsAt) {
      setTimeLeft(null);
      return;
    }

    const calculateTimeLeft = () => {
      const end = new Date(endsAt).getTime();
      const now = new Date().getTime();
      const difference = end - now;

      if (difference <= 0) {
        return '00:00';
      }

      const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((difference % (1000 * 60)) / 1000);

      const parts = [];
      if (hours > 0) {
        parts.push(hours.toString().padStart(2, '0'));
      }
      parts.push(minutes.toString().padStart(2, '0'));
      parts.push(seconds.toString().padStart(2, '0'));

      return parts.join(':');
    };

    // Update immediately
    setTimeLeft(calculateTimeLeft());

    const interval = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);

    return () => clearInterval(interval);
  }, [endsAt]);

  return timeLeft;
}
