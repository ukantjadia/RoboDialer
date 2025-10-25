import re

def validate_phone_number(phone: str) -> tuple[bool, str]:
    """
    Validate phone number format and return (is_valid, cleaned_number)
    Accepts various formats and cleans them to E.164 format
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # If no + prefix, assume US number and add +1
    if not cleaned.startswith('+'):
        if len(cleaned) == 10:
            cleaned = '+1' + cleaned
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            cleaned = '+' + cleaned
        else:
            return False, f"Invalid phone number format: {phone}. For US numbers use 10 digits (234-567-8901), for international use +country_code format (+918369099653)"
    
    # Basic validation for US numbers (+1 followed by 10 digits)
    if cleaned.startswith('+1') and len(cleaned) == 12:
        return True, cleaned
    
    # Enhanced validation for international numbers
    if cleaned.startswith('+') and len(cleaned) >= 8 and len(cleaned) <= 16:
        # Check for common country codes
        if cleaned.startswith('+91'):  # India
            if len(cleaned) == 13:  # +91 + 10 digits
                return True, cleaned
        elif cleaned.startswith('+44'):  # UK
            if len(cleaned) >= 12 and len(cleaned) <= 13:
                return True, cleaned
        elif cleaned.startswith('+86'):  # China
            if len(cleaned) == 14:  # +86 + 11 digits
                return True, cleaned
        elif cleaned.startswith('+33'):  # France
            if len(cleaned) == 12:  # +33 + 9 digits
                return True, cleaned
        elif cleaned.startswith('+49'):  # Germany
            if len(cleaned) >= 12 and len(cleaned) <= 15:
                return True, cleaned
        else:
            # Generic international validation
            return True, cleaned
    
    return False, f"Invalid phone number format: {phone}. For US numbers use +1234567890 format, for international use +country_code format (e.g., +918369099653)"

def format_phone_display(phone: str) -> str:
    """Format phone number for display purposes"""
    if not phone:
        return ""
    
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    if cleaned.startswith('+1') and len(cleaned) == 12:
        # US number format: +1 (234) 567-8901
        digits = cleaned[2:]  # Remove +1
        return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif cleaned.startswith('+91') and len(cleaned) == 13:
        # Indian number format: +91 83690 99653
        digits = cleaned[3:]  # Remove +91
        return f"+91 {digits[:5]} {digits[5:]}"
    elif cleaned.startswith('+44'):
        # UK number format: +44 20 1234 5678
        digits = cleaned[3:]  # Remove +44
        if len(digits) >= 10:
            return f"+44 {digits[:2]} {digits[2:6]} {digits[6:]}"
        return cleaned
    elif cleaned.startswith('+86') and len(cleaned) == 14:
        # Chinese number format: +86 138 0013 8000
        digits = cleaned[3:]  # Remove +86
        return f"+86 {digits[:3]} {digits[3:7]} {digits[7:]}"
    elif cleaned.startswith('+33') and len(cleaned) == 12:
        # French number format: +33 1 23 45 67 89
        digits = cleaned[3:]  # Remove +33
        return f"+33 {digits[:1]} {digits[1:3]} {digits[3:5]} {digits[5:7]} {digits[7:]}"
    elif cleaned.startswith('+49'):
        # German number format: +49 30 12345678
        digits = cleaned[3:]  # Remove +49
        if len(digits) >= 10:
            return f"+49 {digits[:2]} {digits[2:]}"
        return cleaned
    
    # For other international numbers, add spaces for readability
    if len(cleaned) > 8:
        # Add space after country code and group remaining digits
        for i in range(2, 5):  # Try different country code lengths
            if len(cleaned) > i + 3:
                country_code = cleaned[:i+1]
                remaining = cleaned[i+1:]
                # Group remaining digits in groups of 3-4
                if len(remaining) <= 4:
                    return f"{country_code} {remaining}"
                elif len(remaining) <= 8:
                    mid = len(remaining) // 2
                    return f"{country_code} {remaining[:mid]} {remaining[mid:]}"
                else:
                    return f"{country_code} {remaining[:3]} {remaining[3:6]} {remaining[6:]}"
    
    return cleaned