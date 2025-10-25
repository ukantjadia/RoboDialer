
import { NextRequest, NextResponse } from 'next/server';

// POST handler to grade an agent
export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ agent_id: string }> }
) {
  const { agent_id } = await params;
  const gradeAgentEndpoint = `${process.env.BASE_URL}/api/v1/grade_agents/${agent_id}`;

  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Backend API endpoint is not configured.' },
      { status: 500 }
    );
  }

  if (!agent_id) {
    return NextResponse.json({ error: 'Agent ID is required.' }, { status: 400 });
  }

  try {
    // The frontend sends { score: X }, which is what the backend expects.
    const body = await req.json();

    if (body.score === undefined) {
        return NextResponse.json({ error: "Missing 'score' in request body." }, { status: 400 });
    }

    const response = await fetch(gradeAgentEndpoint, {
      method: 'POST',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ score: body.score }), // Forwarding the expected format
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorDetails = errorText;
      try {
        const errorJson = JSON.parse(errorText);
        errorDetails = errorJson.message || errorJson.error || errorText;
      } catch (e) { /* Not a JSON response */ }
      
      console.error(`Error from external grade agent API (ID: ${agent_id}):`, errorDetails);
      return NextResponse.json(
        { error: `Failed to grade agent. Status: ${response.status}`, details: errorDetails },
        { status: response.status }
      );
    }

    const data = await response.json();
    // The backend returns { new_score: ... }, let's return it consistently as score_given
    return NextResponse.json({ agent_id: data.agent_id, score_given: data.new_score });

  } catch (error) {
    console.error(`Error proxying grade agent request (ID: ${agent_id}):`, error);
    return NextResponse.json(
      { error: 'Failed to proxy grade agent request to the backend API.' },
      { status: 500 }
    );
  }
}
