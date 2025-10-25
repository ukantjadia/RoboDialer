"use client"

import React, { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Search, RefreshCw, Building2, ChevronDown, MoreHorizontal, Copy, Trash2, Save } from "lucide-react";
import axios from "axios";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { useRouter } from "next/navigation";
import RestrictionPopup from "@/components/restrictionPopup";

// Interfaces
interface EnrichCompaniesProps {
  showNotification: (message: string, type?: "success" | "error" | "info") => void;
  onCompanyEnriched?: (enrichedData: any) => void;
}

interface EnrichedCompanyData {
  name: string;
  location: string;
  address: string;
  website: string;
  phone: string;
  yearFounded: string;
  revenue: string;
  employees: string;
  industry: string;
  businessType: string;
  productCategory: string;
  linkedin: string;
  description: string;
  notFound?: boolean;
}

interface EnrichCompaniesState {
  enrichCompanyName: string;
  enrichCompanyDomain: string;
  enrichLoading: boolean;
  enrichedCompanyData: EnrichedCompanyData | null;
  multipleResults: any[];
  showResultsDialog: boolean;
  enrichmentPopupOpen: boolean;
  enrichmentResults: any[];
  currentResultIndex: number;
  enrichmentSource: string;
  enrichmentProgress: {
    current: number;
    total: number;
    sources: string[];
  };
  searchingMore: boolean;
  initialSearchComplete: boolean;
  showRestrictionPopup: boolean;
}

