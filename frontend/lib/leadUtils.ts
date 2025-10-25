import { Lead } from "../components/LeadsProvider";
import { createHash } from "crypto";

/**
 * Generates a unique identifier for a lead based on its details
 * @param lead The lead object to generate an ID for
 * @returns A unique string identifier
 */
export function generateLeadId(lead: Lead): string {
  // Combine relevant fields to create a unique string
  const uniqueString = [
    lead.company,
    lead.street,
    lead.city,
    lead.state,
    lead.business_phone,
    lead.website
  ].join('|').toLowerCase();

  // Create a SHA-256 hash of the combined string
  const hash = createHash('sha256');
  hash.update(uniqueString);
  
  // Return the first 12 characters of the hex digest
  return hash.digest('hex').substring(0, 12);
}

/**
 * Adds unique identifiers to an array of leads
 * @param leads Array of leads to process
 * @returns Array of leads with unique identifiers
 */
export function addUniqueIdsToLeads(leads: Lead[]): Lead[] {
  return leads.map(lead => ({
    ...lead,
    id: parseInt(generateLeadId(lead), 16) // Convert hex to number for compatibility
  }));
}

/**
 * Checks if a LinkedIn value indicates missing information and should be replaced with "N/A"
 * @param linkedinValue - The LinkedIn URL or value to check
 * @returns true if the value indicates missing information, false otherwise
 */
export const isLinkedInMissing = (linkedinValue: string): boolean => {
  if (!linkedinValue || linkedinValue.trim() === '') return true;
  
  const missingPatterns = [
    /linkedin\s*information\s*is\s*missing/i,
    /not\s*found/i,
    /not\s*provided/i,
    /n\/a/i,
    /none/i,
    /unknown/i,
    /missing/i,
    /unavailable/i,
    /no\s*linkedin/i,
    /linkedin\s*not\s*available/i,
    /linkedin\s*not\s*found/i,
    /linkedin\s*not\s*provided/i,
    /linkedin\s*missing/i,
    /linkedin\s*unavailable/i,
    /linkedin\s*information\s*not\s*found/i,
    /linkedin\s*information\s*not\s*provided/i,
    /linkedin\s*information\s*unavailable/i,
    /linkedin\s*information\s*missing/i,
    /linkedin\s*profile\s*not\s*found/i,
    /linkedin\s*profile\s*not\s*provided/i,
    /linkedin\s*profile\s*unavailable/i,
    /linkedin\s*profile\s*missing/i,
    /linkedin\s*profile\s*information\s*is\s*missing/i,
    /linkedin\s*profile\s*information\s*not\s*found/i,
    /linkedin\s*profile\s*information\s*not\s*provided/i,
    /linkedin\s*profile\s*information\s*unavailable/i,
    /linkedin\s*profile\s*not\s*available\./i,
    /couldn't\s*find\s*a\s*linkedin\s*link\./i,
    /couldn't\s*find\s*a\s*linkedin\s*link/i,
    /couldn't\s*find\s*linkedin\s*link/i,
    /couldn't\s*find\s*linkedin/i,
    /no\s*linkedin\s*link\s*found/i,
    /no\s*linkedin\s*link/i,
    /linkedin\s*link\s*not\s*found/i,
    /linkedin\s*link\s*not\s*available/i
  ];
  
  return missingPatterns.some(pattern => pattern.test(linkedinValue.trim()));
};

/**
 * Checks if a website value indicates missing information and should be replaced with "N/A"
 * @param websiteValue - The website URL or value to check
 * @returns true if the value indicates missing information, false otherwise
 */
