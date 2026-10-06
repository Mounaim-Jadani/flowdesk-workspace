import { usePresenceStore } from '../../stores/presenceStore';

// Une fonction utilitaire pour formater l'heure (ex: "17h30")
const formatHHMM = (isoString: string) => {
  const d = new Date(isoString);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }).replace(':', 'h');
};

export const DeepWorkBadge = ({ userId }: { userId: number }) => {
  const info = usePresenceStore((s) => s.onlineUsers[userId]?.deepWork);
  
  if (!info?.active) return null;
  
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 rounded-full whitespace-nowrap" title="Deep Work actif">
      🎧 {info.endsAt ? `jusqu'à ${formatHHMM(info.endsAt)}` : 'concentration'}
    </span>
  );
};
