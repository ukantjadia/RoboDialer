
'use client';

import type { Call, Lead, Agent, CallStatus, CallDirection, ActionTaken, NewAgent } from '@/lib/types';
import React, {
  createContext,
  useContext,
  useReducer,
  ReactNode,
  useCallback,
  useEffect,
  useRef,
} from 'react';
import { useToast } from '@/hooks/use-toast';
import { formatUSPhoneNumber } from '@/lib/utils';
import { useRouter } from 'next/navigation';

type TwilioDeviceStatus = 'uninitialized' | 'initializing' | 'ready' | 'error';
type LoginRole = 'agent' | 'admin';

interface QueuedCall {
    to: string;
    contactName?: string;
    leadId?: string;
}

interface CallState {
  callHistory: Call[];
  allCallHistory: Call[]; // To track all calls for lead status
  agents: Agent[];
  activeCall: Call | null;
  softphoneOpen: boolean;
  showIncomingCall: boolean;
  showPostCallSheetForId: string | null;
  voicemailLeadTarget: Lead | null;
  currentAgent: Agent | null;
}

type CallAction =
  | { type: 'TOGGLE_SOFTPHONE' }
  | { type: 'SET_SOFTPHONE_OPEN'; payload: boolean }
  | { type: 'SET_ACTIVE_CALL'; payload: { call: Call | null } }
  | { type: 'UPDATE_ACTIVE_CALL'; payload: { call: Partial<Call> } }
  | { type: 'ADD_TO_HISTORY'; payload: { call: Call } }
  | { type: 'UPDATE_IN_HISTORY'; payload: { call: Call } }
  | { type: 'REPLACE_IN_HISTORY'; payload: { tempId: string, finalCall: Call } }
  | { type: 'SET_CALL_HISTORY'; payload: Call[] }
  | { type: 'SET_ALL_CALL_HISTORY'; payload: Call[] }
  | { type: 'SET_AGENTS'; payload: Agent[] }
  | { type: 'ADD_AGENT'; payload: Agent }
  | { type: 'REMOVE_AGENT'; payload: { agentId: number } }
  | { type: 'UPDATE_AGENT'; payload: { agent: Partial<Agent> & Pick<Agent, 'id'> } }
  | { type: 'CLOSE_POST_CALL_SHEET' }
  | { type: 'OPEN_POST_CALL_SHEET'; payload: { callId: string; } }
  | { type: 'OPEN_VOICEMAIL_DIALOG'; payload: { lead: Lead } }
  | { type: 'CLOSE_VOICEMAIL_DIALOG' }
  | { type: 'SET_CURRENT_AGENT'; payload: { agent: Agent | null } }
  | { type: 'SHOW_INCOMING_CALL'; payload: boolean };

const initialState: CallState = {
  callHistory: [],
  allCallHistory: [],
  agents: [],
  activeCall: null,
  softphoneOpen: false,
  showIncomingCall: false,
  showPostCallSheetForId: null,
  voicemailLeadTarget: null,
  currentAgent: null,
};

