import { useState, useRef, useEffect } from 'react';
import { Headphones, ChevronDown } from 'lucide-react';
import { usePresenceStore } from '../../stores/presenceStore';
import { useCountdown } from '../../hooks/useCountdown';
import { presenceApi } from '../../api/presence';
import toast from 'react-hot-toast';

export function DeepWorkButton() {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  const mySession = usePresenceStore((state) => state.mySession);
  const timeLeft = useCountdown(mySession?.endsAt || null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleStart = async (duration: number) => {
    try {
      setIsLoading(true);
      await presenceApi.startDeepWork(duration);
      toast.success(`Deep Work activé (${duration === 0 ? "jusqu'à pause" : duration + ' min'})`);
      setIsOpen(false);
    } catch (error) {
      toast.error("Erreur lors de l'activation du Deep Work");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    try {
      setIsLoading(true);
      await presenceApi.stopDeepWork();
    } catch (error) {
      toast.error("Erreur lors de la désactivation du Deep Work");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const DURATION_OPTIONS = [
    { label: '1 heure', minutes: 60 },
    { label: '2 heures', minutes: 120 },
    { label: '4 heures', minutes: 240 },
    { label: "Jusqu'à pause", minutes: 0 },
  ];

  if (mySession?.active) {
    return (
      <button
        onClick={handleStop}
        disabled={isLoading}
        className="relative inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-bold bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:from-indigo-600 hover:to-purple-700 transition-all shadow-md overflow-hidden group"
        title="Arrêter la session"
      >
        <div className="absolute inset-0 bg-white/20 animate-pulse opacity-0 group-hover:opacity-100 transition-opacity"></div>
        <Headphones className="h-4 w-4 animate-pulse" />
        <span className="w-12 text-center">{timeLeft}</span>
      </button>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors"
      >
        <Headphones className="h-4 w-4" />
        <ChevronDown className={`h-3 w-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute bottom-full right-0 mb-2 w-48 rounded-lg bg-white dark:bg-slate-900 shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden z-50 transform origin-bottom-right transition-all">
          <div className="py-1">
            <div className="px-3 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Démarrer Deep Work
            </div>
            {DURATION_OPTIONS.map((option) => (
              <button
                key={option.minutes}
                onClick={() => handleStart(option.minutes)}
                className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
