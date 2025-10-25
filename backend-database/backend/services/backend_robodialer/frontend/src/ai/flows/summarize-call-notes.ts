'use server';

/**
 * @fileOverview A call summarization AI agent.
 *
 * - summarizeCallNotes - A function that handles the call summarization process.
 * - SummarizeCallNotesInput - The input type for the summarizeCallNotes function.
 * - SummarizeCallNotesOutput - The return type for the summarizeCallNotes function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const SummarizeCallNotesInputSchema = z.object({
  notes: z.string().describe('The transcript or notes from the call.'),
});
export type SummarizeCallNotesInput = z.infer<typeof SummarizeCallNotesInputSchema>;

const SummarizeCallNotesOutputSchema = z.object({
  summary: z.string().describe('A concise summary of the call.'),
});
export type SummarizeCallNotesOutput = z.infer<typeof SummarizeCallNotesOutputSchema>;

export async function summarizeCallNotes(input: SummarizeCallNotesInput): Promise<SummarizeCallNotesOutput> {
  return summarizeCallNotesFlow(input);
}

const prompt = ai.definePrompt({
  name: 'summarizeCallNotesPrompt',
  input: {schema: SummarizeCallNotesInputSchema},
  output: {schema: SummarizeCallNotesOutputSchema},
  prompt: `You are an AI assistant that summarizes phone calls between agents and customers. You will be given a transcript or notes from the call. Your job is to provide a short summary, extracting the key information. The summary should be no more than 3 sentences long.

Call Notes/Transcript: {{{notes}}}`,
});

const summarizeCallNotesFlow = ai.defineFlow(
  {
    name: 'summarizeCallNotesFlow',
    inputSchema: SummarizeCallNotesInputSchema,
    outputSchema: SummarizeCallNotesOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
