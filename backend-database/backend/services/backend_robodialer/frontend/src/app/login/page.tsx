
'use client';

import { useEffect, useState, useCallback } from 'react';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useRouter } from 'next/navigation';
import { Loader2, User, AlertCircle, ShieldCheck, Phone } from 'lucide-react';
import Image from 'next/image';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';

function AgentLoginTab() {
  const { loginAsAgent, state, fetchAgents } = useCall();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoggingIn, setIsLoggingIn] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);
  const router = useRouter();

  useEffect(() => {
    if (state.currentAgent && state.currentAgent.role === 'agent') {
      router.replace('/');
    }
  }, [state.currentAgent, router]);

  const loadAgents = useCallback(async () => {
    if (attempts >= 5) {
      setError('No agents found. Please check the backend configuration.');
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const fetchedAgents = await fetchAgents();
      if (fetchedAgents && fetchedAgents.length > 0) {
        // Filter out archived agents and hardcoded admin agents from login
        const availableAgents = fetchedAgents.filter(a => 
          !a.is_archived && 
          a.name !== 'Zackary Beckham' && 
          a.name !== 'Kevin Hong'
        );
        setAgents(availableAgents);
        setIsLoading(false);
      } else {
        // If fetchAgents returns empty, it might be a temporary issue.
        setTimeout(() => {
            setAttempts(prev => prev + 1);
        }, 2000); // Wait 2 seconds before retrying
      }
    } catch (e: any) {
       setTimeout(() => {
            setAttempts(prev => prev + 1);
        }, 2000);
    }
  }, [fetchAgents, attempts]);

  useEffect(() => {
    loadAgents();
  }, [attempts, loadAgents]);

  const handleLogin = async (agent: Agent) => {
    setIsLoggingIn(agent.id);
    await loginAsAgent(agent, 'agent');
  };

  if (isLoading && !error) {
    return (
      <div className="flex justify-center items-center p-8 h-64">
        <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 animate-spin" />
            <p className="text-sm text-muted-foreground">Loading agents...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-destructive text-center p-4 flex items-center gap-2 justify-center h-64">
        <AlertCircle className="h-5 w-5" />
        <p>{error}</p>
      </div>
    );
  }
  
  if (agents.length === 0) {
     return (
      <div className="text-muted-foreground text-center p-4 flex items-center gap-2 justify-center h-64">
        <User className="h-5 w-5" />
        <p>No agents available to log in.</p>
      </div>
    );
  }

  return (
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
  );
}


function AdminLoginTab() {
  const { loginAsAgent, state } = useCall();
  
  const hardcodedAdmins: Agent[] = [
    { id: 999, name: 'Zackary Beckham', email: 'zack@capraecapital.com', phone: '', status: 'admin', role: 'admin' },
    { id: 998, name: 'Kevin Hong', email: 'kevin@capraecapital.com', phone: '', status: 'admin', role: 'admin' }
  ];
  const adminCredentials: { [email: string]: string } = {
    'zack@capraecapital.com': 'zack@caprae123',
    'kevin@capraecapital.com': 'kevin@caprae123',
  };
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (state.currentAgent && state.currentAgent.role === 'admin') {
      router.replace('/dashboard');
    }
  }, [state.currentAgent, router]);

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoggingIn(true);
    setError(null);

    const lowerCaseEmail = email.toLowerCase();
    const expectedPassword = adminCredentials[lowerCaseEmail];

    if (expectedPassword && password === expectedPassword) {
      const adminUser = hardcodedAdmins.find(a => a.email.toLowerCase() === lowerCaseEmail);
      if (adminUser) {
        await loginAsAgent(adminUser, 'admin');
        // useEffect will handle navigation
      } else {
        // This case should theoretically not happen if credentials are correct
        setError('An unexpected error occurred. Admin profile mismatch.');
        setIsLoggingIn(false);
      }
    } else {
      setError('Invalid email or password.');
      setIsLoggingIn(false);
    }
  };
  
  return (
    <form onSubmit={handleLogin} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="admin@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isLoggingIn}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={isLoggingIn}
        />
      </div>
      {error && (
        <div className="text-destructive text-sm flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
      <Button type="submit" className="w-full" disabled={isLoggingIn}>
        {isLoggingIn && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Login as Admin
      </Button>
    </form>
  );
}

export default function LoginPage() {
  const { state } = useCall();
  const router = useRouter();

  // Redirect if already logged in
  useEffect(() => {
    if (state.currentAgent) {
      if (state.currentAgent.role === 'admin') {
        router.replace('/dashboard');
      } else {
        router.replace('/');
      }
    }
  }, [state.currentAgent, router]);

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
          <CardDescription>Select your role to start your session</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="agent" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="agent">
                <Phone className="mr-2 h-4 w-4" /> Agent
              </TabsTrigger>
              <TabsTrigger value="admin">
                <ShieldCheck className="mr-2 h-4 w-4" /> Admin
              </TabsTrigger>
            </TabsList>
            <TabsContent value="agent" className="pt-4">
                <AgentLoginTab />
            </TabsContent>
            <TabsContent value="admin" className="pt-4">
                <AdminLoginTab />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
