
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const sendEmailEndpoint = `${process.env.BASE_URL}/api/v1/send_email`;

  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Email endpoint is not configured.' },
      { status: 500 }
    );
  }

  try {
    const body = await req.json();
    
    const response = await fetch(sendEmailEndpoint, {
      method: 'POST',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error from send_email endpoint:', errorText);
      return NextResponse.json({ error: `Failed to send email. Status: ${response.status} ${response.statusText}`, details: errorText }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error proxying send_email request:', error);
    return NextResponse.json(
      { error: 'Failed to proxy send_email request' },
      { status: 500 }
    );
  }
}
