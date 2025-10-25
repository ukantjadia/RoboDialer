
'use client';

import { useCall } from '@/contexts/call-context';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import CallHistoryTable from '@/components/call-history-table';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import Image from 'next/image';
import { Button } from '@/components/ui/button';

export default function Home() {
  const { state, logout } = useCall();
  const router = useRouter();

  useEffect(() => {
    if (!state.currentAgent) {
      router.replace('/login');
    } else if (state.currentAgent.role === 'admin') {
      router.replace('/dashboard');
    }
  }, [state.currentAgent, router]);

  const handleLogout = () => {
    logout();
    router.replace('/login');
  }

  if (!state.currentAgent || state.currentAgent.role === 'admin') {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-4 p-4 sm:p-6 lg:p-8">
      <div className="flex items-center justify-between space-x-4">
        <div className="flex items-center space-x-4">
            <Image
                src="/saasquatchleads_logo_notext.png" 
                alt="Caprae Capital Partners Logo"
                width={40}
                height={40}
            />
            <div>
                <h1 className="text-3xl font-bold font-headline tracking-tight">
                    Caprae Capital Partners
                </h1>
                <p className="text-sm text-muted-foreground">
                    Welcome, {state.currentAgent.name} | Your AI-powered softphone for
                    enhanced productivity.
                </p>
            </div>
        </div>
        <Button onClick={handleLogout} variant="outline">Logout</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Call History</CardTitle>
          <CardDescription>
            A log of all your recent incoming and outgoing calls.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CallHistoryTable />
        </CardContent>
      </Card>
    </div>
  );
}
