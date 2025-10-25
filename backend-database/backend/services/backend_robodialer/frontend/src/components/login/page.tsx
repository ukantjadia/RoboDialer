
'use client';

import { useEffect, useState } from 'react';
import { useCall } from '@/contexts/call-context';
import type { Agent } from '@/lib/types';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useRouter } from 'next/navigation';
import { Loader2, User, AlertCircle } from 'lucide-react';
import Image from 'next/image';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';

export default function LoginPage() {
  const { loginAsAgent, state, fetchAgents } = useCall();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoggingIn, setIsLoggingIn] = useState<number | null>(null); // Store agentId
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (state.currentAgent) {
      router.replace('/');
    }
  }, [state.currentAgent, router]);

  useEffect(() => {
    const loadAgents = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const fetchedAgents = await fetchAgents();
        if (fetchedAgents && fetchedAgents.length > 0) {
          setAgents(fetchedAgents);
        } else {
          setError('No agents found. Please check the backend configuration.');
        }
      } catch (e: any) {
        setError(e.message || 'Failed to fetch agents.');
      } finally {
        setIsLoading(false);
      }
    };
    loadAgents();
  }, [fetchAgents]);

  const handleLogin = async (agent: Agent) => {
    setIsLoggingIn(agent.id);
    await loginAsAgent(agent);
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <Image
            src="/saasquatchleads_logo_notext.png"
            alt="Caprae Capital Partners Logo"
            width={50}
            height={50}
            className="mb-2"
            unoptimized
          />
          <CardTitle className="text-2xl">Caprae Capital Partners</CardTitle>
          <CardDescription>Select an agent to start your session</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {isLoading ? (
              <div className="flex justify-center items-center p-8">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : error ? (
              <div className="text-destructive text-center p-4 flex items-center gap-2 justify-center">
                <AlertCircle className="h-5 w-5" />
                <p>{error}</p>
              </div>
            ) : (
              <ScrollArea className="h-64">
                <div className="space-y-2 pr-4">
                  {agents.map((agent) => (
                    <Card key={agent.id} className="p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                           <Avatar>
                            <AvatarFallback>
                                <User />
                            </AvatarFallback>
                           </Avatar>
                           <div>
                               <p className="font-semibold">{agent.name}</p>
                               <p className="text-sm text-muted-foreground">{agent.email}</p>
                           </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => handleLogin(agent)}
                          disabled={isLoggingIn !== null}
                          className="w-24"
                        >
                          {isLoggingIn === agent.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            'Login'
                          )}
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
