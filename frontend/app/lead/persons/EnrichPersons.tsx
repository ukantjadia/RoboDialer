"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Search, RefreshCw, Users, ChevronLeft, ChevronRight } from "lucide-react";
import axios from "axios";
import { useRouter } from "next/navigation";
import RestrictionPopup from "@/components/restrictionPopup";

interface EnrichPersonsProps {
  showNotification: (message: string, type: "success" | "error" | "info") => void;
  onPersonEnriched: (enrichedData: any) => void;
}

interface EnrichedPersonData {
  name: string;
  title: string;
  company: string;
  email: string;
  phone: string;
  linkedin: string;
  companyLocation: string;
  companyAddress: string;
  notFound?: boolean;
}

interface EnrichPersonsState {
  enrichPersonName: string;
  enrichPersonCompany: string;
  enrichCompanyDomain: string;
  enrichPersonLoading: boolean;
  enrichedPersonData: EnrichedPersonData | null;
  multipleResults: any[];
  fallbackResults: any[];
  showResultsDialog: boolean;
  resultsTab: 'database' | 'fallback';
  showRestrictionPopup: boolean;
  // Pagination state for external results
  currentPage: number;
  totalPages: number;
  totalResults: number;
  paginationLoading: boolean;
  currentDomain: string;
}

