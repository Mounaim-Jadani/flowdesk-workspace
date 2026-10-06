import { useEffect, useMemo, useState } from 'react';
import { Check, ChevronDown, ChevronUp, Clock, Loader2, Sparkles, X } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { useChatStore } from '../../stores/chatStore';
import { useDigestStore } from '../../stores/digestStore';
import { ChatRoom, DigestData } from '../../types';
import { scrollToMessage } from '../../utils/messageNavigation';

interface CatchUpBannerProps {
  room: ChatRoom;
}

function formatSince(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'votre dernière visite';
  }

  return `Depuis le ${date.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })}`;
}

function getOtherParticipantName(room: ChatRoom, currentUserId?: number): string | null {
  const participant = room.participants_info?.find(({ user }) => user.id !== currentUserId);
  return participant?.user.display_name || participant?.user.username || room.display_name || null;
}

function getStats(digest: DigestData | null) {
  return {
    messageCount: digest?.stats?.message_count ?? 0,
    participants: digest?.stats?.participants ?? 0,
    decisions: digest?.stats?.decisions_count ?? 0,
    openItems: digest?.stats?.open_items ?? 0,
  };
}

function languageLabel(value?: string): string {
  return {
    french: 'français',
    english: 'anglais',
    fusha: 'arabe standard',
    darija_arabic: 'darija arabe',
    darija_latin: 'darija latin',
  }[value || ''] || value || 'automatique';
}