export const isWebsiteMissing = (websiteValue: string): boolean => {
  if (!websiteValue || websiteValue.trim() === '') return true;
  
  const missingPatterns = [
    /not\s*found/i,
    /not\s*provided/i,
    /n\/a/i,
    /none/i,
    /unknown/i,
    /missing/i,
    /unavailable/i,
    /no\s*website/i,
    /website\s*not\s*available/i,
    /website\s*not\s*found/i,
    /website\s*not\s*provided/i,
    /website\s*missing/i,
    /website\s*unavailable/i,
    /website\s*information\s*not\s*found/i,
    /website\s*information\s*not\s*provided/i,
    /website\s*information\s*unavailable/i,
    /website\s*information\s*missing/i,
    /http:\/\/localhost:\d+\/lead\/N\/A/i,
    /localhost:\d+\/lead\/N\/A/i
  ];
  
  return missingPatterns.some(pattern => pattern.test(websiteValue.trim()));
};

/**
 * Checks if an email value indicates missing information and should be replaced with "N/A"
 * @param emailValue - The email address or value to check
 * @returns true if the value indicates missing information, false otherwise
 */
export const isEmailMissing = (emailValue: string): boolean => {
  if (!emailValue || emailValue.trim() === '') return true;
  
  const missingPatterns = [
    /not\s*found/i,
    /not\s*provided/i,
    /n\/a/i,
    /none/i,
    /unknown/i,
    /missing/i,
    /unavailable/i,
    /no\s*email/i,
    /email\s*not\s*available/i,
    /email\s*not\s*found/i,
    /email\s*not\s*provided/i,
    /email\s*missing/i,
    /email\s*unavailable/i,
    /email\s*information\s*not\s*found/i,
    /email\s*information\s*not\s*provided/i,
    /email\s*information\s*unavailable/i,
    /email\s*information\s*missing/i,
    /email\s*is\s*currently\s*unavailable/i,
    /email\s*is\s*not\s*listed/i,
    /email\s*is\s*not\s*available/i,
    /mailto:N\/A/i,
    /mailto:n\/a/i,
    /email:\s*$/i,
    /email:\s*-$/i,
    /email:\s*not\s*listed$/i,
    /email:\s*not\s*available$/i,
    /email:\s*unavailable$/i,
    /email:\s*missing$/i,
    /email:\s*n\/a$/i,
    /email:\s*none$/i,
    /^email:\s*$/i,
    /^email:\s*-$/i,
    /^email:\s*not\s*listed$/i,
    /^email:\s*not\s*available$/i,
    /^email:\s*unavailable$/i,
    /^email:\s*missing$/i,
    /^email:\s*n\/a$/i,
    /^email:\s*none$/i
  ];
  
  return missingPatterns.some(pattern => pattern.test(emailValue.trim()));
};

/**
 * Normalizes LinkedIn values by replacing missing information indicators with "N/A"
 * @param linkedinValue - The LinkedIn URL or value to normalize
 * @returns "N/A" if the value indicates missing information, otherwise the original value
 */
export const normalizeLinkedInValue = (linkedinValue: string): string => {
  return isLinkedInMissing(linkedinValue) ? 'N/A' : linkedinValue;
};

/**
 * Normalizes website values by replacing missing information indicators with "N/A"
 * @param websiteValue - The website URL or value to normalize
 * @returns "N/A" if the value indicates missing information, otherwise the original value
 */
export const normalizeWebsiteValue = (websiteValue: string): string => {
  return isWebsiteMissing(websiteValue) ? 'N/A' : websiteValue;
};

/**
 * Normalizes email values by replacing missing information indicators with "N/A"
 * @param emailValue - The email address or value to normalize
 * @returns "N/A" if the value indicates missing information, otherwise the original value
 */
export const normalizeEmailValue = (emailValue: string): string => {
  return isEmailMissing(emailValue) ? 'N/A' : emailValue;
};

/**
 * Checks if a phone value indicates missing information and should be replaced with "N/A"
 * @param phoneValue - The phone number or value to check
 * @returns true if the value indicates missing information, false otherwise
 */