export default function EnrichCompanies({ showNotification, onCompanyEnriched }: EnrichCompaniesProps) {
  const router = useRouter();
  const [state, setState] = useState<EnrichCompaniesState>({
    enrichCompanyName: "",
    enrichCompanyDomain: "",
    enrichLoading: false,
    enrichedCompanyData: null,
    multipleResults: [],
    showResultsDialog: false,
    enrichmentPopupOpen: false,
    enrichmentResults: [],
    currentResultIndex: 0,
    enrichmentSource: "",
    enrichmentProgress: {
      current: 0,
      total: 0,
      sources: []
    },
    searchingMore: false,
    initialSearchComplete: false,
    showRestrictionPopup: false
  });

  const updateState = (updates: Partial<EnrichCompaniesState>) => {
    setState(prev => ({ ...prev, ...updates }));
  };

  // Check if user has access to enrichment features
  const checkUserAccess = () => {
    const userData = sessionStorage.getItem('user');
    if (userData) {
      try {
        const user = JSON.parse(userData);
        const userRole = user.role || '';
        const userTier = user.tier || '';
        
        // Allow access for developers with any tier
        if (userRole === 'developer') {
          return true;
        }
        
        // Allow access for bronze, silver, gold, platinum tiers
        const allowedTiers = ['bronze', 'silver', 'gold', 'platinum'];
        if (allowedTiers.includes(userTier.toLowerCase())) {
          return true;
        }
      } catch (error) {
        console.error('Error parsing user data:', error);
      }
    }
    return false;
  };

  // Show upgrade popup for free users
  const showUpgradePopup = () => {
    updateState({ showRestrictionPopup: true });
  };

  // Get current user ID function
  const getCurrentUserId = () => {
    const userData = sessionStorage.getItem('user');
    if (userData) {
      try {
        const parsedUser = JSON.parse(userData);
        return parsedUser.user_id || 'default-user-id';
      } catch (error) {
        console.error('Error parsing user data from session storage:', error);
        return 'default-user-id';
      }
    }
    return 'default-user-id';
  };

  // Function to clear enrichment form fields
  const clearEnrichmentFields = () => {
    updateState({
      enrichCompanyName: "",
      enrichCompanyDomain: "",
      enrichedCompanyData: null,
      multipleResults: [],
      showResultsDialog: false,
      enrichmentResults: [],
      enrichmentPopupOpen: false,
      currentResultIndex: 0,
      searchingMore: false,
      initialSearchComplete: false
    });
  };

  // Helper function to normalize domain input
  const normalizeDomain = (domain: string) => {
    if (!domain || typeof domain !== 'string') return '';
    
    // Remove protocol, www, and trailing slashes
    let cleanDomain = domain.trim()
      .replace(/^https?:\/\//i, '')
      .replace(/^www\./i, '')
      .split('/')[0]
      .toLowerCase();
    
    return cleanDomain;
  };

  // Helper function to determine business type using AI
  const determineBusinessType = async (products: string) => {
    try {
      if (!products || products === "N/A" || products.trim() === "") {
        return "B2B"; // Default fallback
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/business-type-decider`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ products })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.business_type) {
          console.log(`✅ Business type determined: ${result.business_type} for products: ${products}`);
          return result.business_type;
        }
      }
      
      console.log(`⚠️ Business type decider failed, using default B2B`);
      return "B2B"; // Default fallback
    } catch (error) {
      console.error("Business type decider error:", error);
      return "B2B"; // Default fallback
    }
  };

  // Helper function to generate type string for deduct API
  const generateDeductType = (dataSource: 'db' | 'growjo' | 'apollo'): string => {
    return `standalone enrich company_${dataSource}`;
  };

  // Navigation functions for enrichment popup
  const goToNextResult = () => {
    console.log(`Navigating next: current=${state.currentResultIndex}, total=${state.enrichmentResults.length}`);
    if (state.currentResultIndex < state.enrichmentResults.length - 1) {
      const newIndex = state.currentResultIndex + 1;
      console.log(`Moving to next result: ${newIndex} - ${state.enrichmentResults[newIndex]?.name} (${state.enrichmentResults[newIndex]?.source})`);
      updateState({ currentResultIndex: newIndex });
    } else {
      console.log('Already at last result');
    }
  };

  const goToPreviousResult = () => {
    console.log(`Navigating previous: current=${state.currentResultIndex}, total=${state.enrichmentResults.length}`);
    if (state.currentResultIndex > 0) {
      const newIndex = state.currentResultIndex - 1;
      console.log(`Moving to previous result: ${newIndex} - ${state.enrichmentResults[newIndex]?.name} (${state.enrichmentResults[newIndex]?.source})`);
      updateState({ currentResultIndex: newIndex });
    } else {
      console.log('Already at first result');
    }
  };

  const handleSelectEnrichedCompany = async (company: any) => {
    // Set loading state
    updateState({ enrichLoading: true });
    
    try {
      // Check if this is an Apollo search result that needs enrichment
      if (company._isApolloSearch) {
        console.log(`🔍 Apollo search result selected, enriching first...`);
        
        if (company._domain) {
          const enrichResponse = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/apollo-enrich-company`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ domain: company._domain })
            }
          );
          
          if (enrichResponse.ok) {
            const enrichResult = await enrichResponse.json();
            console.log(`✅ Apollo enrich result:`, enrichResult);
            
            if (enrichResult.success && enrichResult.data) {
              const enrichedCompany = enrichResult.data;
              
              // Determine business type using AI
              const products = enrichedCompany.product_category || enrichedCompany.industry || "";
              const businessType = await determineBusinessType(products);
              
              // Update the company object with enriched data
              company = {
                name: enrichedCompany.name || company.name || state.enrichCompanyName.trim(),
                location: `${enrichedCompany.city || ""} ${enrichedCompany.state || ""} ${enrichedCompany.country || ""}`.trim() || "N/A",
                address: enrichedCompany.address || "N/A",
                website: enrichedCompany.website_url || `https://${company._domain}`,
                phone: enrichedCompany.phone || "N/A",
                yearFounded: enrichedCompany.founded_year || "N/A",
                revenue: enrichedCompany.revenue || enrichedCompany.annual_revenue_printed || "N/A",
                employees: enrichedCompany.employees || "N/A",
                industry: enrichedCompany.industry || "N/A",
                businessType: businessType,
                productCategory: enrichedCompany.product_category || "N/A",
                linkedin: enrichedCompany.linkedin_url || "N/A",
                description: enrichedCompany.description || "N/A"
              };
            }
          }
        }
      }

      // Get current user ID
      const userId = getCurrentUserId();
      if (!userId) {
        showNotification("User authentication required", "error");
        updateState({ enrichLoading: false });
        return;
      }

      // Transform enriched data to match API format
      const basePayload = {
        user_id: userId,
        lead_id: "", // Empty for new leads
        company: company.name || "",
        website: company.website && company.website !== "N/A" ? company.website : "",
        industry: company.industry && company.industry !== "N/A" ? company.industry : "",
        product_category: company.productCategory && company.productCategory !== "N/A" ? company.productCategory : "",
        business_type: company.businessType && company.businessType !== "N/A" ? company.businessType : "",
        employees: company.employees && company.employees !== "N/A" ? company.employees : "",
        revenue: company.revenue && company.revenue !== "N/A" ? company.revenue : "",
        year_founded: company.yearFounded && company.yearFounded !== "N/A" ? company.yearFounded : "",
        bbb_rating: "", // Not available in enriched data
        street: company.address && company.address !== "N/A" ? company.address : "",
        city: company.location && company.location !== "N/A" ? company.location.split(',')[0]?.trim() || "" : "",
        state: company.location && company.location !== "N/A" ? company.location.split(',')[1]?.trim() || "" : "",
        country: company.location && company.location !== "N/A" ? company.location.split(',')[2]?.trim() || "" : "",
        company_phone: company.phone && company.phone !== "N/A" ? company.phone : "",
        company_linkedin: company.linkedin && company.linkedin !== "N/A" ? company.linkedin : "",
        owner_first_name: "",
        owner_last_name: "",
        owner_title: "",
        owner_email: "",
        owner_phone_number: "",
        owner_linkedin: "",
        source: `Enrichment from multiple sources`,
        contacts: []
      };

      let lead_id = "";
      let uploadPayload = { ...basePayload };

      const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;

      // Step 1: Call upload_leads API
      try {
        const uploadRes = await axios.post(
          `${DATABASE_URL}/upload_leads`,
          JSON.stringify([uploadPayload]),
          { headers: { "Content-Type": "application/json" } }
        );
        
        const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
        const leadFromResponse = detailedResults[0] || {};
        if (leadFromResponse.lead_id) {
          lead_id = leadFromResponse.lead_id;
          uploadPayload.lead_id = lead_id;
        }
        
        console.log("✅ Upload leads successful:", uploadRes.data);
      } catch (uploadErr) {
        console.error("❌ Failed to upload lead:", uploadPayload, uploadErr);
        showNotification("Failed to upload lead data", "error");
      }

      // Step 2: Call drafts API
      try {
        const draftPayload = {
          lead_id,
          draft_data: uploadPayload,
          change_summary: `Company enrichment from multiple sources`
        };

        const response = await axios.post(
          `${DATABASE_URL}/leads/drafts`,
          draftPayload,
          {
            headers: { "Content-Type": "application/json" },
            withCredentials: true
          }
        );

        if (response.data && response.data.draft_id) {
          console.log("✅ Draft created successfully");
        } else {
          console.error("❌ Failed to create draft");
        }
      } catch (draftErr) {
        console.error("❌ Failed to create draft:", draftErr);
      }

      // Step 3: Call deduct credit API if lead_id was obtained
      if (lead_id) {
        try {
          // Determine data source from the selected company
          const dataSource = company._dataSource || 'db'; // Default to 'db' if not specified
          await axios.post(
            `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
            { type: generateDeductType(dataSource) },
            { withCredentials: true }
          );
          console.log(`✅ Credit deducted successfully for lead: ${lead_id} (source: ${dataSource})`);
        } catch (deductErr) {
          console.error(`❌ Credit deduction failed for lead ${lead_id}`, deductErr);
          // Don't show error to user as this is not critical
        }
      }

      // Update state and close popup
      updateState({
        enrichedCompanyData: company,
        enrichmentPopupOpen: false
      });
      
      showNotification("Company selected and saved successfully!", "success");
      if (onCompanyEnriched) {
        onCompanyEnriched(company);
      }

    } catch (error) {
      console.error("Error selecting and saving company:", error);
      showNotification("Failed to save company data. Please try again.", "error");
    } finally {
      // Reset loading state
      updateState({ enrichLoading: false });
    }
  };

  // Function to save enriched company data to both upload_leads and drafts APIs
  const handleSaveEnrichedCompany = async () => {
    if (!state.enrichedCompanyData) {
      showNotification("No enriched data to save", "error");
      return;
    }

    try {
      // Get current user ID
      const userId = getCurrentUserId();
      if (!userId) {
        showNotification("User authentication required", "error");
        return;
      }

      // Transform enriched data to match API format
      const basePayload = {
        user_id: userId,
        lead_id: "", // Empty for new leads
        company: state.enrichedCompanyData.name || "",
        website: state.enrichedCompanyData.website && state.enrichedCompanyData.website !== "N/A" ? state.enrichedCompanyData.website : "",
        industry: state.enrichedCompanyData.industry && state.enrichedCompanyData.industry !== "N/A" ? state.enrichedCompanyData.industry : "",
        product_category: state.enrichedCompanyData.productCategory && state.enrichedCompanyData.productCategory !== "N/A" ? state.enrichedCompanyData.productCategory : "",
        business_type: state.enrichedCompanyData.businessType && state.enrichedCompanyData.businessType !== "N/A" ? state.enrichedCompanyData.businessType : "",
        employees: state.enrichedCompanyData.employees && state.enrichedCompanyData.employees !== "N/A" ? state.enrichedCompanyData.employees : "",
        revenue: state.enrichedCompanyData.revenue && state.enrichedCompanyData.revenue !== "N/A" ? state.enrichedCompanyData.revenue : "",
        year_founded: state.enrichedCompanyData.yearFounded && state.enrichedCompanyData.yearFounded !== "N/A" ? state.enrichedCompanyData.yearFounded : "",
        bbb_rating: "", // Not available in enriched data
        street: state.enrichedCompanyData.address && state.enrichedCompanyData.address !== "N/A" ? state.enrichedCompanyData.address : "",
        city: state.enrichedCompanyData.location && state.enrichedCompanyData.location !== "N/A" ? state.enrichedCompanyData.location.split(',')[0]?.trim() || "" : "",
        state: state.enrichedCompanyData.location && state.enrichedCompanyData.location !== "N/A" ? state.enrichedCompanyData.location.split(',')[1]?.trim() || "" : "",
        country: state.enrichedCompanyData.location && state.enrichedCompanyData.location !== "N/A" ? state.enrichedCompanyData.location.split(',')[2]?.trim() || "" : "",
        company_phone: state.enrichedCompanyData.phone && state.enrichedCompanyData.phone !== "N/A" ? state.enrichedCompanyData.phone : "",
        company_linkedin: state.enrichedCompanyData.linkedin && state.enrichedCompanyData.linkedin !== "N/A" ? state.enrichedCompanyData.linkedin : "",
        owner_first_name: "",
        owner_last_name: "",
        owner_title: "",
        owner_email: "",
        owner_phone_number: "",
        owner_linkedin: "",
        source: `Enrichment from multiple sources`,
        contacts: []
      };

      let lead_id = "";
      let uploadPayload = { ...basePayload };

      const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;

      // Step 1: Call upload_leads API
      try {
        const uploadRes = await axios.post(
          `${DATABASE_URL}/upload_leads`,
          JSON.stringify([uploadPayload]),
          { headers: { "Content-Type": "application/json" } }
        );
        
        const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
        const leadFromResponse = detailedResults[0] || {};
        if (leadFromResponse.lead_id) {
          lead_id = leadFromResponse.lead_id;
          uploadPayload.lead_id = lead_id;
        }
        
        console.log("✅ Upload leads successful:", uploadRes.data);
      } catch (uploadErr) {
        console.error("❌ Failed to upload lead:", uploadPayload, uploadErr);
        showNotification("Failed to upload lead data", "error");
      }

      // Step 2: Call drafts API
      try {
        const draftPayload = {
          lead_id,
          draft_data: uploadPayload,
          change_summary: `Company enrichment from multiple sources`
        };

        const response = await axios.post(
          `${DATABASE_URL}/leads/drafts`,
          draftPayload,
          {
            headers: { "Content-Type": "application/json" },
            withCredentials: true
          }
        );

        if (response.data && response.data.draft_id) {
          showNotification("Company data saved successfully to both upload_leads and drafts!", "success");
        } else {
          showNotification("Failed to create draft", "error");
        }
      } catch (draftErr) {
        console.error("❌ Failed to create draft:", draftErr);
        showNotification("Failed to create draft", "error");
      }

      // Step 3: Call deduct credit API if lead_id was obtained
      if (lead_id) {
        try {
          // For handleSaveEnrichedCompany, we don't have direct access to the data source
          // Default to 'db' as this function is typically called for database-enriched data
          const dataSource = 'db';
          await axios.post(
            `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
            { type: generateDeductType(dataSource) },
            { withCredentials: true }
          );
          console.log(`✅ Credit deducted successfully for lead: ${lead_id} (source: ${dataSource})`);
        } catch (deductErr) {
          console.error(`❌ Credit deduction failed for lead ${lead_id}`, deductErr);
          // Don't show error to user as this is not critical
        }
      }

    } catch (error) {
      console.error("Error saving enriched company data:", error);
      showNotification("Failed to save company data. Please try again.", "error");
    }
  };

  // Smart enrichment handler with domain support and fallback strategy
  const handleEnrichCompany = async () => {
    // Check user access first
    if (!checkUserAccess()) {
      showUpgradePopup();
      return;
    }

    if (!state.enrichCompanyName.trim()) {
      showNotification("Please provide a company name", "error");
      return;
    }

    // Show popup immediately with loading state
    updateState({ enrichmentPopupOpen: true });
    updateState({ enrichmentResults: [] });
    updateState({ currentResultIndex: 0 });
    updateState({ enrichmentSource: "" });
    updateState({
      enrichmentProgress: {
        current: 0,
        total: 0,
        sources: []
      }
    });

    console.log(`🚀 Starting company enrichment for: "${state.enrichCompanyName.trim()}"`);
    if (state.enrichCompanyDomain.trim()) {
      console.log(`🌐 Domain provided: "${state.enrichCompanyDomain.trim()}" (normalized: "${normalizeDomain(state.enrichCompanyDomain.trim())}")`);
    }
    
    try {
      const allResults = [];
      let currentSource = "";
      let hasSearched = false;
      
      // Step 1: Try database first (SaaSquatch Leads) - this is the first API result
      console.log(`📊 Step 1: Trying database enrichment...`);
      const dbResults = await tryDatabaseEnrichment(state.enrichCompanyName.trim());
      hasSearched = true;
      
      if (dbResults && dbResults.length > 0) {
        const resultsWithSource = dbResults.map(result => ({ ...result, source: 'SaaSquatch Database' }));
        allResults.push(...resultsWithSource);
        currentSource = 'SaaSquatch Database';
        
        // Update popup with first results immediately
        updateState({ enrichmentResults: resultsWithSource });
        updateState({ enrichmentSource: currentSource });
        updateState({
          enrichmentProgress: {
            current: resultsWithSource.length,
            total: resultsWithSource.length,
            sources: [currentSource]
          }
        });
        
        showNotification(`Found ${resultsWithSource.length} companies in database!`, "success");
      } else {
        // No results found in database - show "no results" state
        updateState({ enrichmentResults: [] });
        updateState({ enrichmentSource: "" });
        updateState({
          enrichmentProgress: {
            current: 0,
            total: 0,
            sources: []
          }
        });
        
        showNotification("No companies found in database. Try 'Search for More' to check other sources.", "info");
      }
      
      // Mark initial search as complete
      updateState({ initialSearchComplete: true });

      // Store all results for later use with "Search for More"
      updateState({ enrichmentResults: allResults });
      updateState({
        enrichmentProgress: {
          current: allResults.length,
          total: allResults.length,
          sources: Array.from(new Set(allResults.map(r => r.source)))
        }
      });

    } catch (error) {
      console.error("Error enriching company:", error);
      
      const notFoundData = {
        name: state.enrichCompanyName,
        location: "Enrichment failed",
        address: "Enrichment failed",
        website: "Enrichment failed",
        phone: "Enrichment failed",
        yearFounded: "Enrichment failed",
        revenue: "Enrichment failed",
        employees: "Enrichment failed",
        industry: "Enrichment failed",
        businessType: "Enrichment failed",
        productCategory: "Enrichment failed",
        linkedin: "Enrichment failed",
        description: "Enrichment failed",
        notFound: true
      };
      
      updateState({ enrichedCompanyData: notFoundData });
      updateState({ enrichmentPopupOpen: false });
      showNotification("Enrichment failed. Please try again later.", "error");
    }
  };

  // Domain-based enrichment using Apollo
  const tryDomainBasedEnrichment = async (domain: string) => {
    try {
      console.log(`🌐 Attempting domain-based enrichment for: ${domain}`);
      
      // Clean the domain using the helper function
      const cleanDomain = normalizeDomain(domain);
      if (!cleanDomain) {
        console.error("Invalid domain format");
        return [];
      }
      
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/apollo-enrich-company`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ domain: cleanDomain })
        }
      );

      if (response.ok) {
        const result = await response.json();
        console.log(`🔍 Apollo domain enrichment response:`, result);
        
        if (result.success && result.data) {
          const company = result.data;
          console.log(`✅ Apollo domain enrichment found company:`, company);
          
          // Determine business type using AI
          const products = company.product_category || company.industry || "";
          const businessType = await determineBusinessType(products);
          
          return [{
            name: company.name || state.enrichCompanyName,
            location: company.city || company.state || company.country || "N/A",
            address: company.address || "N/A",
            website: company.website_url || `https://${cleanDomain}`,
            phone: company.phone || "N/A",
            yearFounded: company.founded_year || "N/A",
            revenue: company.revenue || company.annual_revenue_printed || "N/A",
            employees: company.employees || "N/A",
            industry: company.industry || "N/A",
            businessType: businessType,
            productCategory: company.product_category || "N/A",
            linkedin: company.linkedin_url || "N/A",
            description: company.description || "N/A",
            _dataSource: 'apollo' // Track data source
          }];
        } else if (result.success && result.company) {
          // Fallback for old format
          const company = result.company;
          console.log(`✅ Apollo domain enrichment found company (old format):`, company);
          
          // Determine business type using AI
          const products = company.product_category || company.industry || "";
          const businessType = await determineBusinessType(products);
          
          return [{
            name: company.name || state.enrichCompanyName,
            location: company.location || company.city || company.state || "N/A",
            address: company.address || company.street_address || "N/A",
            website: company.website_url || `https://${cleanDomain}`,
            phone: company.phone || company.phone_number || "N/A",
            yearFounded: company.founded_year || company.year_founded || "N/A",
            revenue: company.revenue_range || company.annual_revenue || "N/A",
            employees: company.employee_count || company.num_employees || "N/A",
            industry: company.industry || company.industry_tag || "N/A",
            businessType: businessType,
            productCategory: company.product_category || "N/A",
            linkedin: company.linkedin_url || "N/A",
            description: company.description || company.short_description || "N/A",
            _dataSource: 'apollo' // Track data source
          }];
        } else if (result.success && result.companies && result.companies.length > 0) {
          const companies = result.companies;
          console.log(`✅ Apollo domain enrichment found multiple companies:`, companies);
          
          // Process each company with business type determination
          const enrichedCompanies = [];
          for (const company of companies) {
            const products = company.product_category || company.industry || "";
            const businessType = await determineBusinessType(products);
            
            enrichedCompanies.push({
              name: company.name || state.enrichCompanyName,
              location: company.location || company.city || company.state || "N/A",
              address: company.address || company.street_address || "N/A",
              website: company.website_url || `https://${cleanDomain}`,
              phone: company.phone || company.phone_number || "N/A",
              yearFounded: company.founded_year || company.year_founded || "N/A",
              revenue: company.revenue_range || company.annual_revenue || "N/A",
              employees: company.employee_count || company.num_employees || "N/A",
              industry: company.industry || company.industry_tag || "N/A",
              businessType: businessType,
              productCategory: company.product_category || "N/A",
              linkedin: company.linkedin_url || "N/A",
              description: company.description || company.short_description || "N/A",
              _dataSource: 'apollo' // Track data source
            });
          }
          return enrichedCompanies;
        } else {
          console.log(`⚠️ Apollo domain enrichment returned no company data:`, result);
        }
      }
      return [];
    } catch (error) {
      console.error("Domain-based enrichment failed:", error);
      return [];
    }
  };

  // Step 1: Try database enrichment (SaaSquatch Leads)
  const tryDatabaseEnrichment = async (companyName: string) => {
    try {
      const userId = getCurrentUserId();
      if (!userId) return [];

      const payload = { company_name: companyName };
      const response = await axios.post(`${process.env.NEXT_PUBLIC_DATABASE_URL}/leads/search_companies`, payload, {
        withCredentials: true
      });
      
      if (response.data && response.data.companies && response.data.companies.length > 0) {
        const companies = response.data.companies;
        return companies.map(company => ({
          name: company.company || companyName,
          location: [company.city, company.state, company.country].filter(Boolean).join(', ') || "N/A",
          address: [company.street, company.city, company.state, company.country].filter(Boolean).join(', ') || "N/A",
          website: company.website ? (company.website.startsWith('http') ? company.website : `https://${company.website}`) : "N/A",
          phone: company.phone || company.company_phone || "N/A",
          yearFounded: company.year_founded || "N/A",
          revenue: company.revenue ? `$${company.revenue}M` : "N/A",
          employees: company.employees ? company.employees.toString() : "N/A",
          industry: company.industry || "N/A",
          businessType: company.business_type || "N/A",
          productCategory: company.product_category || "N/A",
          linkedin: company.company_linkedin || "N/A",
          description: company.product_category || "N/A",
          _dataSource: 'db' // Track data source
        }));
      }
      return [];
    } catch (error) {
      console.error("Database enrichment failed:", error);
      return [];
    }
  };

  // Step 2: Try Growjo enrichment
  const tryGrowjoEnrichment = async (companyName: string) => {
    try {
      // Step 1: Call new Growjo companies API to get company data + IDs
      const batchResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/growjo/companies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_names: [companyName],
          per_page: 5
        })
      });

      if (!batchResponse.ok) {
        console.error("Growjo batch API failed:", batchResponse.status);
        return [];
      }

      const batchResult = await batchResponse.json();
      if (!batchResult.success || !batchResult.company_batch_results || batchResult.company_batch_results.length === 0) {
        console.log("No companies found in Growjo companies API");
        return [];
      }

      const companies = batchResult.company_batch_results;
      const enrichedCompanies = [];
      
      // Process each company found in the batch response
      for (const lookupResult of companies) {
        console.log(`🔍 Processing lookup result for ${lookupResult.company_name}:`, lookupResult);
        
        if (lookupResult.items && lookupResult.items.length > 0) {
          const companyData = lookupResult.items[0];
          console.log(`✅ Found company data for ${companyName}:`, companyData);
          
          // Check if batch data provides sufficient enrichment
          const hasCompleteData = 
            companyData.revenue_range && companyData.revenue_range !== "N/A" &&
            companyData.employee_number && companyData.employee_number !== "N/A" &&
            companyData.url && companyData.url !== "N/A";

          if (hasCompleteData) {
            console.log(`✅ ${companyName} has complete data from Growjo companies API`);
            
            enrichedCompanies.push({
              name: companyData.name || companyName,
              location: `${companyData.city || ""} ${companyData.state || ""} ${companyData.country_code || ""}`.trim() || "N/A",
              address: companyData.address1 || companyData.address2 || "N/A",
              website: companyData.url || "N/A",
              phone: companyData.phone || "N/A",
              yearFounded: companyData.year_founded || "N/A",
              revenue: companyData.revenue_range || "N/A",
              employees: companyData.employee_number || "N/A",
              industry: companyData.Industry || "N/A",
              businessType: companyData.business_type || "N/A",
              productCategory: companyData.tags || "N/A",
              linkedin: companyData.linkedin_url || "N/A",
              description: companyData.bio_LI || "N/A",
              source: "Growjo (Companies API)",
              _dataSource: 'growjo' // Track data source
            });
          } else {
            console.log(`⚠️ ${companyName} batch data insufficient, trying individual API...`);
            
            // Fallback to individual Growjo company API if batch data is insufficient
            try {
              const enrichResponse = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/growjo/company/${companyData.company_id}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" }
              });

              if (enrichResponse.ok) {
                const enrichResult = await enrichResponse.json();
                console.log(`🔍 Individual Growjo API response:`, enrichResult);
                
                if (enrichResult.success && enrichResult.company) {
                  const enrichedCompany = enrichResult.company;
                  console.log(`✅ ${companyName} enriched via individual Growjo API`);
                  
                  // Determine business type using AI
                  const products = enrichedCompany.product_category || enrichedCompany.industry || "";
                  const businessType = await determineBusinessType(products);
                  
                  enrichedCompanies.push({
                    name: enrichedCompany.name || companyName,
                    location: `${enrichedCompany.city || ""} ${enrichedCompany.state || ""} ${enrichedCompany.country || ""}`.trim() || "N/A",
                    address: enrichedCompany.address || "N/A",
                    website: enrichedCompany.website || "N/A",
                    phone: enrichedCompany.phone || "N/A",
                    yearFounded: enrichedCompany.year_founded || "N/A",
                    revenue: enrichedCompany.revenue || "N/A",
                    employees: enrichedCompany.employees || "N/A",
                    industry: enrichedCompany.industry || "N/A",
                    businessType: businessType,
                    productCategory: enrichedCompany.product_category || "N/A",
                    linkedin: enrichedCompany.linkedin_url || "N/A",
                    description: enrichedCompany.bio || "N/A",
                    source: "Growjo (Individual API)",
                    _dataSource: 'growjo' // Track data source
                  });
                } else {
                  console.log(`⚠️ Individual Growjo API response missing company data:`, enrichResult);
                }
              }
            } catch (enrichError) {
              console.error(`❌ Failed to enrich company ${companyData.company_id}:`, enrichError);
            }
          }
        } else {
          console.log(`⚠️ No company data found for ${lookupResult.company_name} - items array is empty`);
        }
      }
      
      if (enrichedCompanies.length === 0) {
        console.log(`⚠️ Growjo enrichment found no usable companies for ${companyName}`);
      } else {
        console.log(`✅ Growjo enrichment completed for ${companyName}: ${enrichedCompanies.length} companies found`);
      }
      
      return enrichedCompanies;

    } catch (error) {
      console.error("Growjo enrichment failed:", error);
      return [];
    }
  };

  // Step 3: Try Apollo search (without enriching) as final fallback
  const tryApolloEnrichment = async (companyName: string) => {
    try {
      console.log(`🔍 Apollo search: Searching for ${companyName}...`);
      
      const allResults = [];
      
      // Search for company (don't enrich yet)
      const searchResponse = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/apollo-search-company`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            company_name: companyName, 
            per_page: 5 
          })
        }
      );

      if (searchResponse.ok) {
        const searchResult = await searchResponse.json();
        if (searchResult.success && searchResult.companies?.length > 0) {
          const foundCompanies = searchResult.companies;
          console.log(`✅ Apollo search found ${foundCompanies.length} companies`);
          
          // Return raw search results without enriching (only show available fields)
          for (const foundCompany of foundCompanies) {
            allResults.push({
              name: foundCompany.name || companyName,
              website: foundCompany.website_url || `https://${foundCompany.primary_domain}`,
              phone: foundCompany.phone || "N/A",
              yearFounded: foundCompany.founded_year ? foundCompany.founded_year.toString() : "N/A",
              linkedin: foundCompany.linkedin_url || "N/A",
              // Store domain for later enrichment
              _domain: foundCompany.primary_domain,
              _isApolloSearch: true, // Flag to identify Apollo search results
              _dataSource: 'apollo' // Track data source
            });
          }
        }
      }
      
      return allResults;
    } catch (error) {
      console.error("Apollo search failed:", error);
      return [];
    }
  };

  const handleSearchForMore = async () => {
    // Check user access first
    if (!checkUserAccess()) {
      showUpgradePopup();
      return;
    }

    if (!state.enrichCompanyName.trim()) return;
    
    updateState({ searchingMore: true });
    try {
      const additionalResults = [];
      
      // Step 1: Try Growjo APIs first
      console.log(`🔍 Step 1: Searching for more companies using Growjo...`);
      const growjoResults = await tryGrowjoEnrichment(state.enrichCompanyName.trim());
      if (growjoResults && growjoResults.length > 0) {
        const resultsWithSource = growjoResults.map(result => ({ ...result, source: 'Growjo' }));
        additionalResults.push(...resultsWithSource);
        showNotification(`Found ${growjoResults.length} companies from Growjo!`, "success");
      } else {
        console.log(`⚠️ No results from Growjo, trying Apollo APIs...`);
        
        // Step 2a: Try Apollo domain enrichment first (if domain provided)
        if (state.enrichCompanyDomain.trim()) {
          console.log(`🔍 Step 2a: Trying Apollo domain enrichment for: ${state.enrichCompanyDomain.trim()}`);
          const domainResults = await tryDomainBasedEnrichment(state.enrichCompanyDomain.trim());
          if (domainResults && domainResults.length > 0) {
            const resultsWithSource = domainResults.map(result => ({ ...result, source: 'Apollo' }));
            additionalResults.push(...resultsWithSource);
            showNotification(`Found ${domainResults.length} companies from Apollo domain enrichment!`, "success");
            console.log(`✅ Apollo domain enrichment successful, stopping here`);
          } else {
            console.log(`⚠️ No results from Apollo domain enrichment, trying Apollo search...`);
            
            // Step 2b: Try Apollo search as final fallback
            console.log(`🔍 Step 2b: Trying Apollo search for: ${state.enrichCompanyName.trim()}`);
            const apolloResults = await tryApolloEnrichment(state.enrichCompanyName.trim());
            if (apolloResults && apolloResults.length > 0) {
              const resultsWithSource = apolloResults.map(result => ({ ...result, source: 'Apollo Search' }));
              additionalResults.push(...resultsWithSource);
              showNotification(`Found ${apolloResults.length} companies from Apollo search!`, "success");
            }
          }
        } else {
          // No domain provided, go straight to Apollo search
          console.log(`🔍 Step 2: No domain provided, trying Apollo search for: ${state.enrichCompanyName.trim()}`);
          const apolloResults = await tryApolloEnrichment(state.enrichCompanyName.trim());
          if (apolloResults && apolloResults.length > 0) {
            const resultsWithSource = apolloResults.map(result => ({ ...result, source: 'Apollo Search' }));
            additionalResults.push(...resultsWithSource);
            showNotification(`Found ${apolloResults.length} companies from Apollo search!`, "success");
          }
        }
      }

      if (additionalResults.length > 0) {
        // Add new results to existing ones, with deduplication by name and source
        const existingNames = new Set(state.enrichmentResults.map(r => `${r.name}-${r.source}`));
        const uniqueNewResults = additionalResults.filter(result => 
          !existingNames.has(`${result.name}-${result.source}`)
        );
        
        const allResults = [...state.enrichmentResults, ...uniqueNewResults];
        console.log(`Total results after search for more: ${allResults.length}`);
        console.log(`Results breakdown:`, allResults.map(r => ({ name: r.name, source: r.source })));
        
        updateState({ enrichmentResults: allResults });
        updateState({
          enrichmentProgress: {
            current: allResults.length,
            total: allResults.length,
            sources: Array.from(new Set(allResults.map(r => r.source)))
          }
        });
        
        // Keep current position if user was viewing results, otherwise go to first new result
        if (state.enrichmentResults.length === 0) {
          updateState({ currentResultIndex: 0 });
        } else {
          updateState({ currentResultIndex: state.enrichmentResults.length });
        }
        
        showNotification(`Found ${uniqueNewResults.length} additional companies from other sources! Total: ${allResults.length}`, "success");
      } else {
        showNotification("No additional companies found from other sources.", "info");
      }
    } catch (error) {
      console.error("Error searching for more companies:", error);
      showNotification("Failed to search for more companies.", "error");
    } finally {
      updateState({ searchingMore: false });
    }
  };

  // Handle company selection from multiple results
  const handleCompanySelection = async (selectedCompany: any) => {
    let companyData;
    
    console.log(`🔍 Selected company:`, selectedCompany);
    console.log(`🔍 Is Apollo search result:`, selectedCompany._isApolloSearch);
    console.log(`🔍 Has domain:`, selectedCompany._domain);
    
    // Determine the source based on the data structure
    if (selectedCompany.company) {
      // Database source (SaaSquatch Leads)
      companyData = {
        name: selectedCompany.company || state.enrichCompanyName,
        location: [selectedCompany.city, selectedCompany.state, selectedCompany.country].filter(Boolean).join(', ') || "N/A",
        address: [selectedCompany.street, selectedCompany.city, selectedCompany.state, selectedCompany.country].filter(Boolean).join(', ') || "N/A",
        website: selectedCompany.website ? (selectedCompany.website.startsWith('http') ? selectedCompany.website : `https://${selectedCompany.website}`) : "N/A",
        phone: selectedCompany.phone || selectedCompany.company_phone || "N/A",
        yearFounded: selectedCompany.year_founded || "N/A",
        revenue: selectedCompany.revenue ? `$${selectedCompany.revenue}M` : "N/A",
        employees: selectedCompany.employees ? selectedCompany.employees.toString() : "N/A",
        industry: selectedCompany.industry || "N/A",
        businessType: selectedCompany.business_type || "N/A",
        productCategory: selectedCompany.product_category || "N/A",
        linkedin: selectedCompany.company_linkedin || "N/A",
        description: selectedCompany.product_category || "N/A"
      };
    } else if (selectedCompany.id || selectedCompany.company_id) {
      // Growjo source - need to enrich the selected company
      try {
        // Enrich the selected company using its ID
        const enrichResponse = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/growjo/company/${selectedCompany.company_id}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });

        if (enrichResponse.ok) {
          const enrichResult = await enrichResponse.json();
          if (enrichResult.success && enrichResult.company) {
            const enrichedCompany = enrichResult.company;
            companyData = {
              name: enrichedCompany.name || selectedCompany.name || state.enrichCompanyName.trim(),
              location: enrichedCompany.location || enrichedCompany.city || enrichedCompany.state || "N/A",
              address: enrichedCompany.address || enrichedCompany.street_address || "N/A",
              website: enrichedCompany.website_url || "N/A",
              phone: enrichedCompany.phone || enrichedCompany.phone_number || "N/A",
              yearFounded: enrichedCompany.founded_year || enrichedCompany.year_founded || "N/A",
              revenue: enrichedCompany.revenue_range || enrichedCompany.annual_revenue || "N/A",
              employees: enrichedCompany.employee_count || enrichedCompany.num_employees || "N/A",
              industry: enrichedCompany.industry || enrichedCompany.industry_tag || "N/A",
              businessType: enrichedCompany.business_type || "N/A",
              productCategory: enrichedCompany.product_category || "N/A",
              linkedin: enrichedCompany.linkedin_url || "N/A",
              description: enrichedCompany.description || enrichedCompany.short_description || "N/A"
            };
          } else {
            // Fallback to basic data if enrichment fails
            companyData = {
              name: selectedCompany.name || state.enrichCompanyName.trim(),
              location: selectedCompany.location || selectedCompany.city || selectedCompany.state || "N/A",
              address: selectedCompany.address || selectedCompany.street_address || "N/A",
              website: selectedCompany.website_url || "N/A",
              phone: selectedCompany.phone || selectedCompany.phone_number || "N/A",
              yearFounded: selectedCompany.founded_year || selectedCompany.year_founded || "N/A",
              revenue: selectedCompany.revenue_range || selectedCompany.annual_revenue || "N/A",
              employees: selectedCompany.employee_count || selectedCompany.num_employees || "N/A",
              industry: selectedCompany.industry || selectedCompany.industry_tag || "N/A",
              businessType: selectedCompany.business_type || "N/A",
              productCategory: selectedCompany.product_category || "N/A",
              linkedin: selectedCompany.linkedin_url || "N/A",
              description: selectedCompany.description || selectedCompany.short_description || "N/A"
            };
          }
        } else {
          // Fallback to basic data if API call fails
          companyData = {
            name: selectedCompany.name || state.enrichCompanyName.trim(),
            location: selectedCompany.location || selectedCompany.city || selectedCompany.state || "N/A",
            address: selectedCompany.address || selectedCompany.street_address || "N/A",
            website: selectedCompany.website_url || "N/A",
            phone: selectedCompany.phone || selectedCompany.phone_number || "N/A",
            yearFounded: selectedCompany.founded_year || selectedCompany.year_founded || "N/A",
            revenue: selectedCompany.revenue_range || selectedCompany.annual_revenue || "N/A",
            employees: selectedCompany.employee_count || selectedCompany.num_employees || "N/A",
            industry: selectedCompany.industry || selectedCompany.industry_tag || "N/A",
            businessType: selectedCompany.business_type || "N/A",
            productCategory: selectedCompany.product_category || "N/A",
            linkedin: selectedCompany.linkedin_url || "N/A",
            description: selectedCompany.description || selectedCompany.short_description || "N/A"
          };
        }
      } catch (error) {
        console.error("Error enriching selected company:", error);
        // Fallback to basic data on error
        companyData = {
          name: selectedCompany.name || state.enrichCompanyName.trim(),
          location: selectedCompany.location || selectedCompany.city || selectedCompany.state || "N/A",
          address: selectedCompany.address || selectedCompany.street_address || "N/A",
          website: selectedCompany.website_url || "N/A",
          phone: selectedCompany.phone || selectedCompany.phone_number || "N/A",
          yearFounded: selectedCompany.founded_year || selectedCompany.year_founded || "N/A",
          revenue: selectedCompany.revenue_range || selectedCompany.annual_revenue || "N/A",
          employees: selectedCompany.employee_count || selectedCompany.num_employees || "N/A",
          industry: selectedCompany.industry || selectedCompany.industry_tag || "N/A",
          businessType: selectedCompany.business_type || "N/A",
          productCategory: selectedCompany.product_category || "N/A",
          linkedin: selectedCompany.linkedin_url || "N/A",
          description: selectedCompany.description || selectedCompany.short_description || "N/A"
        };
      }
    } else if (selectedCompany._isApolloSearch) {
      // Apollo search result - need to enrich it first
      try {
        console.log(`🔍 Enriching Apollo search result for: ${selectedCompany.name}`);
        
        if (selectedCompany._domain) {
          const enrichResponse = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/apollo-enrich-company`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ domain: selectedCompany._domain })
            }
          );
          
          if (enrichResponse.ok) {
            const enrichResult = await enrichResponse.json();
            console.log(`✅ Apollo enrich result:`, enrichResult);
            
            if (enrichResult.success && enrichResult.data) {
              const company = enrichResult.data;
              
              // Determine business type using AI
              const products = company.product_category || company.industry || "";
              const businessType = await determineBusinessType(products);
              
              companyData = {
                name: company.name || selectedCompany.name || state.enrichCompanyName.trim(),
                location: company.city || company.state || company.country || "N/A",
                address: company.address || "N/A",
                website: company.website_url || `https://${selectedCompany._domain}`,
                phone: company.phone || "N/A",
                yearFounded: company.founded_year || "N/A",
                revenue: company.revenue || company.annual_revenue_printed || "N/A",
                employees: company.employees || "N/A",
                industry: company.industry || "N/A",
                businessType: businessType,
                productCategory: company.product_category || "N/A",
                linkedin: company.linkedin_url || "N/A",
                description: company.description || "N/A"
              };
            } else {
              // Fallback to search result data if enrichment fails
              companyData = {
                name: selectedCompany.name || state.enrichCompanyName.trim(),
                location: selectedCompany.location || "N/A",
                address: selectedCompany.address || "N/A",
                website: selectedCompany.website || "N/A",
                phone: selectedCompany.phone || "N/A",
                yearFounded: selectedCompany.yearFounded || "N/A",
                revenue: selectedCompany.revenue || "N/A",
                employees: selectedCompany.employees || "N/A",
                industry: selectedCompany.industry || "N/A",
                businessType: "B2B", // Default fallback
                productCategory: selectedCompany.productCategory || "N/A",
                linkedin: selectedCompany.linkedin || "N/A",
                description: selectedCompany.description || "N/A"
              };
            }
          } else {
            // Fallback to search result data if API call fails
            companyData = {
              name: selectedCompany.name || state.enrichCompanyName.trim(),
              location: selectedCompany.location || "N/A",
              address: selectedCompany.address || "N/A",
              website: selectedCompany.website || "N/A",
              phone: selectedCompany.phone || "N/A",
              yearFounded: selectedCompany.yearFounded || "N/A",
              revenue: selectedCompany.revenue || "N/A",
              employees: selectedCompany.employees || "N/A",
              industry: selectedCompany.industry || "N/A",
              businessType: "B2B", // Default fallback
              productCategory: selectedCompany.productCategory || "N/A",
              linkedin: selectedCompany.linkedin || "N/A",
              description: selectedCompany.description || "N/A"
            };
          }
        } else {
          // No domain available, use search result data
          companyData = {
            name: selectedCompany.name || state.enrichCompanyName.trim(),
            location: selectedCompany.location || "N/A",
            address: selectedCompany.address || "N/A",
            website: selectedCompany.website || "N/A",
            phone: selectedCompany.phone || "N/A",
            yearFounded: selectedCompany.yearFounded || "N/A",
            revenue: selectedCompany.revenue || "N/A",
            employees: selectedCompany.employees || "N/A",
            industry: selectedCompany.industry || "N/A",
            businessType: "B2B", // Default fallback
            productCategory: selectedCompany.productCategory || "N/A",
            linkedin: selectedCompany.linkedin || "N/A",
            description: selectedCompany.description || "N/A"
          };
        }
      } catch (error) {
        console.error("Error enriching Apollo search result:", error);
        // Fallback to search result data on error
        companyData = {
          name: selectedCompany.name || state.enrichCompanyName.trim(),
          location: selectedCompany.location || "N/A",
          address: selectedCompany.address || "N/A",
          website: selectedCompany.website || "N/A",
          phone: selectedCompany.phone || "N/A",
          yearFounded: selectedCompany.yearFounded || "N/A",
          revenue: selectedCompany.revenue || "N/A",
          employees: selectedCompany.employees || "N/A",
          industry: selectedCompany.industry || "N/A",
          businessType: "B2B", // Default fallback
          productCategory: selectedCompany.productCategory || "N/A",
          linkedin: selectedCompany.linkedin || "N/A",
          description: selectedCompany.description || "N/A"
        };
      }
    } else {
      // Other sources (Apollo domain enrichment, etc.) - handle both single company and companies array
      if (selectedCompany.companies && Array.isArray(selectedCompany.companies)) {
        // This is from domain-based enrichment with multiple results
        const company = selectedCompany.companies[0] || selectedCompany;
        companyData = {
          name: company.name || state.enrichCompanyName.trim(),
          location: company.location || company.city || company.state || "N/A",
          address: company.address || company.street_address || "N/A",
          website: company.website_url || (state.enrichCompanyDomain.trim() ? `https://${state.enrichCompanyDomain.trim()}` : "N/A"),
          phone: company.phone || company.phone_number || "N/A",
          yearFounded: company.founded_year || company.year_founded || "N/A",
          revenue: company.revenue_range || company.annual_revenue || "N/A",
          employees: company.employee_count || company.num_employees || "N/A",
          industry: company.industry || company.industry_tag || "N/A",
          businessType: company.business_type || "N/A",
          productCategory: company.product_category || "N/A",
          linkedin: company.linkedin_url || "N/A",
          description: company.description || company.short_description || "N/A"
        };
      } else {
        // Single company result
        companyData = {
          name: selectedCompany.name || state.enrichCompanyName.trim(),
          location: selectedCompany.location || selectedCompany.city || selectedCompany.state || "N/A",
          address: selectedCompany.address || selectedCompany.street_address || "N/A",
          website: selectedCompany.website_url || (state.enrichCompanyDomain.trim() ? `https://${state.enrichCompanyDomain.trim()}` : "N/A"),
          phone: selectedCompany.phone || selectedCompany.phone_number || "N/A",
          yearFounded: selectedCompany.founded_year || selectedCompany.year_founded || "N/A",
          revenue: selectedCompany.revenue_range || selectedCompany.annual_revenue || "N/A",
          employees: selectedCompany.employee_count || selectedCompany.num_employees || "N/A",
          industry: selectedCompany.industry || selectedCompany.industry_tag || "N/A",
          businessType: selectedCompany.business_type || "N/A",
          productCategory: selectedCompany.product_category || "N/A",
          linkedin: selectedCompany.linkedin_url || "N/A",
          description: selectedCompany.description || selectedCompany.short_description || "N/A"
        };
      }
    }

    updateState({ enrichedCompanyData: companyData });
    updateState({ enrichmentPopupOpen: false });
    updateState({ enrichmentResults: [] });
    showNotification("Company enrichment completed successfully!", "success");
    if (onCompanyEnriched) {
      onCompanyEnriched(companyData);
    }
  };

  return (
    <>
      {/* Enrich Companies Section */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Form Card */}
        <Card className="h-full bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 border-blue-200 dark:border-gray-700 shadow-lg">
          <CardHeader className="pb-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-t-lg -mt-1 -mx-1">
            <CardTitle className="text-lg font-semibold flex items-center">
              <div className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></div>
              Enrich Company Data
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 p-4">
            <div className="space-y-4">
              {/* Company Name - Required */}
              <div>
                <Label htmlFor="enrichCompanyName">Company Name <span className="text-red-500">*</span></Label>
                <Input
                  id="enrichCompanyName"
                  placeholder="Enter company name..."
                  value={state.enrichCompanyName}
                  onChange={(e) => updateState({ enrichCompanyName: e.target.value })}
                  className="w-full"
                  required
                />
              </div>

              {/* Company Domain - Optional */}
              <div>
                <Label htmlFor="enrichCompanyDomain">Company Domain <span className="text-gray-500 text-xs">(Optional - for more accurate results)</span></Label>
                <Input
                  id="enrichCompanyDomain"
                  placeholder="e.g., example.com or https://example.com"
                  value={state.enrichCompanyDomain}
                  onChange={(e) => updateState({ enrichCompanyDomain: e.target.value })}
                  className="w-full"
                />
                {state.enrichCompanyDomain.trim() && (
                  <div className="mt-1 text-xs text-gray-500">
                    Will search for: <span className="font-mono bg-gray-100 dark:bg-gray-800 px-1 rounded">
                      {normalizeDomain(state.enrichCompanyDomain) || 'Invalid domain'}
                    </span>
                  </div>
                )}
              </div>

              {/* Enrich Button */}
              <div className="pt-4">
                <Button
                  onClick={handleEnrichCompany}
                  disabled={state.enrichLoading || !state.enrichCompanyName.trim()}
                  className="w-full h-12 text-lg font-semibold"
                >
                  {state.enrichLoading ? (
                    <>
                      <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
                      Enriching...
                    </>
                  ) : (
                    <>
                      <Search className="h-5 w-5 mr-2" />
                      Enrich Company
                    </>
                  )}
                </Button>
              </div>
              
              {/* Help Text */}
              <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
                <p>Company name is required for enrichment:</p>
                <p>• <strong>Company Name:</strong> For database and API searches</p>
                <p>• <strong>Domain:</strong> Optional - for more accurate results</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Conditional Card - Shows either Info Card or Enriched Data */}
        {state.enrichedCompanyData ? (
          <Card className={`h-full ${state.enrichedCompanyData.notFound ? 'bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border-red-200 dark:border-red-700' : 'bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 border-blue-200 dark:border-gray-700'} shadow-lg`}>
            <CardHeader className={`pb-3 ${state.enrichedCompanyData.notFound ? 'bg-gradient-to-r from-red-600 to-orange-600' : 'bg-gradient-to-r from-blue-600 to-indigo-600'} text-white rounded-t-lg -mt-1 -mx-1`}>
              <CardTitle className="text-lg font-semibold flex items-center">
                <div className={`w-2 h-2 ${state.enrichedCompanyData.notFound ? 'bg-red-400' : 'bg-green-400'} rounded-full mr-2 ${state.enrichedCompanyData.notFound ? '' : 'animate-pulse'}`}></div>
                {state.enrichedCompanyData.notFound ? 'No Results Found' : 'Enriched Company Data'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-4">
              {state.enrichedCompanyData.notFound ? (
                // Simple "not found" message
                <div className="text-center py-8 flex-1 flex flex-col justify-center items-center">
                  <div className="text-6xl mb-4">🔍</div>
                  <h3 className="text-xl font-semibold text-red-800 dark:text-red-200 mb-2">
                    No Results Found
                  </h3>
                  <p className="text-red-600 dark:text-red-400">
                    We couldn't find any matches for "{state.enrichedCompanyData.name}" in any of our data sources.
                  </p>
                  <p className="text-sm text-red-500 dark:text-red-400 mt-2">
                    Try a different company name or check the spelling.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {/* Company Info Section */}
                  <div className={`p-3 rounded-lg border shadow-sm hover:shadow-md transition-shadow ${state.enrichedCompanyData.notFound ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'}`}>
                    <span className={`text-xs font-medium uppercase tracking-wide ${state.enrichedCompanyData.notFound ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'}`}>Company Name</span>
                    <div className={`font-semibold mt-1 ${state.enrichedCompanyData.notFound ? 'text-red-800 dark:text-red-200' : 'text-gray-900 dark:text-white'}`}>{state.enrichedCompanyData.name}</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Website</span>
                    <div className="font-semibold mt-1">
                      {state.enrichedCompanyData.website !== "N/A" ? (
                        <a
                          href={state.enrichedCompanyData.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline decoration-dotted hover:decoration-solid transition-all"
                        >
                          Visit Website →
                        </a>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Phone</span>
                    <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedCompanyData.phone}</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Year Founded</span>
                    <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedCompanyData.yearFounded}</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Revenue</span>
                    <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedCompanyData.revenue}</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Employees</span>
                    <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedCompanyData.employees}</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Industry</span>
                    <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedCompanyData.industry}</div>
                  </div>
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Business Type</span>
                    <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedCompanyData.businessType}</div>
                  </div>
                  <div className="col-span-2 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Product Category</span>
                    <div className="mt-2">
                      {state.enrichedCompanyData.productCategory && state.enrichedCompanyData.productCategory !== "N/A" ? (
                        <div className="flex flex-wrap gap-2">
                          {state.enrichedCompanyData.productCategory.split(',').map((category, index) => (
                            <span 
                              key={index}
                              className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 border border-blue-200 dark:border-blue-700"
                            >
                              {category.trim()}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </div>
                  </div>
                  <div className="col-span-2 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Location</span>
                    <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedCompanyData.location}</div>
                  </div>
                  <div className="col-span-2 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Address</span>
                    <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedCompanyData.address}</div>
                  </div>
                </div>
              )}
              <div className="flex justify-end pt-2 border-t border-gray-200 dark:border-gray-700">
                <Button
                  onClick={clearEnrichmentFields}
                  variant="outline"
                  size="sm"
                  className="border-gray-300 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800"
                >
                  Clear
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="h-full bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 border-gray-200 dark:border-gray-700 shadow-lg">
            <CardHeader className="pb-3 bg-gradient-to-r from-gray-600 to-gray-700 text-white rounded-t-lg -mt-1 -mx-1">
              <CardTitle className="text-lg font-semibold flex items-center">
                <div className="w-2 h-2 bg-gray-400 rounded-full mr-2"></div>
                Enrichment Results
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col justify-center items-center p-8">
              <div className="text-6xl mb-4">🔍</div>
              <h3 className="text-xl font-semibold text-gray-600 dark:text-gray-400 mb-2 text-center">
                Ready to Enrich
              </h3>
              <p className="text-gray-500 dark:text-gray-500 text-center">
                Fill out the form above and click "Enrich Company" to start searching for data.
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Company Enrichment Results Popup */}
      <Dialog open={state.enrichmentPopupOpen} onOpenChange={(open) => updateState({ enrichmentPopupOpen: open })}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">
              Company Enrichment Results
            </DialogTitle>
            <DialogDescription>
              Found {state.enrichmentResults.length} companies from multiple sources. Navigate through the results and select the best match.
            </DialogDescription>
          </DialogHeader>
          
          {!state.initialSearchComplete ? (
            // Loading state when initial search is still running
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Searching for companies...
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Looking in our database for "{state.enrichCompanyName}"...
              </p>
            </div>
          ) : state.enrichmentResults.length === 0 ? (
            // No results found state
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🔍</div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No companies found in database
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                We couldn't find any companies matching "{state.enrichCompanyName}" in our database.
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                Try clicking "Search for More" to check other data sources like Growjo and Apollo.
              </p>
              <Button
                onClick={handleSearchForMore}
                disabled={state.searchingMore}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {state.searchingMore ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Search for More
                  </>
                )}
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Progress Indicator */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Results from {state.enrichmentProgress.sources.length} sources
                  </span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {state.currentResultIndex + 1} of {state.enrichmentResults.length}
                  </span>
                </div>
                <div className="flex space-x-2">
                  {state.enrichmentProgress.sources.map((source, idx) => (
                    <div
                      key={idx}
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        state.enrichmentResults[state.currentResultIndex]?.source === source
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {source}
                    </div>
                  ))}
                </div>
              </div>

              {/* Current Result Display */}
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      {state.enrichmentResults[state.currentResultIndex]?.name || 'Unknown Company'}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Source: {state.enrichmentResults[state.currentResultIndex]?.source} | Result {state.currentResultIndex + 1} of {state.enrichmentResults.length}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={goToPreviousResult}
                      disabled={state.currentResultIndex === 0}
                      className="px-3"
                      title={`Go to previous result (${state.currentResultIndex > 0 ? state.currentResultIndex : 'None'})`}
                    >
                      Previous ({state.currentResultIndex > 0 ? state.currentResultIndex : 0})
                    </Button>
                    
                    {/* <Button
                      variant="outline"
                      size="sm"
                      onClick={goToNextResult}
                      disabled={state.currentResultIndex === state.enrichmentResults.length - 1}
                      className="px-3"
                      title={`Go to next result (${state.currentResultIndex < state.enrichmentResults.length - 1 ? state.currentResultIndex + 2 : 'None'})`}
                    >
                      Next ({state.currentResultIndex < state.enrichmentResults.length - 1 ? state.currentResultIndex + 2 : state.enrichmentResults.length})
                    </Button> */}
                  </div>
                </div>

                {/* Company Details Grid */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  {/* Website - Always show */}
                  <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Website</span>
                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                      {state.enrichmentResults[state.currentResultIndex]?.website && state.enrichmentResults[state.currentResultIndex]?.website !== "N/A" ? (
                        <a
                          href={state.enrichmentResults[state.currentResultIndex]?.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
                        >
                          Visit Website →
                        </a>
                      ) : (
                        <span className="text-gray-500">N/A</span>
                      )}
                    </div>
                  </div>

                  {/* Phone - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.phone && state.enrichmentResults[state.currentResultIndex]?.phone !== "N/A" && (
                    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Phone</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.phone}
                      </div>
                    </div>
                  )}

                  {/* Year Founded - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.yearFounded && state.enrichmentResults[state.currentResultIndex]?.yearFounded !== "N/A" && (
                    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Year Founded</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.yearFounded}
                      </div>
                    </div>
                  )}

                  {/* Revenue - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.revenue && state.enrichmentResults[state.currentResultIndex]?.revenue !== "N/A" && (
                    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Revenue</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.revenue}
                      </div>
                    </div>
                  )}

                  {/* Employees - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.employees && state.enrichmentResults[state.currentResultIndex]?.employees !== "N/A" && (
                    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Employees</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.employees}
                      </div>
                    </div>
                  )}

                  {/* Industry - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.industry && state.enrichmentResults[state.currentResultIndex]?.industry !== "N/A" && (
                    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Industry</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.industry}
                      </div>
                    </div>
                  )}

                  {/* Business Type - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.businessType && state.enrichmentResults[state.currentResultIndex]?.businessType !== "N/A" && (
                    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Business Type</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.businessType}
                      </div>
                    </div>
                  )}

                  {/* Product Category - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.productCategory && state.enrichmentResults[state.currentResultIndex]?.productCategory !== "N/A" && (
                    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Product Category</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.productCategory}
                      </div>
                    </div>
                  )}

                  {/* LinkedIn - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.linkedin && state.enrichmentResults[state.currentResultIndex]?.linkedin !== "N/A" && (
                    <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">LinkedIn</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        <a
                          href={state.enrichmentResults[state.currentResultIndex]?.linkedin}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline"
                        >
                          Visit LinkedIn →
                        </a>
                      </div>
                    </div>
                  )}

                  {/* Location - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.location && state.enrichmentResults[state.currentResultIndex]?.location !== "N/A" && (
                    <div className="col-span-2 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Location</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.location}
                      </div>
                    </div>
                  )}

                  {/* Address - Show if available */}
                  {state.enrichmentResults[state.currentResultIndex]?.address && state.enrichmentResults[state.currentResultIndex]?.address !== "N/A" && (
                    <div className="col-span-2 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700">
                      <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Address</span>
                      <div className="font-medium text-gray-900 dark:text-white mt-1">
                        {state.enrichmentResults[state.currentResultIndex]?.address}
                      </div>
                    </div>
                  )}
                </div>

                {/* Search for More Button */}
                <div className="flex justify-center pt-4 border-t border-gray-200 dark:border-gray-700">
                  <Button
                    onClick={handleSearchForMore}
                    disabled={state.searchingMore}
                    className="w-full max-w-xs"
                  >
                    {state.searchingMore ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Searching...
                      </>
                    ) : (
                      <>
                        <Search className="h-4 w-4 mr-2" />
                        Search for More
                      </>
                    )}
                  </Button>
                </div>

                {/* Separator Line */}
                <div className="border-t border-gray-200 dark:border-gray-700 my-4"></div>

                {/* Action Buttons */}
                <div className="flex justify-between items-center">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Result {state.currentResultIndex + 1} of {state.enrichmentResults.length}
                  </div>
                  <div className="flex space-x-3">
                    <Button
                      variant="outline"
                      onClick={() => updateState({ enrichmentPopupOpen: false })}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={() => handleSelectEnrichedCompany(state.enrichmentResults[state.currentResultIndex])}
                      disabled={state.enrichLoading}
                    >
                      {state.enrichLoading ? (
                        <>
                          <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        "Select This Company"
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Restriction Popup */}
      <RestrictionPopup
        isOpen={state.showRestrictionPopup}
        onClose={() => updateState({ showRestrictionPopup: false })}
      />
    </>
  );
}
