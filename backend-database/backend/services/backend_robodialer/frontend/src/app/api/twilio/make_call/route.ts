
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const baseUrl = process.env.BASE_URL;
  const makeCallEndpoint = `${baseUrl}/api/twilio/make_call`;

  console.log('Frontend API: BASE_URL =', baseUrl);
  console.log('Frontend API: make_call endpoint =', makeCallEndpoint);

  if (!baseUrl) {
    console.error('BASE_URL not set in environment variables');
    return NextResponse.json(
      { error: 'Twilio make_call endpoint is not configured in environment variables.' },
      { status: 500 }
    );
  }

  try {
    const body = await req.json();
    
    // Debug and validate request body
    console.log('Frontend API: Original request body:', body);
    
    // Ensure agent_id and to are in the body being forwarded
    if (!body.agent_id || !body.to) {
        console.error('Missing agent_id or to in request body:', body);
        // Add debugging info about what's missing
        const missing = [];
        if (!body.agent_id) missing.push('agent_id');
        if (!body.to) missing.push('to');
        return NextResponse.json({ 
          error: `Missing required fields: ${missing.join(', ')}`,
          received_body: body,
          debug_info: `agent_id: ${body.agent_id}, to: ${body.to}, dialer_type: ${body.dialer_type}`
        }, { status: 400 });
    }
    
    // Ensure dialer_type is provided
    if (!body.dialer_type) {
        body.dialer_type = 'manual'; // Default fallback
        console.log('Frontend API: Added default dialer_type: manual');
    }
    
    console.log('Frontend API: Forwarding request to backend:', makeCallEndpoint);
    console.log('Frontend API: Final request body:', body);
    
    const response = await fetch(makeCallEndpoint, {
      method: 'POST',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    console.log('Frontend API: Backend response status:', response.status);
    console.log('Frontend API: Backend response ok:', response.ok);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error from make_call endpoint:', errorText);
      try {
        const errorJson = JSON.parse(errorText);
        return NextResponse.json({ error: errorJson.description || `Failed to initiate call from backend.` }, { status: response.status });
      } catch (e) {
        return NextResponse.json({ error: `Failed to initiate call from backend. Status: ${response.status}` }, { status: response.status });
      }
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Error proxying make_call request:', error);
    return NextResponse.json({ error: 'Failed to proxy make_call request' }, { status: 500 });
  }
}
