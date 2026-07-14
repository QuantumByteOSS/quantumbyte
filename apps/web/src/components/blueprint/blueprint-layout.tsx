'use client';

import { SidebarSimple } from '@phosphor-icons/react';
import { useRef, useState } from 'react';
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
  type ImperativePanelHandle,
} from 'react-resizable-panels';
import { AppPreview } from './app-preview';
import { ChatPanel } from './chat-panel';
import { HarnessSlide } from './harness-slide';
import { useProjectStream } from './use-project-stream';

function ResizeHandle() {
  return (
    <PanelResizeHandle className="w-1 shrink-0 transition-colors hover:bg-primary/20 data-[resize-handle-state=drag]:bg-primary/40" />
  );
}

export function BlueprintLayout({
  projectId,
  title,
  updatedAt,
}: {
  projectId: string;
  title: string;
  updatedAt: string;
}) {
  const chatRef = useRef<ImperativePanelHandle>(null);
  const [chatCollapsed, setChatCollapsed] = useState(false);

  // One shared SSE connection for the whole blueprint view — chat + harness both
  // read from it (see useProjectStream: browsers cap ~6 connections per origin).
  const { messages, project, harness, poke, refetch } = useProjectStream(projectId, {
    title,
    updatedAt,
  });

  return (
    <div className="h-screen bg-slate-50">
      <PanelGroup direction="horizontal">
        {/* Left: chat */}
        <Panel
          ref={chatRef}
          defaultSize={25}
          minSize={15}
          maxSize={30}
          collapsible
          collapsedSize={0}
          onCollapse={() => setChatCollapsed(true)}
          onExpand={() => setChatCollapsed(false)}
          className="h-full"
        >
          <ChatPanel
            projectId={projectId}
            title={project.title || title}
            updatedAt={project.updatedAt || updatedAt}
            messages={messages}
            onSent={poke}
            onCollapse={() => chatRef.current?.collapse()}
          />
        </Panel>
        <ResizeHandle />

        {/* Right: header + harness + preview */}
        <Panel defaultSize={75} minSize={50} className="h-full min-h-0">
          <div className="flex h-full min-h-0 flex-col overflow-hidden">
            <div className="flex items-center">
              {chatCollapsed && (
                <button
                  type="button"
                  aria-label="Expand chat"
                  onClick={() => chatRef.current?.expand()}
                  className="mt-1 ml-2 rounded-md p-1.5 text-slate-500 hover:bg-slate-200"
                >
                  <SidebarSimple size={16} />
                </button>
              )}
            </div>

            <div data-chatcollapsed={chatCollapsed} className="mr-2 ms-1 my-3 data-[chatcollapsed=true]:mt-1 min-h-0 flex-1 overflow-hidden rounded-2xl border-2 border-slate-200 bg-white">
              <PanelGroup direction="horizontal">
                {/* Center: harness slide */}
                <Panel defaultSize={65} minSize={40} className="h-full min-h-0">
                  <div className="flex h-full min-h-0 flex-col">
                    <div className="min-h-0 flex-1">
                      <HarnessSlide
                        projectId={projectId}
                        harness={harness}
                        onPoke={poke}
                        onRefetch={refetch}
                      />
                    </div>
                  </div>
                </Panel>
                <ResizeHandle />

                {/* Right: app preview */}
                <Panel defaultSize={35} minSize={20} maxSize={50} className="h-full">
                  <AppPreview projectId={projectId} />
                </Panel>
              </PanelGroup>
            </div>
          </div>
        </Panel>
      </PanelGroup>
    </div>
  );
}