export const isPhoneMissing = (phoneValue: string): boolean => {
  if (!phoneValue || phoneValue.trim() === '') return true;
  
  const missingPatterns = [
    /not\s*found/i,
    /not\s*provided/i,
    /n\/a/i,
    /none/i,
    /unknown/i,
    /missing/i,
    /unavailable/i,
    /no\s*contact\s*number\s*found/i,
    /no\s*phone/i,
    /phone\s*not\s*available/i,
    /phone\s*not\s*found/i,
    /phone\s*not\s*provided/i,
    /phone\s*missing/i,
    /phone\s*unavailable/i,
    /phone\s*information\s*not\s*found/i,
    /phone\s*information\s*not\s*provided/i,
    /phone\s*information\s*unavailable/i,
    /phone\s*information\s*missing/i,
    /phone\s*is\s*currently\s*unavailable/i,
    /phone\s*is\s*not\s*listed/i,
    /phone\s*is\s*not\s*available/i,
    /contact\s*number\s*not\s*found/i,
    /contact\s*number\s*not\s*available/i,
    /contact\s*number\s*not\s*provided/i,
    /contact\s*number\s*missing/i,
    /contact\s*number\s*unavailable/i,
    /no\s*contact\s*number/i,
    /contact\s*information\s*not\s*found/i,
    /contact\s*information\s*not\s*provided/i,
    /contact\s*information\s*unavailable/i,
    /contact\s*information\s*missing/i
  ];
  
  return missingPatterns.some(pattern => pattern.test(phoneValue.trim()));
};

/**
 * Normalizes phone values by replacing missing information indicators with "N/A"
 * @param phoneValue - The phone number or value to normalize
 * @returns "N/A" if the value indicates missing information, otherwise the original value
 */
export const normalizePhoneValue = (phoneValue: string): string => {
  return isPhoneMissing(phoneValue) ? 'N/A' : phoneValue;
};

export const parseRevenueStringToMillions = (input: string): number | null => {
  if (!input) return null;

  const match = input.match(/^([\d.,]+)\s*([KMB])?$/i);
  if (!match) return null;

  const value = parseFloat(match[1].replace(/,/g, ""));
  const unit = match[2]?.toUpperCase();

  switch (unit) {
    case "K":
      return value / 1000;
    case "M":
      return value;
    case "B":
      return value * 1000;
    default:
      return value; // Assume millions if no unit
  }
};

