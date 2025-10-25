import { NextRequest, NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    BASE_URL: process.env.BASE_URL || 'NOT_SET',
    NODE_ENV: process.env.NODE_ENV || 'NOT_SET',
    allEnvKeys: Object.keys(process.env).filter(key => 
      key.includes('BASE') || key.includes('URL') || key.includes('BACKEND')
    ),
    timestamp: new Date().toISOString(),
    renderInfo: {
      RENDER: process.env.RENDER || 'NOT_SET',
      RENDER_SERVICE_NAME: process.env.RENDER_SERVICE_NAME || 'NOT_SET'
    }
  });
}