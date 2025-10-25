import { NextRequest, NextResponse } from 'next/server';

// Handle PUT requests to update specific call logs
export async function PUT(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id: callLogId } = await params;
  const putCallLogEndpoint = `${process.env.BASE_URL}/api/v1/call_logs/${callLogId}`;
  
  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Call logs endpoint is not configured in environment variables.' },
      { status: 500 }
    );
  }

  try {
    const body = await req.json();
    console.log(`📨 Frontend API route - Proxying PUT request to: ${putCallLogEndpoint}`);
    console.log('📨 Request body:', body);
    
    const response = await fetch(putCallLogEndpoint, {
      method: 'PUT',
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Error from PUT call_logs endpoint:', errorText);
      return NextResponse.json({ 
        error: `Failed to update call log. Status: ${response.status} ${response.statusText}`, 
        details: errorText 
      }, { status: response.status });
    }

    const data = await response.json();
    console.log('✅ Successfully updated call log:', data);
    return NextResponse.json(data);

  } catch (error) {
    console.error('❌ Error proxying PUT call_logs request:', error);
    return NextResponse.json({ error: 'Failed to proxy PUT call_logs request' }, { status: 500 });
  }
}