const callReducer = (state: CallState, action: CallAction): CallState => {
  const sortHistory = (history: Call[]) => history.sort((a, b) => (b.startTime || 0) - (a.startTime || 0));

  switch (action.type) {
    case 'TOGGLE_SOFTPHONE':
      return { ...state, softphoneOpen: !state.softphoneOpen };
    case 'SET_SOFTPHONE_OPEN':
      return { ...state, softphoneOpen: action.payload };
    case 'SET_ACTIVE_CALL':
      return { ...state, activeCall: action.payload.call };
    case 'UPDATE_ACTIVE_CALL': {
        if (!state.activeCall) return state;
        const updatedCall = { ...state.activeCall, ...action.payload.call };
        return {
            ...state,
            activeCall: updatedCall,
        };
    }
    case 'ADD_TO_HISTORY': {
        const { call } = action.payload;
        
        const newHistory = state.callHistory.some(c => c.id === call.id) 
            ? state.callHistory 
            : [call, ...state.callHistory];

        const newAllHistory = state.allCallHistory.some(c => c.id === call.id)
            ? state.allCallHistory
            : [call, ...state.allCallHistory];

        return {
            ...state,
            callHistory: sortHistory(newHistory),
            allCallHistory: sortHistory(newAllHistory),
        };
    }
    case 'UPDATE_IN_HISTORY': {
        const { call } = action.payload;
        const update = (history: Call[]) => {
            const index = history.findIndex(c => c.id === call.id);
            if (index === -1) {
              // If not found, add it. This handles cases where a call object was created
              // but didn't make it into history for some reason (e.g. race conditions)
              return sortHistory([call, ...history]);
            }
            const newHistory = [...history];
            newHistory[index] = { ...newHistory[index], ...call };
            return sortHistory(newHistory);
        };
        
        return {
            ...state,
            callHistory: update(state.callHistory),
            allCallHistory: update(state.allCallHistory),
        };
    }
    case 'REPLACE_IN_HISTORY': {
        const { tempId, finalCall } = action.payload;
        const replace = (history: Call[]) => history.map(c => c.id === tempId ? finalCall : c);
        return {
            ...state,
            callHistory: sortHistory(replace(state.callHistory)),
            allCallHistory: sortHistory(replace(state.allCallHistory)),
        }
    }
    case 'SET_CALL_HISTORY':
        return { ...state, callHistory: sortHistory(action.payload) };
    case 'SET_ALL_CALL_HISTORY':
        console.log('📊 SET_ALL_CALL_HISTORY - Raw payload:', action.payload.length);
        // Backend already provides correct ordering - don't sort again
        console.log('📊 Using backend order - First 5 calls:', action.payload.slice(0, 5).map(c => ({
          id: c.id, 
          startTime: c.startTime, 
          date: new Date(c.startTime).toLocaleString(),
          notes: c.notes?.substring(0, 50),
          from: c.from,
          to: c.to,
          status: c.status
        })));
        return { ...state, allCallHistory: action.payload };
    case 'SET_AGENTS':
        return { ...state, agents: action.payload };
    case 'ADD_AGENT':
        return { ...state, agents: [...state.agents, action.payload] };
     case 'REMOVE_AGENT':
        return { ...state, agents: state.agents.filter(a => a.id !== action.payload.agentId) };
    case 'UPDATE_AGENT': {
        const { agent } = action.payload;
        return {
            ...state,
            agents: state.agents.map(a => a.id === agent.id ? { ...a, ...agent } : a),
        };
    }
    case 'CLOSE_POST_CALL_SHEET':
      return { ...state, showPostCallSheetForId: null };
    case 'OPEN_POST_CALL_SHEET':
      return { ...state, showPostCallSheetForId: action.payload.callId };
    case 'OPEN_VOICEMAIL_DIALOG':
      return { ...state, voicemailLeadTarget: action.payload.lead };
    case 'CLOSE_VOICEMAIL_DIALOG':
      return { ...state, voicemailLeadTarget: null };
    case 'SET_CURRENT_AGENT':
        return { ...state, currentAgent: action.payload.agent };
    case 'SHOW_INCOMING_CALL':
      return { ...state, showIncomingCall: action.payload };
    default:
      return state;
  }
};

const CallContext = createContext<any>(null);

