
'use client';

import { useCall } from '@/contexts/call-context';
import { useRouter } from 'next/navigation';
import { useEffect, useState, useMemo, useCallback } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import Image from 'next/image';
import type { Agent, Call } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Loader2, User, RefreshCw, BarChart, FileText, Phone, Wand2, PlusCircle, Archive, Users, Timer, TimerOff, Star, Edit, Crown, AlertCircle, RotateCcw, Eye, EyeOff } from 'lucide-react';
import { evaluateAgentPerformanceAction } from '@/lib/actions';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import AddAgentDialog from '@/components/add-agent-dialog';
import ArchiveAgentDialog from '@/components/delete-agent-dialog';
import AgentEvaluationCard from '@/components/agent-evaluation-card';
import GradeAgentDialog from '@/components/grade-agent-dialog';
import { Badge } from '@/components/ui/badge';


interface AgentStats extends Agent {
    calls: Call[];
    evaluation: string;
    aiSuggestedScore: number;
    isEvaluating: boolean;
}

export default function DashboardPage() {
  const { state, fetchAgents, fetchAllCallHistory, logout, addAgent, deleteAgent, updateAgentScore, archiveAgent, unarchiveAgent } = useCall();
  const router = useRouter();
  const [agentStats, setAgentStats] = useState<AgentStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [isAddAgentOpen, setIsAddAgentOpen] = useState(false);
  const [agentToDelete, setAgentToDelete] = useState<Agent | null>(null);
  const [agentToGrade, setAgentToGrade] = useState<Agent | null>(null);
  const [showArchived, setShowArchived] = useState(false);


  useEffect(() => {
    if (!state.currentAgent || state.currentAgent.role !== 'admin') {
      router.replace('/login');
    }
  }, [state.currentAgent, router]);
  
  const loadData = useCallback(async () => {
    if (attempts >= 5) {
      setError("Could not load dashboard data. Please check the backend or try refreshing.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
        // Fetch all agents including archived ones for admin dashboard
        const response = await fetch('/api/agents?include_archived=true');
        const agentsData = await response.json();
        const agents = agentsData.agents || [];
        
        const calls = await fetchAllCallHistory();

        if ((!agents || agents.length === 0) && (!calls || calls.length === 0)) {
            setTimeout(() => setAttempts(prev => prev + 1), 2000);
            return;
        }
        
        const stats: AgentStats[] = (agents || []).map((agent: Agent) => ({
          ...agent,
          score: agent.score,
          calls: (calls || []).filter((c: Call) => String(c.agentId) === String(agent.id)),
          evaluation: '',
          aiSuggestedScore: 0,
          isEvaluating: false,
        }));

        setAgentStats(stats);
        setIsLoading(false);

    } catch (e) {
        setTimeout(() => setAttempts(prev => prev + 1), 2000);
    }
  }, [attempts, fetchAgents, fetchAllCallHistory]);

  useEffect(() => {
    if (state.currentAgent && state.currentAgent.role === 'admin') {
      loadData();
    }
  }, [state.currentAgent, loadData]);

  const filteredAgentStats = useMemo(() => {
    if (showArchived) {
      return agentStats; // Show all agents including archived
    } else {
      return agentStats.filter(agent => !agent.is_archived); // Only show active agents
    }
  }, [agentStats, showArchived]);

  const sortedAgentStats = useMemo(() => {
    return [...filteredAgentStats].sort((a, b) => (b.score || 0) - (a.score || 0));
  }, [filteredAgentStats]);

  const topPerformerId = useMemo(() => {
    if (sortedAgentStats.length > 0 && (sortedAgentStats[0].score || 0) > 0) {
      return sortedAgentStats[0].id;
    }
    return null;
  }, [sortedAgentStats]);
  
  const handleEvaluate = async (agentId: number, agentName: string) => {
    setAgentStats(prevStats => prevStats.map(stat => 
        stat.id === agentId ? { ...stat, isEvaluating: true } : stat
    ));

    const agentToEvaluate = agentStats.find(stat => stat.id === agentId);
    if (!agentToEvaluate) return;

    const result = await evaluateAgentPerformanceAction(agentName, agentToEvaluate.calls);
    
    setAgentStats(prevStats => prevStats.map(stat => 
        stat.id === agentId ? { 
            ...stat, 
            evaluation: result.evaluation || result.error || '', 
            aiSuggestedScore: result.score || 0,
            isEvaluating: false 
        } : stat
    ));
  };
  
  const handleScoreUpdate = async (agentId: number, score: number) => {
    if(updateAgentScore) {
        const success = await updateAgentScore(agentId, score);
        if (success) {
            setAgentStats(prevStats => prevStats.map(stat =>
              stat.id === agentId ? { ...stat, score: score } : stat
            ));
            setAgentToGrade(null); // Close dialog on success
        }
    }
  };
  
  const handleLogout = () => {
    logout();
    router.replace('/login');
  }

  const handleAgentAdded = async () => {
    setIsAddAgentOpen(false);
    await loadData(); // Reload all data
  }

  const handleDeleteConfirm = async () => {
    if (agentToDelete && archiveAgent) {
      const success = await archiveAgent(agentToDelete.id);
      if (success) {
        setAgentStats(prev => prev.map(stat => 
          stat.id === agentToDelete.id 
            ? { ...stat, is_archived: true, status: 'archived', is_available: false }
            : stat
        ));
        setAgentToDelete(null);
      }
    }
  };

  const handleRestoreAgent = async (agentId: number) => {
    if (unarchiveAgent) {
      const success = await unarchiveAgent(agentId);
      if (success) {
        setAgentStats(prev => prev.map(stat => 
          stat.id === agentId 
            ? { ...stat, is_archived: false, status: 'active', is_available: true }
            : stat
        ));
      }
    }
  };

  const totalCalls = useMemo(() => filteredAgentStats.reduce((sum, agent) => sum + agent.calls.length, 0), [filteredAgentStats]);
  const totalActiveAgents = useMemo(() => agentStats.filter(agent => !agent.is_archived).length, [agentStats]);
  const totalArchivedAgents = useMemo(() => agentStats.filter(agent => agent.is_archived).length, [agentStats]);

  if (!state.currentAgent || state.currentAgent.role !== 'admin') {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <p>Redirecting to login...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-8 p-4 sm:p-6 lg:p-8">
       <AddAgentDialog
        open={isAddAgentOpen}
        onOpenChange={setIsAddAgentOpen}
        onAgentAdded={handleAgentAdded}
        addAgent={addAgent}
      />
       <ArchiveAgentDialog
        open={!!agentToDelete}
        onOpenChange={() => setAgentToDelete(null)}
        agentName={agentToDelete?.name || ''}
        onConfirm={handleDeleteConfirm}
      />
      <GradeAgentDialog 
        agent={agentToGrade}
        open={!!agentToGrade}
        onOpenChange={() => setAgentToGrade(null)}
        onSave={handleScoreUpdate}
      />
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
                    Performance Dashboard
                </h1>
                <p className="text-sm text-muted-foreground">
                    Welcome, {state.currentAgent.name}. | AI-powered agent performance analysis.
                </p>
            </div>
        </div>
        <div className="flex items-center gap-2">
            <Button onClick={() => setIsAddAgentOpen(true)}>
                <PlusCircle className="mr-2 h-4 w-4" />
                Add Agent
            </Button>
            <Button 
                onClick={() => setShowArchived(!showArchived)} 
                variant="outline"
                className={showArchived ? "bg-orange-100 border-orange-300" : ""}
            >
                {showArchived ? <EyeOff className="mr-2 h-4 w-4" /> : <Eye className="mr-2 h-4 w-4" />}
                {showArchived ? 'Hide Archived' : 'Show Archived'}
                {totalArchivedAgents > 0 && (
                    <span className="ml-1 bg-orange-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                        {totalArchivedAgents}
                    </span>
                )}
            </Button>
            <Button onClick={handleLogout} variant="outline">Logout</Button>
        </div>
      </div>

        <Card>
            <CardHeader>
                <CardTitle>Team Overview</CardTitle>
                <CardDescription>A real-time summary of your team's performance metrics.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
                <Card className="p-6">
                    <div className="flex items-center gap-4">
                        <div className="bg-muted p-3 rounded-full">
                            <Users className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground">Active Agents</p>
                            <p className="text-2xl font-bold">{totalActiveAgents}</p>
                            {totalArchivedAgents > 0 && (
                                <p className="text-xs text-orange-600">
                                    +{totalArchivedAgents} archived
                                </p>
                            )}
                        </div>
                    </div>
                </Card>
                <Card className="p-6">
                    <div className="flex items-center gap-4">
                        <div className="bg-muted p-3 rounded-full">
                            <Phone className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground">Total Calls Made</p>
                            <p className="text-2xl font-bold">{totalCalls}</p>
                        </div>
                    </div>
                </Card>
                <Card className="p-6">
                    <div className="flex items-center gap-4">
                        <div className="bg-muted p-3 rounded-full">
                            <BarChart className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <div>
                            <p className="text-sm text-muted-foreground">Avg Calls per Agent</p>
                            <p className="text-2xl font-bold">
                                {totalActiveAgents > 0 ? (totalCalls / totalActiveAgents).toFixed(1) : 0}
                            </p>
                        </div>
                    </div>
                </Card>
            </CardContent>
        </Card>

      <Card>
        <CardHeader>
          <CardTitle>Agent Performance</CardTitle>
          <CardDescription>
            Detailed call metrics and AI-powered evaluation for each agent.
          </CardDescription>
        </CardHeader>
        <CardContent>
        {isLoading ? (
            <div className="flex justify-center items-center h-48">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <p className="ml-4 text-muted-foreground">Loading dashboard data...</p>
            </div>
        ) : error ? (
            <div className="text-destructive text-center p-8 flex items-center gap-2 justify-center h-48">
                <AlertCircle className="h-5 w-5" />
                <p>{error}</p>
            </div>
        ) : agentStats.length === 0 ? (
            <div className="text-muted-foreground text-center p-8 flex items-center gap-2 justify-center h-48">
                <Users className="h-5 w-5" />
                <p>No agents found. You can add one using the "Add Agent" button.</p>
            </div>
        ) : (
          <Accordion type="single" collapsible className="w-full space-y-4">
            {sortedAgentStats.map((agent) => (
              <AccordionItem value={`agent-${agent.id}`} key={agent.id} className="border-b-0">
                 <Card className={agent.is_archived ? "opacity-60 bg-gray-50/50" : ""}>
                    <div className="flex w-full items-center p-4">
                        <AccordionTrigger className="flex-1 p-0 justify-start hover:no-underline group">
                            <div className="flex items-center gap-4 text-left">
                                <Avatar className="h-12 w-12">
                                    <AvatarFallback>
                                    <User size={24} />
                                    </AvatarFallback>
                                </Avatar>
                                <div className="flex flex-col">
                                    <div className="flex items-center gap-2">
                                        <p className="text-lg font-semibold">{agent.name}</p>
                                        {agent.id === topPerformerId && !agent.is_archived && (
                                            <Badge variant="secondary" className="border-yellow-500/50 bg-yellow-500/10 text-yellow-300">
                                                <Crown className="h-4 w-4 mr-1.5"/>
                                                Top Performer
                                            </Badge>
                                        )}
                                        {agent.is_archived && (
                                            <Badge variant="secondary" className="border-orange-500/50 bg-orange-500/10 text-orange-600">
                                                <Archive className="h-4 w-4 mr-1.5"/>
                                                Archived
                                            </Badge>
                                        )}
                                    </div>
                                    <p className="text-sm text-muted-foreground">
                                    {agent.calls.length} calls recorded
                                    </p>
                                </div>
                                <div className="flex items-center gap-1 text-primary ml-4">
                                <Star className="h-5 w-5" />
                                <span className="text-lg font-bold">
                                  {(agent.score || 0).toFixed(1)}
                                </span>
                                </div>
                            </div>
                        </AccordionTrigger>
                        <div className="flex items-center gap-2 ml-4 shrink-0">
                            {agent.is_archived ? (
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        handleRestoreAgent(agent.id);
                                    }}
                                >
                                    <RotateCcw className="h-4 w-4 text-green-600 hover:text-green-700" title="Restore Agent" />
                                </Button>
                            ) : (
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setAgentToDelete(agent);
                                    }}
                                >
                                    <Archive className="h-4 w-4 text-muted-foreground hover:text-orange-600" title="Archive Agent" />
                                </Button>
                            )}
                        </div>
                    </div>
                    <AccordionContent>
                        <div className="p-6 bg-background/50 rounded-b-lg border-t">
                        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                            <div className="lg:col-span-2">
                            <h4 className="font-semibold mb-4 text-lg">
                                Call Statistics
                            </h4>
                            <Card>
                                <CardContent className="p-0">
                                <Table>
                                    <TableBody>
                                    <TableRow>
                                        <TableCell className="font-medium">Total Calls</TableCell>
                                        <TableCell className="text-right">{agent.calls.length}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell className="font-medium">Completed</TableCell>
                                        <TableCell className="text-right">{agent.calls.filter((c) => c.status === 'completed').length}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell className="font-medium">Voicemails</TableCell>
                                        <TableCell className="text-right">{agent.calls.filter((c) => c.status === 'voicemail-dropped').length}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell className="font-medium">Failed/Busy</TableCell>
                                        <TableCell className="text-right">{agent.calls.filter((c) => c.status === 'failed' || c.status === 'busy').length}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell className="font-medium flex items-center gap-2"><TimerOff className="h-4 w-4 text-yellow-500" /> Short Calls (&lt; 30s)</TableCell>
                                        <TableCell className="text-right">{agent.calls.filter(c => c.status === 'completed' && (c.duration || 0) < 30).length}</TableCell>
                                    </TableRow>
                                     <TableRow>
                                        <TableCell className="font-medium flex items-center gap-2"><Timer className="h-4 w-4 text-green-500" /> Long Calls (&gt; 3m)</TableCell>
                                        <TableCell className="text-right">{agent.calls.filter(c => c.status === 'completed' && (c.duration || 0) > 180).length}</TableCell>
                                    </TableRow>
                                    <TableRow className="border-none">
                                        <TableCell className="font-medium">Avg. Duration</TableCell>
                                        <TableCell className="text-right">
                                        {agent.calls.length > 0
                                            ? `${Math.round(
                                                agent.calls.reduce((acc, c) => acc + (c.duration || 0),0) / agent.calls.length
                                            )}s`
                                            : 'N/A'}
                                        </TableCell>
                                    </TableRow>
                                    </TableBody>
                                </Table>
                                </CardContent>
                            </Card>
                            </div>
                            <div className="lg:col-span-3">
                            <div className="flex justify-between items-center mb-4">
                                <h4 className="font-semibold text-lg">
                                Agent Evaluation
                                </h4>
                                <div className="flex gap-2">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() =>
                                        handleEvaluate(agent.id, agent.name)
                                    }
                                    disabled={
                                        agent.isEvaluating || agent.calls.length === 0 || agent.is_archived
                                    }
                                    >
                                    {agent.isEvaluating ? (
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    ) : (
                                        <Wand2 className="mr-2 h-4 w-4" />
                                    )}
                                    {agent.evaluation
                                        ? 'Re-Analyze'
                                        : 'Run AI Analysis'}
                                  </Button>
                                   <Button
                                    size="sm"
                                    onClick={() => setAgentToGrade(agent)}
                                    disabled={agent.is_archived}
                                  >
                                    <Edit className="mr-2 h-4 w-4" />
                                    Grade Agent
                                  </Button>
                                </div>
                            </div>

                            <AgentEvaluationCard
                                isEvaluating={agent.isEvaluating}
                                evaluation={agent.evaluation}
                                score={agent.aiSuggestedScore}
                            />
                            
                            </div>
                        </div>
                        </div>
                    </AccordionContent>
                 </Card>
              </AccordionItem>
            ))}
          </Accordion>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

    
