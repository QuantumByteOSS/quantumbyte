'use client';

import {
  ArrowClockwise,
  ArrowSquareOut,
  CircleNotch,
  DeviceMobile,
  DeviceTablet,
  Monitor,
} from '@phosphor-icons/react';
import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';

// App Preview (tasks T6/T7/T8). Three states driven by the ping-test route
// GET /api/projects/[id]/preview (T5):
//   hidden   — no preview port allocated (no live affinity / no chat yet)
//   starting — port allocated, app not answering (installing / booting / restarting)
//   ready    — app answered: render it in an iframe inside a device frame
// Once the preview has been ready, a failing ping falls back to `starting`
// ("restarting…"), never to `hidden` — the panel must not flash away.
type PingState = 'hidden' | 'starting' | 'ready';

type PreviewStatus = {
  state: PingState;
  port: number | null;
  previewUrl: string | null;
};

type DeviceMode = 'mobile' | 'tablet' | 'desktop';

// Screen cutout of each device PNG, measured from the transparent pixels of the
// asset (see docs/tasks/2026-07-14-preview-runtime-chat.md). Percentages of the
// full PNG so the iframe can sit under the frame at any rendered size.
const DEVICE_FRAMES: Record<
  Exclude<DeviceMode, 'desktop'>,
  { src: string; aspect: string; screen: { left: string; top: string; width: string; height: string }; radius: string }
> = {
  mobile: {
    src: '/devices/iphone17.png',
    aspect: '1019 / 2052',
    screen: { left: '6.87%', top: '3.41%', width: '86.16%', height: '93.13%' },
    radius: '9%',
  },
  tablet: {
    src: '/devices/tablet.png',
    aspect: '4512 / 5872',
    screen: { left: '4.43%', top: '3.61%', width: '90.78%', height: '93.05%' },
    radius: '2%',
  },
};

const POLL_MS_WAITING = 2500;
const POLL_MS_READY = 8000;

export function AppPreview({ projectId }: { projectId: string }) {
  const [status, setStatus] = useState<PreviewStatus>({
    state: 'hidden',
    port: null,
    previewUrl: null,
  });
  const [mode, setMode] = useState<DeviceMode>('mobile');
  // Bumped to force-remount the iframe: on refresh, and when the app (re)becomes
  // reachable so a stale error page never lingers.
  const [frameEpoch, setFrameEpoch] = useState(0);
  const wasReady = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const tick = async () => {
      let next: PreviewStatus | null = null;
      try {
        const res = await fetch(`/api/projects/${projectId}/preview`, { cache: 'no-store' });
        if (res.ok) next = await res.json();
      } catch {
        /* network blip — keep last state */
      }
      if (cancelled) return;
      if (next) {
        setStatus((prev) => {
          // J8: after the port disappears mid-session (affinity expired) the panel
          // may go hidden again — that's correct, the app is gone. But a mere ping
          // failure while the port is still allocated stays `starting`.
          if (next!.state === 'ready' && !wasReady.current) {
            wasReady.current = true;
            setFrameEpoch((e) => e + 1); // fresh iframe the moment it boots
          }
          if (next!.state !== 'ready') wasReady.current = false;
          return prev.state === next!.state && prev.port === next!.port ? prev : next!;
        });
      }
      timer = setTimeout(tick, next?.state === 'ready' ? POLL_MS_READY : POLL_MS_WAITING);
    };

    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [projectId]);

  return (
    <div
      className="flex h-full w-full flex-col"
      style={{
        backgroundColor: 'rgba(241,245,249,0.6)',
        backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)',
        backgroundSize: '16px 16px',
      }}
    >
      {status.state !== 'hidden' && (
        <PreviewToolbar
          mode={mode}
          onMode={setMode}
          previewUrl={status.state === 'ready' ? status.previewUrl : null}
          onRefresh={() => setFrameEpoch((e) => e + 1)}
        />
      )}

      <div className="min-h-0 flex-1 p-4">
        {status.state === 'hidden' ? (
          <HiddenHint />
        ) : mode === 'desktop' ? (
          <DesktopFrame status={status} epoch={frameEpoch} />
        ) : (
          <DeviceFrame device={mode} status={status} epoch={frameEpoch} />
        )}
      </div>
    </div>
  );
}