export function CatchUpBanner({ room }: CatchUpBannerProps) {
  const roomId = room.id;
  const digest = useDigestStore((state) => state.digestByRoom[roomId]);
  const isLoading = useDigestStore((state) => state.loadingRooms[roomId] === true);
  const error = useDigestStore((state) => state.errorByRoom[roomId]);
  const isOpen = useDigestStore((state) => state.openRooms.includes(roomId));
  const consumeDigest = useChatStore((state) => state.consumeDigest);
  const dismiss = useDigestStore((state) => state.dismiss);
  const regenerate = useDigestStore((state) => state.regenerate);
  const currentUserId = useAuthStore((state) => state.user?.id);
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState(
    () => window.localStorage.getItem('flowdesk-digest-language') || '',
  );
  const [isConsuming, setIsConsuming] = useState(false);

  useEffect(() => {
    setIsExpanded(false);
    setSelectedLanguage(window.localStorage.getItem('flowdesk-digest-language') || '');
  }, [roomId]);

  const stats = useMemo(() => getStats(digest), [digest]);
  const otherParticipantName = useMemo(
    () => getOtherParticipantName(room, currentUserId),
    [room, currentUserId],
  );

  if (!isOpen || (!digest && !isLoading && !error)) {
    return null;
  }

  const sinceLabel = digest ? formatSince(digest.since) : 'Préparation du rattrapage';
  const isDirectMessage = room.room_type === 'direct';
  const keyPoints = digest?.key_points?.slice(0, 6) ?? [];
  const mentions = digest?.mentions?.slice(0, 4) ?? [];
  const summary = digest?.summary?.trim();

  const summaryParts = isDirectMessage
    ? [`${stats.messageCount} message${stats.messageCount > 1 ? 's' : ''}${otherParticipantName ? ` de ${otherParticipantName}` : ''}`]
    : [
        `${stats.messageCount} message${stats.messageCount > 1 ? 's' : ''}`,
        ...(stats.decisions > 0 ? [`${stats.decisions} décision${stats.decisions > 1 ? 's' : ''}`] : []),
      ];

  const scrollToDigestMessage = (messageId: string) => {
    scrollToMessage(messageId);
  };

  const handleConsume = async () => {
    setIsConsuming(true);
    try {
      await consumeDigest(roomId);
    } catch {
      // The store keeps the banner visible and exposes the retry message.
    } finally {
      setIsConsuming(false);
    }
  };

  const handleOpenActions = () => {
    const key = `flowdesk-open-checklist-${roomId}`;
    sessionStorage.setItem(key, 'true');
    window.dispatchEvent(new CustomEvent('flowdesk-open-checklist', {
      detail: String(roomId),
    }));
  };

  return (
    <div className="relative z-20 w-full px-4 py-3">
      <div className="relative overflow-hidden rounded-xl border border-sky-200/70 bg-gradient-to-r from-sky-50 to-indigo-50 shadow-lg ring-1 ring-sky-200/50 dark:border-sky-800 dark:from-sky-950 dark:to-indigo-950 dark:ring-sky-800">
        <div className="pointer-events-none absolute -left-16 -top-20 h-36 w-36 rounded-full bg-sky-400/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -right-16 h-36 w-36 rounded-full bg-indigo-400/15 blur-3xl" />

        <div className="relative p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-md">
                <Sparkles className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-sky-700 dark:text-sky-300">
                  Catch-Me-Up
                </p>
                <p className="mt-0.5 truncate text-sm font-semibold text-slate-900 dark:text-white">
                  {isLoading && !digest ? 'Préparation de votre rattrapage…' : sinceLabel}
                </p>
                {digest && (
                  <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                    {summaryParts.join(' · ')}
                    {stats.openItems > 0 && (
                      <>
                        {' · '}
                        <button
                          type="button"
                          onClick={handleOpenActions}
                          className="font-medium text-violet-700 underline decoration-violet-300 underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:decoration-violet-700 dark:hover:text-violet-100"
                        >
                          {stats.openItems} action{stats.openItems > 1 ? 's' : ''} pour vous
                        </button>
                      </>
                    )}
                  </p>
                )}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-1">
              {digest && (
                <button
                  type="button"
                  onClick={() => setIsExpanded((expanded) => !expanded)}
                  disabled={isLoading || isConsuming}
                  className="inline-flex items-center gap-1 rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isExpanded ? 'Réduire' : 'Voir le rattrapage'}
                  {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                </button>
              )}
              <button
                type="button"
                onClick={() => dismiss(roomId)}
                className="rounded-full p-1.5 text-slate-500 transition-colors hover:bg-white/70 hover:text-slate-800 dark:text-slate-400 dark:hover:bg-slate-900/60 dark:hover:text-white"
                title="Fermer"
                aria-label="Fermer le rattrapage"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs text-rose-800 dark:border-rose-900 dark:bg-rose-950/60 dark:text-rose-200">
              <span>{error}</span>
              <button
                type="button"
                onClick={() => regenerate(roomId, selectedLanguage)}
                disabled={isLoading || isConsuming}
                className="rounded-md bg-rose-600 px-3 py-1.5 font-medium text-white transition-colors hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Réessayer
              </button>
            </div>
          )}

          {isExpanded && digest && (
            <div className="mt-4 space-y-4 border-t border-sky-200/70 pt-4 dark:border-sky-800/70">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-medium text-slate-600 dark:text-slate-300">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    {stats.messageCount} messages
                  </span>
                  {!isDirectMessage && <span>{stats.participants} participant{stats.participants > 1 ? 's' : ''}</span>}
                  {!isDirectMessage && stats.decisions > 0 && <span>{stats.decisions} décision{stats.decisions > 1 ? 's' : ''}</span>}
                   {stats.openItems > 0 && (
                     <button
                       type="button"
                       onClick={handleOpenActions}
                       className="font-medium text-violet-700 underline decoration-violet-300 underline-offset-2 hover:text-violet-900 dark:text-violet-300 dark:decoration-violet-700 dark:hover:text-violet-100"
                     >
                       {stats.openItems} action{stats.openItems > 1 ? 's' : ''} pour vous
                     </button>
                   )}
                </div>
                <label className="inline-flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <span>Résumé en</span>
                  <select
                    value={selectedLanguage}
                    onChange={(event) => {
                      const language = event.target.value;
                      setSelectedLanguage(language);
                      if (language) {
                        window.localStorage.setItem('flowdesk-digest-language', language);
                      } else {
                        window.localStorage.removeItem('flowdesk-digest-language');
                      }
                      regenerate(roomId, language);
                    }}
                    disabled={isLoading}
                    className="rounded-md border border-sky-200 bg-white/70 px-2 py-1 text-xs text-slate-700 outline-none transition-colors hover:bg-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-60 dark:border-sky-800 dark:bg-slate-900/60 dark:text-slate-200"
                  >
                    <option value="">Automatique</option>
                    <option value="french">Français</option>
                    <option value="english">English</option>
                    <option value="fusha">العربية الفصحى</option>
                    <option value="darija_arabic">Darija (arabe)</option>
                    <option value="darija_latin">Darija (latin)</option>
                  </select>
                </label>
                {digest.summary_language && (
                  <span className="text-[11px] text-slate-500 dark:text-slate-400">
                    Langue : {languageLabel(digest.summary_language)}
                  </span>
                )}
              </div>

              <section>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Résumé de la conversation
                </h4>
                <div dir="auto" className="whitespace-pre-line rounded-lg bg-white/60 p-3 text-sm leading-relaxed text-slate-700 ring-1 ring-black/5 dark:bg-slate-900/50 dark:text-slate-200 dark:ring-white/5">
                  {summary || 'Aucun résumé disponible pour cette période.'}
                </div>
              </section>

              {keyPoints.length > 0 && (
                <section>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Points clés
                  </h4>
                  <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-700 dark:text-slate-200">
                    {keyPoints.map((point) => (
                      <li key={point.message_id}>
                        <button
                          type="button"
                          onClick={() => scrollToDigestMessage(point.message_id)}
                          className="text-left underline decoration-sky-300 underline-offset-2 transition-colors hover:text-sky-700 dark:decoration-sky-700 dark:hover:text-sky-300"
                        >
                          {point.text}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {mentions.length > 0 && (
                <section>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
                    Vos mentions
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {mentions.map((mention) => (
                      <button
                        type="button"
                        key={mention.message_id}
                        onClick={() => scrollToDigestMessage(mention.message_id)}
                        className="max-w-full rounded-md bg-amber-50 px-2 py-1 text-left text-xs text-amber-800 transition-colors hover:bg-amber-100 dark:bg-amber-950 dark:text-amber-200 dark:hover:bg-amber-900"
                        title={mention.preview}
                      >
                        <span className="font-semibold">@{mention.username}</span>{' '}
                        <span>{mention.preview}</span>
                      </button>
                    ))}
                  </div>
                </section>
              )}

              <div className="flex flex-wrap items-center justify-end gap-2 border-t border-sky-200/70 pt-3 dark:border-sky-800/70">
                <button
                  type="button"
                  onClick={() => dismiss(roomId)}
                  className="rounded-md px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-white/70 dark:text-slate-300 dark:hover:bg-slate-900/60"
                >
                  Fermer
                </button>
                <button
                  type="button"
                  onClick={handleConsume}
                  disabled={isConsuming || isLoading}
                  className="inline-flex items-center rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 dark:focus:ring-offset-slate-950"
                >
                  <Check className="mr-1.5 h-3.5 w-3.5" />
                  Lu, c’est à jour
                </button>
              </div>
            </div>
          )}

          {isLoading && digest && (
            <div className="mt-3 inline-flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Régénération du rattrapage…
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
