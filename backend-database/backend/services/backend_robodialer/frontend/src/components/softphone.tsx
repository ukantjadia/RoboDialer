
'use client';

import {
  Grid3x3,
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  Clock,
  CircleDotDashed,
  Move,
  Upload,
  AlertCircle,
  Loader2,
  X,
  Users,
} from 'lucide-react';
import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useCall } from '@/contexts/call-context';
import { cn, formatDuration } from '@/lib/utils';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { AnimatePresence, motion, useDragControls } from 'framer-motion';
import { useToast } from '@/hooks/use-toast';
import type { CallStatus, Lead } from '@/lib/types';
import LeadsDialog from './leads-dialog';


const DialpadButton = ({
  digit,
  letters,
  onPress,
}: {
  digit: string;
  letters: string;
  onPress: (digit: string) => void;
}) => (
  <Button
    variant="ghost"
    className="h-16 w-16 rounded-full text-2xl flex flex-col items-center justify-center"
    onClick={() => onPress(digit)}
  >
    <span>{digit}</span>
    <span className="text-xs font-normal tracking-widest">{letters}</span>
  </Button>
);

const DialpadView = ({ onCall, onBack }: { onCall: (number: string) => void; onBack: () => void }) => {
  const [number, setNumber] = useState('');

  const handleKeyPress = (digit: string) => {
    setNumber(number + digit);
  };
  
  const handleCall = () => {
    if (number) {
      onCall(number);
      setNumber('');
    }
  };

  return (
    <div className="flex flex-col items-center gap-4 p-4">
      <Input
        value={number}
        onChange={(e) => setNumber(e.target.value)}
        placeholder="(555) 123-4567"
        className="text-center text-lg h-12"
      />
      <div className="grid grid-cols-3 gap-2">
        <DialpadButton digit="1" letters="" onPress={handleKeyPress} />
        <DialpadButton digit="2" letters="ABC" onPress={handleKeyPress} />
        <DialpadButton digit="3" letters="DEF" onPress={handleKeyPress} />
        <DialpadButton digit="4" letters="GHI" onPress={handleKeyPress} />
        <DialpadButton digit="5" letters="JKL" onPress={handleKeyPress} />
        <DialpadButton digit="6" letters="MNO" onPress={handleKeyPress} />
        <DialpadButton digit="7" letters="PQRS" onPress={handleKeyPress} />
        <DialpadButton digit="8" letters="TUV" onPress={handleKeyPress} />
        <DialpadButton digit="9" letters="WXYZ" onPress={handleKeyPress} />
        <DialpadButton digit="*" letters="" onPress={handleKeyPress} />
        <DialpadButton digit="0" letters="+" onPress={handleKeyPress} />
        <DialpadButton digit="#" letters="" onPress={handleKeyPress} />
      </div>
      <div className="flex w-full gap-2">
         <Button
            size="lg"
            variant="secondary"
            className="flex-1 rounded-full h-14"
            onClick={onBack}
          >
            Back
          </Button>
        <Button
          size="lg"
          className="flex-1 bg-green-500 hover:bg-green-600 rounded-full h-14"
          onClick={handleCall}
          disabled={!number}
        >
          <Phone className="mr-2 h-5 w-5" /> Call
        </Button>
      </div>
    </div>
  );
};


