import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  try {
    const baseUrl = process.env.BASE_URL;
    const nodeEnv = process.env.NODE_ENV;
    const port = process.env.PORT;

    return NextResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      environment: {
        NODE_ENV: nodeEnv,
        PORT: port,
        BASE_URL: baseUrl ? 'configured' : 'missing',
        BASE_URL_VALUE: baseUrl || 'not set'
      },
      message: baseUrl 
        ? 'Frontend is properly configured' 
        : 'BASE_URL environment variable is missing'
    });
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    }, { status: 500 });
  }
}