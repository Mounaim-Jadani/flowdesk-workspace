import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { useKarmaStore } from '../../stores/karmaStore';
import { KarmaBadge } from './KarmaBadge';

export function KarmaPanel({ roomId, isGroup }: { roomId: string; isGroup: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const { myKarma, leaderboard, loading, load } = useKarmaStore();

  useEffect(() => {
    void load(isGroup ? roomId : undefined);
  }, [load, roomId, isGroup]);

  return (
    <div className="border-t border-slate-700 bg-gray-850 px-3 py-2 text-xs text-slate-300">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left hover:bg-slate-800"
      >
        <span className="inline-flex items-center gap-2 font-semibold"><Sparkles className="h-4 w-4 text-amber-400" /> Karma</span>
        <span className="inline-flex items-center gap-2">{myKarma?.monthly ?? 0} ce mois {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}</span>
      </button>
      {expanded && (
        <div className="mt-2 space-y-3 rounded-lg bg-slate-900/70 p-3">
          <div className="flex items-center justify-between">
            <span>Total : <strong className="text-emerald-400">{myKarma?.total ?? 0}</strong></span>
           <span>Rang : <strong>{myKarma?.rank ?? '—'}</strong></span>
          </div>
          <div className="flex gap-1">
            {(myKarma?.badges || []).map((badge) => <KarmaBadge key={`${badge.kind}-${badge.period_key || 'all'}`} badge={badge} />)}
          </div>
          {isGroup && <div className="space-y-1 border-t border-slate-700 pt-2">
            <p className="font-semibold text-slate-400">Classement du groupe</p>
            {loading && <p className="text-slate-500">Chargement…</p>}
            {leaderboard.map((entry, index) => (
              <div key={entry.user_id} className="flex items-center justify-between py-1">
                <span><span className="mr-2 text-slate-500">{index + 1}.</span>{entry.username}</span>
                <strong className="text-emerald-400">{entry.score}</strong>
              </div>
            ))}
            {!loading && leaderboard.length === 0 && <p className="text-slate-500">Aucune contribution ce mois.</p>}
          </div>}
        </div>
      )}
    </div>
  );
}
