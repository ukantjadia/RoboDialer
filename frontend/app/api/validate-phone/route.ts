import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { phone } = await request.json()

    if (!phone) {
      return NextResponse.json(
        { error: 'Phone number is required' },
        { status: 400 }
      )
    }

    // Basic phone validation using regex
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/
    const cleanPhone = phone.replace(/[\s\-\(\)\.]/g, '')
    
    const isValid = phoneRegex.test(cleanPhone) && cleanPhone.length >= 8

    // Additional validation logic
    let message = ''
    let details: any = {}

    if (isValid) {
      message = 'Phone number is valid'
      details = {
        original: phone,
        cleaned: cleanPhone,
        country_code: cleanPhone.startsWith('1') ? '+1' : '',
        local_number: cleanPhone.startsWith('1') ? cleanPhone.slice(1) : cleanPhone,
        length: cleanPhone.length
      }
    } else {
      message = 'Phone number is invalid'
      details = {
        original: phone,
        cleaned: cleanPhone,
        issues: []
      }

      if (cleanPhone.length < 8) {
        details.issues.push('Too short - must be at least 8 digits')
      }
      if (!phoneRegex.test(cleanPhone)) {
        details.issues.push('Contains invalid characters')
      }
    }

    return NextResponse.json({
      is_valid: isValid,
      message,
      details,
      timestamp: new Date().toISOString()
    })

  } catch (error) {
    console.error('Phone validation error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
