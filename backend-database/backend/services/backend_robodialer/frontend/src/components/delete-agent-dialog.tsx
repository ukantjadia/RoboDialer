
'use client';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { Loader2, Archive } from 'lucide-react';

interface ArchiveAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agentName: string;
  onConfirm: () => Promise<void>;
}

export default function ArchiveAgentDialog({
  open,
  onOpenChange,
  agentName,
  onConfirm,
}: ArchiveAgentDialogProps) {
  const [isArchiving, setIsArchiving] = useState(false);

  const handleConfirm = async () => {
    setIsArchiving(true);
    await onConfirm();
    setIsArchiving(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Archive Agent</AlertDialogTitle>
          <AlertDialogDescription>
            This will archive the agent profile for{' '}
            <span className="font-semibold text-foreground">{agentName}</span>. 
            The agent will be hidden from the active list but their call history and statistics will be preserved. 
            You can restore the agent later if needed.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isArchiving}>Cancel</AlertDialogCancel>
          <Button
            variant="secondary"
            onClick={handleConfirm}
            disabled={isArchiving}
          >
            {isArchiving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Archive className="mr-2 h-4 w-4" />}
            {isArchiving ? 'Archiving...' : 'Archive Agent'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

// Legacy export for backward compatibility
export { ArchiveAgentDialog as DeleteAgentDialog };
