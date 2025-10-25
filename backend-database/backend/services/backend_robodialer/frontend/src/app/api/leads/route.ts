
import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const leadsEndpoint = `${process.env.BASE_URL}/api/v1/leads`;

  if (!process.env.BASE_URL) {
    return NextResponse.json(
      { error: 'Leads API endpoint is not configured.' },
      { status: 500 }
    );
  }

  try {
    const response = await fetch(leadsEndpoint, {
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error from external leads API:', errorText);
      return NextResponse.json(
        { error: `Failed to fetch from external API. Status: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error proxying request to leads API:', error);
    return NextResponse.json(
      { error: 'Failed to proxy request to the leads API.' },
      { status: 500 }
    );
  }
}