const ChoiceView = ({ 
  onDial, 
  onViewLeads, 
  autoVoicemailEnabled, 
  onAutoVoicemailToggle 
}: { 
  onDial: () => void; 
  onViewLeads: () => void; 
  autoVoicemailEnabled: boolean;
  onAutoVoicemailToggle: (enabled: boolean) => void;
}) => {
  return (
      <div className="p-4">
          <Card>
              <CardContent className="p-4">
                  <div className="flex flex-col items-center justify-center gap-4">
                      <p className="text-center sm:text-left text-muted-foreground">
                          Start a new call:
                      </p>
                      <div className="flex flex-col gap-2 w-full">
                          <Button onClick={onDial}>
                              <Phone className="mr-2" />
                              Dial Number
                          </Button>
                          {/* <Button variant="secondary" onClick={onLoadEnrichedLeads}>
                              <Users className="mr-2" />
                              Load Enriched Leads
                          </Button> */}
                          <Button variant="outline" onClick={onViewLeads}>
                              <Upload className="mr-2" />
                              Upload CSV File
                          </Button>
                      </div>
                      
                      {/* Auto-voicemail setting */}
                      <div className="flex items-center justify-between w-full pt-4 border-t">
                          <div className="flex flex-col gap-1">
                              <Label htmlFor="auto-voicemail" className="text-sm font-medium">
                                  Auto-send voicemail
                              </Label>
                              <p className="text-xs text-muted-foreground">
                                  Automatically send voicemail when calls aren't answered
                              </p>
                          </div>
                          <Switch
                              id="auto-voicemail"
                              checked={autoVoicemailEnabled}
                              onCheckedChange={onAutoVoicemailToggle}
                          />
                      </div>
                  </div>
              </CardContent>
          </Card>
      </div>
  );
};


