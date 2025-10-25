import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest, 
  { params }: { params: Promise<{ agent_id: string }> }
) {
  try {
    const { agent_id } = await params;
    const baseUrl = process.env.BASE_URL;
    
    if (!baseUrl) {
      return NextResponse.json(
        { error: 'Backend service configuration error' },
        { status: 500 }
      );
    }

    const response = await fetch(`${baseUrl}/api/twilio/agent_preferences/${agent_id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching agent preferences:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest, 
  { params }: { params: Promise<{ agent_id: string }> }
) {
  try {
    const { agent_id } = await params;
    const body = await request.json();
    const baseUrl = process.env.BASE_URL;
    
    if (!baseUrl) {
      return NextResponse.json(
        { error: 'Backend service configuration error' },
        { status: 500 }
      );
    }

    const response = await fetch(`${baseUrl}/api/twilio/agent_preferences/${agent_id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error updating agent preferences:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}