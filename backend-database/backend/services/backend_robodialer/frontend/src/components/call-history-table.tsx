
'use client';

import { useState, useMemo, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from './ui/button';
import { ArrowDown, ArrowUp, Edit, Mail, PhoneCall, PhoneIncoming, PhoneOutgoing, Voicemail, Check } from 'lucide-react';
import { useCall } from '@/contexts/call-context';
import type { Call, CallStatus, ActionTaken, Lead, Agent } from '@/lib/types';
import { formatDuration, cn } from '@/lib/utils';
import { format, isValid, formatRelative } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';
import { useToast } from '@/hooks/use-toast';

type ActionStatus = 'idle' | 'success';

const StatusBadge = ({ status }: { status: CallStatus }) => {
  const variant: { [key in CallStatus]?: 'default' | 'secondary' | 'destructive' | 'outline' } = {
    completed: 'default',
    'in-progress': 'default',
    'voicemail-dropped': 'outline',
    busy: 'secondary',
    failed: 'destructive',
    canceled: 'destructive',
    emailed: 'outline',
  };

  const text: { [key in CallStatus]?: string } = {
    'ringing-outgoing': 'Ringing',
    'ringing-incoming': 'Ringing',
    'in-progress': 'In Progress',
    'voicemail-dropping': 'Voicemail Left',
    'voicemail-dropped': 'Voicemail Left',
    'emailed': 'Emailed',
  }

  return (
    <Badge variant={variant[status] || 'secondary'} className="capitalize">
      {text[status] || status}
    </Badge>
  );
};

const CALLS_PER_PAGE = 10;

export default function CallHistoryTable() {
  const { state, dispatch, openVoicemailDialogForLead, sendMissedCallEmail, fetchAgents } = useCall();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [directionFilter, setDirectionFilter] = useState<'all' | 'incoming' | 'outgoing'>('all');
  // Disable frontend sorting - use backend order (most recent first)
  const [sortConfig, setSortConfig] = useState<{ key: keyof Call, direction: 'asc' | 'desc' } | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [currentPage, setCurrentPage] = useState(1);
  const [actionFeedback, setActionFeedback] = useState<Record<string, { email?: ActionStatus, voicemail?: ActionStatus }>>({});
  const { toast } = useToast();

  useEffect(() => {
    // Update current time every minute to keep relative times fresh
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const loadAgents = async () => {
        if (fetchAgents) {
            const fetched = await fetchAgents();
            setAgents(fetched);
        }
    }
    loadAgents();
  }, [fetchAgents])
  
  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, directionFilter, searchQuery]);


  const handleSort = (key: keyof Call) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };
  
  const handleEditNotes = (callId: string) => {
    if (dispatch) {
      dispatch({ type: 'OPEN_POST_CALL_SHEET', payload: { callId } });
    }
  }

  const showActionFeedback = (callId: string, action: 'email' | 'voicemail') => {
    setActionFeedback(prev => ({
      ...prev,
      [callId]: { ...prev[callId], [action]: 'success' }
    }));
    setTimeout(() => {
      setActionFeedback(prev => ({
        ...prev,
        [callId]: { ...prev[callId], [action]: 'idle' }
      }));
    }, 3000); // Reset after 3 seconds
  }
  
  const constructLeadForAction = (call: Call): Lead | null => {
    const phoneNumber = call.direction === 'outgoing' ? call.to : call.from;
    const name = call.contactName || phoneNumber;

    if (!phoneNumber) {
        return null;
    }

    return {
        lead_id: call.leadId || `call-${call.id}`,
        company: name,
        companyPhone: phoneNumber,
        email: call.notes?.match(/Email: (.*)/)?.[1], // Basic email parsing from notes if available
    };
  }

  const handleVoicemail = (call: Call) => {
    const leadForAction = constructLeadForAction(call);
    if (leadForAction && openVoicemailDialogForLead) {
      openVoicemailDialogForLead(leadForAction);
      showActionFeedback(call.id, 'voicemail');
    } else {
      toast({ title: "Cannot Send Voicemail", description: "Contact name or phone number for this call could not be found.", variant: 'destructive' });
    }
  }

  const handleEmail = (call: Call) => {
    const leadForAction = constructLeadForAction(call);
    if (leadForAction && sendMissedCallEmail) {
      sendMissedCallEmail(leadForAction);
      showActionFeedback(call.id, 'email');
    } else {
      toast({ title: "Cannot Send Email", description: "Contact name or phone number for this call could not be found.", variant: 'destructive' });
    }
  }


  const { paginatedCalls, totalPages } = useMemo(() => {
    let filtered = state.allCallHistory;

    if (searchQuery) {
        filtered = filtered.filter(call => {
            const searchTerm = searchQuery.toLowerCase();
            const from = call.from?.toLowerCase() || '';
            const to = call.to?.toLowerCase() || '';
            const name = call.contactName?.toLowerCase() || '';
            const agent = agents.find(a => String(a.id) === String(call.agentId));
            const agentName = agent?.name.toLowerCase() || '';
            return from.includes(searchTerm) || to.includes(searchTerm) || name.includes(searchTerm) || agentName.includes(searchTerm);
        });
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter((call) => call.status === statusFilter);
    }
    if (directionFilter !== 'all') {
      filtered = filtered.filter((call) => call.direction === directionFilter);
    }
    
    // No frontend sorting - use backend order (most recent first by created_at)
    // Backend already returns calls ordered by created_at DESC

    const calculatedTotalPages = Math.ceil(filtered.length / CALLS_PER_PAGE);
    const startIndex = (currentPage - 1) * CALLS_PER_PAGE;
    const paginated = filtered.slice(startIndex, startIndex + CALLS_PER_PAGE);

    return { paginatedCalls: paginated, totalPages: calculatedTotalPages };
  }, [state.allCallHistory, agents, statusFilter, directionFilter, sortConfig, currentPage, searchQuery]);

  const allStatuses = useMemo(() => {
    return ['all', ...Array.from(new Set(state.allCallHistory.map(c => c.status)))];
  }, [state.allCallHistory]);


  const SortableHeader = ({ tkey, label }: { tkey: keyof Call; label: string }) => (
    <TableHead onClick={() => handleSort(tkey)} className="cursor-pointer">
      <div className="flex items-center gap-2">
        {label}
        {sortConfig?.key === tkey && (sortConfig.direction === 'asc' ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />)}
      </div>
    </TableHead>
  );

  const getIconForAction = (action?: ActionTaken, direction?: 'incoming' | 'outgoing') => {
    switch (action) {
      case 'email':
        return <Mail className="h-5 w-5 text-yellow-500" />;
      case 'voicemail':
        return <Voicemail className="h-5 w-5 text-purple-500" />;
      case 'call':
        if (direction === 'incoming') {
          return <PhoneIncoming className="h-5 w-5 text-blue-500" />;
        }
        return <PhoneOutgoing className="h-5 w-5 text-green-500" />;
      default:
        return <PhoneCall className="h-5 w-5 text-gray-500" />;
    }
  }

  const ActionButton = ({ call, action, icon: Icon, onClick }: { call: Call, action: 'email' | 'voicemail', icon: React.ElementType, onClick: () => void }) => {
    const feedback = actionFeedback[call.id]?.[action];
    const isSuccess = feedback === 'success';

    return (
        <Button
            variant="ghost"
            size="icon"
            onClick={onClick}
            disabled={isSuccess}
            className={cn(isSuccess && "text-green-500 hover:text-green-600")}
        >
            {isSuccess ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
        </Button>
    )
  }
  
  const timeZone = 'America/New_York';

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-2">
        <Input
          placeholder="Search by contact, number, or agent..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full sm:w-[300px]"
        />
        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              {allStatuses.map((status, index) => (
                <SelectItem key={`${status}-${index}`} value={status} className="capitalize">{status}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={directionFilter} onValueChange={(v) => setDirectionFilter(v as 'all' | 'incoming' | 'outgoing')}>
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Filter by direction" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Directions</SelectItem>
              <SelectItem value="incoming">Incoming</SelectItem>
              <SelectItem value="outgoing">Outgoing</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">Type</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead>Agent</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead className="w-[200px]">Notes</TableHead>
              <TableHead>Timestamp (US Eastern)</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedCalls.length > 0 ? (
              paginatedCalls.map((call, index) => {
                const callDate = call.startTime ? new Date(call.startTime) : null;
                const isDateValid = callDate && isValid(callDate);
                const contactIdentifier = call.direction === 'incoming' ? call.from : call.to;
                const displayName = call.contactName || contactIdentifier;
                const agent = agents.find(a => String(a.id) === String(call.agentId));
                
                return (
                  <TableRow key={`${call.id}-${index}`}>
                    <TableCell>
                      {getIconForAction(call.action_taken, call.direction)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar>
                          <AvatarImage src={call.avatarUrl} alt="Contact" data-ai-hint="person face" />
                          <AvatarFallback>{displayName?.charAt(0) || '?'}</AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="font-medium">{displayName}</div>
                          <p className="text-sm text-muted-foreground">{contactIdentifier}</p>
                        </div>
                      </div>
                    </TableCell>
                     <TableCell>{agent?.name || 'Unknown'}</TableCell>
                    <TableCell>
                      <StatusBadge status={call.status} />
                    </TableCell>
                    <TableCell>{formatDuration(call.duration || 0)}</TableCell>
                    <TableCell className="max-w-[200px]">
                      <div className="truncate text-sm text-muted-foreground" title={call.notes || 'No notes'}>
                        {call.notes || <span className="italic">No notes</span>}
                      </div>
                    </TableCell>
                    <TableCell>
                      {isDateValid ? (
                        <div className="flex flex-col">
                          <span className='font-medium'>{formatRelative(callDate, currentTime)}</span>
                          <span className='text-sm text-muted-foreground'>
                            {formatInTimeZone(callDate, timeZone, 'MMM d, p')} ET
                          </span>
                        </div>
                      ) : (
                        <div className="text-muted-foreground">Invalid date</div>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                       <div className="flex items-center justify-end">
                        <Button variant="ghost" size="icon" onClick={() => handleEditNotes(String(call.id))} disabled={call.status === 'emailed'}>
                            <Edit className="h-4 w-4" />
                            <span className="sr-only">Edit Notes</span>
                        </Button>
                        <ActionButton
                          call={call}
                          action="voicemail"
                          icon={Voicemail}
                          onClick={() => handleVoicemail(call)}
                        />
                        <ActionButton
                          call={call}
                          action="email"
                          icon={Mail}
                          onClick={() => handleEmail(call)}
                        />
                       </div>
                    </TableCell>
                  </TableRow>
                )
              })
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">
                  No calls found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
       <div className="flex items-center justify-end space-x-2 pt-4">
        <span className="text-sm text-muted-foreground">
          Page {currentPage} of {totalPages > 0 ? totalPages : 1}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
          disabled={currentPage === 1}
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
          disabled={currentPage === totalPages || totalPages === 0}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

    