const DialerContainer = ({ 
  onCall, 
  onNewLeads, 
  autoVoicemailEnabled, 
  onAutoVoicemailToggle 
}: { 
  onCall: (number: string, contactName?: string, leadId?: string) => void; 
  onNewLeads: (event: React.ChangeEvent<HTMLInputElement>) => void; 
  autoVoicemailEnabled: boolean;
  onAutoVoicemailToggle: (enabled: boolean) => void;
}) => {
  const [view, setView] = useState<'choice' | 'dialpad'>('choice');
  const { state } = useCall();
  const { toast } = useToast();
  const [showLeadsDialog, setShowLeadsDialog] = useState(false);
  const [fetchedLeads, setFetchedLeads] = useState<Lead[]>([]);
  const [currentDataSource, setCurrentDataSource] = useState<'csv' | 'enriched'>('csv');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Load CSV leads by default
    const persistedLeads = localStorage.getItem('uploadedLeads');
    const persistedEnrichedLeads = localStorage.getItem('enrichedLeads');
    
    if (persistedLeads) {
        try {
            const csvLeads = JSON.parse(persistedLeads);
            setFetchedLeads(csvLeads);
            setCurrentDataSource('csv');
        } catch (e) {
            console.error("Failed to parse persisted CSV leads", e);
        }
    } else if (persistedEnrichedLeads) {
        try {
            const enrichedLeads = JSON.parse(persistedEnrichedLeads);
            setFetchedLeads(enrichedLeads);
            setCurrentDataSource('enriched');
        } catch (e) {
            console.error("Failed to parse persisted enriched leads", e);
        }
    }
    
    const handleNewLeadsEvent = (event: Event) => {
        const customEvent = event as CustomEvent;
        setFetchedLeads(customEvent.detail);
        setShowLeadsDialog(true); 
    };

    const handleFileSelected = (event: Event) => {
      const customEvent = event as CustomEvent;
      const fileEvent = customEvent.detail as React.ChangeEvent<HTMLInputElement>;
      handleFileUpload(fileEvent);
    };

    window.addEventListener('leadsUpdated', handleNewLeadsEvent);
    window.addEventListener('fileSelected', handleFileSelected);
    return () => {
        window.removeEventListener('leadsUpdated', handleNewLeadsEvent);
        window.removeEventListener('fileSelected', handleFileSelected);
    };
  }, []);

  const parseCSV = (text: string): Lead[] => {
    try {
        const lines = text.trim().split(/\r\n|\n/);
        if (lines.length < 2) return [];

        const delimiter = lines[0].includes('\t') ? '\t' : ',';
        
        const cleanHeader = (header: string) => {
            let clean = header.trim().replace(/"/g, '').toLowerCase();
            // Specific mappings for user's columns
            if (clean.includes('phone') || clean === 'companyphone') return 'phoneNumber';
            if (clean.includes('email') || clean === 'owneremail') return 'email';
            if (clean.includes('company')) return 'company';
            if (clean.includes('website')) return 'website';
            if (clean.includes('name')) return 'name';
            if (clean === 'lead_id') return 'lead_id';
            // Generic camelCase conversion for others
            return clean.replace(/[^a-zA-Z0-9]+(.)/g, (m, chr) => chr.toUpperCase());
        };

        const headers = lines[0].split(delimiter).map(cleanHeader);

        const leads = lines.slice(1).map((line, rowIndex) => {
            const values = line.split(delimiter);
            const leadData: { [key: string]: any } = {};

            headers.forEach((header, index) => {
                let value = (values[index] || '').trim().replace(/"/g, '');
                
                if (header === 'phoneNumber') {
                    if (/e/i.test(value)) {
                        const num = parseFloat(value);
                        if (!isNaN(num)) {
                            value = String(BigInt(Math.round(num)));
                        }
                    }
                    value = value.replace(/[^\d+]/g, '');
                }
                
                leadData[header] = value;
            });

            // Ensure unique lead_id for each row
            if (!leadData['lead_id'] || leadData['lead_id'].trim() === '') {
                leadData['lead_id'] = `csv_gen_${Date.now()}_${rowIndex}`;
            } else {
                // Append row index to existing ID to ensure uniqueness
                leadData['lead_id'] = `${leadData['lead_id']}_row_${rowIndex}`;
            }
            
            return leadData as Lead;
        });

        // Remove duplicates based on company and phone number
        const filteredLeads = leads.filter((lead, index, array) => 
            lead.company && 
            array.findIndex(l => 
                l.company === lead.company && 
                (l.phoneNumber || l.companyPhone) === (lead.phoneNumber || lead.companyPhone)
            ) === index
        );

        return filteredLeads;

    } catch (e) {
        console.error("Failed to parse CSV", e);
        toast({ title: 'Upload Failed', description: 'Could not parse the CSV file. Please check the format.', variant: 'destructive' });
        return [];
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        if (text) {
            try {
              const parsedLeads = parseCSV(text);
              if (parsedLeads.length > 0) {
                setFetchedLeads(parsedLeads);
                setCurrentDataSource('csv');
                localStorage.setItem('uploadedLeads', JSON.stringify(parsedLeads));
                window.dispatchEvent(new CustomEvent('leadsUpdated', { detail: parsedLeads }));
                toast({ title: 'Leads Uploaded', description: `${parsedLeads.length} leads have been successfully loaded.` });
              } else {
                toast({ title: 'Parsing Error', description: 'No valid leads found in the file. Please check the file content and format.', variant: 'destructive' });
              }
            } catch (error) {
              console.error("Error processing file:", error);
              toast({ title: 'Upload Failed', description: 'An unexpected error occurred while processing the file.', variant: 'destructive' });
            }
        } else {
           toast({ title: 'Upload Failed', description: 'The file appears to be empty.', variant: 'destructive' });
        }
      };
      reader.onerror = () => {
          toast({ title: 'Upload Failed', description: 'Could not read the file.', variant: 'destructive' });
      }
      reader.readAsText(file);
    }
  };

  const handleViewLeads = () => {
    if (state.activeCall) {
        toast({ title: 'Finish current call first', variant: 'destructive' });
        return;
    }
    
    // Load CSV data specifically
    const persistedCsvLeads = localStorage.getItem('uploadedLeads');
    if (persistedCsvLeads) {
        try {
            const csvLeads = JSON.parse(persistedCsvLeads);
            setFetchedLeads(csvLeads);
            setCurrentDataSource('csv');
            setShowLeadsDialog(true);
        } catch (e) {
            console.error("Failed to parse CSV leads", e);
            triggerFileUpload();
        }
        } else {
        triggerFileUpload();
    }
  };

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  }

  const handleRefreshLeads = () => {
    setShowLeadsDialog(false);
    // If current data source is CSV, trigger file upload
    if (currentDataSource === 'csv') {
      triggerFileUpload();
    } else {
      // For enriched leads, reload from the main application
      // handleLoadEnrichedLeads(); // COMMENTED OUT: Enriched leads functionality disabled
    }
  }

  /* 
  // COMMENTED OUT: Load Enriched Leads functionality
  const handleLoadEnrichedLeads = async () => {
    if (state.activeCall?.status === 'in-progress') {
        toast({ title: 'Finish current call first', variant: 'destructive' });
        return;
    }
    
    try {
      const response = await fetch('http://localhost:8001/api/v1/enriched_leads', {
        method: 'GET',
        credentials: 'include',  // Include cookies for authentication
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in to the main application first.');
        }
        throw new Error('Failed to fetch enriched leads');
      }
      const data = await response.json();
      
      if (data.status === 'success' && data.data && data.data.length > 0) {
        // Transform enriched leads to match the CSV lead format
        const enrichedLeads = data.data.map((lead: any, index: number) => ({
          lead_id: `enriched_${lead.lead_id || lead.draft_id}_${index}`, // Ensure unique IDs
          company: lead.company || '',
          website: lead.website || '',
          industry: lead.industry || '',
          revenue: lead.revenue || '',
          employees: lead.employees || '',
          city: lead.city || '',
          state: lead.state || '',
          companyPhone: lead.phone_number, // Map phone_number to companyPhone
          phoneNumber: lead.phone_number, // Ensure consistent phone field
          phone: lead.phone_number, // Also include as phone for compatibility
          source: 'enriched',
          draft_id: lead.draft_id,
          // Explicitly don't include email fields for enriched leads
          owner_email: undefined,
          email: undefined
        }));
        
        // Remove duplicates based on company and phone number
        const uniqueEnrichedLeads = enrichedLeads.filter((lead, index, array) => 
          lead.company && 
          array.findIndex(l => 
            l.company === lead.company && 
            l.phoneNumber === lead.phoneNumber
          ) === index
        );
        
        setFetchedLeads(uniqueEnrichedLeads);
        setCurrentDataSource('enriched');
        // Store enriched leads separately to preserve CSV data
        localStorage.setItem('enrichedLeads', JSON.stringify(uniqueEnrichedLeads));
        window.dispatchEvent(new CustomEvent('leadsUpdated', { detail: enrichedLeads }));
        setShowLeadsDialog(true);
        toast({ 
          title: 'Enriched Leads Loaded', 
          description: `${uniqueEnrichedLeads.length} enriched leads have been successfully loaded. ${data.mode === 'standalone' ? '(Demo mode)' : ''}` 
        });
      } else {
        toast({ 
          title: 'No Enriched Leads', 
          description: 'No enriched leads found. Please create some leads first in the main application.', 
          variant: 'destructive' 
        });
      }
    } catch (error) {
      console.error('Error loading enriched leads:', error);
      const errorMessage = error instanceof Error ? error.message : 'Could not load enriched leads. Please try again.';
      toast({ 
        title: 'Failed to Load', 
        description: errorMessage, 
        variant: 'destructive' 
      });
    }
  };
  */

  return (
    <>
    <AnimatePresence mode="wait">
      {view === 'choice' ? (
        <motion.div
          key="choice"
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 50 }}
          transition={{ duration: 0.2 }}
        >
          <ChoiceView 
            onDial={() => setView('dialpad')} 
            onViewLeads={handleViewLeads} 
            autoVoicemailEnabled={autoVoicemailEnabled}
            onAutoVoicemailToggle={onAutoVoicemailToggle}
          />
        </motion.div>
      ) : (
        <motion.div
          key="dialpad"
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -50 }}
          transition={{ duration: 0.2 }}
        >
          <DialpadView onCall={onCall} onBack={() => setView('choice')} />
        </motion.div>
      )}
    </AnimatePresence>
    <LeadsDialog 
        open={showLeadsDialog}
        onOpenChange={setShowLeadsDialog}
        leads={fetchedLeads}
        onRefreshLeads={handleRefreshLeads}
        dataSource={currentDataSource}
      />
    <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        className="hidden"
        accept=".csv,.tsv,.txt"
      />
    </>
  );
};


