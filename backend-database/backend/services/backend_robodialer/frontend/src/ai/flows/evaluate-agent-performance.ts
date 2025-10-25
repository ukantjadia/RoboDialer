
'use server';

/**
 * @fileOverview An agent performance evaluation AI agent.
 *
 * - evaluateAgentPerformance - A function that handles the performance evaluation.
 * - EvaluateAgentPerformanceInput - The input type for the function.
 * - EvaluateAgentPerformanceOutput - The return type for the function.
 */

import { ai } from '@/ai/genkit';
import { z } from 'genkit';

const EvaluateAgentPerformanceInputSchema = z.object({
    agentName: z.string().describe("The name of the agent being evaluated."),
    calls: z.array(
        z.object({
            id: z.string(),
            direction: z.enum(['incoming', 'outgoing']),
            status: z.string(),
            duration: z.number().optional(),
            notes: z.string().optional(),
            summary: z.string().optional(),
        })
    ),
});

export type EvaluateAgentPerformanceInput = z.infer<typeof EvaluateAgentPerformanceInputSchema>;

const EvaluateAgentPerformanceOutputSchema = z.object({
  evaluation: z.string().describe("A comprehensive, yet concise, evaluation of the agent's performance, formatted as a professional report. Use Markdown for formatting (e.g., headings, bullet points). This evaluation must explain the reasoning behind the score."),
  score: z.number().describe("A numerical score from 1 to 10 representing the agent's overall performance, where 1 is poor and 10 is excellent."),
});

export type EvaluateAgentPerformanceOutput = z.infer<typeof EvaluateAgentPerformanceOutputSchema>;

export async function evaluateAgentPerformance(
  input: EvaluateAgentPerformanceInput
): Promise<EvaluateAgentPerformanceOutput> {
  return evaluateAgentPerformanceFlow(input);
}

const prompt = ai.definePrompt({
  name: 'evaluateAgentPerformancePrompt',
  input: { schema: z.object({ agentName: z.string(), callDataJson: z.string() }) },
  output: { schema: EvaluateAgentPerformanceOutputSchema },
  prompt: `You are an expert performance analyst for a financial services company, Caprae Capital Partners. Your task is to evaluate the performance of agent '{{{agentName}}}' based on their recent call logs and provide a score out of 10.

Your analysis and score MUST be based strictly on the following two criteria:
1.  **Successful Calls:** Only consider calls with a 'completed' status. The duration of these calls is important. Long calls (over 3 minutes) are positive ONLY if the notes indicate a successful outcome. A high number of very short completed calls (under 30 seconds) is a major red flag.
2.  **Call Notes Analysis:** This is the most critical factor. For 'completed' calls, analyze the 'notes' field (which contains the raw call transcript and agent notes). Look for evidence of positive engagement, such as scheduled follow-ups, expressions of interest, or successful information gathering. Vague or empty notes are a strong negative signal, regardless of call duration.

**Your Output:**
1.  **Score:** Provide an overall performance score from 1 (poor) to 10 (excellent) based ONLY on the criteria above.
2.  **Evaluation:** Provide a concise, professional evaluation in Markdown. The evaluation must explain *why* you gave the score, referencing the call durations and the content of the notes. It should include:
    - A brief overall summary.
    - A "Strengths" section with 2-3 bullet points.
    - An "Areas for Improvement" section with 2-3 bullet points.
    - A final "Recommendation".

Here are the call logs for {{{agentName}}} to analyze:
{{{callDataJson}}}
`,
});

const evaluateAgentPerformanceFlow = ai.defineFlow(
  {
    name: 'evaluateAgentPerformanceFlow',
    inputSchema: EvaluateAgentPerformanceInputSchema,
    outputSchema: EvaluateAgentPerformanceOutputSchema,
  },
  async (input) => {
    // Filter for actual phone calls, excluding logged emails or voicemails without interaction.
    const actualCalls = input.calls.filter(call => 
        call.status === 'completed' || call.status === 'busy' || call.status === 'failed'
    );

    if (actualCalls.length === 0) {
        return { 
            evaluation: `No actual call data available for ${input.agentName} to analyze. An evaluation requires at least one completed, busy, or failed call log.`, 
            score: 0 
        };
    }

    // Further clean the data for the prompt
    const cleanCalls = actualCalls.map(call => ({
        id: call.id,
        direction: call.direction,
        status: call.status,
        duration: call.duration,
        notes: call.notes,
        summary: call.summary,
    }));

    const { output } = await prompt({ agentName: input.agentName, callDataJson: JSON.stringify(cleanCalls) });
    return output!;
  }
);
