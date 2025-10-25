

'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useCall } from '@/contexts/call-context';
import { useState, useEffect } from 'react';
import { Loader2, Voicemail as VoicemailIcon } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const DEFAULT_VOICEMAIL_SCRIPT = `Hello, this is Zackary Beckham from Caprae Capital Partners.
I’m reaching out because we’ve identified opportunities that may help your business grow through strategic funding and advisory support.
I’d be happy to share more details at your convenience.
You can reach me directly at 480-518-2592, or reply to this message, and we’ll schedule a quick call.
Once again, this is Zackary Beckham with Caprae Capital Partners. Thank you, and I look forward to connecting.`;

export default function VoicemailDialog() {
  const { sendVoicemail, state, dispatch, getAgentPreferences, updateAgentPreferences } = useCall();
  const { toast } = useToast();
  const [script, setScript] = useState(DEFAULT_VOICEMAIL_SCRIPT);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingPreferences, setIsLoadingPreferences] = useState(false);

  const { voicemailLeadTarget } = state;
  const currentAgent = state.currentAgent;

  // Load agent's custom voicemail script when dialog opens
  useEffect(() => {
    if (voicemailLeadTarget && currentAgent) {
      setIsLoadingPreferences(true);
      getAgentPreferences(currentAgent.id).then(preferences => {
        let customScript = preferences?.voicemail_script || DEFAULT_VOICEMAIL_SCRIPT;
        
        // Replace placeholder with lead name if available
        if (voicemailLeadTarget?.company) {
          customScript = customScript.replace('Hello,', `Hello ${voicemailLeadTarget.company},`);
        }
        
        setScript(customScript);
      }).catch(error => {
        console.error('Failed to load agent preferences:', error);
        setScript(DEFAULT_VOICEMAIL_SCRIPT);
      }).finally(() => {
        setIsLoadingPreferences(false);
      });
    } else {
      setScript(DEFAULT_VOICEMAIL_SCRIPT);
    }
  }, [voicemailLeadTarget, currentAgent, getAgentPreferences]);

  const handleClose = () => {
    if (dispatch) {
      dispatch({ type: 'CLOSE_VOICEMAIL_DIALOG' });
    }
  };

  const handleSend = async () => {
    if (!voicemailLeadTarget || !script || !currentAgent) {
      toast({
        title: 'Error',
        description: 'Cannot send voicemail without a target lead and a script.',
        variant: 'destructive',
      });
      return;
    }

    const phoneNumber = voicemailLeadTarget.companyPhone || voicemailLeadTarget.phoneNumber;
    if (!phoneNumber) {
        toast({ title: 'No Phone Number', description: 'This lead does not have a phone number.', variant: 'destructive' });
        return;
    }
    
    setIsSending(true);
    
    try {
      // Save the script as agent's preference if it's different from default
      const cleanScript = script.replace(`Hello ${voicemailLeadTarget?.company || ''},`, 'Hello,');
      if (cleanScript !== DEFAULT_VOICEMAIL_SCRIPT) {
        await updateAgentPreferences(currentAgent.id, { voicemail_script: cleanScript });
      }
      
      // Send the voicemail
      await sendVoicemail(voicemailLeadTarget, script);
      
      // Close the dialog
      handleClose();
    } catch (error) {
      console.error('Error sending voicemail:', error);
      toast({
        title: 'Error',
        description: 'Failed to send voicemail. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSending(false);
    }
  };

  if (!voicemailLeadTarget) return null;

  const phoneNumber = voicemailLeadTarget.companyPhone || voicemailLeadTarget.phoneNumber;
  const leadName = voicemailLeadTarget.company;

  return (
    <Dialog open={!!voicemailLeadTarget} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Send Voicemail</DialogTitle>
          <DialogDescription>
            Edit the script below and send it as a voicemail to {leadName} at {phoneNumber}. 
            {isLoadingPreferences ? ' Loading your preferences...' : ' Your changes will be saved for future use.'} This action will be logged.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <Textarea
            value={script}
            onChange={(e) => setScript(e.target.value)}
            className="min-h-[200px]"
            placeholder="Enter your voicemail script..."
            disabled={isLoadingPreferences}
          />
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSending}
          >
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={isSending || isLoadingPreferences || !script || !phoneNumber}>
            {isSending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <VoicemailIcon className="mr-2 h-4 w-4" />
            )}
            {isSending ? 'Sending...' : 'Send & Log Voicemail'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
