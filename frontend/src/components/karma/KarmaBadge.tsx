import { KarmaBadge as KarmaBadgeData } from '../../stores/karmaStore';

const LABELS: Record<string, string> = {
  problem_solver: 'Résolveur de problèmes',
  reliable_partner: 'Partenaire fiable',
  mentor: 'Mentor',
  pillar: 'Pilier de l’équipe',
  top_contributor: 'Top Contributeur',
};

export function KarmaBadge({ badge }: { badge: KarmaBadgeData | string }) {
  const kind = typeof badge === 'string' ? badge : badge.kind;
  return (
    <span
      title={LABELS[kind] || kind}
      className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-amber-100 text-sm dark:bg-amber-900"
    >
      🏅
    </span>
  );
}
