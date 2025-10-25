
import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const identity = searchParams.get('identity');
  
  if (!identity) {
    return NextResponse.json({ error: 'Identity is required' }, { status: 400 });
  }

  // The backend endpoint for getting a token, using the server-side BASE_URL
  // The backend expects the identity to be the client_id, which is derived from the agent_id
  const tokenEndpoint = `${process.env.BASE_URL}/api/twilio/token?identity=agent_${identity}_client_id`;

  try {
    const response = await fetch(tokenEndpoint, {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error from token endpoint:', errorText);
      return NextResponse.json({ error: 'Failed to fetch token from backend' }, { status: response.status });
    }

    const data = await response.json();
    // The backend returns { "token": "..." }, so we extract the actual token string.
    return NextResponse.json({ token: data.token });

  } catch (error) {
    console.error('Error proxying token request:', error);
    return NextResponse.json({ error: 'Failed to proxy token request' }, { status: 500 });
  }
}
