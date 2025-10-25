
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const sendVoicemailEndpoint = `${process.env.BASE_URL}/api/twilio/send_voicemail`;

  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Voicemail endpoint is not configured.' },
      { status: 500 }
    );
  }

  try {
    const body = await req.json();
    
    const { phone, script } = body;

    if (!phone || !script) {
        return NextResponse.json({ message: "Both 'phone' and 'script' fields are required" }, { status: 400 });
    }
    
    const response = await fetch(sendVoicemailEndpoint, {
      method: 'POST',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ phone, script }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error from send_voicemail endpoint:', errorText);
      try {
        const errorJson = JSON.parse(errorText);
        return NextResponse.json({ message: errorJson.message || `Failed to send voicemail. Status: ${response.status}` }, { status: response.status });
      } catch(e) {
        return NextResponse.json({ message: `Failed to send voicemail. Status: ${response.status}`, details: errorText }, { status: response.status });
      }
    }

    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error proxying send_voicemail request:', error);
    return NextResponse.json(
      { error: 'Failed to proxy send_voicemail request' },
      { status: 500 }
    );
  }
}