/*
Test cases for the utility functions:

// LinkedIn tests - Should return true (missing information)
isLinkedInMissing("linkedin information is missing") // true
isLinkedInMissing("not found") // true
isLinkedInMissing("not provided") // true
isLinkedInMissing("N/A") // true
isLinkedInMissing("none") // true
isLinkedInMissing("unknown") // true
isLinkedInMissing("missing") // true
isLinkedInMissing("unavailable") // true
isLinkedInMissing("no linkedin") // true
isLinkedInMissing("linkedin not available") // true
isLinkedInMissing("linkedin not found") // true
isLinkedInMissing("linkedin not provided") // true
isLinkedInMissing("linkedin missing") // true
isLinkedInMissing("linkedin unavailable") // true
isLinkedInMissing("linkedin information not found") // true
isLinkedInMissing("linkedin information not provided") // true
isLinkedInMissing("linkedin information unavailable") // true
isLinkedInMissing("linkedin information missing") // true
isLinkedInMissing("linkedin profile not found") // true
isLinkedInMissing("linkedin profile not provided") // true
isLinkedInMissing("linkedin profile unavailable") // true
isLinkedInMissing("linkedin profile missing") // true
isLinkedInMissing("linkedin profile information is missing") // true
isLinkedInMissing("linkedin profile information not found") // true
isLinkedInMissing("linkedin profile information not provided") // true
isLinkedInMissing("linkedin profile information unavailable") // true
isLinkedInMissing("linkedin profile not available.") // true
isLinkedInMissing("Couldn't find a LinkedIn link.") // true
isLinkedInMissing("Couldn't find a LinkedIn link") // true
isLinkedInMissing("Couldn't find LinkedIn link") // true
isLinkedInMissing("Couldn't find LinkedIn") // true
isLinkedInMissing("no linkedin link found") // true
isLinkedInMissing("no linkedin link") // true
isLinkedInMissing("linkedin link not found") // true
isLinkedInMissing("linkedin link not available") // true

// Website tests - Should return true (missing information)
isWebsiteMissing("not found") // true
isWebsiteMissing("not provided") // true
isWebsiteMissing("N/A") // true
isWebsiteMissing("none") // true
isWebsiteMissing("unknown") // true
isWebsiteMissing("missing") // true
isWebsiteMissing("unavailable") // true
isWebsiteMissing("no website") // true
isWebsiteMissing("website not available") // true
isWebsiteMissing("website not found") // true
isWebsiteMissing("website not provided") // true
isWebsiteMissing("website missing") // true
isWebsiteMissing("website unavailable") // true
isWebsiteMissing("website information not found") // true
isWebsiteMissing("website information not provided") // true
isWebsiteMissing("website information unavailable") // true
isWebsiteMissing("website information missing") // true
isWebsiteMissing("http://localhost:3000/lead/N/A") // true
isWebsiteMissing("localhost:3000/lead/N/A") // true

// Email tests - Should return true (missing information)
isEmailMissing("not found") // true
isEmailMissing("not provided") // true
isEmailMissing("N/A") // true
isEmailMissing("none") // true
isEmailMissing("unknown") // true
isEmailMissing("missing") // true
isEmailMissing("unavailable") // true
isEmailMissing("no email") // true
isEmailMissing("email not available") // true
isEmailMissing("email not found") // true
isEmailMissing("email not provided") // true
isEmailMissing("email missing") // true
isEmailMissing("email unavailable") // true
isEmailMissing("email information not found") // true
isEmailMissing("email information not provided") // true
isEmailMissing("email information unavailable") // true
isEmailMissing("email information missing") // true
isEmailMissing("email is currently unavailable") // true
isEmailMissing("email is not listed") // true
isEmailMissing("email is not available") // true
isEmailMissing("mailto:N/A") // true
isEmailMissing("mailto:n/a") // true
isEmailMissing("email:") // true
isEmailMissing("email:-") // true
isEmailMissing("email:not listed") // true
isEmailMissing("email:not available") // true
isEmailMissing("email:unavailable") // true
isEmailMissing("email:missing") // true
isEmailMissing("email:n/a") // true
isEmailMissing("email:none") // true

// Should return false (valid values)
isLinkedInMissing("https://linkedin.com/in/johndoe") // false
isLinkedInMissing("https://linkedin.com/company/acme-corp") // false
isLinkedInMissing("linkedin.com/in/johndoe") // false
isLinkedInMissing("www.linkedin.com/in/johndoe") // false

isWebsiteMissing("https://example.com") // false
isWebsiteMissing("http://example.com") // false
isWebsiteMissing("www.example.com") // false
isWebsiteMissing("example.com") // false

isEmailMissing("john.doe@example.com") // false
isEmailMissing("test@company.com") // false

// Normalize function examples:
normalizeLinkedInValue("linkedin information is missing") // "N/A"
normalizeLinkedInValue("not found") // "N/A"
normalizeLinkedInValue("not provided") // "N/A"
normalizeLinkedInValue("https://linkedin.com/in/johndoe") // "https://linkedin.com/in/johndoe"
normalizeLinkedInValue("") // "N/A"
normalizeLinkedInValue("   ") // "N/A"

normalizeWebsiteValue("not found") // "N/A"
normalizeWebsiteValue("http://localhost:3000/lead/N/A") // "N/A"
normalizeWebsiteValue("https://example.com") // "https://example.com"
normalizeWebsiteValue("") // "N/A"

normalizeEmailValue("email is currently unavailable") // "N/A"
normalizeEmailValue("mailto:N/A") // "N/A"
normalizeEmailValue("john.doe@example.com") // "john.doe@example.com"
normalizeEmailValue("") // "N/A"
*/