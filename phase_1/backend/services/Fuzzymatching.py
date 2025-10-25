from rapidfuzz import fuzz
import re

def clean_phone(phone):
    """Extract only digits from phone number."""
    if not phone:
        return ""
    return re.sub(r'\D', '', str(phone))

def normalize_address(address):
    """Standardize address format."""
    if not address:
        return ""
    # Remove common terms and punctuation
    address = re.sub(r'\s+', ' ', str(address))
    address = address.lower().strip()
    return address

def combine_phone_numbers(existing_phone, new_phone):
    """
    Combine phone numbers if they are different.
    
    Args:
        existing_phone (str): Current phone number(s), possibly comma-separated
        new_phone (str): New phone number to potentially add
        
    Returns:
        str: Combined phone numbers if different, otherwise the existing phone
    """
    if not new_phone:
        return existing_phone
    
    if not existing_phone:
        return new_phone
    
    clean_new_phone = clean_phone(new_phone)
    
    # If existing phone has multiple numbers
    if ',' in existing_phone:
        existing_phones = [clean_phone(p.strip()) for p in existing_phone.split(',')]
        # Only add if not already in the list
        if clean_new_phone not in existing_phones:
            return existing_phone + ',' + new_phone
        return existing_phone
    else:
        # If single existing phone, combine if different
        clean_existing_phone = clean_phone(existing_phone)
        if clean_new_phone != clean_existing_phone:
            return existing_phone + ',' + new_phone
        return existing_phone

def combine_addresses(existing_address, new_address):
    """
    Combine addresses if they are different.
    
    Args:
        existing_address (str): Current address(es), possibly comma-separated
        new_address (str): New address to potentially add
        
    Returns:
        str: Combined addresses if different, otherwise the existing address
    """
    if not new_address:
        return existing_address
    
    if not existing_address:
        return new_address
    
    norm_new_address = normalize_address(new_address)
    
    # If existing address has multiple addresses
    if ',' in existing_address:
        existing_addresses = [normalize_address(a.strip()) for a in existing_address.split(',')]
        # Only add if not already in the list
        if norm_new_address not in existing_addresses:
            return existing_address + ', ' + new_address  # Note: using comma+space for readability
        return existing_address
    else:
        # If single existing address, combine if different
        norm_existing_address = normalize_address(existing_address)
        if norm_new_address != norm_existing_address:
            return existing_address + ', ' + new_address  # Note: using comma+space for readability
        return existing_address

def deduplicate_businesses(businesses_list):
    """
    Remove duplicate businesses from a list of business dictionaries and
    combine phone numbers and addresses for businesses with the same name.
    
    Deduplication logic:
    - If companies have similar names, consider them potential duplicates
    - When duplicates are found, combine their phone numbers and addresses
    
    Args:
        businesses_list (List[Dict[str, str]]): List of dictionaries containing business information
        
    Returns:
        List[Dict[str, str]]: List of dictionaries with duplicates removed and info combined
    """
    if not businesses_list or len(businesses_list) == 0:
        return []
    
    # Initialize with first business
    unique_businesses = [businesses_list[0].copy()]  # Use copy to avoid modifying original
    
    for business in businesses_list[1:]:
        # Find name, address, and phone fields
        name_field = 'Company' if 'Company' in business else next((f for f in business if 'name' in f.lower() or 'company' in f.lower()), None)
        address_field = 'Address' if 'Address' in business else next((f for f in business if 'address' in f.lower()), None)
        phone_field = next((f for f in business if 'phone' in f.lower()), None)
        
        # Skip if essential fields are missing
        if not name_field:
            unique_businesses.append(business.copy())
            continue
        
        # Get current business info
        name = str(business.get(name_field, '')).lower().strip()
        address = business.get(address_field, '') if address_field else ""
        phone = business.get(phone_field, '') if phone_field else ''
        
        # Check if this business can be merged with an existing one
        merged = False
        
        for unique_business in unique_businesses:
            # Compare name
            unique_name = str(unique_business.get(name_field, '')).lower().strip()
            name_similarity = fuzz.token_sort_ratio(name, unique_name)
            
            # Only consider merging if names are similar enough
            if name_similarity >= 85:
                # Get unique business phone and address
                unique_phone = unique_business.get(phone_field, '') if phone_field else ''
                unique_address = unique_business.get(address_field, '') if address_field else ""
                
                # Combine phone numbers
                if phone:
                    unique_business[phone_field] = combine_phone_numbers(unique_phone, phone)
                
                # Combine addresses
                if address:
                    unique_business[address_field] = combine_addresses(unique_address, address)
                
                # Mark as merged
                merged = True
                break
        
        # If not merged with any existing one, add as new unique business
        if not merged:
            unique_businesses.append(business.copy())
    
    return unique_businesses