const ActiveCallView = () => {
  const { state, endActiveCall } = useCall();
  const { activeCall } = state;
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (activeCall?.status === 'in-progress' || activeCall?.status === 'ringing-outgoing') {
      const startTime = activeCall.startTime || Date.now();
      setDuration(Math.floor((Date.now() - startTime) / 1000));
      interval = setInterval(() => {
        setDuration(d => d + 1);
      }, 1000);
    }
    return () => {
        if(interval) clearInterval(interval);
    };
  }, [activeCall?.status, activeCall?.startTime]);


  if (!activeCall) return null;
  
  const isConnecting = ['ringing-outgoing', 'queued'].includes(activeCall.status);
  const isCallActive = activeCall.status === 'in-progress';

  const handleHangup = () => {
    endActiveCall('canceled');
  };

  const statusTextMap: { [key in CallStatus]?: string } = {
    'ringing-outgoing': 'Ringing...',
    'in-progress': formatDuration(duration),
    'queued': 'Connecting...',
    'completed': 'Call Ended',
    'busy': 'Busy',
    'failed': 'Call Failed',
    'canceled': 'Canceled',
    'voicemail-dropped': 'Voicemail Sent',
    'fetching-transcript': 'Finalizing...',
  }

  const getStatusInfo = () => {
    const status = activeCall.status as CallStatus;
    const text = statusTextMap[status] || 'Connecting...';

    switch(status) {
      case 'ringing-outgoing':
      case 'queued':
      case 'ringing-incoming':
        return { text, icon: <CircleDotDashed className="animate-spin h-4 w-4 text-muted-foreground" />, color: 'text-muted-foreground' };
      case 'in-progress':
        return { text, icon: <Clock className="h-4 w-4 text-green-500" />, color: 'text-green-500' };
      case 'fetching-transcript':
        return { text, icon: <Loader2 className="animate-spin h-4 w-4 text-blue-500" />, color: 'text-blue-500' };
      case 'failed':
      case 'busy':
      case 'canceled':
        return { text, icon: <AlertCircle className="h-4 w-4 text-destructive" />, color: 'text-destructive' };
      case 'voicemail-dropped':
        return { text: 'Voicemail Sent', icon: <PhoneOff className="h-4 w-4 text-muted-foreground" />, color: 'text-muted-foreground' };
      default:
        return { text: 'Call Ended', icon: <PhoneOff className="h-4 w-4 text-muted-foreground" />, color: 'text-muted-foreground' };
    }
  };

  const statusInfo = getStatusInfo();
  
  return (
    <>
      <div className="flex flex-col items-center justify-between p-4 h-full min-h-[400px]">
        <div className="text-center mt-8">
          <p className="text-2xl font-semibold">{activeCall.contactName || (activeCall.direction === 'outgoing' ? activeCall.to : activeCall.from)}</p>
          <div className={cn("flex items-center justify-center gap-2 mt-2 font-mono", statusInfo.color)}>
            {statusInfo.icon}
            <span>{statusInfo.text}</span>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 my-8">
            <Button variant="outline" className="h-16 w-16 rounded-full flex-col" disabled>
                <Mic />
                <span className="text-xs mt-1">Mute</span>
            </Button>
            <Button variant="outline" className="h-16 w-16 rounded-full flex-col" disabled>
                <Grid3x3 />
                <span className="text-xs mt-1">Keypad</span>
            </Button>
        </div>

        <Button
        size="lg"
        variant={(isConnecting || isCallActive) ? 'destructive' : 'secondary'}
        className="w-full rounded-full h-14"
        onClick={handleHangup}
        >
        {(isConnecting || isCallActive) ? <PhoneOff className="mr-2 h-5 w-5" /> : <X className="mr-2 h-5 w-s5" />}
        {(isConnecting || isCallActive) ? 'End Call' : 'Close'}
        </Button>
      </div>
    </>
  );
};


