import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json()

    if (!email) {
      return NextResponse.json(
        { error: 'Email address is required' },
        { status: 400 }
      )
    }

    // Basic email validation using regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    const isValid = emailRegex.test(email)

    // Additional validation logic
    let message = ''
    let details: any = {}

    if (isValid) {
      message = 'Email address is valid'
      details = {
        original: email,
        local_part: email.split('@')[0],
        domain: email.split('@')[1],
        length: email.length,
        has_common_tld: /\.(com|org|net|edu|gov|mil|int|co|io|ai|dev)$/i.test(email)
      }
    } else {
      message = 'Email address is invalid'
      details = {
        original: email,
        issues: []
      }

      if (!email.includes('@')) {
        details.issues.push('Missing @ symbol')
      } else if (!email.split('@')[0]) {
        details.issues.push('Missing local part before @')
      } else if (!email.split('@')[1]) {
        details.issues.push('Missing domain after @')
      } else if (!email.split('@')[1].includes('.')) {
        details.issues.push('Missing top-level domain')
      } else if (email.split('@')[1].split('.')[1]?.length < 2) {
        details.issues.push('Top-level domain too short')
      }
    }

    return NextResponse.json({
      is_valid: isValid,
      message,
      details,
      timestamp: new Date().toISOString()
    })

  } catch (error) {
    console.error('Email validation error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