function PreviewToolbar({
  mode,
  onMode,
  previewUrl,
  onRefresh,
}: {
  mode: DeviceMode;
  onMode: (m: DeviceMode) => void;
  previewUrl: string | null;
  onRefresh: () => void;
}) {
  const modes: { id: DeviceMode; icon: typeof DeviceMobile; label: string }[] = [
    { id: 'mobile', icon: DeviceMobile, label: 'Mobile' },
    { id: 'tablet', icon: DeviceTablet, label: 'Tablet' },
    { id: 'desktop', icon: Monitor, label: 'Desktop' },
  ];
  return (
    <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-white/70 px-3 py-1.5">
      <div className="flex rounded-lg bg-slate-100 p-0.5">
        {modes.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            type="button"
            aria-label={`${label} preview`}
            aria-pressed={mode === id}
            onClick={() => onMode(id)}
            className={`rounded-md px-2 py-1 transition-colors ${
              mode === id
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Icon size={16} />
          </button>
        ))}
      </div>
      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="Reload preview"
          onClick={onRefresh}
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
        >
          <ArrowClockwise size={15} />
        </button>
        {previewUrl && (
          <a
            href={previewUrl}
            target="_blank"
            rel="noreferrer"
            aria-label="Open app in new tab"
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
          >
            <ArrowSquareOut size={15} />
          </a>
        )}
      </div>
    </div>
  );
}

function HiddenHint() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <Image src="/logo_qbits_fav.png" alt="" width={40} height={40} className="opacity-40" />
      <p className="max-w-[16rem] text-xs text-slate-400">
        Your app preview appears here once the agent starts building.
      </p>
    </div>
  );
}

function StartingInfo({ status }: { status: PreviewStatus }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 bg-white px-6 text-center">
      <Image src="/logo_qbits_fav.png" alt="" width={48} height={48} />
      <p className="flex items-center gap-2 text-sm text-slate-600">
        <CircleNotch size={16} className="animate-spin text-slate-400" />
        Starting your app…
      </p>
      <p className="text-xs text-slate-400">
        Port {status.port} is reserved on localhost — the preview connects as soon
        as the app answers.
      </p>
    </div>
  );
}

function ScreenContent({ status, epoch }: { status: PreviewStatus; epoch: number }) {
  if (status.state !== 'ready' || !status.previewUrl) {
    return <StartingInfo status={status} />;
  }
  return (
    <iframe
      key={`${status.previewUrl}-${epoch}`}
      src={status.previewUrl}
      title="App preview"
      className="h-full w-full border-0 bg-white"
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
    />
  );
}

/** Largest {width, height} of the given aspect ratio that fits the observed
 * container — CSS alone can't express "fit both bounds" for an aspect-ratio box
 * whose parent isn't the viewport, so measure it. */
function useFitBox(ref: React.RefObject<HTMLDivElement | null>, aspect: number) {
  const [box, setBox] = useState<{ width: number; height: number } | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width: cw, height: ch } = entry.contentRect;
      if (cw <= 0 || ch <= 0) return;
      const height = Math.min(ch, cw / aspect);
      setBox({ width: height * aspect, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref, aspect]);
  return box;
}

function DeviceFrame({
  device,
  status,
  epoch,
}: {
  device: Exclude<DeviceMode, 'desktop'>;
  status: PreviewStatus;
  epoch: number;
}) {
  const frame = DEVICE_FRAMES[device];
  const containerRef = useRef<HTMLDivElement>(null);
  const [aw, ah] = frame.aspect.split('/').map((s) => Number(s.trim()));
  const box = useFitBox(containerRef, aw / ah);
  return (
    <div ref={containerRef} className="flex h-full items-center justify-center">
      {/* The PNG's screen area is a transparent cutout: the app renders in a div
          positioned under it and the frame image overlays everything (pointer
          events pass through the cutout to the iframe). */}
      <div
        className="relative drop-shadow-2xl"
        style={
          box
            ? { width: box.width, height: box.height }
            : { aspectRatio: frame.aspect, height: '100%', maxWidth: '100%' }
        }
      >
        <div
          className="absolute overflow-hidden"
          style={{ ...frame.screen, borderRadius: frame.radius, position: 'absolute' }}
        >
          <ScreenContent status={status} epoch={epoch} />
        </div>
        {/* Device chrome overlays the screen; unoptimized: already a local static
            asset and next/image resizing would soften the frame's fine edges. */}
        <Image
          src={frame.src}
          alt=""
          fill
          unoptimized
          className="pointer-events-none z-10 select-none"
          draggable={false}
        />
      </div>
    </div>
  );
}

function DesktopFrame({ status, epoch }: { status: PreviewStatus; epoch: number }) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-300 bg-white shadow-2xl">
      {/* Minimal browser chrome — no asset for desktop, so it's drawn in CSS. */}
      <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-100 px-3 py-2">
        <span className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
          <span className="h-2.5 w-2.5 rounded-full bg-green-400" />
        </span>
        <span className="ml-2 flex-1 truncate rounded-md bg-white px-3 py-1 text-xs text-slate-500">
          {status.previewUrl ?? 'localhost'}
        </span>
      </div>
      <div className="min-h-0 flex-1">
        <ScreenContent status={status} epoch={epoch} />
      </div>
    </div>
  );
}