export default function Softphone() {
  const { state, dispatch, startOutgoingCall, getAgentPreferences, updateAgentPreferences } = useCall();
  const { toast } = useToast();
  const { activeCall, softphoneOpen } = state;
  const dragControls = useDragControls();
  const constraintsRef = useRef(null);
  const [autoVoicemailEnabled, setAutoVoicemailEnabled] = useState(false);
  const currentAgent = state.currentAgent;

  // Load agent preferences when component mounts or agent changes
  useEffect(() => {
    if (currentAgent) {
      getAgentPreferences(currentAgent.id).then(preferences => {
        if (preferences) {
          setAutoVoicemailEnabled(preferences.auto_voicemail_enabled || false);
        }
      }).catch(error => {
        console.error('Failed to load agent preferences:', error);
      });
    }
  }, [currentAgent, getAgentPreferences]);

  const handleAutoVoicemailToggle = async (enabled: boolean) => {
    if (!currentAgent) return;
    
    try {
      await updateAgentPreferences(currentAgent.id, { auto_voicemail_enabled: enabled });
      setAutoVoicemailEnabled(enabled);
    } catch (error) {
      console.error('Failed to update auto-voicemail preference:', error);
      toast({
        title: 'Error',
        description: 'Failed to save preference. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const handleCall = (number: string, contactName?: string, leadId?: string) => {
    startOutgoingCall(number, contactName, leadId);
  };
  
  const handleToggle = (open: boolean) => {
    dispatch({ type: 'SET_SOFTPHONE_OPEN', payload: open });
  }

  const getTriggerIcon = () => {
    return <Phone className="h-6 w-6" />;
  };
  
  const isRinging = activeCall?.status === 'ringing-outgoing';

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    // This function is just a placeholder - the actual processing is handled by DialerContainer
    // Clear the file input after processing
    const target = event.target;
    if (target) {
      target.value = '';
    }
  };

  return (
    <div ref={constraintsRef} className="fixed inset-0 pointer-events-none">
      <motion.div
        drag
        dragControls={dragControls}
        dragConstraints={constraintsRef}
        dragListener={false}
        className="absolute bottom-6 right-6 z-50 pointer-events-auto"
      >
        <Popover open={softphoneOpen} onOpenChange={handleToggle}>
          <PopoverTrigger asChild>
            <Button
              className={cn(
                'h-16 w-16 rounded-full shadow-lg transition-colors duration-300',
                activeCall ? 'bg-green-500 hover:bg-green-600' : 'bg-primary text-primary-foreground hover:bg-primary/90',
                isRinging && 'animate-pulse'
              )}
              size="icon"
            >
              {getTriggerIcon()}
            </Button>
          </PopoverTrigger>
          <PopoverContent
            side="top"
            align="end"
            className="w-80 rounded-2xl shadow-2xl p-0 border-0 mb-2"
            sideOffset={16}
          >
              <Card className="border-0 shadow-none">
                <div
                  onPointerDown={(e) => dragControls.start(e)}
                  className="absolute top-2 right-2 cursor-grab active:cursor-grabbing p-2 text-muted-foreground"
                >
                  <Move className="h-4 w-4" />
                </div>
                <CardContent className="p-0">
                  <AnimatePresence mode="wait">
                    {activeCall ? (
                      <motion.div
                        key="active-call"
                        initial={{ opacity: 0, x: 50 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -50 }}
                        transition={{ duration: 0.2 }}
                      >
                        <ActiveCallView />
                      </motion.div>
                    ) : (
                       <DialerContainer 
                         onCall={handleCall} 
                         onNewLeads={handleFileChange} 
                         autoVoicemailEnabled={autoVoicemailEnabled}
                         onAutoVoicemailToggle={handleAutoVoicemailToggle}
                       />
                    )}
                  </AnimatePresence>
                </CardContent>
              </Card>
          </PopoverContent>
        </Popover>
      </motion.div>
    </div>
  );
}
