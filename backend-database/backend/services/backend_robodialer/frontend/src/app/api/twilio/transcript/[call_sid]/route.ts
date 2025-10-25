
import { NextRequest, NextResponse } from 'next/server';

// Handle GET requests to fetch a transcript for a specific call
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ call_sid: string }> }
) {
  const { call_sid } = await params;

  if (!call_sid) {
    return NextResponse.json({ error: 'Call SID is required.' }, { status: 400 });
  }
  
  const getTranscriptEndpoint = `${process.env.BASE_URL}/api/twilio/get_transcript/${call_sid}`;

  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Transcript endpoint is not configured in environment variables.' },
      { status: 500 }
    );
  }

  try {
    const response = await fetch(getTranscriptEndpoint, {
      method: 'GET',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error from get_transcript endpoint:', errorText);
      return NextResponse.json({ error: `Failed to fetch transcript. Status: ${response.status} ${response.statusText}` }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Error proxying get_transcript request:', error);
    return NextResponse.json({ error: 'Failed to proxy get_transcript request' }, { status: 500 });
  }
}
