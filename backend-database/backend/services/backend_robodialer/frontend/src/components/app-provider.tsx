
'use client';

import { CallProvider, useCall } from '@/contexts/call-context';
import { Toaster } from '@/components/ui/toaster';
import Softphone from '@/components/softphone';
import IncomingCallDialog from '@/components/incoming-call-dialog';
import PostCallSheet from '@/components/post-call-sheet';
import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import VoicemailDialog from './voicemail-dialog';
import { useRouter, useSearchParams } from 'next/navigation';

function AppShell({ children }: { children: React.ReactNode }) {
  const { state } = useCall();
  const postCall = state.showPostCallSheetForId ? state.allCallHistory.find(c => c.id === state.showPostCallSheetForId) : null;
  const pathname = usePathname();

  const showSoftphone = state.currentAgent && state.currentAgent.role === 'agent' && pathname !== '/login';

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      // Only run this for logged-in agents
      if (state.currentAgent && state.currentAgent.role === 'agent') {
        const url = `/api/agents/${state.currentAgent.id}`;
        const data = JSON.stringify({ status: 'inactive' });

        // Use fetch with keepalive to ensure the request is sent
        // even when the page is closing. This is more reliable than sendBeacon
        // for PUT/POST requests.
        try {
          fetch(url, {
            method: 'PUT',
            body: data,
            headers: {
              'Content-Type': 'application/json',
            },
            keepalive: true,
          });
        } catch (error) {
            // This might fail if the browser blocks it, but it's our best effort
            console.error('Error sending final status update:', error);
        }
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [state.currentAgent]);

  return (
    <>
      {children}
      {showSoftphone && <Softphone />}
      <Toaster />
      {state.showIncomingCall && state.activeCall && <IncomingCallDialog call={state.activeCall} />}
      {postCall && <PostCallSheet call={postCall} />}
      <VoicemailDialog />
    </>
  );
}


export function AppProvider({ children }: { children: React.ReactNode }) {
  return (
    <CallProvider>
      <AppShell>
        {children}
      </AppShell>
    </CallProvider>
  );
}
