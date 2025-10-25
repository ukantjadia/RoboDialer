export interface ApolloCompany {
  domain: string
  company_website?: string
  employee_count?: string
  annual_revenue_printed?: string
  founded_year?: string
  linkedin_url?: string
  industry?: string
  keywords?: string[] | string
  business_type?: string
}

export interface GrowjoCompany {
  input_name?: string
  company_name?: string
  company_website?: string
  employee_count?: string
  revenue?: string
  location?: string
  decider_name?: string
  decider_email?: string
  decider_phone?: string
  decider_title?: string
  decider_linkedin?: string
  interests?: string
  industry?: string
}

export interface ApolloPerson {
  domain?: string
  email?: string
  phone_number?: string
  first_name?: string
  last_name?: string
  title?: string
  linkedin_url?: string
}
