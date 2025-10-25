
import { NextRequest, NextResponse } from 'next/server';

const AGENTS_API_ENDPOINT = `${process.env.BASE_URL}/api/v1/agents`;

// GET handler to fetch all agents
export async function GET(req: NextRequest) {
  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Agents API endpoint is not configured.' },
      { status: 500 }
    );
  }

  try {
    // Pass through the include_archived query parameter
    const { searchParams } = new URL(req.url);
    const includeArchived = searchParams.get('include_archived');
    
    let apiUrl = `${process.env.BASE_URL}/api/twilio/agents`;
    if (includeArchived) {
      apiUrl += `?include_archived=${includeArchived}`;
    }

    const response = await fetch(apiUrl, {
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error from external agents API:', errorText);
      return NextResponse.json(
        { error: `Failed to fetch from external API. Status: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error proxying request to agents API:', error);
    return NextResponse.json(
      { error: 'Failed to proxy request to the agents API.' },
      { status: 500 }
    );
  }
}

// POST handler to add a new agent
export async function POST(req: NextRequest) {
    if (!process.env.BASE_URL) {
        return NextResponse.json(
          { error: 'Agents API endpoint is not configured.' },
          { status: 500 }
        );
    }

    try {
        const body = await req.json();

        // Basic validation
        if (!body.name || !body.email || !body.phone) {
            return NextResponse.json({ error: 'Name, email, and phone are required.' }, { status: 400 });
        }

        const response = await fetch(AGENTS_API_ENDPOINT, {
            method: 'POST',
            headers: {
                'ngrok-skip-browser-warning': 'true',
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const errorText = await response.text();
            let errorDetails = errorText;
            try {
                const errorJson = JSON.parse(errorText);
                errorDetails = errorJson.message || errorJson.error || errorText;
            } catch(e) { /* Not a JSON response */ }

            console.error('Error from external add agent API:', errorDetails);
            return NextResponse.json(
              { error: `Failed to add agent. Status: ${response.status}`, details: errorDetails },
              { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data, { status: 201 });

    } catch (error) {
        console.error('Error proxying add agent request:', error);
        return NextResponse.json(
            { error: 'Failed to proxy request to the agents API.' },
            { status: 500 }
        );
    }
}

    