export default function EnrichPersons({ showNotification, onPersonEnriched }: EnrichPersonsProps) {
  const router = useRouter();
  const [state, setState] = useState<EnrichPersonsState>({
    enrichPersonName: "",
    enrichPersonCompany: "",
    enrichCompanyDomain: "",
    enrichPersonLoading: false,
    enrichedPersonData: null,
    multipleResults: [],
    fallbackResults: [],
    showResultsDialog: false,
    resultsTab: 'database',
    showRestrictionPopup: false,
    // Pagination state for external results
    currentPage: 1,
    totalPages: 1,
    totalResults: 0,
    paginationLoading: false,
    currentDomain: ""
  });

  const updateState = (updates: Partial<EnrichPersonsState>) => {
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

  // Helper function to generate type string for deduct API
  const generateDeductType = (dataSource: 'db' | 'growjo' | 'apollo'): string => {
    return `standalone enrich person_${dataSource}`;
  };

  // Function to clear enrichment form fields
  const clearEnrichmentFields = () => {
    updateState({
      enrichPersonName: "",
      enrichPersonCompany: "",
      enrichCompanyDomain: "",
      enrichedPersonData: null,
      multipleResults: [],
      fallbackResults: [],
      totalResults: 0,
      currentPage: 1,
      totalPages: 1,
      resultsTab: 'database',
      showResultsDialog: false
    });
  };

  // Step 1: Try database enrichment (SaaSquatch Leads)
  const tryDatabaseEnrichment = async (personName: string, personCompany: string) => {
    try {
      // Get current user ID
      const user = JSON.parse(sessionStorage.getItem("user") || "{}");
      const user_id = user.user_id || "";
      
      if (!user_id) return null;

      // Search for persons in database
      const payload = { 
        person_name: personName,
        company_name: personCompany 
      };
      
      const response = await axios.post(`${process.env.NEXT_PUBLIC_DATABASE_URL}/leads/search_persons`, payload, {
        withCredentials: true
      });
      
      if (response.data && response.data.persons && response.data.persons.length > 0) {
        const persons = response.data.persons;
        console.log("📋 Database found persons:", persons.length, persons);
        
        // Always show results dialog for database results (single or multiple)
        console.log("🔍 Database found persons, showing selection dialog");
        
        // Add source indicator to database results
        const personsWithSource = persons.map((person: any) => ({
          ...person,
          source: "Database"
        }));
        
        updateState({
          multipleResults: personsWithSource,
          showResultsDialog: true,
          resultsTab: 'database'
        });
        showNotification(`Found ${persons.length} person(s) in database. Please select one.`, "info");
        return { multipleResults: true }; // Special indicator for multiple results
      }
      return null;
    } catch (error) {
      console.error("Database enrichment failed:", error);
      return null;
    }
  };

  // Step 2: Try Growjo enrichment using new improved flow
  const tryGrowjoEnrichment = async (personName: string, personCompany: string) => {
    try {
      console.log(`🔍 Step 1: Calling new Growjo companies API for: ${personCompany}`);
      
      // Step 1: Call new Growjo companies API to get company data + IDs
      const batchResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/growjo/companies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_names: [personCompany]
        })
      });

      if (!batchResponse.ok) {
        console.error("❌ Growjo companies API failed:", batchResponse.status);
        return null;
      }

      const batchResult = await batchResponse.json();
      console.log("🔍 Growjo companies API response:", batchResult);
      
      if (!batchResult.success || !batchResult.company_batch_results || batchResult.company_batch_results.length === 0) {
        console.log("⚠️ No companies found in Growjo companies API");
        return null;
      }

      // Process the batch results to find company data
      const lookupResult = batchResult.company_batch_results[0];
      if (!lookupResult.items || lookupResult.items.length === 0) {
        console.log(`⚠️ No company data found for ${personCompany} - items array is empty`);
        return null;
      }

      const companyData = lookupResult.items[0];
      console.log(`✅ Found company data for ${personCompany}:`, companyData);
      
      // Step 2: Call Growjo people API using the company_id
      console.log(`🔄 Calling Growjo people API for ${personCompany} with company_id: ${companyData.company_id}`);
      console.log(`🌐 Endpoint: ${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/growjo/people/${companyData.company_id}`);
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/growjo/people/${companyData.company_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      if (response.ok) {
        const result = await response.json();
        console.log(`✅ Growjo people response for ${personCompany}:`, result);
        
        if (result.success && result.data && result.data.people && result.data.people.length > 0) {
          const persons = result.data.people;
          
          // Check if we have meaningful people data (using same logic as data-enhancement.tsx)
          const hasCompletePeopleData = persons.some((person: any) => 
            person.name && person.name !== "N/A" &&
            person.title && person.title !== "N/A" &&
            (person.email && person.email !== "N/A" || person.phone_number && person.phone_number !== "N/A")
          );

          console.log(`🔍 Growjo people data check for ${personCompany}:`, {
            totalPeople: persons.length,
            samplePerson: persons[0],
            hasCompletePeopleData
          });

          if (hasCompletePeopleData) {
            if (persons.length === 1) {
              const person = persons[0];
              return {
                name: person.name || personName,
                title: person.title || person.job_title || "N/A",
                company: person.company || personCompany,
                email: person.email || person.email_address || "N/A",
                phone: person.phone_number || person.phone || "N/A",
                linkedin: person.linkedin_url || person.linkedin || "N/A",
                companyLocation: person.locality || person.location || person.city || person.state || "N/A",
                companyAddress: person.address || person.street_address || "N/A"
              };
            } else {
              // Multiple results - show selection dialog
              const enrichedPersons = persons.map((person: any) => ({
                name: person.name || personName,
                title: person.title || person.job_title || "N/A",
                company: person.company || personCompany,
                email: person.email || person.email_address || "N/A",
                phone: person.phone_number || person.phone || "N/A",
                linkedin: person.linkedin_url || person.linkedin || "N/A",
                companyLocation: person.locality || person.location || person.city || person.state || "N/A",
                companyAddress: person.address || person.street_address || "N/A",
                source: "Growjo"
              }));
              updateState({
                multipleResults: enrichedPersons,
                showResultsDialog: true
              });
              showNotification(`Found ${persons.length} persons in Growjo. Please select one.`, "info");
              return { multipleResults: true }; // Special indicator for multiple results
            }
          } else {
            console.log(`⚠️ ${personCompany} people data from Growjo is incomplete, will try Apollo fallback`);
            return null; // Will trigger Apollo fallback
          }
        } else {
          console.log(`⚠️ No people data returned from Growjo for ${personCompany}`);
          return null; // Will trigger Apollo fallback
        }
      } else {
        console.error(`❌ Growjo people API failed for ${personCompany}:`, response.status);
        return null; // Will trigger Apollo fallback
      }
      
      return null;
    } catch (error) {
      console.error("Growjo enrichment failed:", error);
      return null;
    }
  };

  // Try Growjo people enrichment by company ID
  const tryGrowjoPeopleEnrichment = async (companyId: number) => {
    try {
      // Get the current user from session storage
      const user = JSON.parse(sessionStorage.getItem("user") || "{}");
      const user_id = user.user_id || "";
      
      if (!user_id) {
        showNotification("User not authenticated. Please log in again.", "error");
        return null;
      }

      const apiEndpoint = `${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/growjo/people/${companyId}`;
      
      console.log("🔍 Calling Growjo people enrichment endpoint:", apiEndpoint);
      
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        console.error(`❌ Growjo people API failed with status: ${response.status}`);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const growjoResult = await response.json();
      console.log("✅ Growjo people API response:", growjoResult);
      
      if (!growjoResult.success) {
        console.error("❌ Growjo people API returned error:", growjoResult.error);
        return null;
      }
      
      // Return the people results
      return growjoResult;
      
    } catch (error) {
      console.error("❌ Growjo People API failed:", error);
      return null;
    }
  };

  // Helper function to check if Apollo Enrich result has meaningful data
  const hasMeaningfulApolloEnrichData = (enrichedPerson: any) => {
    // Check if we have at least one meaningful field (not "N/A")
    const meaningfulFields = [
      enrichedPerson.email && enrichedPerson.email !== "N/A",
      enrichedPerson.phone && enrichedPerson.phone !== "N/A",
      enrichedPerson.phone_number && enrichedPerson.phone_number !== "N/A",
      enrichedPerson.linkedin && enrichedPerson.linkedin !== "N/A",
      enrichedPerson.linkedin_url && enrichedPerson.linkedin_url !== "N/A",
      enrichedPerson.location && enrichedPerson.location !== "N/A",
      enrichedPerson.address && enrichedPerson.address !== "N/A",
      enrichedPerson.title && enrichedPerson.title !== "N/A"
    ];
    
    // Return true if at least 2 fields have meaningful data
    return meaningfulFields.filter(Boolean).length >= 2;
  };

  // New function: Try Apollo enrich people first (single person match)
  const tryApolloEnrichPeople = async (personName: string, domain: string) => {
    try {
      // Get the current user from session storage
      const user = JSON.parse(sessionStorage.getItem("user") || "{}");
      const user_id = user.user_id || "";
      
      if (!user_id) {
        showNotification("User not authenticated. Please log in again.", "error");
        return null;
      }

      const apiEndpoint = `${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/apollo-enrich-people`;
      
      // Build payload for apollo-enrich-people - name and domain
      const apolloPayload = {
        name: personName.trim(),
        domain: domain.trim()
      };
      
      console.log("🔍 Calling apollo-enrich-people with payload:", apolloPayload);
      console.log("🌐 Apollo endpoint:", apiEndpoint);
      
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apolloPayload)
      });
      
      if (!response.ok) {
        console.error(`❌ Apollo apollo-enrich-people API failed with status: ${response.status}`);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const apolloResult = await response.json();
      console.log("✅ Apollo apollo-enrich-people API response:", apolloResult);
      
      if (!apolloResult.success) {
        console.error("❌ Apollo apollo-enrich-people API returned error:", apolloResult.error);
        return null;
      }
      
      // Return the enriched person data
      return apolloResult;
      
    } catch (error) {
      console.error("❌ Apollo Enrich People API failed:", error);
      return null;
    }
  };

  // New function: Try Apollo search people to get multiple options
  const tryApolloSearchPeople = async (domain: string, page: number = 1) => {
    try {
      // Get the current user from session storage
      const user = JSON.parse(sessionStorage.getItem("user") || "{}");
      const user_id = user.user_id || "";
      
      if (!user_id) {
        showNotification("User not authenticated. Please log in again.", "error");
        return null;
      }

      const apiEndpoint = `${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/apollo-search-people`;
      
      // Build payload for search - only domain is required by Apollo API
      let apolloPayload: any = {};
      
      // Add domain (required) - use correct Apollo API parameter name
      if (domain.trim() !== "") {
        let cleanDomain = domain.trim().replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        apolloPayload.q_organization_domains_list = cleanDomain;
        console.log(`🌐 Using domain: ${cleanDomain}`);
      }
      
      // Add pagination parameters
      apolloPayload.page = page;
      apolloPayload.per_page = 10;
      
      console.log("🔍 Calling Apollo apollo-search-people endpoint with payload:", apolloPayload);
      console.log("🌐 Apollo endpoint:", apiEndpoint);
      
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apolloPayload)
      });
      
      if (!response.ok) {
        console.error(`❌ Apollo apollo-search-people API failed with status: ${response.status}`);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const apolloResult = await response.json();
      console.log("✅ Apollo apollo-search-people API response:", apolloResult);
      
      if (!apolloResult.success) {
        console.error("❌ Apollo apollo-search-people API returned error:", apolloResult.error);
        return null;
      }
      
      // Return the search results
      return apolloResult;
      
    } catch (error) {
      console.error("❌ Apollo Search People API failed:", error);
      return null;
    }
  };

  // Load a specific page of Apollo results
  const loadApolloPage = async (page: number) => {
    if (!state.currentDomain) {
      showNotification("No domain available for pagination", "error");
      return;
    }

    updateState({ paginationLoading: true });

    try {
      const enrichedData = await tryApolloSearchPeople(state.currentDomain, page);
      
      if (enrichedData && enrichedData.people && enrichedData.people.length > 0) {
        // Add source indicator to Apollo Search People results
        const peopleWithSource = enrichedData.people.map((person: any) => ({
          ...person,
          source: "Apollo Search"
        }));
        
        updateState({
          fallbackResults: peopleWithSource,
          currentPage: page,
          totalPages: enrichedData.pagination?.total_pages || 1,
          totalResults: enrichedData.pagination?.total || 0,
          paginationLoading: false
        });
        console.log(`📄 Loaded page ${page} of ${enrichedData.pagination?.total_pages || 1}`);
      } else {
        showNotification(`No results found for page ${page}`, "info");
        updateState({ paginationLoading: false });
      }
    } catch (error) {
      console.error("Error loading page:", error);
      showNotification("Failed to load page. Please try again.", "error");
      updateState({ paginationLoading: false });
    }
  };

  // Handle person selection from multiple results
  const handlePersonSelection = async (selectedPerson: any) => {
    // Set loading state
    updateState({ enrichPersonLoading: true });
    
    try {
      console.log("✅ Person selected from results:", selectedPerson);
      
      let enrichedData;
      
      // Check if this person comes from database
      if (selectedPerson.source === "Database") {
        console.log("🔍 Person from database, using existing data directly");
        // Use the database data directly without calling apollo-enrich-people
        enrichedData = {
          name: selectedPerson.name || selectedPerson.owner_first_name || selectedPerson.first_name || "Unknown",
          title: selectedPerson.title || selectedPerson.owner_title || selectedPerson.job_title || "No title",
          company: selectedPerson.company || selectedPerson.organization_name || "Unknown Company",
          email: selectedPerson.email || selectedPerson.owner_email || selectedPerson.email_address || "No email",
          phone: selectedPerson.phone || selectedPerson.owner_phone_number || selectedPerson.phone_number || "No phone",
          linkedin: selectedPerson.linkedin || selectedPerson.owner_linkedin || selectedPerson.linkedin_url || "No LinkedIn",
          companyLocation: selectedPerson.location || [selectedPerson.city, selectedPerson.state, selectedPerson.country].filter(Boolean).join(', ') || "No location",
          companyAddress: selectedPerson.address || [selectedPerson.street, selectedPerson.city, selectedPerson.state, selectedPerson.country].filter(Boolean).join(', ') || "No address"
        };
      } else if (selectedPerson.source === "Apollo Enrich") {
        console.log("🔍 Person already enriched from Apollo Enrich, using existing data");
        // Use the already enriched data directly
        enrichedData = {
          name: selectedPerson.name || "Unknown",
          title: selectedPerson.title || "No title",
          company: selectedPerson.company || "Unknown Company",
          email: selectedPerson.email || "No email",
          phone: selectedPerson.phone || selectedPerson.phone_number || "No phone",
          linkedin: selectedPerson.linkedin || selectedPerson.linkedin_url || "No LinkedIn",
          companyLocation: selectedPerson.companyLocation || selectedPerson.location || "No location",
          companyAddress: selectedPerson.companyAddress || selectedPerson.address || "No address"
        };
      } else {
        // Step 1: Call apollo-enrich-people API with person name, company name, and domain
        const apolloPayload = {
          name: selectedPerson.name || selectedPerson.owner_first_name || selectedPerson.first_name || state.enrichPersonName,
          organization_name: selectedPerson.company || selectedPerson.organization_name || state.enrichPersonCompany,
          domain: state.enrichCompanyDomain
        };
        
        console.log("🔍 Calling apollo-enrich-people with payload:", apolloPayload);
        
        const apolloResponse = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/apollo-enrich-people`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(apolloPayload)
        });
        
        if (apolloResponse.ok) {
          const apolloResult = await apolloResponse.json();
          console.log("✅ Apollo enrich people response:", apolloResult);
          
          if (apolloResult.success && apolloResult.data) {
            // Use Apollo enriched data
            const apolloPerson = apolloResult.data;
            
            // Check if location is missing from apollo-enrich-people response
            let companyLocation = apolloPerson.location || apolloPerson.city || apolloPerson.state;
            let companyAddress = apolloPerson.address || apolloPerson.street_address;
            
            // If location is missing, try to get it from apollo-search-people results
            if (!companyLocation || companyLocation === "N/A") {
              // Look for matching person in fallbackResults (from apollo-search-people)
              const matchingPerson = state.fallbackResults.find(person => 
                (person.name && apolloPerson.name && person.name.toLowerCase() === apolloPerson.name.toLowerCase()) ||
                (person.first_name && person.last_name && apolloPerson.name && 
                 `${person.first_name} ${person.last_name}`.toLowerCase() === apolloPerson.name.toLowerCase())
              );
              
              if (matchingPerson) {
                console.log("🔍 Found matching person in apollo-search-people results, using location data");
                companyLocation = matchingPerson.location || matchingPerson.city || matchingPerson.state || companyLocation;
                companyAddress = matchingPerson.address || matchingPerson.street_address || companyAddress;
              }
            }
            
            enrichedData = {
              name: apolloPerson.name || selectedPerson.name || selectedPerson.owner_first_name || selectedPerson.first_name || "Unknown",
              title: apolloPerson.title || apolloPerson.job_title || selectedPerson.title || selectedPerson.owner_title || selectedPerson.job_title || "No title",
              company: apolloPerson.organization_name || selectedPerson.company || selectedPerson.organization_name || "Unknown Company",
              email: apolloPerson.email || apolloPerson.email_address || selectedPerson.email || selectedPerson.owner_email || selectedPerson.email_address || "No email",
              phone: apolloPerson.phone || apolloPerson.phone_number || selectedPerson.phone || selectedPerson.owner_phone_number || selectedPerson.phone_number || "No phone",
              linkedin: apolloPerson.linkedin_url || apolloPerson.linkedin || selectedPerson.linkedin || selectedPerson.owner_linkedin || selectedPerson.linkedin_url || "No LinkedIn",
              companyLocation: companyLocation || selectedPerson.location || selectedPerson.city || selectedPerson.state || selectedPerson.country || "No location",
              companyAddress: companyAddress || selectedPerson.address || selectedPerson.street_address || "No address"
            };
          } else {
            // Fallback to original selected person data if Apollo enrichment fails
            enrichedData = {
              name: selectedPerson.name || selectedPerson.owner_first_name || selectedPerson.first_name || "Unknown",
              title: selectedPerson.title || selectedPerson.owner_title || selectedPerson.job_title || "No title",
              company: selectedPerson.company || selectedPerson.organization_name || "Unknown Company",
              email: selectedPerson.email || selectedPerson.owner_email || selectedPerson.email_address || "No email",
              phone: selectedPerson.phone || selectedPerson.owner_phone_number || selectedPerson.phone_number || "No phone",
              linkedin: selectedPerson.linkedin || selectedPerson.owner_linkedin || selectedPerson.linkedin_url || "No LinkedIn",
              companyLocation: selectedPerson.location || selectedPerson.city || selectedPerson.state || selectedPerson.country || "No location",
              companyAddress: selectedPerson.address || selectedPerson.street_address || "No address"
            };
          }
        } else {
          console.error("❌ Apollo enrich people API failed:", apolloResponse.status);
          // Fallback to original selected person data
          enrichedData = {
            name: selectedPerson.name || selectedPerson.owner_first_name || selectedPerson.first_name || "Unknown",
            title: selectedPerson.title || selectedPerson.owner_title || selectedPerson.job_title || "No title",
            company: selectedPerson.company || selectedPerson.organization_name || "Unknown Company",
            email: selectedPerson.email || selectedPerson.owner_email || selectedPerson.email_address || "No email",
            phone: selectedPerson.phone || selectedPerson.owner_phone_number || selectedPerson.phone_number || "No phone",
            linkedin: selectedPerson.linkedin || selectedPerson.owner_linkedin || selectedPerson.linkedin_url || "No LinkedIn",
            companyLocation: selectedPerson.location || selectedPerson.city || selectedPerson.state || selectedPerson.country || "No location",
            companyAddress: selectedPerson.address || selectedPerson.street_address || "No address"
          };
        }
      }

      // Get current user ID
      const user = JSON.parse(sessionStorage.getItem("user") || "{}");
      const user_id = user.user_id || "";
      
      if (!user_id) {
        showNotification("User authentication required", "error");
        updateState({ enrichPersonLoading: false });
        return;
      }

      // Transform enriched data to match API format
      const basePayload = {
        user_id: user_id,
        lead_id: "", // Empty for new leads
        company: enrichedData.company || "",
        website: "", // Not available in person enrichment
        industry: "", // Not available in person enrichment
        product_category: "", // Not available in person enrichment
        business_type: "", // Not available in person enrichment
        employees: "", // Not available in person enrichment
        revenue: "", // Not available in person enrichment
        year_founded: "", // Not available in person enrichment
        bbb_rating: "", // Not available in person enrichment
        street: enrichedData.companyAddress && enrichedData.companyAddress !== "No address" ? enrichedData.companyAddress : "",
        city: enrichedData.companyLocation && enrichedData.companyLocation !== "No location" ? enrichedData.companyLocation.split(',')[0]?.trim() || "" : "",
        state: enrichedData.companyLocation && enrichedData.companyLocation !== "No location" ? enrichedData.companyLocation.split(',')[1]?.trim() || "" : "",
        country: enrichedData.companyLocation && enrichedData.companyLocation !== "No location" ? enrichedData.companyLocation.split(',')[2]?.trim() || "" : "",
        company_phone: "", // Not available in person enrichment
        company_linkedin: "", // Not available in person enrichment
        owner_first_name: enrichedData.name && enrichedData.name !== "Unknown" ? enrichedData.name.split(' ')[0] || "" : "",
        owner_last_name: enrichedData.name && enrichedData.name !== "Unknown" ? enrichedData.name.split(' ').slice(1).join(' ') || "" : "",
        owner_title: enrichedData.title && enrichedData.title !== "No title" ? enrichedData.title : "",
        owner_email: enrichedData.email && enrichedData.email !== "No email" ? enrichedData.email : "",
        owner_phone_number: enrichedData.phone && enrichedData.phone !== "No phone" ? enrichedData.phone : "",
        owner_linkedin: enrichedData.linkedin && enrichedData.linkedin !== "No LinkedIn" ? enrichedData.linkedin : "",
        source: `Person enrichment from multiple sources`,
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
          change_summary: `Person enrichment from multiple sources`
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
          // Determine data source from the selected person
          let dataSource: 'db' | 'growjo' | 'apollo' = 'db'; // Default to 'db'
          
          if (selectedPerson.source === "Database") {
            dataSource = 'db';
          } else if (selectedPerson.source === "Growjo") {
            dataSource = 'growjo';
          } else if (selectedPerson.source === "Apollo Enrich" || selectedPerson.source === "Apollo Search") {
            dataSource = 'apollo';
          }
          
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
      
      // Update state and close dialog
      updateState({
        enrichedPersonData: enrichedData,
        showResultsDialog: false,
        multipleResults: [],
        fallbackResults: [],
        totalResults: 0,
        currentPage: 1,
        totalPages: 1
      });
      
      showNotification("Person selected and saved successfully!", "success");
      
      // Notify parent component
      onPersonEnriched(enrichedData);
      
    } catch (error) {
      console.error("Error handling person selection:", error);
      showNotification("Failed to process selected person. Please try again.", "error");
    } finally {
      // Reset loading state
      updateState({ enrichPersonLoading: false });
    }
  };

  // Handle more results (Growjo first, then Apollo fallback)
  const handleMoreResults = async () => {
    // Check user access first
    if (!checkUserAccess()) {
      showUpgradePopup();
      return;
    }

    if (!state.enrichCompanyDomain.trim()) {
      showNotification("Please provide a company domain to search for more results.", "error");
      return;
    }

    updateState({ enrichPersonLoading: true });
    
    try {
      // Step 1: Try Growjo APIs first
      console.log("🔍 Step 1: Trying Growjo APIs first...");
      
      // First, get company data from Growjo
      const companyData = await tryGrowjoEnrichment(state.enrichPersonName, state.enrichPersonCompany);
      
      // Check if we got a successful result with company_id
      if (companyData && typeof companyData === 'object' && 'company_id' in companyData) {
        console.log(`✅ Found company in Growjo with ID: ${companyData.company_id}`);
        
        // Now get people data from Growjo
        const peopleData = await tryGrowjoPeopleEnrichment(companyData.company_id as number);
        
        if (peopleData && peopleData.success && peopleData.people && peopleData.people.length > 0) {
          console.log(`✅ Found ${peopleData.people.length} people from Growjo`);
          
          // Show Growjo results
          updateState({
            fallbackResults: peopleData.people,
            resultsTab: 'fallback',
            currentPage: 1,
            totalPages: 1,
            totalResults: peopleData.people.length,
            currentDomain: state.enrichCompanyDomain.trim()
          });
          showNotification(`Found ${peopleData.people.length} results from Growjo!`, "success");
          updateState({ enrichPersonLoading: false });
          return;
        } else {
          console.log("⚠️ No people found in Growjo, trying Apollo...");
        }
      } else {
        console.log("⚠️ No company found in Growjo, trying Apollo...");
      }
      
      // Step 2: Try Apollo enrich people first (single person match)
      console.log("🔍 Step 2: Trying Apollo enrich people first...");
      const apolloEnrichResult = await tryApolloEnrichPeople(state.enrichPersonName.trim(), state.enrichCompanyDomain.trim());
      
      if (apolloEnrichResult && apolloEnrichResult.success && apolloEnrichResult.data) {
        const enrichedPerson = apolloEnrichResult.data;
        
        // Check if the Apollo Enrich result has meaningful data
        if (hasMeaningfulApolloEnrichData(enrichedPerson)) {
          console.log("✅ Apollo enrich people found meaningful data, adding to external results");
          
          // Transform to match our expected format
          const enrichedData = {
            name: enrichedPerson.name || state.enrichPersonName,
            title: enrichedPerson.title || "N/A",
            company: enrichedPerson.company || state.enrichPersonCompany,
            email: enrichedPerson.email || "N/A",
            phone: enrichedPerson.phone || enrichedPerson.phone_number || "N/A",
            linkedin: enrichedPerson.linkedin || enrichedPerson.linkedin_url || "N/A",
            location: enrichedPerson.location || "N/A",
            address: enrichedPerson.address || "N/A",
            companyLocation: enrichedPerson.location || "N/A",
            companyAddress: enrichedPerson.address || "N/A",
            source: "Apollo Enrich"
          };
          
          // Add to fallback results and keep modal open
          updateState({
            fallbackResults: [enrichedData],
            resultsTab: 'fallback',
            currentPage: 1,
            totalPages: 1,
            totalResults: 1,
            currentDomain: state.enrichCompanyDomain.trim()
          });
          showNotification("Found 1 result from Apollo Enrich! Please select it.", "success");
          updateState({ enrichPersonLoading: false });
          return;
        } else {
          console.log("⚠️ Apollo enrich people returned mostly N/A values, treating as empty and trying Apollo search people...");
        }
      } else {
        console.log("⚠️ Apollo enrich people found no single match, trying Apollo search people...");
      }
      
      // Step 3: If Apollo enrich didn't return results, try Apollo search people
      console.log("🔍 Step 3: Trying Apollo search people...");
      const enrichedData = await tryApolloSearchPeople(state.enrichCompanyDomain.trim(), 1);
      
      if (enrichedData && enrichedData.people && enrichedData.people.length > 0) {
        // Add Apollo results to fallbackResults and show in External Results tab
        console.log("🔍 Apollo search returned multiple results, adding to External Results tab");
        
        // Add source indicator to Apollo Search People results
        const peopleWithSource = enrichedData.people.map((person: any) => ({
          ...person,
          source: "Apollo Search"
        }));
        
        updateState({
          fallbackResults: peopleWithSource,
          resultsTab: 'fallback',
          currentPage: 1,
          totalPages: enrichedData.pagination?.total_pages || 1,
          totalResults: enrichedData.pagination?.total || 0,
          currentDomain: state.enrichCompanyDomain.trim()
        });
        showNotification(`Found ${enrichedData.people.length} additional results from Apollo! (${enrichedData.pagination?.total || 0} total)`, "success");
      } else {
        showNotification("No additional results found from Growjo or Apollo.", "info");
      }
    } catch (error) {
      console.error("Error getting more results:", error);
      showNotification("Failed to get more results. Please try again.", "error");
    } finally {
      updateState({ enrichPersonLoading: false });
    }
  };

  // Enrich Persons handler - only tries database first, external APIs require "Search for More"
  const handleEnrichPerson = async () => {
    // Check user access first
    if (!checkUserAccess()) {
      showUpgradePopup();
      return;
    }

    if (!state.enrichPersonName.trim()) {
      showNotification("Please provide a person name", "error");
      return;
    }
    
    if (!state.enrichPersonCompany.trim()) {
      showNotification("Please provide a company name", "error");
      return;
    }
    
    if (!state.enrichCompanyDomain.trim()) {
      showNotification("Please provide a company domain", "error");
      return;
    }

    updateState({ enrichPersonLoading: true });
    
    try {
      // Step 1: Try database first (SaaSquatch Leads) - restricted to paid users
      console.log("🔍 Starting enrichment for:", state.enrichPersonName.trim(), state.enrichPersonCompany.trim(), state.enrichCompanyDomain.trim());
      let enrichedData = await tryDatabaseEnrichment(state.enrichPersonName.trim(), state.enrichPersonCompany.trim());
      console.log("📊 Database enrichment result:", enrichedData);
      
      if (enrichedData) {
        // Check if database returned multiple results (special indicator)
        if ('multipleResults' in enrichedData && enrichedData.multipleResults) {
          console.log("🔍 Database returned results, showing selection dialog");
          return; // Stop here, user will select from dialog or click "More"
        }
      }
      
      // Database returned no results - show the results dialog so user can click "Search for More"
      // This allows paid users to access external APIs
      updateState({
        multipleResults: [],
        fallbackResults: [],
        totalResults: 0,
        currentPage: 1,
        totalPages: 1,
        showResultsDialog: true,
        resultsTab: 'fallback'
      });
      showNotification("No results found in database. Use 'Search for More' to check external sources.", "info");
    } catch (error) {
      console.error("Error enriching person:", error);
      
      const notFoundData = {
        name: state.enrichPersonName || "Unknown",
        title: "Enrichment failed",
        company: state.enrichPersonCompany || "Unknown",
        email: "Enrichment failed",
        phone: "Enrichment failed",
        linkedin: "Enrichment failed",
        companyLocation: "Enrichment failed",
        companyAddress: "Enrichment failed",
        notFound: true
      };
      
      updateState({ enrichedPersonData: notFoundData });
      showNotification("Enrichment failed. Please try again later.", "error");
    } finally {
      updateState({ enrichPersonLoading: false });
    }
  };

  return (
    <>
      {/* Enrichment Form Card */}
      <Card className="h-full bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 border-blue-200 dark:border-gray-700 shadow-lg">
        <CardHeader className="pb-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-t-lg -mt-1 -mx-1">
          <CardTitle className="text-lg font-semibold flex items-center">
            <div className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse"></div>
            Enrich Person Data
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 p-4">
          <div className="space-y-4">
            <div>
              <Label htmlFor="enrichPersonName">Person Name</Label>
              <Input
                id="enrichPersonName"
                placeholder="Enter person's full name"
                value={state.enrichPersonName}
                onChange={(e) => updateState({ enrichPersonName: e.target.value })}
                className="w-full"
                required
              />
            </div>
            <div>
              <Label htmlFor="enrichPersonCompany">Company Name</Label>
              <Input
                id="enrichPersonCompany"
                placeholder="Enter company name"
                value={state.enrichPersonCompany}
                onChange={(e) => updateState({ enrichPersonCompany: e.target.value })}
                className="w-full"
                required
              />
            </div>
            <div>
              <Label htmlFor="enrichCompanyDomain">Company Domain</Label>
              <Input
                id="enrichCompanyDomain"
                placeholder="Enter company domain (e.g., example.com)"
                value={state.enrichCompanyDomain}
                onChange={(e) => updateState({ enrichCompanyDomain: e.target.value })}
                className="w-full"
                required
              />
            </div>

            {/* Enrich Button */}
            <div className="pt-4">
              <Button
                onClick={handleEnrichPerson}
                disabled={state.enrichPersonLoading || !state.enrichPersonName.trim() || !state.enrichPersonCompany.trim() || !state.enrichCompanyDomain.trim()}
                className="w-full h-12 text-lg font-semibold"
              >
                {state.enrichPersonLoading ? (
                  <>
                    <RefreshCw className="h-5 w-5 mr-2 animate-spin" />
                    Enriching...
                  </>
                ) : (
                  <>
                    <Search className="h-5 w-5 mr-2" />
                    Enrich Person
                  </>
                )}
              </Button>
            </div>
            
            {/* Help Text */}
            <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
              <p>All fields are required for optimal enrichment results:</p>
              <p>• <strong>Person Name:</strong> For database, Growjo, and Apollo enrich searches</p>
              <p>• <strong>Company:</strong> For database and Growjo company matching</p>
              <p>• <strong>Domain:</strong> For Apollo enrich and search APIs</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Conditional Card - Shows either Info Card or Enriched Data */}
      {state.enrichedPersonData ? (
        <Card className={`h-full ${state.enrichedPersonData.notFound ? 'bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border-red-200 dark:border-red-700' : 'bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 border-blue-200 dark:border-gray-700'} shadow-lg`}>
          <CardHeader className={`pb-3 ${state.enrichedPersonData.notFound ? 'bg-gradient-to-r from-red-600 to-orange-600' : 'bg-gradient-to-r from-blue-600 to-indigo-600'} text-white rounded-t-lg -mt-1 -mx-1`}>
            <CardTitle className="text-lg font-semibold flex items-center">
              <div className={`w-2 h-2 ${state.enrichedPersonData.notFound ? 'bg-red-400' : 'bg-green-400'} rounded-full mr-2 ${state.enrichedPersonData.notFound ? '' : 'animate-pulse'}`}></div>
              {state.enrichedPersonData.notFound ? 'No Results Found' : 'Enriched Person Data'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 p-4">
            {state.enrichedPersonData.notFound ? (
              // Simple "not found" message
              <div className="text-center py-8 flex-1 flex flex-col justify-center items-center">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-xl font-semibold text-red-800 dark:text-red-200 mb-2">
                  No Results Found
                </h3>
                <p className="text-red-600 dark:text-red-400">
                  We couldn't find any matches for "{state.enrichedPersonData.name}" from any data source.
                </p>
                <p className="text-sm text-red-500 dark:text-red-400 mt-2">
                  Try adjusting your search criteria or try a different person name.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4 text-sm">
                {/* Person Info Section */}
                <div className={`p-3 rounded-lg border shadow-sm hover:shadow-md transition-shadow ${state.enrichedPersonData.notFound ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-700' : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'}`}>
                  <span className={`text-xs font-medium uppercase tracking-wide ${state.enrichedPersonData.notFound ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-gray-400'}`}>Name</span>
                  <div className={`font-semibold mt-1 ${state.enrichedPersonData.notFound ? 'text-red-800 dark:text-red-200' : 'text-gray-900 dark:text-white'}`}>{state.enrichedPersonData.name}</div>
                </div>
                <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Title</span>
                  <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedPersonData.title}</div>
                </div>
                <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Email</span>
                  <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedPersonData.email}</div>
                </div>
                <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Phone</span>
                  <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedPersonData.phone}</div>
                </div>
                <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">LinkedIn</span>
                  <div className="font-semibold mt-1">
                    <a
                      href={state.enrichedPersonData.linkedin}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 underline decoration-dotted hover:decoration-solid transition-all"
                    >
                      View Profile →
                    </a>
                  </div>
                </div>
                
                {/* Company Info Section */}
                <div className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Company</span>
                  <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedPersonData.company}</div>
                </div>
                <div className="col-span-2 bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Location</span>
                  <div className="font-semibold text-gray-900 dark:text-white mt-1">{state.enrichedPersonData.companyLocation}</div>
                </div>
                
              </div>
            )}
            <div className="flex justify-end space-x-2 pt-2 border-t border-gray-200 dark:border-gray-700">
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
              Fill out the form above and click "Enrich Person" to start searching for data.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Multiple Results Selection Dialog */}
      <Dialog open={state.showResultsDialog} onOpenChange={(open) => updateState({ showResultsDialog: open })}>
        <DialogContent className="max-w-4xl h-[90vh] flex flex-col">
          {/* Sticky Header Section */}
          <div className="sticky top-0 z-10">
            <DialogHeader className="pb-4">
              <DialogTitle>Select Person from Results</DialogTitle>
              <DialogDescription>
                Found {state.multipleResults.length} person(s) matching your search. Please select the one you want to enrich.
              </DialogDescription>
            </DialogHeader>
            
            {/* Tab Navigation */}
            <div className="border-b border-gray-200 dark:border-gray-700">
              <div className="flex space-x-4">
                <button
                  onClick={() => updateState({ resultsTab: 'database' })}
                  className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                    state.resultsTab === 'database'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Database Results ({state.multipleResults.length})
                </button>
                <button
                  onClick={() => updateState({ resultsTab: 'fallback' })}
                  className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                    state.resultsTab === 'fallback'
                      ? 'border-green-500 text-green-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  External Results ({state.totalResults})
                </button>
              </div>
            </div>
          </div>
          
          {/* Scrollable Content Section */}
          <div className="flex-1 overflow-y-auto py-4">
            {state.resultsTab === 'database' ? (
              // Database Results Tab
              <div className="space-y-4">
                {state.multipleResults.map((person, index) => (
                  <div
                    key={index}
                    className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
                    onClick={() => handlePersonSelection(person)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                            <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                          </div>
                          <div>
                            <h4 className="font-semibold text-gray-900 dark:text-white">
                              {person.name || `${person.owner_first_name || ''} ${person.owner_last_name || ''}`.trim() || 'Unknown Name'}
                            </h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {person.title || person.owner_title || person.job_title || 'No title'}
                            </p>
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Company</span>
                            <div className="font-medium text-gray-900 dark:text-white mt-1">
                              {person.company || 'Unknown Company'}
                            </div>
                          </div>
                          <div>
                            <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Email</span>
                            <div className="font-medium text-gray-900 dark:text-white mt-1">
                              {person.email || person.owner_email || person.email_address || 'No email'}
                            </div>
                          </div>
                          <div>
                            <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Phone</span>
                            <div className="font-medium text-gray-900 dark:text-white mt-1">
                              {person.phone || person.owner_phone_number || person.phone_number || 'No phone'}
                            </div>
                          </div>
                          <div>
                            <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Location</span>
                            <div className="font-medium text-gray-900 dark:text-white mt-1">
                              {person.location || [person.city, person.state, person.country].filter(Boolean).join(', ') || 'No location'}
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="ml-4">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePersonSelection(person);
                          }}
                          disabled={state.enrichPersonLoading}
                        >
                          {state.enrichPersonLoading ? (
                            <>
                              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                              Saving...
                            </>
                          ) : (
                            "Select"
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              // External Results Tab
              <div className="space-y-4">
                {state.fallbackResults.length > 0 ? (
                  <>
                    {/* Results List */}
                    {state.fallbackResults.map((person, index) => (
                      <div
                        key={index}
                        className="p-4 border border-green-200 dark:border-green-700 rounded-lg hover:bg-green-50 dark:hover:bg-green-800 cursor-pointer transition-colors"
                        onClick={() => handlePersonSelection(person)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3 mb-2">
                              <div className="w-10 h-10 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
                                <Users className="h-5 w-5 text-green-600 dark:text-green-400" />
                              </div>
                              <div>
                                <h4 className="font-semibold text-gray-900 dark:text-white">
                                  {person.name || `${person.owner_first_name || person.first_name || ''} ${person.owner_last_name || person.last_name || ''}`.trim() || 'Unknown Name'}
                                </h4>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                  {person.title || person.owner_title || person.job_title || 'No title'}
                                </p>
                              </div>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              {person.source === "Apollo Enrich" ? (
                                // Apollo Enrich fields: Company, Email, Phone, Location
                                <>
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Company</span>
                                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                                      {person.company || person.organization_name || 'Unknown Company'}
                                    </div>
                                  </div>
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Email</span>
                                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                                      {person.email || person.owner_email || person.email_address || 'No email'}
                                    </div>
                                  </div>
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Phone</span>
                                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                                      {person.phone || person.owner_phone_number || person.phone_number || 'No phone'}
                                    </div>
                                  </div>
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Location</span>
                                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                                      {person.location || person.city || person.state || person.country || 'No location'}
                                    </div>
                                  </div>
                                </>
                              ) : (
                                // Apollo Search People fields: Title, Seniority, Company, Location
                                <>
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Title</span>
                                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                                      {person.title || person.job_title || 'No title'}
                                    </div>
                                  </div>
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Seniority</span>
                                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                                      {person.seniority || 'No seniority info'}
                                    </div>
                                  </div>
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Company</span>
                                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                                      {person.company || person.organization_name || 'Unknown Company'}
                                    </div>
                                  </div>
                                  <div>
                                    <span className="text-gray-500 dark:text-gray-400 text-xs font-medium uppercase tracking-wide">Location</span>
                                    <div className="font-medium text-gray-900 dark:text-white mt-1">
                                      {person.location || person.city || person.state || person.country || 'No location'}
                                    </div>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                          
                          <div className="ml-4">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePersonSelection(person);
                              }}
                              disabled={state.enrichPersonLoading}
                            >
                              {state.enrichPersonLoading ? (
                                <>
                                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                  Saving...
                                </>
                              ) : (
                                "Select"
                              )}
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                    
                    {/* Pagination Controls */}
                    {state.totalPages > 1 && (
                      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => loadApolloPage(state.currentPage - 1)}
                            disabled={state.currentPage <= 1 || state.paginationLoading}
                          >
                            <ChevronLeft className="h-4 w-4 mr-1" />
                            Previous
                          </Button>
                          
                          <div className="flex items-center space-x-1">
                            {Array.from({ length: Math.min(5, state.totalPages) }, (_, i) => {
                              const pageNum = Math.max(1, Math.min(state.totalPages - 4, state.currentPage - 2)) + i;
                              if (pageNum > state.totalPages) return null;
                              
                              return (
                                <Button
                                  key={pageNum}
                                  variant={pageNum === state.currentPage ? "default" : "outline"}
                                  size="sm"
                                  onClick={() => loadApolloPage(pageNum)}
                                  disabled={state.paginationLoading}
                                  className="w-8 h-8 p-0"
                                >
                                  {pageNum}
                                </Button>
                              );
                            })}
                          </div>
                          
                          {/* <Button
                            variant="outline"
                            size="sm"
                            onClick={() => loadApolloPage(state.currentPage + 1)}
                            disabled={state.currentPage >= state.totalPages || state.paginationLoading}
                          >
                            Next
                            <ChevronRight className="h-4 w-4 ml-1" />
                          </Button> */}
                        </div>
                        
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {state.paginationLoading ? (
                            <div className="flex items-center space-x-2">
                              <RefreshCw className="h-4 w-4 animate-spin" />
                              <span>Loading...</span>
                            </div>
                          ) : (
                            `Page ${state.currentPage} of ${state.totalPages} (${state.totalResults} total)`
                          )}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-8 text-gray-400">
                    <Search className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p className="text-lg font-medium">No external results yet</p>
                    <p className="text-sm">Click "More Results" to search external APIs</p>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Footer Section - Always Visible */}
          <div className="flex-shrink-0 flex justify-end items-center gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex gap-2">
                             <Button
                 onClick={handleMoreResults}
                 disabled={state.enrichPersonLoading}
                 className="bg-blue-600 hover:bg-blue-700 text-white"
               >
                 {state.enrichPersonLoading ? (
                   <>
                     <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                     Searching...
                   </>
                 ) : (
                   <>
                     <Search className="h-4 w-4 mr-2" />
                     More Results
                   </>
                 )}
               </Button>
              <Button
                variant="outline"
                onClick={() => {
                  updateState({
                    showResultsDialog: false,
                    multipleResults: [],
                    fallbackResults: [],
                    totalResults: 0,
                    currentPage: 1,
                    totalPages: 1,
                    resultsTab: 'database'
                  });
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
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
