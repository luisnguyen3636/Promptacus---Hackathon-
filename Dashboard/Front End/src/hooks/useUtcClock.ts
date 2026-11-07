import { useState, useEffect } from 'react';

export function useUtcClock(): string {
  const [clockString, setClockString] = useState<string>('Mar 23, 2026 · 16:47:26 UTC');

  useEffect(() => {
    function formatUtc(): string {
      const now = new Date();
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const month = months[now.getUTCMonth()];
      const date = String(now.getUTCDate()).padStart(2, '0');
      const year = now.getUTCFullYear();
      const hours = String(now.getUTCHours()).padStart(2, '0');
      const minutes = String(now.getUTCMinutes()).padStart(2, '0');
      const seconds = String(now.getUTCSeconds()).padStart(2, '0');
      return `${month} ${date}, ${year} · ${hours}:${minutes}:${seconds} UTC`;
    }

    setClockString(formatUtc());
    const interval = setInterval(() => {
      setClockString(formatUtc());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return clockString;
}