export const CallProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(callReducer, initialState);
  const { toast } = useToast();
  const currentAgentRef = useRef<Agent | null>(null);

  useEffect(() => {
    currentAgentRef.current = state.currentAgent;
  }, [state.currentAgent]);

  const mapCallLog = useCallback((log: any): Call => {
    let summary = log.summary || '';
    let notes = log.notes || '';
    
    const summaryMarker = 'SUMMARY: ';
    const notesMarker = '\n---\nNOTES: ';
    const summaryIndex = notes.indexOf(summaryMarker);
    const notesIndex = notes.indexOf(notesMarker);

    if (summaryIndex === 0 && notesIndex > 0) {
        summary = notes.substring(summaryMarker.length, notesIndex);
        notes = notes.substring(notesIndex + notesMarker.length);
    }

    // Handle timestamp conversion for main backend format
    let startTime = log.startTime;
    if (!startTime && log.started_at) {
      if (typeof log.started_at === 'string') {
        startTime = new Date(log.started_at).getTime();
        console.log('🕐 Converting string started_at:', log.started_at, '→', startTime, '→', new Date(startTime).toLocaleString());
      } else {
        startTime = log.started_at * 1000;
        console.log('🕐 Converting numeric started_at:', log.started_at, '→', startTime, '→', new Date(startTime).toLocaleString());
      }
    }

    let endTime = log.endTime;
    if (!endTime && log.ended_at) {
      if (typeof log.ended_at === 'string') {
        endTime = new Date(log.ended_at).getTime();
      } else {
        endTime = log.ended_at * 1000;
      }
    }

    // Get agent info
    const agentId = log.agentId || log.agent_id;
    const agentName = log.agentName || (agentId && state.agents.find(a => a.id === agentId)?.name) || 'Unknown';
    
    const mappedCall = {
      id: String(log.id || log.call_log_id || `temp-${Date.now()}`),
      direction: log.direction || 'outgoing',
      from: log.from || (log.direction === 'incoming' ? log.phone_number : 'Agent'),
      to: log.to || (log.direction === 'outgoing' ? log.phone_number : 'Agent'),
      startTime: startTime || new Date().getTime(), // Use current time only if no valid timestamp available
      endTime: endTime,
      duration: log.duration || 0,
      status: log.status || 'completed',
      notes: notes,
      summary: summary,
      agentId: agentId,
      agentName: agentName,
      leadId: log.leadId || log.lead_id || '',
      action_taken: log.action_taken || 'call',
      contactName: log.contactName || log.contact_name || '',
      avatarUrl: log.avatarUrl || '',
      followUpRequired: log.follow_up_required || false,
      callAttemptNumber: log.call_attempt_number || 1,
    };
    
    console.log('🔄 Mapped call log:', {
      id: mappedCall.id,
      notes: mappedCall.notes?.substring(0, 30),
      startTime: mappedCall.startTime,
      agentName: mappedCall.agentName
    });
    
    return mappedCall;
  }, [state.agents]);

  const getAllCallHistory = useCallback(async () => {
    try {
      console.log('🔄 Fetching call history...');
      const url = '/api/twilio/call_logs';
      const response = await fetch(url, { method: 'GET' });
      if (!response.ok) {
        throw new Error(`Failed to fetch all call history. Status: ${response.status}`);
      }
      const data = await response.json();
      console.log('📡 Raw response from backend:', { status: data.status, count: data.count, hasLogs: !!data.call_logs });
      
      const formattedCalls: Call[] = (data.call_logs || []).map(mapCallLog);
      console.log('📊 Raw calls from backend:', formattedCalls.length);
      
      // Backend returns calls in correct order (newest first by created_at)
      // No frontend sorting needed - use backend order as-is
      if (formattedCalls.length > 0) {
        console.log('📊 First 5 calls from backend (pre-sorted):', formattedCalls.slice(0, 5).map(c => ({
          id: c.id,
          startTime: c.startTime,
          date: new Date(c.startTime).toLocaleString(),
          notes: c.notes?.substring(0, 30)
        })));
        
        const newestCall = formattedCalls[0]; // First call should be newest
        console.log('🆕 Newest call (first in list):', {
          id: newestCall.id,
          startTime: newestCall.startTime,
          date: new Date(newestCall.startTime).toLocaleString(),
          notes: newestCall.notes?.substring(0, 30)
        });
      }
      
      // Use backend-provided order directly (no frontend sorting)
      dispatch({ type: 'SET_ALL_CALL_HISTORY', payload: formattedCalls });
      console.log('✅ Call history updated successfully');
      return formattedCalls;
    } catch (error: any) {
      console.error("❌ getAllCallHistory error:", error);
      toast({
        variant: 'destructive',
        title: 'API Error',
        description: error.message || 'Could not fetch full call history.'
      });
      return [];
    }
  }, [toast, mapCallLog]);
  
  const fetchAllCallHistory = useCallback(async () => {
    if (state.allCallHistory.length > 0) {
        return state.allCallHistory;
    }
    return getAllCallHistory();
  }, [state.allCallHistory, getAllCallHistory]);


 const createOrUpdateCallOnBackend = useCallback(async (call: Call | null) => {
    if (!call) {
        console.error("Cannot create or update call log on backend: call data is null.");
        return null;
    }
    
    if (!call.id) {
        console.error("Cannot create or update call log: call.id is missing.", call);
        return null;
    }
    
    const agentId = call.agentId || currentAgentRef.current?.id;
    
    const phoneNumber = call.direction === 'outgoing' ? call.to : call.from;
    
    if (!agentId || !phoneNumber) {
        console.error("Cannot create call log: agentId or phoneNumber is missing.", { agentId, phoneNumber });
        return null;
    }
    
    try {
        const combinedNotes = call.summary ? `SUMMARY: ${call.summary}\n---\nNOTES: ${call.notes || ''}` : call.notes || '';

        // Determine if this is an update (existing DB record) or create (new call)
        // Only treat as update if the ID is a numeric database ID
        const isNumericId = call.id && /^\d+$/.test(call.id.toString());
        const isUpdate = isNumericId;
        
        const body: { [key: string]: any } = {
            agent_id: agentId,
            phone_number: phoneNumber,
            notes: combinedNotes,
            // Use the original call's start time, or current time only for brand new calls
            started_at: call.startTime ? new Date(call.startTime).toISOString() : new Date().toISOString(),
            // Only set ended_at if the call has actually ended (has endTime)
            ended_at: call.endTime ? new Date(call.endTime).toISOString() : null,
            duration: call.duration,
            status: call.status,
            action_taken: call.action_taken,
            direction: call.direction,
            contact_name: call.contactName,
            follow_up_required: call.followUpRequired,
            call_attempt_number: call.callAttemptNumber || 1,
        };

        // Add optional fields only if they have values
        if (call.summary) {
            body.summary = call.summary;
        }
        if (call.leadId) {
            const leadIdInt = parseInt(call.leadId, 10);
            if (!isNaN(leadIdInt)) {
                body.lead_id = leadIdInt;
            }
        }

        // Add the appropriate ID field for updates
        if (isUpdate) {
            body.id = call.id; // Use database ID for updates
            console.log('🔄 Updating existing call log:', call.id);
        } else {
            // Only set call_log_id for actual Twilio call IDs (start with 'CA')
            if (call.id && call.id.startsWith('CA')) {
                body.call_log_id = call.id; // Keep Twilio ID for new calls
            }
            console.log('🆕 Creating new call log for action:', call.action_taken);
        }
        
        console.log('📤 Sending to backend:', body);
        
        // Use PUT for updates, POST for creates
        const url = isUpdate ? `/api/twilio/call_logs/${call.id}` : '/api/twilio/call_logs';
        const method = isUpdate ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            let errorDetails = `Request failed with status ${response.status}`;
            try {
                const errorJson = await response.json();
                errorDetails = errorJson.message || errorDetails;
            } catch (e) {
                const text = await response.text();
                errorDetails = text || errorDetails;
            }
            console.error('Call log creation failed:', response.status, errorDetails);
            throw new Error(errorDetails);
        }

        const responseData = await response.json();
        console.log('✅ Backend response:', responseData);
        const mappedCall = mapCallLog(responseData.call_log);
        console.log('🔄 Mapped call from response:', {
          id: mappedCall.id,
          startTime: mappedCall.startTime,
          date: new Date(mappedCall.startTime).toLocaleString(),
          notes: mappedCall.notes?.substring(0, 50)
        });
        return mappedCall;

    } catch (error: any) {
        console.error('Failed to create/update call log:', error.message);
        toast({
            title: 'Logging Error',
            description: `Failed to save call log: ${error.message}`,
            variant: 'destructive'
        });
        return null;
    }
}, [toast, mapCallLog]);

  const startOutgoingCall = useCallback(async (to: string, contactName?: string, leadId?: string) => {
    const agent = currentAgentRef.current;
    if (!agent) {
        toast({ title: 'Softphone Not Ready', description: 'No agent logged in.', variant: 'destructive' });
        return;
    }
    
    dispatch({ type: 'SET_SOFTPHONE_OPEN', payload: true });

    const formattedNumber = formatUSPhoneNumber(to);
    const tempId = `temp-${Date.now()}`;
    const callData: Call = {
        id: tempId, from: agent.phone, to: formattedNumber, direction: 'outgoing', status: 'ringing-outgoing',
        startTime: Date.now(), duration: 0, agentId: agent.id, leadId, contactName,
        action_taken: 'call', followUpRequired: false, callAttemptNumber: 1,
    };
    
    dispatch({ type: 'SET_ACTIVE_CALL', payload: { call: callData } });
    dispatch({ type: 'ADD_TO_HISTORY', payload: { call: callData } });

    try {
        const response = await fetch('/api/twilio/make_call', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_id: agent.id, to: formattedNumber }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to initiate call.');
        }

        const { call_sid, customer_call_sid, conference } = await response.json();
        // Use customer_call_sid as the primary ID, fallback to call_sid
        const actualCallSid = customer_call_sid || call_sid;
        
        if (!actualCallSid) {
            throw new Error('No call ID received from server');
        }
        
        const permanentCall: Call = { ...callData, id: actualCallSid };

        dispatch({ type: 'REPLACE_IN_HISTORY', payload: { tempId, finalCall: permanentCall } });
        dispatch({ type: 'SET_ACTIVE_CALL', payload: { call: permanentCall } });
        
        toast({ title: 'Calling...', description: `Calling ${contactName || formattedNumber}`});

    } catch (error: any) {
        console.error('Error starting outgoing call:', error);
        toast({ title: 'Call Failed', description: error.message, variant: 'destructive' });
        
        // Create a permanent ID for failed calls to avoid issues when ending the call
        const failedCallId = `failed-${Date.now()}`;
        const failedCall: Call = { ...callData, id: failedCallId, status: 'failed', endTime: Date.now() };
        dispatch({ type: 'UPDATE_IN_HISTORY', payload: { call: failedCall }});
        dispatch({ type: 'SET_ACTIVE_CALL', payload: { call: failedCall } });
    }
  }, [toast]);
  
  const forceFetchAgents = useCallback(async () => {
    try {
      const response = await fetch('/api/agents');
      if (!response.ok) {
        throw new Error(`Failed to fetch agents. Status: ${response.status}`);
      }
      const data = await response.json();
      const agents: Agent[] = (data.agents || []).map((agent: any) => ({
        id: agent.id,
        name: agent.name,
        email: agent.email,
        phone: agent.phone,
        status: agent.status,
        score: agent.score,
      }));
      dispatch({ type: 'SET_AGENTS', payload: agents });
      return agents;
    } catch (error: any) {
      console.error("Fetch agents error:", error);
      toast({
        variant: 'destructive',
        title: 'API Error',
        description: error.message || 'Could not fetch agents.'
      });
      return [];
    }
  }, [toast]);

  const fetchAgents = useCallback(async (): Promise<Agent[]> => {
    if (state.agents.length > 0) {
        return state.agents;
    }
    return forceFetchAgents();
  }, [state.agents, forceFetchAgents]);

  const addAgent = useCallback(async (agentData: NewAgent): Promise<boolean> => {
    try {
        const response = await fetch('/api/agents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(agentData),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.details || error.error || 'Failed to add agent.');
        }
        
        toast({ title: 'Success', description: 'New agent has been added.' });
        forceFetchAgents(); // Refresh the list
        return true;

    } catch (error: any) {
        toast({
            variant: 'destructive',
            title: 'Error',
            description: error.message,
        });
        return false;
    }
}, [toast, forceFetchAgents]);

  const deleteAgent = useCallback(async (agentId: number): Promise<boolean> => {
    try {
      const response = await fetch(`/api/agents/${agentId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.details || `Failed to delete agent. Status: ${response.status}`);
      }

      toast({ title: 'Success', description: 'Agent has been deleted.' });
      forceFetchAgents(); // Refresh the list
      return true;

    } catch (error: any) {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message,
      });
      return false;
    }
  }, [toast, forceFetchAgents]);

  const updateAgent = useCallback(async (agentId: number, data: Partial<Agent>): Promise<boolean> => {
    try {
        const response = await fetch(`/api/agents/${agentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `Failed to update agent. Status: ${response.status}`);
        }
        
        const updatedAgent = await response.json();
        dispatch({ type: 'UPDATE_AGENT', payload: { agent: { id: agentId, ...updatedAgent } } });
        return true;
    } catch (error: any) {
        // Don't show toast for background updates like status changes
        console.error(`Failed to update agent ${agentId}:`, error.message);
        return false;
    }
  }, []);

  const updateAgentScore = useCallback(async (agentId: number, score: number): Promise<boolean> => {
    try {
        const response = await fetch(`/api/agents/grade/${agentId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ score: score }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ details: "Failed to save score." }));
            throw new Error(error.details || `Failed to update score. Status: ${response.status}`);
        }

        toast({ title: 'Score Saved', description: 'The agent\'s score has been updated.' });
        forceFetchAgents(); // Refresh the agent list
        return true;
    } catch (error: any) {
        toast({
            variant: 'destructive',
            title: 'Error Saving Score',
            description: error.message,
        });
        return false;
    }
  }, [toast, forceFetchAgents]);
  
  const loginAsAgent = useCallback(async (agent: Agent, role: LoginRole) => {
    const agentWithRole = { ...agent, role };
    dispatch({ type: 'SET_CURRENT_AGENT', payload: { agent: agentWithRole } });
    
    // Only update status for real agents, not hardcoded admins
    if (role === 'agent') {
        await updateAgent(agent.id, { status: 'active' });
    }
    
    // Initial data load on login
    await getAllCallHistory();
    await forceFetchAgents();

  }, [getAllCallHistory, forceFetchAgents, updateAgent]);

  const updateNotesAndSummary = useCallback(async (callId: string, notes: string, summary?: string) => {
    console.log('Updating notes and summary for call:', callId, { notes, summary });
    const callToUpdate = state.allCallHistory.find(c => c.id === callId);
    console.log('Found call to update:', callToUpdate);
    
    if(callToUpdate) {
      const updatedCall: Call = { 
        ...callToUpdate,
        notes, 
        summary,
      };
      
      console.log('Saving updated call to backend:', updatedCall);
      const savedCall = await createOrUpdateCallOnBackend(updatedCall);
      
      if (savedCall) {
        console.log('Received saved call from backend:', savedCall);
        toast({ title: 'Notes Saved', description: 'Your call notes have been saved.' });
        // Update the call in local state
        dispatch({ type: 'UPDATE_IN_HISTORY', payload: { call: savedCall } });
        
        // Refresh call history to ensure latest data and proper ordering
        console.log('🔄 Refreshing call history after saving notes...');
        getAllCallHistory().then(calls => {
          console.log('✅ Call history refreshed after notes save:', calls.length, 'calls');
        }).catch(error => {
          console.error('❌ Failed to refresh call history after notes save:', error);
        });
      } else {
        console.error('Backend returned null when saving notes');
        toast({ title: 'Error', description: 'Failed to save notes to backend.', variant: 'destructive' });
      }
      
    } else {
      console.error("Could not find call to update notes for:", callId, 'Available calls:', state.allCallHistory.map(c => c.id));
      toast({ title: 'Error', description: 'Could not find the call to update.', variant: 'destructive' });
    }
  }, [state.allCallHistory, createOrUpdateCallOnBackend, toast, getAllCallHistory]);

  const logout = useCallback(async () => {
    if (currentAgentRef.current && currentAgentRef.current.role === 'agent') {
      await updateAgent(currentAgentRef.current.id, { status: 'inactive' });
    }
    dispatch({ type: 'SET_CURRENT_AGENT', payload: { agent: null } });
    dispatch({ type: 'SET_CALL_HISTORY', payload: [] });
    dispatch({ type: 'SET_ALL_CALL_HISTORY', payload: [] });
    dispatch({ type: 'SET_AGENTS', payload: [] });
  }, [updateAgent]);

  const openVoicemailDialogForLead = useCallback((lead: Lead) => {
    dispatch({ type: 'OPEN_VOICEMAIL_DIALOG', payload: { lead } });
  }, []);

  const sendVoicemail = useCallback((lead: Lead, script: string) => {
    const agent = currentAgentRef.current;
    const phoneNumber = lead.phoneNumber || lead.companyPhone;

    if (!agent || !phoneNumber) {
        toast({ title: 'Error', description: 'Agent or lead phone number is missing.', variant: 'destructive' });
        return;
    }

    const formattedNumber = formatUSPhoneNumber(phoneNumber);
    toast({ title: 'Voicemail Sending...', description: `Sending to ${formattedNumber}.` });

    fetch('/api/twilio/send_voicemail', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: formattedNumber, script: script }),
    })
    .then(async (response) => {
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || error.message || 'Failed to send voicemail');
        }
        return response.json();
    })
    .then(responseData => {
        const interactionLog: Call = {
            id: responseData.call_sid || `voicemail-${Date.now()}`,
            direction: 'outgoing', from: agent.phone, to: formattedNumber,
            startTime: Date.now(), duration: 0, status: 'voicemail-dropped',
            agentId: agent.id, leadId: lead.lead_id, action_taken: 'voicemail',
            contactName: lead.company,
        };
        return createOrUpdateCallOnBackend(interactionLog);
    })
    .then(savedLog => {
        if (savedLog) {
            dispatch({ type: 'UPDATE_IN_HISTORY', payload: { call: savedLog } });
            // Refresh call history to ensure proper ordering
            getAllCallHistory().then(calls => {
                console.log('✅ Call history refreshed after voicemail:', calls.length, 'calls');
            }).catch(error => {
                console.error('❌ Failed to refresh call history after voicemail:', error);
            });
        }
    })
    .catch(error => {
        console.error('Error sending voicemail:', error);
        toast({ title: 'Voicemail Failed', description: error.message, variant: 'destructive' });
    });
  }, [toast, createOrUpdateCallOnBackend, getAllCallHistory]);
  
  const sendMissedCallEmail = useCallback((lead: Lead) => {
    const agent = currentAgentRef.current;
    if (!agent) {
      toast({ title: 'Cannot Send Email', description: 'No agent is logged in.', variant: 'destructive' });
      return;
    }
    
    if (!lead.email) {
      toast({ title: 'Cannot Send Email', description: `No email address found for ${lead.company}.`, variant: 'destructive' });
      return;
    }
    
    toast({ title: 'Sending Email...', description: `Sending follow-up to ${lead.company}.` });

    fetch('/api/send_email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: lead.email, name: lead.name || lead.company }),
    })
    .then(async response => {
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Backend failed to send email');
        }
        return response.json();
    })
    .then(() => {
        const interactionLog: Call = {
            id: `email-${Date.now()}`, direction: 'outgoing', from: agent.email,
            to: lead.phone || lead.company, startTime: Date.now(), duration: 0, status: 'emailed',
            agentId: agent.id, leadId: lead.lead_id, action_taken: 'email',
            contactName: lead.name || lead.company,
        };
        return createOrUpdateCallOnBackend(interactionLog);
    })
    .then(savedLog => {
        if (savedLog) {
            dispatch({ type: 'UPDATE_IN_HISTORY', payload: { call: savedLog } });
            // Refresh call history to ensure proper ordering
            getAllCallHistory().then(calls => {
                console.log('✅ Call history refreshed after email:', calls.length, 'calls');
            }).catch(error => {
                console.error('❌ Failed to refresh call history after email:', error);
            });
        }
    })
    .catch(error => {
        console.error('Error sending email:', error);
        toast({ title: 'Email Failed', description: error.message, variant: 'destructive' });
    });
  }, [createOrUpdateCallOnBackend, toast, getAllCallHistory]);
  
  const endActiveCall = useCallback((status: CallStatus = 'completed') => {
      const { activeCall } = state;
      if (!activeCall) {
          console.log('No active call to end');
          return;
      }
      
      console.log('Ending active call:', activeCall);
      
      // Ensure the call has a valid ID
      if (!activeCall.id) {
          console.error('Active call missing ID, cannot end call properly');
          // Generate a fallback ID based on timestamp and other available data
          const fallbackId = `fallback-${Date.now()}-${activeCall.to || 'unknown'}`;
          activeCall.id = fallbackId;
          console.log('Generated fallback ID:', fallbackId);
      }
      
      // Additional validation to ensure the call object is not corrupted
      if (!activeCall.startTime || isNaN(activeCall.startTime)) {
          console.error('Active call has invalid startTime:', activeCall.startTime);
          activeCall.startTime = Date.now() - 30000; // Default to 30 seconds ago
      }
      
      // Validate that the active call object is complete
      const requiredFields = ['id', 'direction', 'from', 'to', 'startTime'];
      const missingFields = requiredFields.filter(field => !activeCall[field as keyof Call]);
      
      if (missingFields.length > 0) {
          console.error('Active call missing required fields:', missingFields, activeCall);
          toast({ 
              title: 'Call End Warning', 
              description: 'Call data is incomplete. Saving what we can.', 
              variant: 'destructive' 
          });
          
          // Fill in missing fields with defaults
          if (!activeCall.direction) activeCall.direction = 'outgoing';
          if (!activeCall.from) activeCall.from = currentAgentRef.current?.phone || 'unknown';
          if (!activeCall.to) activeCall.to = 'unknown';
      }

      const updatedCall: Call = {
          ...activeCall,
          status,
          endTime: Date.now(),
          duration: Math.round((Date.now() - activeCall.startTime) / 1000)
      };
      
      console.log('Updated call for backend:', updatedCall);

      // Clear the active call immediately to prevent multiple end attempts
      dispatch({ type: 'SET_ACTIVE_CALL', payload: { call: null } });
      
      // Update the call in history with the final status
      dispatch({ type: 'UPDATE_IN_HISTORY', payload: { call: updatedCall } });
      
      // Try to save to backend
      createOrUpdateCallOnBackend(updatedCall).then(async savedCall => {
          if (savedCall) {
              console.log('Successfully saved call to backend:', savedCall);
              dispatch({ type: 'UPDATE_IN_HISTORY', payload: { call: savedCall } });
              dispatch({ type: 'OPEN_POST_CALL_SHEET', payload: { callId: savedCall.id } });
              console.log('Call saved successfully, post-call sheet opened');
              
              // Refresh call history to ensure proper ordering
              console.log('🔄 Refreshing call history after call end...');
              getAllCallHistory().then(calls => {
                console.log('✅ Call history refreshed after call end:', calls.length, 'calls');
              }).catch(error => {
                console.error('❌ Failed to refresh call history after call end:', error);
              });
          } else {
              console.error('Backend returned null for saved call');
          }
      }).catch(async error => {
          console.error('Failed to create/update call log:', error);
          toast({ 
              title: 'Call Log Error', 
              description: 'Call ended but could not save to history. Check console for details.', 
              variant: 'destructive' 
          });
      });
  }, [state.activeCall, createOrUpdateCallOnBackend, toast]);

  // Load call history on component mount (page refresh)
  useEffect(() => {
    console.log('🔄 CallProvider mounted - loading initial call history...');
    getAllCallHistory().then(calls => {
      console.log('✅ Initial call history loaded:', calls.length, 'calls');
    }).catch(error => {
      console.error('❌ Failed to load initial call history:', error);
    });
  }, []); // Empty dependency array - run only on mount


  return (
    <CallContext.Provider value={{
      state,
      dispatch,
      fetchAgents,
      addAgent,
      deleteAgent,
      updateAgent,
      updateAgentScore,
      fetchAllCallHistory,
      getAllCallHistory,
      loginAsAgent,
      logout,
      startOutgoingCall,
      endActiveCall,
      updateNotesAndSummary,
      openVoicemailDialogForLead,
      sendVoicemail,
      sendMissedCallEmail,
    }}>
      {children}
    </CallContext.Provider>
  );
};

export const useCall = () => {
  const context = useContext(CallContext);
  if (context === undefined) {
    throw new Error('useCall must be used within a CallProvider');
  }
  return context;
};

    