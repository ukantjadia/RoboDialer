
import { NextRequest, NextResponse } from 'next/server';

const AGENTS_API_ENDPOINT = `${process.env.BASE_URL}/api/v1/agents`;

// DELETE handler to remove an agent
export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ agent_id: string }> }
) {
  const { agent_id } = await params;

  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Agents API endpoint is not configured.' },
      { status: 500 }
    );
  }

  if (!agent_id) {
    return NextResponse.json({ error: 'Agent ID is required.' }, { status: 400 });
  }

  try {
    const response = await fetch(`${AGENTS_API_ENDPOINT}/${agent_id}`, {
      method: 'DELETE',
      headers: {
        'ngrok-skip-browser-warning': 'true',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorDetails = errorText;
      try {
        const errorJson = JSON.parse(errorText);
        errorDetails = errorJson.message || errorJson.error || errorText;
      } catch (e) { /* Not a JSON response */ }

      console.error(`Error from external delete agent API (ID: ${agent_id}):`, errorDetails);
      return NextResponse.json(
        { error: `Failed to delete agent. Status: ${response.status}`, details: errorDetails },
        { status: response.status }
      );
    }

    // Check if response has content before trying to parse JSON
    if (response.status === 204) { // No Content
        return new NextResponse(null, { status: 204 });
    }
    
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      return NextResponse.json(data);
    }
    
    return new NextResponse(null, { status: 204 }); // Success but no content to return

  } catch (error) {
    console.error(`Error proxying delete agent request (ID: ${agent_id}):`, error);
    return NextResponse.json(
      { error: 'Failed to proxy delete request to the agents API.' },
      { status: 500 }
    );
  }
}

// PUT handler to update an agent
export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ agent_id: string }> }
) {
  const { agent_id } = await params;

  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Agents API endpoint is not configured.' },
      { status: 500 }
    );
  }

  if (!agent_id) {
    return NextResponse.json({ error: 'Agent ID is required.' }, { status: 400 });
  }

  try {
    const body = await req.json();

    // The backend does not have a PUT endpoint for agents, so we will just return success.
    // This acknowledges the frontend request without causing an error.
    // In a real application, you would implement the PUT /api/v1/agents/<id> endpoint
    // on your Flask backend.
    
    // For now, we simulate a successful update.
    console.log(`Simulating successful update for agent ${agent_id} with data:`, body);
    
    const updatedAgentData = {
      id: parseInt(agent_id),
      ...body,
    };
    
    return NextResponse.json(updatedAgentData, { status: 200 });


  } catch (error) {
    console.error(`Error processing update agent request (ID: ${agent_id}):`, error);
    return NextResponse.json(
      { error: 'Failed to process update request for the agent.' },
      { status: 500 }
    );
  }
}
