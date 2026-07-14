import { CircleNotch, Rocket, RocketLaunch } from '@phosphor-icons/react/dist/ssr';

type Props = {
  status: 'ACTIVE' | 'HIDE' | 'NOT_ACTIVE';
  generationStatus:
    | 'DRAFT'
    | 'PENDING'
    | 'PROCESSING'
    | 'COMPLETED'
    | 'FAILED'
    | 'CANCELLED';
};

export function StatusBadge({ status, generationStatus }: Props) {
  if (generationStatus === 'DRAFT') {
    return (
      <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
        Draft
      </span>
    );
  }
  if (generationStatus === 'PENDING' || generationStatus === 'PROCESSING') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-slate-900 px-2.5 py-0.5 text-xs font-medium text-white">
        <CircleNotch size={12} className="animate-spin" /> Generating
      </span>
    );
  }
  if (status === 'ACTIVE') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
        <RocketLaunch size={12} weight="fill" /> Live
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-medium text-white">
      <Rocket size={12} /> Prototype
    </span>
  );
}
