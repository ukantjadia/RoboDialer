
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
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { useState, useEffect } from 'react';
import { Loader2, Star } from 'lucide-react';
import type { Agent } from '@/lib/types';

interface GradeAgentDialogProps {
  agent: Agent | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (agentId: number, score: number) => Promise<void>;
}

export default function GradeAgentDialog({
  agent,
  open,
  onOpenChange,
  onSave,
}: GradeAgentDialogProps) {
  const [score, setScore] = useState(agent?.score || 5);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (agent) {
      setScore(agent.score || 5);
    }
  }, [agent]);

  const handleSave = async () => {
    if (agent) {
      setIsSaving(true);
      await onSave(agent.id, score);
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    if (!isSaving) {
      onOpenChange(false);
    }
  };

  if (!agent) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Grade Agent: {agent.name}</DialogTitle>
          <DialogDescription>
            Set a manual performance score for this agent. This score will be saved to their profile.
          </DialogDescription>
        </DialogHeader>
        <div className="py-6 space-y-6">
          <div className="flex items-center justify-between">
            <Label htmlFor={`score-slider-${agent.id}`} className="font-semibold text-lg flex items-center gap-2">
                <Star className="text-primary"/>
                Manual Score
            </Label>
            <span className="font-bold text-2xl">{score.toFixed(1)}</span>
          </div>
          <Slider
            id={`score-slider-${agent.id}`}
            min={1}
            max={10}
            step={0.1}
            value={[score]}
            onValueChange={(value) => setScore(value[0])}
            disabled={isSaving}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Score
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
