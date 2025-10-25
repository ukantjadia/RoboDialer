
'use client';

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useCall } from '@/contexts/call-context';
import type { Call } from '@/lib/types';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from './ui/form';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { generateSummaryAction } from '@/lib/actions';
import { useState, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Wand2 } from 'lucide-react';

const notesFormSchema = z.object({
  notes: z.string().optional(),
  summary: z.string().optional(),
});

type NotesFormValues = z.infer<typeof notesFormSchema>;

// This function parses the combined notes field from the backend
const parseCombinedNotes = (call: Call | undefined | null) => {
    if (!call) {
        return { summary: '', notes: '' };
    }
    
    const combinedNotes = call.notes || '';
    const summaryFromCall = call.summary || '';

    // If a separate summary exists, prioritize it.
    if (summaryFromCall) {
        return { summary: summaryFromCall, notes: combinedNotes };
    }

    // Otherwise, parse the combined field
    const summaryMarker = 'SUMMARY: ';
    const notesMarker = '\n---\nNOTES: ';
    const summaryIndex = combinedNotes.indexOf(summaryMarker);
    const notesIndex = combinedNotes.indexOf(notesMarker);

    if (summaryIndex === 0 && notesIndex > 0) {
        const summary = combinedNotes.substring(summaryMarker.length, notesIndex);
        const notes = combinedNotes.substring(notesIndex + notesMarker.length);
        return { summary, notes };
    }

    return { summary: '', notes: combinedNotes };
};


export default function PostCallSheet({ call }: { call: Call }) {
  const { dispatch, updateNotesAndSummary } = useCall();
  const { toast } = useToast();
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const form = useForm<NotesFormValues>({
    resolver: zodResolver(notesFormSchema),
    defaultValues: {
      notes: '',
      summary: '',
    },
  });

  useEffect(() => {
    if (call) {
      const { summary, notes } = parseCombinedNotes(call);
      form.reset({
          notes: notes || '',
          summary: summary || '',
      });
    }
  }, [call, form]);

  const handleOpenChange = (open: boolean) => {
    if (!open && !isSaving) {
      if (dispatch) {
        dispatch({ type: 'CLOSE_POST_CALL_SHEET' });
      }
    }
  };
  
  const handleGenerateSummary = async () => {
    const notes = form.getValues('notes');
    if (!notes) {
        form.setError('notes', { message: 'Please enter notes or wait for transcript before generating a summary.' });
        return;
    }
    setIsSummarizing(true);
    const result = await generateSummaryAction(notes);
    if (result.summary) {
        form.setValue('summary', result.summary);
        toast({ title: 'Summary Generated', description: 'AI summary has been successfully created.' });
    } else {
        toast({
            variant: 'destructive',
            title: 'Error',
            description: result.error || 'Could not generate summary.'
        });
    }
    setIsSummarizing(false);
  }

  const onSubmit = async (data: NotesFormValues) => {
    setIsSaving(true);
    if (updateNotesAndSummary) {
        await updateNotesAndSummary(call.id, data.notes || '', data.summary);
    }
    setIsSaving(false);
    if (dispatch) {
        dispatch({ type: 'CLOSE_POST_CALL_SHEET' });
    }
  };

  return (
    <Sheet open={!!call} onOpenChange={handleOpenChange}>
      <SheetContent className="sm:max-w-lg">
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-col h-full"
          >
            <SheetHeader>
              <SheetTitle>Post-Call Notes</SheetTitle>
              <SheetDescription>
                Add notes and generate a summary for your call with{' '}
                {call.contactName || call.to || call.from}.
              </SheetDescription>
            </SheetHeader>
            <div className="py-6 space-y-4 flex-1 overflow-y-auto">
              <FormField
                control={form.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Call Notes & Transcript</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Call transcript will appear here. You can add your own notes as well."
                        className="min-h-[120px]"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="summary"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex justify-between items-center">
                      <FormLabel>AI Summary</FormLabel>
                      <Button type="button" variant="outline" size="sm" onClick={handleGenerateSummary} disabled={isSummarizing || isSaving}>
                        {isSummarizing ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Wand2 className="mr-2 h-4 w-4" />
                        )}
                        Generate
                      </Button>
                    </div>
                    <FormControl>
                      <Textarea
                        placeholder="AI-generated summary will appear here."
                        className="min-h-[120px] bg-muted/50"
                        readOnly={isSummarizing}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <SheetFooter>
              <Button type="submit" disabled={isSaving}>
                {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Notes
              </Button>
            </SheetFooter>
          </form>
        </Form>
      </SheetContent>
    </Sheet>
  );
}
