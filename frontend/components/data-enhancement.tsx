"use client"
import React from "react"
import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card"
import { EnrichmentResults } from "../components/enrichment-results"
import ForwardDropdown from "@/components/ui/ForwardDropdown"
import { Button } from "../components/ui/button"
import { Checkbox } from "../components/ui/checkbox"
import { Input } from "../components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import { Search, Filter, Download, X, ExternalLink, ChevronDown, Building, Users, Database, Info } from "lucide-react"
import { useLeads } from "./LeadsProvider"
import { useEnrichment } from "../contexts/EnrichmentContext"
import type { ApolloCompany, GrowjoCompany, ApolloPerson } from "../types/enrichment"
import axios from "axios"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import type { EnrichedCompany } from "@/components/enrichment-results"
import Loader from "@/components/ui/loader"
import { useRouter, useSearchParams } from "next/navigation";
import { flushSync } from "react-dom";
import Popup from "@/components/ui/popup";
import Notif from "@/components/ui/notif"
// import { parseRevenueStringToMillions } from "@/lib/leadUtils"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@radix-ui/react-tooltip"
import { EmptyResultsBanner } from "@/components/ui/empty-results-banner"


const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL_P2
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL!

export function DataEnhancement() {

  const [notif, setNotif] = useState({
    show: false,
    message: "",
    type: "success" as "success" | "error" | "info",
  });
  const showNotification = (message: string, type: "success" | "error" | "info" = "success") => {
    // Clear any existing timer to ensure only the latest notification's timer is active
    if (notifTimeoutRef.current) {
      clearTimeout(notifTimeoutRef.current);
    }

    setNotif({ show: true, message, type });

    // Set a new timer to automatically hide the notification after 8 seconds
    notifTimeoutRef.current = setTimeout(() => {
      setNotif(prev => ({ ...prev, show: false }));
      notifTimeoutRef.current = null; // Clean up the ref
    }, 8000); // Increased timeout for better error readability
  };

  const [hasEnrichedOnce, setHasEnrichedOnce] = useState(false);
  const [showTokenPopup, setShowTokenPopup] = useState(false);
  const [hasErrors, setHasErrors] = useState(false);
  const hasErrorsRef = useRef(false);
  // showResults now managed by context
  const { leads, setLeads } = useLeads()
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const notifTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const searchParams = useSearchParams()

  // Revenue Map
  const [revenueMap, setRevenueMap] = useState<Record<string, string>>({});

  useEffect(() => {
    const stored = sessionStorage.getItem("revenueMap");
    if (stored) {
      try {
        setRevenueMap(JSON.parse(stored));
      } catch (e) {
        console.error("Invalid revenue map", e);
      }
    }
  }, []);

  // Merge revenue data with leads when both are available
  useEffect(() => {
    if (Object.keys(revenueMap).length > 0 && leads.length > 0) {
      const updatedLeads = leads.map(lead => {
        const revenueKey = lead.lead_id || lead.id.toString();
        const estimatedRevenue = revenueMap[revenueKey];
        
        if (estimatedRevenue) {
          // Parse the revenue string to extract both range and confidence
          const [rangePart, confidence] = estimatedRevenue.split(" - ");
          const revenueValue = rangePart.split(": ")[1] || rangePart;
          
          return {
            ...lead,
            revenue: revenueValue,
            revenue_confidence: confidence || null
          };
        }
        return lead;
      });
      
      // Check if any leads have estimated revenue data
      const hasAnyEstimatedRevenue = updatedLeads.some(lead => 
        lead.revenue && lead.revenue_confidence
      );
      setHasEstimatedRevenue(hasAnyEstimatedRevenue);
      
      // Update the leads context with the merged data
      setLeads(updatedLeads);
    } else {
      // No revenueMap data, check if any leads have revenue_confidence (from previous sessions)
      const hasAnyEstimatedRevenue = leads.some(lead => 
        lead.revenue && lead.revenue_confidence
      );
      setHasEstimatedRevenue(hasAnyEstimatedRevenue);
    }
  }, [revenueMap, leads.length, setLeads]);

  // Team membership state
  const [isTeamMember, setIsTeamMember] = useState<boolean | null>(null);
  const [teamMembershipLoading, setTeamMembershipLoading] = useState(true);
  const [teamMembershipChecked, setTeamMembershipChecked] = useState(false);

  // Get the original search criteria from URL parameters
  const getSearchCriteria = () => {
    if (typeof window === 'undefined') return { industry: '', location: '', country: '' };

    const params = new URLSearchParams(window.location.search);
    const industry = params.get('industry') || '';
    const location = params.get('location') || '';
    const countryCode = params.get('country') || '';

    return {
      industry: industry,
      location: location,
      country: countryCode
    };
  };

  const searchCriteria = getSearchCriteria();

  // Add sorting state
  const [sortConfig, setSortConfig] = useState<{
    key: string;
    direction: 'ascending' | 'descending';
  } | null>(null);

  // Cleanup function for progress simulation

  const router = useRouter();

  // Function to check if user is a member of any team
  const checkTeamMembership = async () => {
    try {
      setTeamMembershipLoading(true);
      // console.log('Checking team membership from:', `${DATABASE_URL}/workspace/`);

      const response = await fetch(`${DATABASE_URL}/workspace/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        console.error('Failed to fetch workspaces:', response.statusText);
        setIsTeamMember(false);
        return;
      }

      const responseData = await response.json();
      // console.log('Workspace response data:', responseData);

      // Handle nested structure: { "workspaces": [...] } or direct array [...]
      const workspacesData = responseData.workspaces || responseData;

      // Check if user has any workspace membership (admin, manager, or member role)
      const hasTeamMembership = workspacesData && workspacesData.length > 0 &&
        workspacesData.some((workspace: any) =>
          workspace.user_role &&
          ['admin', 'manager', 'member'].includes(workspace.user_role.toLowerCase())
        );

      // console.log('User team membership status:', hasTeamMembership);
      setIsTeamMember(hasTeamMembership);

      // Store the workspace data in session storage for potential future use
      sessionStorage.setItem('team', JSON.stringify(responseData));

    } catch (error) {
      console.error('Error checking team membership:', error);
      setIsTeamMember(false);
    } finally {
      setTeamMembershipLoading(false);
      setTeamMembershipChecked(true);
    }
  };

  const handleBack = () => {
    sessionStorage.removeItem("leads");
    // sessionStorage.removeItem("enrichedResults");
    sessionStorage.removeItem("subscriptionInfo");
    sessionStorage.removeItem("leadToDraftMap");
    router.push("/scraper"); // 🔁 adjust the path if needed
  };

  useEffect(() => {

    // Cleanup: clear progress simulation
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);

  // Check team membership on component mount
  useEffect(() => {
    checkTeamMembership();
  }, []);

  // Function to stop progress simulation
  const stopProgressSimulation = (finalValue = 100) => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    setProgress(finalValue);
  };

  const normalizeLeadValue = (val: any) => {
    const v = (val || "").toString().trim().toLowerCase()
    return v === "" || v === "na" || v === "n/a" || v === "none" || v === "not" || v === "found" || v === "not found"
      ? "N/A"
      : val
  }

  // Function to clean URLs for display (remove http://, https://, www. and anything after the TLD)
  const cleanUrlForDisplay = (url: string): string => {
    if (!url || url === "N/A" || url === "NA") return url;

    // First remove http://, https://, and www.
    let cleanUrl = url.toString().replace(/^(https?:\/\/)?(www\.)?/i, "");

    // Then truncate everything after the domain (matches common TLDs)
    const domainMatch = cleanUrl.match(/^([^\/\?#]+\.(com|org|net|io|ai|co|gov|edu|app|dev|me|info|biz|us|uk|ca|au|de|fr|jp|ru|br|in|cn|nl|se)).*$/i);
    if (domainMatch) {
      return domainMatch[1];
    }

    // If no common TLD found, just truncate at the first slash, question mark or hash
    return cleanUrl.split(/[\/\?#]/)[0];
  }

  const normalizedLeads = leads.map((lead) => ({
    ...lead,
    lead_id: lead.lead_id,
    company: normalizeLeadValue(lead.company),
    website: normalizeLeadValue(lead.website),
    industry: normalizeLeadValue(lead.industry),
    street: normalizeLeadValue(lead.street),
    city: normalizeLeadValue(lead.city),
    state: normalizeLeadValue(lead.state),
    bbb_rating: normalizeLeadValue(lead.bbb_rating),
    business_phone: normalizeLeadValue(lead.business_phone),
    revenue: lead.revenue || null,
    revenue_confidence: lead.revenue_confidence || null,
  }))

  // 1. First enrichment results (companies) now managed by context
  
  // Second enrichment results (people) - separate state to avoid replacing first enrichment
  const [secondDbEnrichedCompanies, setSecondDbEnrichedCompanies] = useState<EnrichedCompany[]>([]);
  const [secondScrapedEnrichedCompanies, setSecondScrapedEnrichedCompanies] = useState<EnrichedCompany[]>([]);
  
  const [selectedCompanies, setSelectedCompanies] = useState<number[]>([]);
  const [selectedEnrichedCompanies, setSelectedEnrichedCompanies] = useState<number[]>([]);
  const [selectedEnrichedResults, setSelectedEnrichedResults] = useState<string[]>([]);
  const [selectedEnrichedPeople, setSelectedEnrichedPeople] = useState<string[]>([]);
  const [secondEnrichmentResults, setSecondEnrichmentResults] = useState<EnrichedCompany[]>([]);
  const [showSecondEnrichmentResults, setShowSecondEnrichmentResults] = useState(false);
  const [hasEstimatedRevenue, setHasEstimatedRevenue] = useState<boolean>(false);

  // 2. Context handles state management - no need to restore from sessionStorage
  // Each new enrichment session starts with clean state


  // 3. Context automatically handles state synchronization
  // No need for manual sessionStorage persistence

  // const { leads, setLeads } = useLeads(); // from LeadsContext or LeadsProvider

  useEffect(() => {
    const savedLeads = sessionStorage.getItem("leads");
    if (savedLeads) {
      try {
        const parsed = JSON.parse(savedLeads);
        setLeads(parsed);
      } catch (err) {
        console.error("Failed to restore leads from sessionStorage:", err);
      }
    }
  }, []);


  // const [selectAll, setSelectAll] = useState(false)
  const [industryFilter, setIndustryFilter] = useState("")
  const [cityFilter, setCityFilter] = useState("")
  const [stateFilter, setStateFilter] = useState("")
  const [bbbRatingFilter, setBbbRatingFilter] = useState("")
  const [revenueFilter, setRevenueFilter] = useState("")
  const [showFilters, setShowFilters] = useState(false)



  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(25)

  // Pagination state for enrich both results
  const [bothResultsCurrentPage, setBothResultsCurrentPage] = useState(1)
  const bothResultsItemsPerPage = 5 // Hardcoded to 5 items per page

  // Real-time processing state for enrich both - show results after each lead completes ALL APIs
  const [completedLeads, setCompletedLeads] = useState<any[]>([])
  const [currentProcessingLead, setCurrentProcessingLead] = useState<string | null>(null)

  // Helper functions for real-time processing
  const addCompletedLead = (lead: any) => {
    setCompletedLeads(prev => {
      // Check if lead already exists to avoid duplicates
      const exists = prev.some(l => l.company === lead.company)
      if (exists) {
        return prev.map(l => l.company === lead.company ? lead : l)
      }
      return [...prev, lead]
    })
    setCurrentProcessingLead(null)
    
    // Update main enriched companies state for real-time display
    setEnrichedCompanies(prev => {
      const exists = prev.some(l => l.company === lead.company)
      if (exists) {
        return prev.map(l => l.company === lead.company ? lead : l)
      }
      return [...prev, lead]
    })
    
    // Update scraped enriched companies for real-time display (needed for main display condition)
    setScrapedEnrichedCompanies(prev => {
      const exists = prev.some(l => l.company === lead.company)
      if (exists) {
        return prev.map(l => l.company === lead.company ? lead : l)
      }
      return [...prev, lead]
    })
    
    // Show results immediately after first lead is completed
    setShowResults(true)
    setHasEnrichedOnce(true)
  }

  const setProcessingLead = (companyName: string) => {
    setCurrentProcessingLead(companyName)
  }

  const clearRealTimeStates = () => {
    setCompletedLeads([])
    setCurrentProcessingLead(null)
    // Clear enriched results selection
    setSelectedEnrichedResults([])
  }

  // Search, filter, and sort state for enrich both results
  const [bothResultsSearchTerm, setBothResultsSearchTerm] = useState("")
  const [bothResultsShowFilters, setBothResultsShowFilters] = useState(false)
  const [bothResultsSortConfig, setBothResultsSortConfig] = useState<{key: string, direction: 'ascending' | 'descending'} | null>(null)
  
  // Filter states for enrich both results
  const [bothResultsEmployeesFilter, setBothResultsEmployeesFilter] = useState("")
  const [bothResultsRevenueFilter, setBothResultsRevenueFilter] = useState("")
  const [bothResultsBusinessTypeFilter, setBothResultsBusinessTypeFilter] = useState("")
  const [bothResultsProductFilter, setBothResultsProductFilter] = useState("")
  const [bothResultsYearFoundedFilter, setBothResultsYearFoundedFilter] = useState("")
  const [bothResultsBbbRatingFilter, setBothResultsBbbRatingFilter] = useState("")
  const [bothResultsStreetFilter, setBothResultsStreetFilter] = useState("")
  const [bothResultsCityFilter, setBothResultsCityFilter] = useState("")
  const [bothResultsStateFilter, setBothResultsStateFilter] = useState("")

  // Pagination state for enrich people results
  const [peopleResultsCurrentPage, setPeopleResultsCurrentPage] = useState(1)
  const [peopleResultsItemsPerPage, setPeopleResultsItemsPerPage] = useState(25)

  // Search, filter, and sort state for enrich people results
  const [peopleResultsSearchTerm, setPeopleResultsSearchTerm] = useState("")
  const [peopleResultsShowFilters, setPeopleResultsShowFilters] = useState(false)
  const [peopleResultsSortConfig, setPeopleResultsSortConfig] = useState<{key: string, direction: 'ascending' | 'descending'} | null>(null)
  
  // Filter states for enrich people results
  const [peopleResultsNameFilter, setPeopleResultsNameFilter] = useState("")
  const [peopleResultsTitleFilter, setPeopleResultsTitleFilter] = useState("")
  const [peopleResultsEmailFilter, setPeopleResultsEmailFilter] = useState("")
  const [peopleResultsPhoneFilter, setPeopleResultsPhoneFilter] = useState("")
  const [peopleResultsLinkedinFilter, setPeopleResultsLinkedinFilter] = useState("")
  const [peopleResultsCompanyFilter, setPeopleResultsCompanyFilter] = useState("")
  const [peopleResultsIndustryFilter, setPeopleResultsIndustryFilter] = useState("")

  // Dropdown state for enrichment options
  const [enrichmentType, setEnrichmentType] = useState<"company" | "people" | "both">("company")
  const [selectedDataSource, setSelectedDataSource] = useState<"growjo" | "apollo" | "both">("apollo")
  const [showPeopleResults, setShowPeopleResults] = useState(false)
  const [initialEnrichmentType, setInitialEnrichmentType] = useState<"company" | "people" | null>(null)
  const [secondEnrichmentLoading, setSecondEnrichmentLoading] = useState(false)
  
  // Track enrichment order and types
  // firstEnrichmentType and hasFirstEnrichment now managed by context
  const [secondEnrichmentType, setSecondEnrichmentType] = useState<"company" | "people" | "both" | null>(null)
  const [hasSecondEnrichment, setHasSecondEnrichment] = useState(false)

  // Function to get complementary enrichment type
  const getComplementaryEnrichmentType = (initialType: "company" | "people"): "company" | "people" => {
    return initialType === "company" ? "people" : "company"
  }

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [industryFilter, cityFilter, stateFilter, bbbRatingFilter, revenueFilter]);

  // Reset both results pagination when filters change
  useEffect(() => {
    setBothResultsCurrentPage(1);
  }, [bothResultsSearchTerm, bothResultsEmployeesFilter, bothResultsRevenueFilter, bothResultsBusinessTypeFilter, 
      bothResultsProductFilter, bothResultsYearFoundedFilter, bothResultsBbbRatingFilter, 
      bothResultsStreetFilter, bothResultsCityFilter, bothResultsStateFilter, bothResultsSortConfig]);

  // Reset people results pagination when filters change
  useEffect(() => {
    setPeopleResultsCurrentPage(1);
  }, [peopleResultsSearchTerm, peopleResultsNameFilter, peopleResultsTitleFilter, peopleResultsEmailFilter, 
      peopleResultsPhoneFilter, peopleResultsLinkedinFilter, peopleResultsCompanyFilter, 
      peopleResultsIndustryFilter, peopleResultsSortConfig]);


  // Function to format revenue values for CSV export
  const formatRevenue = (revenue: number | null | undefined): string => {
    if (!revenue || revenue === 0) return "-"
    
    if (revenue >= 1000000000) {
      return `$${(revenue / 1000000000).toFixed(1)}B`
    } else if (revenue >= 1000000) {
      return `$${(revenue / 1000000).toFixed(1)}M`
    } else if (revenue >= 1000) {
      return `$${(revenue / 1000).toFixed(1)}K`
    } else {
      return `$${revenue}`
    }
  }

  // Function to format revenue for display (matches UI formatting)
  const formatRevenueForDisplay = (revenue: string | number): string => {
    console.log(`🔍 formatRevenueForDisplay - Input: ${revenue}, type: ${typeof revenue}`);
    
    if (!revenue || revenue === "N/A" || revenue === "") {
      console.log(`🔍 formatRevenueForDisplay - Returning N/A (empty/invalid)`);
      return "N/A";
    }
    
    // If revenue is already formatted (contains $), return as is
    if (typeof revenue === 'string' && revenue.includes('$')) {
      console.log(`🔍 formatRevenueForDisplay - Already formatted, returning: ${revenue}`);
      return revenue;
    }
    
    const numRevenue = typeof revenue === 'string' ? parseFloat(revenue) : revenue;
    console.log(`🔍 formatRevenueForDisplay - Parsed number: ${numRevenue}`);
    
    if (isNaN(numRevenue)) {
      console.log(`🔍 formatRevenueForDisplay - Returning N/A (NaN)`);
      return "N/A";
    }
    
    let result;
    if (numRevenue >= 1000) {
      result = `$${(numRevenue / 1000).toFixed(1)}M`;  // 4.3 → $4.3M
    } else if (numRevenue >= 1) {
      result = `$${numRevenue.toFixed(1)}M`;            // 0.5 → $0.5M
    } else {
      result = `$${numRevenue.toFixed(1)}M`;            // 0.1 → $0.1M
    }
    
    console.log(`🔍 formatRevenueForDisplay - Final result: ${result}`);
    return result;
  };

  // Helper function to generate type string for deduct API
  const generateDeductType = (
    enrichmentPhase: 'first enrichment' | 'second enrichment',
    dataType: 'companies' | 'people',
    dataSource: 'db' | 'growjo' | 'apollo'
  ): string => {
    return `${enrichmentPhase}_${dataType}_${dataSource}`;
  };

  const downloadCSV = (data: any[], filename: string) => {
    const headers = Object.keys(data[0])
    const csvRows = [
      headers.join(","), // header row
      ...data.map(row =>
        headers.map(field => {
          let value = row[field] ?? "";
          
          // Format revenue field for CSV export
          if (field === 'revenue' && value && value !== "" && value !== "-") {
            // Convert string revenue to number if needed
            const numValue = typeof value === 'string' ? parseFloat(value) : value;
            if (!isNaN(numValue)) {
              value = formatRevenue(numValue);
            }
          }
          
          return `"${value.toString().replace(/"/g, '""')}"`;
        }).join(",")
      ),
    ]
    const csvContent = csvRows.join("\n")
    const blob = new Blob([csvContent], { type: "text/csv" })
    const url = URL.createObjectURL(blob)

    const a = document.createElement("a")
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }
  // Add searchTerm state
  const [searchTerm, setSearchTerm] = useState("");
  // ... existing code ...
  // Update the search bar input
  // ...
  <Input
    type="search"
    placeholder="Search companies..."
    className="pl-8"
    value={searchTerm}
    onChange={e => setSearchTerm(e.target.value)}
  />
  const parseRevenue = (revenueStr: string): number | null => {
    if (!revenueStr) return null;
    revenueStr = revenueStr.toString().toLowerCase().trim().replace(/[$,]/g, "");
    let multiplier = 1;

    if (revenueStr.endsWith("k")) {
      multiplier = 1_000;
      revenueStr = revenueStr.slice(0, -1);
    } else if (revenueStr.endsWith("m")) {
      multiplier = 1_000_000;
      revenueStr = revenueStr.slice(0, -1);
    } else if (revenueStr.endsWith("b")) {
      multiplier = 1_000_000_000;
      revenueStr = revenueStr.slice(0, -1);
    }

    const value = parseFloat(revenueStr);
    return isNaN(value) ? null : value * multiplier;
  };

  const parseFilter = (filterStr: string, isRevenue = false) => {
    const result = { operation: "exact", value: null as number | null, upper: null as number | null };
    if (!filterStr) return result;
    filterStr = filterStr.toString().toLowerCase().trim();
    
    const rangeMatch = filterStr.match(/^(\d+(?:\.\d+)?(?:[kmb]?)?)\s*-\s*(\d+(?:\.\d+)?(?:[kmb]?)?)$/);
    if (rangeMatch) {
      const val1 = isRevenue ? parseRevenue(rangeMatch[1]) : parseInt(rangeMatch[1], 10);
      const val2 = isRevenue ? parseRevenue(rangeMatch[2]) : parseInt(rangeMatch[2], 10);
      return { operation: "between", value: val1, upper: val2 };
    }

    if (filterStr.startsWith(">=")) {
      result.operation = "greater than or equal";
      filterStr = filterStr.slice(2);
    } else if (filterStr.startsWith(">")) {
      result.operation = "greater than";
      filterStr = filterStr.slice(1);
    } else if (filterStr.startsWith("<=")) {
      result.operation = "less than or equal";
      filterStr = filterStr.slice(2);
    } else if (filterStr.startsWith("<")) {
      result.operation = "less than";
      filterStr = filterStr.slice(1);
    }
    
    result.value = isRevenue ? parseRevenue(filterStr) : parseInt(filterStr, 10);
    return result;
  };
  // ... existing code ...
  // Update filteredLeads to include searchTerm
  const filteredLeads = normalizedLeads.filter((company) => {
    const matchesSearch =
      company.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      company.website.toLowerCase().includes(searchTerm.toLowerCase()) ||
      company.industry.toLowerCase().includes(searchTerm.toLowerCase());

    // Corrected Revenue Filter Logic
    let matchesRevenue = true;
    if (revenueFilter) {
      const { operation, value: filterValue, upper: filterUpper } = parseFilter(revenueFilter, true);

      if (filterValue !== null) {
        // This helper parses the company's revenue string (e.g., "$5M-$10M") 
        // into a single comparable number (the average).
        const getCompanyRevenueValue = (revStr: string | number | null) => {
          const s = revStr?.toString();
          if (!s) return null;
          
          if (s.includes('-')) {
            const parts = s.split('-').map(p => parseRevenue(p));
            if (parts.length === 2 && parts[0] !== null && parts[1] !== null) {
              return (parts[0] + parts[1]) / 2; // Return the average for range comparison
            }
            return null;
          }
          return parseRevenue(s); // Handle single values
        };
        
        const companyRevNumber = getCompanyRevenueValue(company.revenue);

        if (companyRevNumber === null) {
          matchesRevenue = false;
        } else {
          switch (operation) {
            case "exact": matchesRevenue = (companyRevNumber === filterValue); break;
            case "less than": matchesRevenue = (companyRevNumber < filterValue); break;
            case "less than or equal": matchesRevenue = (companyRevNumber <= filterValue); break;
            case "greater than": matchesRevenue = (companyRevNumber > filterValue); break;
            case "greater than or equal": matchesRevenue = (companyRevNumber >= filterValue); break;
            case "between": matchesRevenue = (filterUpper !== null && companyRevNumber >= filterValue && companyRevNumber <= filterUpper); break;
            default: matchesRevenue = false;
          }
        }
      }
    }

    return (
      matchesSearch &&
      company.industry.toLowerCase().includes(industryFilter.toLowerCase()) &&
      company.city.toLowerCase().includes(cityFilter.toLowerCase()) &&
      company.state.toLowerCase().includes(stateFilter.toLowerCase()) &&
      company.bbb_rating.toLowerCase().includes(bbbRatingFilter.toLowerCase()) &&
      matchesRevenue
    );
  });


  // Function to handle sorting
  const requestSort = (key: string) => {
    let direction: 'ascending' | 'descending' = 'ascending';

    // If already sorting by this key, toggle direction
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }

    setSortConfig({ key, direction });
  };

  // Function to sort data with N/A values at the bottom
  const getSortedData = (data: any[]) => {
    // If no sort config, return original data
    if (!sortConfig) return data;

    return [...data].sort((a, b) => {
      const key = sortConfig.key;

      // Revenue sorting
      if (key === "revenue") {
        const aVal = a.revenue;
        const bVal = b.revenue;

        const aIsNA = !aVal || aVal === "N/A" || aVal === "";
        const bIsNA = !bVal || bVal === "N/A" || bVal === "";

        if (aIsNA && !bIsNA) return 1;
        if (!aIsNA && bIsNA) return -1;
        if (aIsNA && bIsNA) return 0;

        // Convert to numbers for comparison
        const aNum = typeof aVal === 'string' ? parseFloat(aVal) : aVal;
        const bNum = typeof bVal === 'string' ? parseFloat(bVal) : bVal;

        return sortConfig.direction === "ascending"
          ? (aNum ?? 0) - (bNum ?? 0)
          : (bNum ?? 0) - (aNum ?? 0);
      }

      // General string comparison fallback
      const aVal = (a[key] ?? "").toString().toLowerCase();
      const bVal = (b[key] ?? "").toString().toLowerCase();

      const aIsNA = aVal === "n/a" || aVal === "na" || aVal === "";
      const bIsNA = bVal === "n/a" || bVal === "na" || bVal === "";

      if (aIsNA && !bIsNA) return 1;
      if (!aIsNA && bIsNA) return -1;
      if (aIsNA && bIsNA) return 0;

      return sortConfig.direction === "ascending"
        ? aVal.localeCompare(bVal)
        : bVal.localeCompare(aVal);
    });
  };

  // Apply sorting to the filtered data
  const sortedFilteredLeads = getSortedData(filteredLeads);

  // Use the sorted data for pagination
  const totalPages = Math.ceil(sortedFilteredLeads.length / itemsPerPage)
  const indexOfLastItem = currentPage * itemsPerPage
  const indexOfFirstItem = indexOfLastItem - itemsPerPage
  const currentItems = sortedFilteredLeads.slice(indexOfFirstItem, indexOfLastItem)

  // Generate page numbers for pagination
  const getPageNumbers = () => {
    const pageNumbers = [];

    if (totalPages <= 7) {
      // Show all pages if there are 7 or fewer
      for (let i = 1; i <= totalPages; i++) {
        pageNumbers.push(i);
      }
    } else {
      // Always show first and last page, with ellipsis for hidden pages
      pageNumbers.push(1);

      // Determine range to show around current page
      let startPage = Math.max(2, currentPage - 2);
      let endPage = Math.min(totalPages - 1, currentPage + 2);

      // Adjust if we're near the beginning or end
      if (currentPage <= 4) {
        endPage = 5;
      } else if (currentPage >= totalPages - 3) {
        startPage = totalPages - 4;
      }

      // Add ellipsis if needed
      if (startPage > 2) {
        pageNumbers.push('ellipsis');
      }

      // Add middle pages
      for (let i = startPage; i <= endPage; i++) {
        pageNumbers.push(i);
      }

      // Add ellipsis if needed
      if (endPage < totalPages - 1) {
        pageNumbers.push('ellipsis');
      }

      pageNumbers.push(totalPages);
    }

    return pageNumbers;
  };


  //   const companies = [
  //   {
  //     id: "1",
  //     name: "HubSpot",
  //     website: "hubspot.com",
  //     industry: "CRM Software",
  //     street: "25 First Street",
  //     city: "Cambridge",
  //     state: "MA",
  //     phone: "(888) 482-7768",
  //     bbbRating: "A+",
  //   }
  // ]
  const handleSelectAll = () => {
    // If ANY companies are selected (globally), the action is to clear ALL selections.
    if (selectedCompanies.length > 0) {
      setSelectedCompanies([]);
    } else {
      // If NO companies are selected, the action is to select only the items on the CURRENT page.
      const idsOnCurrentPage = currentItems.map((c) => c.id);
      const selectionLimit = 25;

      if (idsOnCurrentPage.length > selectionLimit) {
        showNotification(`Maximum 25 leads allowed. Selected the first ${selectionLimit} on this page.`, "info");
        setSelectedCompanies(idsOnCurrentPage.slice(0, selectionLimit));
      } else {
        setSelectedCompanies(idsOnCurrentPage);
      }
    }
  };

  const handleSelectCompany = (id: number) => {
    if (selectedCompanies.includes(id)) {
      setSelectedCompanies(selectedCompanies.filter((companyId) => companyId !== id))
      setSelectAll(false)
    } else {
      // Check if we're at the 25 lead limit
      if (selectedCompanies.length >= 25) {
        showNotification("Maximum 25 leads allowed. Please deselect some leads first.", "error")
        return
      }
      
      const updated = [...selectedCompanies, id]
      setSelectedCompanies(updated)
      
      // Update selectAll state based on limited selection
      const maxSelectable = Math.min(25, normalizedLeads.length)
      if (updated.length === maxSelectable) {
        setSelectAll(true)
      }
    }
  }

  const handleSelectEnrichedCompany = (id: number) => {
    if (selectedEnrichedCompanies.includes(id)) {
      setSelectedEnrichedCompanies(selectedEnrichedCompanies.filter((companyId) => companyId !== id))
    } else {
      // Check if we're at the 25 lead limit
      if (selectedEnrichedCompanies.length >= 25) {
        showNotification("Maximum 25 leads allowed. Please deselect some leads first.", "error")
        return
      }
      
      setSelectedEnrichedCompanies([...selectedEnrichedCompanies, id])
    }
  }

  const normalizeWebsite = (url: string) => {
    if (!url || url === "N/A") return "";
    return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
  };

  // Utility function to convert N/A values to friendly fallback messages for display
  const getFriendlyFallback = (value: string, fieldType: string): string => {
    if (value && value !== "N/A") return value;

    const fallbacks = {
      website: "We couldn't locate a website just yet.",
      revenue: "Revenue details were not available.",
      location: "Location wasn't listed.",
      industry: "Industry information missing.",
      interests: "Specialties not mentioned.",
      employee_count: "Employee count is unavailable.",
      decider_name: "No decision maker found.",
      decider_title: "Title information not found.",
      decider_email: "Email is currently unavailable.",
      decider_phone: "Phone number not listed.",
      decider_linkedin: "LinkedIn profile not available.",
      name: "Name not available",
      title: "Title not available",
      email: "Email not available",
      phone: "Phone not available",
      linkedin: "LinkedIn not available"
    };

    return fallbacks[fieldType as keyof typeof fallbacks] || "Information unavailable.";
  };

  // Helper function to call business type decider API
  const callBusinessTypeDecider = async (products: string, industry: string): Promise<string> => {
    try {
      // Use products if available, otherwise fallback to industry
      const payload = products && products.trim() !== "" ? products : industry;
      console.log(`🤖 Calling business type decider for payload: ${payload} (source: ${products && products.trim() !== "" ? 'products' : 'industry'})`);
      
      const response = await axios.post(
        `${BACKEND_URL}/business-type-decider`,
        { products: payload },
        { headers: { "Content-Type": "application/json" } }
      );

      if (response.data && response.data.success) {
        console.log(`✅ Business type decider result: ${response.data.business_type}`);
        return response.data.business_type || "N/A";
      } else {
        console.warn(`⚠️ Business type decider failed:`, response.data?.error || "Unknown error");
        return "N/A";
      }
    } catch (error) {
      console.error(`❌ Business type decider API call failed:`, error);
      return "N/A";
    }
  };

  // Helper function to enrich companies with business type
  const enrichWithBusinessType = async (companies: any[]): Promise<any[]> => {
    console.log(`🤖 Starting business type enrichment for ${companies.length} companies...`);
    
    const enrichedCompanies = [];
    
    for (const company of companies) {
      try {
        // Get products/tags for business type analysis
        const products = company.productCategory || "";
        const industry = company.industry || company.company || "";
        
        if ((products && products !== "N/A") || (industry && industry !== "N/A")) {
          const businessType = await callBusinessTypeDecider(products, industry);
          
          // Update the company with the new business type
          const enrichedCompany = {
            ...company,
            businessType: businessType
          };
          
          enrichedCompanies.push(enrichedCompany);
          console.log(`✅ Updated ${company.company} with business type: ${businessType}`);
        } else {
          console.log(`⚠️ Skipping ${company.company} - no products/industry data available`);
          enrichedCompanies.push(company);
        }
      } catch (error) {
        console.error(`❌ Failed to enrich business type for ${company.company}:`, error);
        enrichedCompanies.push(company);
      }
    }
    
    console.log(`✅ Business type enrichment completed for ${enrichedCompanies.length} companies`);
    return enrichedCompanies;
  };

  const getSource = (growjo: any, apollo: any, person: any) => {
    console.log(`🔍 Determining data source for enrichment:`);
    console.log(`  - Growjo data available:`, !!growjo && Object.keys(growjo).some((k) => growjo[k]));
    console.log(`  - Apollo data available:`, !!apollo && Object.keys(apollo).some((k) => apollo[k]));
    console.log(`  - Person data available:`, !!person && Object.keys(person).some((k) => person[k]));
    
    const g = growjo && Object.keys(growjo).some((k) => growjo[k])
    const a = apollo && Object.keys(apollo).some((k) => apollo[k])
    const p = person && Object.keys(person).some((k) => person[k])
    
    let source = "N/A";
    if (g && a) {
      source = "Saasquatch Leads + Apollo";
      console.log(`✅ Using combined data source: ${source}`);
    } else if (g) {
      source = "Saasquatch Leads";
      console.log(`✅ Using Growjo data source: ${source}`);
    } else if (a) {
      source = "Apollo";
      console.log(`✅ Using Apollo data source: ${source}`);
    } else {
      console.log(`⚠️ No enrichment data available, using N/A`);
    }
    
    return source;
  }

  // Helper function to parse employee ranges and return comparable values
  const processEmployeeRange = (employeeValue: any) => {
    if (!employeeValue) return null;
    
    const value = employeeValue.toString().trim();
    
    // Handle single numbers (including with + suffix)
    const singleNumberMatch = value.match(/^(\d+)\+?$/);
    if (singleNumberMatch) {
      return parseInt(singleNumberMatch[1], 10);
    }

    // Handle ranges like "50-100", "25-50 people", "10-20 employees"
    const rangeMatch = value.match(/^(\d+)\s*-\s*(\d+)(?:\s+\w+)?$/);
    if (rangeMatch) {
      const min = parseInt(rangeMatch[1], 10);
      const max = parseInt(rangeMatch[2], 10);
      
      if (min <= max) {
        return { min, max, isRange: true };
      }
    }

    // Handle ranges with words like "fifty to one hundred"
    // This is a basic implementation - could be expanded for more complex text parsing
    return null;
  };

  // Helper function to check if a filter value matches an employee range
  const matchesEmployeeRange = (companyEmployees: any, filterValue: number) => {
    const parsed = processEmployeeRange(companyEmployees);
    
    if (!parsed) return false;
    
    // If it's a single number
    if (typeof parsed === 'number') {
      return parsed === filterValue;
    }
    
    // If it's a range, check if filter value falls within the range
    if (parsed.isRange) {
      return filterValue >= parsed.min && filterValue <= parsed.max;
    }
    
    return false;
  };

  const buildEnrichedCompany = (company: any, growjo: any, apollo: any, person: any, revenueMap?: any) => {
    console.log(`🔍 Building enriched company for: ${company.company}`);
    console.log(`📊 Data sources available:`);
    console.log(`  - Company (original):`, { 
      revenue: company.revenue, 
      employees: company.employees, 
      website: company.website,
      year_founded: company.year_founded,
      company_linkedin: company.company_linkedin,
      business_phone: company.business_phone
    });
    console.log(`  - Growjo:`, { 
      revenue: growjo.revenue, 
      employees: growjo.employees,
      website: growjo.website,
      phone: growjo.phone,
      industry: growjo.industry,
      product_category: growjo.product_category,
      business_type: growjo.business_type,
      linkedin_url: growjo.linkedin_url
    });
    console.log(`  - Apollo:`, { 
      organization_revenue: apollo.organization_revenue,
      annual_revenue_printed: apollo.annual_revenue_printed,
      employees: apollo.employees,
      founded_year: apollo.founded_year,
      linkedin_url: apollo.linkedin_url,
      phone: apollo.phone,
      primary_domain: apollo.primary_domain,
      website_url: apollo.website_url
    });
    console.log(`  - Person:`, { 
      first_name: person.first_name, 
      last_name: person.last_name,
      email: person.email,
      phone_number: person.phone_number,
      linkedin_url: person.linkedin_url,
      title: person.title
    });

    const cleanVal = (val: any) => {
      const s = (val || "").toString().trim().toLowerCase();
      const isObscuredEmail = /^[a-z\*]+@[^ ]+\.[a-z]+$/.test(s) && s.includes("*");
      return (
        ["", "na", "n/a", "none", "not", "found", "not found", "n.a.", "email_not_unlocked@domain.com"].includes(s) ||
        isObscuredEmail
      )
        ? null
        : val.toString().trim();
    };

    // Prefer original company data for these fields, fallback to enrichment
    const preferOriginal = (orig: any, ...fallbacks: any[]) => {
      const cleaned = cleanVal(orig);
      if (cleaned) {
        console.log(`✅ Using original value: ${orig}`);
        return orig;
      }
      
      console.log(`⚠️ Original value missing/invalid: ${orig}, checking fallbacks...`);
      for (let i = 0; i < fallbacks.length; i++) {
        const f = fallbacks[i];
        const v = cleanVal(f);
        if (v) {
          console.log(`🔄 Fallback ${i + 1} successful: ${f}`);
          return f;
        } else {
          console.log(`❌ Fallback ${i + 1} failed: ${f}`);
        }
      }
      console.log(`⚠️ All fallbacks failed, using original: ${orig}`);
      return orig; // fallback to original if all are bad
    };

    const splitGrowjoName = (() => {
      const raw = growjo.decider_name || ""
      const clean = raw.toString().trim().toLowerCase()
      if (["", "na", "n/a", "none", "not", "found", "not found"].includes(clean)) return []
      return raw.split(" ")
    })()
    const growjoFirstName = splitGrowjoName[0] || ""
    const growjoLastName = splitGrowjoName.slice(1).join(" ") || ""

    console.log(`👤 Building decider info with fallbacks:`);
    const decider = {
      firstName: preferOriginal(company.owner_first_name, growjoFirstName, person.first_name),
      lastName: preferOriginal(company.owner_last_name, growjoLastName, person.last_name),
      email: preferOriginal(company.owner_email, growjo.decider_email, person.email),
      phone: preferOriginal(company.owner_phone_number, growjo.decider_phone, person.phone_number),
      linkedin: preferOriginal(company.owner_linkedin, growjo.decider_linkedin, person.linkedin_url),
      title: preferOriginal(company.owner_title, growjo.decider_title, person.title),
    }

    // Revenue enrichment with detailed logging
    console.log(`💰 Revenue enrichment:`);
    let finalRevenue = company.revenue;
    
    // 🆕 UPDATED: Always prioritize API data over company data (including estimated revenue)
    // This ensures that API data takes precedence over any pre-existing company revenue
    if (cleanVal(growjo.revenue)) {
      console.log(`🔄 Using Growjo revenue (API priority): ${growjo.revenue}`);
      finalRevenue = growjo.revenue;
    } else if (apollo.organization_revenue || apollo.annual_revenue_printed) {
      const apolloRevenue = apollo.organization_revenue ? apollo.organization_revenue / 1000000 : apollo.annual_revenue_printed;
      console.log(`🔄 Using Apollo revenue (API priority): ${apolloRevenue}`);
      finalRevenue = apolloRevenue;
    } else if (cleanVal(company.revenue)) {
      console.log(`✅ Using company revenue (no API data available): ${company.revenue}`);
      finalRevenue = company.revenue;
    } else if (revenueMap && company.lead_id && revenueMap[company.lead_id]) {
      // 🆕 NEW: Fallback to estimated revenue from revenueMap if no other sources available
      const estimatedRevenue = revenueMap[company.lead_id];
      console.log(`🔄 All sources missing, falling back to estimated revenue: ${estimatedRevenue}`);
      finalRevenue = estimatedRevenue;
    } else {
      console.log(`❌ All revenue sources missing, keeping original: ${company.revenue}`);
    }

    // Employees enrichment with detailed logging and range processing
    console.log(`👥 Employees enrichment:`);
    let finalEmployees = company.employees;
    if (!cleanVal(company.employees)) {
      console.log(`⚠️ Company employees missing/invalid: "${company.employees}"`);
      if (cleanVal(growjo.employees)) {
        console.log(`🔄 Company employees missing, falling back to Growjo: ${growjo.employees}`);
        const processedGrowjoEmployees = processEmployeeRange(growjo.employees);
        finalEmployees = processedGrowjoEmployees;
        console.log(`📊 Growjo employees processed: "${growjo.employees}" → "${processedGrowjoEmployees}"`);
      } else if (cleanVal(apollo.employees)) {
        console.log(`🔄 Company and Growjo employees missing, falling back to Apollo: ${apollo.employees}`);
        finalEmployees = apollo.employees;
      } else {
        console.log(`❌ All employee sources missing, keeping original: ${company.employees}`);
      }
    } else {
      console.log(`✅ Using company employees: ${company.employees}`);
    }

    // Year founded enrichment with detailed logging
    console.log(`📅 Year founded enrichment:`);
    let finalYearFounded = company.year_founded;
    if (!cleanVal(company.year_founded)) {
      console.log(`⚠️ Company year founded missing/invalid: "${company.year_founded}"`);
      if (cleanVal(apollo.founded_year)) {
        console.log(`🔄 Company year founded missing, falling back to Apollo: ${apollo.founded_year}`);
        finalYearFounded = apollo.founded_year;
      } else {
        console.log(`❌ All year founded sources missing, keeping original: ${company.year_founded}`);
      }
    } else {
      console.log(`✅ Using company year founded: ${company.year_founded}`);
    }

    // Company LinkedIn enrichment with detailed logging (updated to include Growjo)
    console.log(`🔗 Company LinkedIn enrichment:`);
    const finalCompanyLinkedin = preferOriginal(company.company_linkedin, growjo.linkedin_url, apollo.linkedin_url);

    // Company phone enrichment with detailed logging
    console.log(`📞 Company phone enrichment:`);
    const finalCompanyPhone = preferOriginal(company.business_phone || company.company_phone, apollo.phone, growjo.phone);

    // Website enrichment with detailed logging
    console.log(`🌐 Website enrichment:`);
    let finalWebsite = company.website;
    if (!company.website || company.website === "N/A") {
      console.log(`⚠️ Company website missing or N/A: "${company.website}"`);
      if (growjo.website && growjo.website !== "N/A") {
        console.log(`🔄 Company website missing/N/A, falling back to Growjo: ${growjo.website}`);
        finalWebsite = growjo.website;
      } else if (apollo.primary_domain && apollo.primary_domain !== "N/A") {
        console.log(`🔄 Company and Growjo website missing/N/A, falling back to Apollo primary domain: ${apollo.primary_domain}`);
        finalWebsite = apollo.primary_domain;
      } else if (apollo.website_url && apollo.website_url !== "N/A") {
        console.log(`🔄 Company, Growjo, and Apollo primary domain missing/N/A, falling back to Apollo website URL: ${apollo.website_url}`);
        finalWebsite = apollo.website_url;
      } else {
        console.log(`❌ All website sources missing or N/A, keeping original: ${company.website}`);
      }
    } else {
      console.log(`✅ Using company website: ${company.website}`);
    }

    // Industry enrichment with detailed logging
    console.log(`🏭 Industry enrichment:`);
    let finalIndustry = company.industry;
    if (!cleanVal(company.industry)) {
      console.log(`⚠️ Company industry missing/invalid: "${company.industry}"`);
      if (cleanVal(growjo.industry)) {
        console.log(`🔄 Company industry missing, falling back to Growjo: ${growjo.industry}`);
        finalIndustry = growjo.industry;
      } else {
        console.log(`❌ All industry sources missing, keeping original: ${company.industry}`);
      }
    } else {
      console.log(`✅ Using company industry: ${company.industry}`);
    }

    // Product category enrichment with detailed logging
    console.log(`📦 Product category enrichment:`);
    let finalProductCategory = company.product_category;
    if (!cleanVal(company.product_category)) {
      console.log(`⚠️ Company product category missing/invalid: "${company.product_category}"`);
      if (cleanVal(growjo.product_category)) {
        console.log(`🔄 Company product category missing, falling back to Growjo: ${growjo.product_category}`);
        finalProductCategory = growjo.product_category;
      } else {
        console.log(`❌ All product category sources missing, keeping original: ${company.product_category}`);
      }
    } else {
      console.log(`✅ Using company product category: ${company.product_category}`);
    }

    // Business type enrichment with detailed logging
    console.log(`💼 Business type enrichment:`);
    let finalBusinessType = company.business_type;
    if (!cleanVal(company.business_type)) {
      console.log(`⚠️ Company business type missing/invalid: "${company.business_type}"`);
      if (cleanVal(growjo.business_type)) {
        console.log(`🔄 Company business type missing, falling back to Growjo: ${growjo.business_type}`);
        finalBusinessType = growjo.business_type;
      } else {
        console.log(`❌ All business type sources missing, keeping original: ${company.business_type}`);
      }
    } else {
      console.log(`✅ Using company business type: ${company.business_type}`);
    }

    // BBB rating enrichment with detailed logging
    console.log(`⭐ BBB rating enrichment:`);
    let finalBbbRating = company.bbb_rating;
    if (!cleanVal(company.bbb_rating)) {
      console.log(`⚠️ Company BBB rating missing/invalid: "${company.bbb_rating}"`);
      // Note: Growjo doesn't provide BBB rating, so we keep the original or use a default
      if (cleanVal(company.bbb_rating)) {
        console.log(`✅ Using company BBB rating: ${company.bbb_rating}`);
        finalBbbRating = company.bbb_rating;
      } else {
        console.log(`❌ No BBB rating available, keeping original: ${company.bbb_rating}`);
      }
    } else {
      console.log(`✅ Using company BBB rating: ${company.bbb_rating}`);
    }


    const enrichedCompany = {
      company: company.company,
      
      // 🆕 UPDATED: Keep original/database values for these fields (no changes)
      city: company.city,
      state: company.state,
      country: searchCriteria.country,
      industry: finalIndustry,
      productCategory: finalProductCategory,
      businessType: finalBusinessType,
      bbbRating: finalBbbRating,
      street: company.street || "",
      
      // 🆕 UPDATED: Apply improved logic for these fields (pick best value)
      revenue: finalRevenue,
      employees: finalEmployees,
      yearFounded: finalYearFounded,
      companyLinkedin: finalCompanyLinkedin,
      companyPhone: finalCompanyPhone,
      
      // 🆕 UPDATED: Website priority - database first, then fallbacks
      website: finalWebsite,
      
      // Owner info - preserve original when available
      ownerFirstName: decider.firstName,
      ownerLastName: decider.lastName,
      ownerTitle: decider.title,
      ownerEmail: decider.email,
      ownerPhoneNumber: decider.phone,
      ownerLinkedin: decider.linkedin,
      source: getSource(growjo, apollo, person),
    }

    console.log(`✅ Final enriched company data:`, enrichedCompany);
    
    // Summary of data sources used
    console.log(`📊 Data source summary for ${company.company}:`);
    console.log(`  - Revenue: ${finalRevenue === growjo.revenue ? 'Growjo' : finalRevenue === (apollo.organization_revenue ? apollo.organization_revenue / 1000000 : apollo.annual_revenue_printed) ? 'Apollo' : finalRevenue === company.revenue ? 'Original' : (revenueMap && company.lead_id && revenueMap[company.lead_id] && finalRevenue === revenueMap[company.lead_id]) ? 'Estimated' : 'Original'}`);
    console.log(`  - Employees: ${finalEmployees === company.employees ? 'Original' : finalEmployees === growjo.employees ? 'Growjo' : finalEmployees === apollo.employees ? 'Apollo' : 'Original'}`);
    console.log(`  - Year Founded: ${finalYearFounded === company.year_founded ? 'Original' : finalYearFounded === apollo.founded_year ? 'Apollo' : 'Original'}`);
    console.log(`  - Website: ${finalWebsite === company.website ? 'Original' : finalWebsite === growjo.website ? 'Growjo' : finalWebsite === apollo.primary_domain ? 'Apollo Primary Domain' : finalWebsite === apollo.website_url ? 'Apollo Website URL' : 'Original'}`);
    console.log(`  - Industry: ${finalIndustry === company.industry ? 'Original' : finalIndustry === growjo.industry ? 'Growjo' : 'Original'}`);
    console.log(`  - Product Category: ${finalProductCategory === company.product_category ? 'Original' : finalProductCategory === growjo.product_category ? 'Growjo' : 'Original'}`);
    console.log(`  - Business Type: ${finalBusinessType === company.business_type ? 'Original' : finalBusinessType === growjo.business_type ? 'Growjo' : 'Original'}`);
    console.log(`  - BBB Rating: ${finalBbbRating === company.bbb_rating ? 'Original' : 'Original'}`);
    console.log(`  - Company LinkedIn: ${finalCompanyLinkedin === company.company_linkedin ? 'Original' : finalCompanyLinkedin === growjo.linkedin_url ? 'Growjo' : finalCompanyLinkedin === apollo.linkedin_url ? 'Apollo' : 'Original'}`);
    console.log(`  - Company Phone: ${finalCompanyPhone === company.business_phone ? 'Original' : finalCompanyPhone === apollo.phone ? 'Apollo' : finalCompanyPhone === growjo.phone ? 'Growjo' : 'Original'}`);
    
    return enrichedCompany;
  }



  const toCamelCase = (lead: any): EnrichedCompany => {
    console.log(`🔍 toCamelCase - Processing lead: ${lead.company}, revenue: ${lead.revenue}, type: ${typeof lead.revenue}`);
    const formattedRevenue = formatRevenueForDisplay(lead.revenue);
    console.log(`🔍 toCamelCase - Formatted revenue: ${formattedRevenue}`);
    
    return {
      id: lead.id || `${lead.company}-${Math.random()}`,
      lead_id: lead.lead_id,
      draft_id: lead.draft_id,
      company: lead.company,
      website: lead.website,
      industry: lead.industry,
      productCategory: lead.productCategory || lead.product_category,
      businessType: lead.businessType || lead.business_type,
      employees: lead.employees,
      revenue: formattedRevenue,
      yearFounded: lead.yearFounded?.toString() || lead.year_founded?.toString() || "N/A",
      bbbRating: lead.bbbRating || lead.bbb_rating,
      street: lead.street,
      city: lead.city,
      state: lead.state,
      companyPhone: lead.company_phone || lead.business_phone || lead.companyPhone,
      companyLinkedin: lead.company_linkedin || lead.companyLinkedin,
      ownerFirstName: lead.owner_first_name,
      ownerLastName: lead.owner_last_name,
      ownerTitle: lead.owner_title,
      ownerEmail: lead.owner_email,
      ownerPhoneNumber: lead.owner_phone_number,
      ownerLinkedin: lead.owner_linkedin,
      source: lead.source,
      sourceType: lead.source_type,
      people: lead.people, // Include people array if it exists
    };
  };

  const [fromDatabaseLeads, setFromDatabaseLeads] = useState<string[]>([]); // lowercase names
  const { 
    enrichedCompanies, 
    setEnrichedCompanies,
    dbEnrichedCompanies,
    setDbEnrichedCompanies,
    scrapedEnrichedCompanies,
    setScrapedEnrichedCompanies,
    hasFirstEnrichment,
    setHasFirstEnrichment,
    firstEnrichmentType,
    setFirstEnrichmentType,
    showResults,
    setShowResults,
    addEnrichedCompanies,
    clearEnrichedCompanies
  } = useEnrichment();
  const [leadToDraftMap, setLeadToDraftMap] = useState<Record<string, { draft_id: string, company: string }>>({});
  const draftMap: Record<string, { draft_id: string; company: string }> = {};

  // Add state for enrichment view type
  const [enrichmentViewType, setEnrichmentViewType] = useState<"company" | "people" | "both">("company");

  // Function to check for empty results and show banner if needed
  const checkForEmptyResults = (enrichmentType: "company" | "people" | "both", dbResults?: any[], scrapedResults?: any[]) => {
    let hasDbResults = false;
    let hasScrapedResults = false;
    let totalCount = 0;

    // Use passed results if provided, otherwise fall back to state
    const dbData = dbResults !== undefined ? dbResults : dbEnrichedCompanies;
    const scrapedData = scrapedResults !== undefined ? scrapedResults : scrapedEnrichedCompanies;
    const peopleDbData = dbResults !== undefined ? dbResults : dbPeopleResults;
    const peopleScrapedData = scrapedResults !== undefined ? scrapedResults : scrapedPeopleResults;

    if (enrichmentType === "company") {
      hasDbResults = dbData.length > 0;
      hasScrapedResults = scrapedData.length > 0;
      totalCount = hasDbResults ? dbData.length : (hasScrapedResults ? scrapedData.length : 0);
    } else if (enrichmentType === "people") {
      hasDbResults = peopleDbData.length > 0;
      hasScrapedResults = peopleScrapedData.length > 0;
      totalCount = hasDbResults ? peopleDbData.length : (hasScrapedResults ? peopleScrapedData.length : 0);
    } else if (enrichmentType === "both") {
      // For "both" enrichment, check if we have any company results (either from DB or scraped)
      // since "both" enrichment includes company data
      hasDbResults = dbData.length > 0;
      hasScrapedResults = scrapedData.length > 0;
      totalCount = hasDbResults ? dbData.length : (hasScrapedResults ? scrapedData.length : 0);
    }
    
    // Show banner if no results from any source
    if (!hasDbResults && !hasScrapedResults) {
      setEmptyResultsInfo({
        hasDatabaseResults: hasDbResults,
        hasScrapedResults: hasScrapedResults,
        totalCompanies: totalCount,
        enrichmentType
      });
      setShowEmptyResultsBanner(true);
      return true;
    }
    
    // Hide banner if we have results
    setShowEmptyResultsBanner(false);
    return false;
  };

  // Helper to check if user is on free tier
  function isFreeTierUser() {
    console.log("🔍 isFreeTierUser() called");
    console.log("🔍 isTeamMember:", isTeamMember);
    console.log("🔍 teamMembershipLoading:", teamMembershipLoading);
    
    // If user is a team member, they get premium access regardless of individual tier
    if (isTeamMember === true) {
      console.log("🔓 User has premium access through team membership");
      return false; // Not free tier - has premium access through team membership
    }

    // If team membership is still loading or not checked yet, fall back to original logic
    if (isTeamMember === null || teamMembershipLoading) {
      console.log("⏳ Team membership check in progress, falling back to individual tier check");
      try {
        const user = sessionStorage.getItem("user");
        if (user) {
          const parsedUser = JSON.parse(user);
          const tier = parsedUser?.tier?.toLowerCase() || "free";
          const role = parsedUser?.role?.toLowerCase() || "";
          console.log(`⏳ Fallback check - tier: ${tier}, role: ${role}`);
          if (role === "developer") return false;
          return tier === "free";
        }
      } catch (e) { }
      return true; // default to free if user not found
    }

    // If user is not a team member, check their individual tier
    console.log("🔒 User is not a team member, checking individual tier");
    try {
      const user = sessionStorage.getItem("user");
      if (user) {
        const parsedUser = JSON.parse(user);
        const tier = parsedUser?.tier?.toLowerCase() || "free";
        const role = parsedUser?.role?.toLowerCase() || "";
        console.log(`checking user tier: ${tier}`);
        console.log(`checking user role: ${role}`);
        console.log(`Full user data:`, parsedUser);
        if (role === "developer") return false;
        const result = tier === "free";
        console.log(`isFreeTierUser result: ${result}`);
        return result;
      }
    } catch (e) { 
      console.error("Error parsing user data:", e);
    }
    console.log("Defaulting to free tier (true)");
    return true; // default to free if user not found
  }

  // New smart enrichment function for company data
  // This function ensures Apollo is always called as a fallback when:
  // 1. Company doesn't have lead_id, OR
  // 2. Growjo companies API fails, OR  
  // 3. Growjo enrichment fails
  // 
  // IMPORTANT: Apollo will be called for ALL companies that need enrichment,
  // regardless of whether they have lead_id or whether the Growjo companies API worked.
  // This ensures maximum data coverage and fallback protection.
  const handleSmartCompanyEnrichment = async () => {
    console.log(`🚀 Starting Smart Company Enrichment...`);
    
    if (selectedCompanies.length === 0) {
      showNotification("Please select companies to enrich", "error");
      return;
    }

    if (selectedCompanies.length > 25) {
      showNotification("Maximum 25 leads allowed for enrichment", "error");
      return;
    }
    
    // 🆕 NEW: Prevent multiple enrichment functions from running simultaneously
    if (loading) {
      showNotification("Enrichment already in progress. Please wait.", "info");
      return;
    }
    
    const user = JSON.parse(sessionStorage.getItem("user") || "{}");
    const user_id = user.user_id || "";
    setLoading(true);
    setHasErrors(false);
    hasErrorsRef.current = false;
    
    // 🆕 NEW: Clear previous banner state when starting new enrichment
    setShowEmptyResultsBanner(false);
    setEmptyResultsInfo({
      hasDatabaseResults: false,
      hasScrapedResults: false,
      totalCompanies: 0,
      enrichmentType: "company"
    });
    
    // // 🆕 CLEAR RESULTS: Clear previous results when starting new company enrichment
    // console.log("🧹 Clearing previous results - starting new company enrichment");
    // setDbEnrichedCompanies([]);
    // setScrapedEnrichedCompanies([]);
    // setEnrichedCompanies([]);
    // setShowResults(false);
    // setHasEnrichedOnce(false);

    try {
      const selected = normalizedLeads.filter(c => selectedCompanies.includes(c.id));
      
      // Check credits first
      try {
        const { data: subscriptionInfo } = await axios.get(
          `${DATABASE_URL}/user/subscription_info`,
          { withCredentials: true }
        );

        const plan = subscriptionInfo?.plan;
        const isUnlimited =
          plan?.initial_credits === null ||
          (plan?.features_json && plan.features_json.includes("Unlimited Credits"));

        if (!isUnlimited) {
          const availableCredits = subscriptionInfo?.subscription?.credits_remaining ?? 0;
          const requiredCredits = selected.length;
          if (availableCredits < requiredCredits) {
            setShowTokenPopup(true);
            setLoading(false);
            return;
          }
        }
      } catch (checkErr) {
        console.error("❌ Failed to verify subscription:", checkErr);
        alert("Failed to verify your subscription. Please try again later.");
        setLoading(false);
        return;
      }

      // Step 1: Check database for existing data
      console.log("🔍 Step 1: Checking database for existing data...");
      let dbRows: any[] = [];
      let companiesNeedingEnrichment: any[] = [];
      let companiesWithCompleteData: any[] = []; // NEW: Track companies with complete data
      let completeDataDbLeads: any[] = []; // NEW: Store database data for companies with complete data

      const leadIds = selected.map(c => c.lead_id).filter((id): id is string => Boolean(id));
      const companyNames = selected.map(c => c.company).filter((name): name is string => Boolean(name));
      
      // Always try database lookup, even with empty leadIds (will use search_companies)
      try {
        const dbLeads = await fetchCompaniesWithFallback(leadIds, companyNames);

        for (const company of selected) {
          // For companies without lead_id, try to find by company name (case insensitive)
          const dbLead = dbLeads.find((l: any) => 
            l.lead_id === company.lead_id || 
            (company.lead_id ? false : l.company?.toLowerCase() === company.company?.toLowerCase())
          );
          
          console.log(`🔍 Matching company "${company.company}" (lead_id: ${company.lead_id || 'none'}):`, {
            found: !!dbLead,
            dbLead: dbLead ? { company: dbLead.company, lead_id: dbLead.lead_id } : null,
            allDbCompanies: dbLeads.map((l: any) => ({ company: l.company, lead_id: l.lead_id }))
          });
          
          if (dbLead) {
            // Check if this company needs enrichment based on missing core datapoints (year, revenue, employees)
            const missingFields = [];
            if (!dbLead.year_founded || dbLead.year_founded === "N/A") missingFields.push("year_founded");
            if (!dbLead.revenue || dbLead.revenue === "N/A") missingFields.push("revenue");
            if (!dbLead.employees || dbLead.employees === "N/A") missingFields.push("employees");
            
            const hasCompleteData = missingFields.length === 0;

            if (hasCompleteData) {
              // Company has complete data, track for processing but don't add to dbRows yet
              companiesWithCompleteData.push(company); // NEW: Track for processing
              completeDataDbLeads.push(dbLead); // NEW: Store the database data
              console.log(`✅ ${company.company} has complete data in database`);
            } else {
              // Company needs enrichment
              companiesNeedingEnrichment.push(company);
              console.log(`⚠️ ${company.company} needs enrichment - missing: ${missingFields.join(", ")}`);
            }
          } else {
            // Company not in database, needs enrichment
            companiesNeedingEnrichment.push(company);
            console.log(`⚠️ ${company.company} not found in database, needs enrichment`);
          }
        }
      } catch (err) {
        console.error("❌ Failed to fetch from database:", err);
        companiesNeedingEnrichment = selected; // Fallback to enriching all
      }

      // Step 2: Company lookup to get company_ids for Growjo
      console.log("🔍 Step 2: Company lookup to get company_ids...");
      console.log(`🔍 Companies needing enrichment details:`);
      companiesNeedingEnrichment.forEach((company, index) => {
        console.log(`  ${index + 1}. ${company.company} (lead_id: ${company.lead_id || 'none'}, website: ${company.website || 'none'})`);
      });
      
      let companiesWithIds: any[] = [];
      let companiesWithoutIds: any[] = [];

      if (companiesNeedingEnrichment.length > 0) {
        try {
          const companyNames = companiesNeedingEnrichment.map(c => c.company);
          console.log(`🔍 Growjo companies API call details:`);
          console.log(`  - Endpoint: ${DATABASE_URL}/growjo/companies`);
          console.log(`  - Company names being sent:`, companyNames);
          console.log(`  - Payload:`, { company_names: companyNames });
          
          const lookupResponse = await axios.post(
            `${DATABASE_URL}/growjo/companies`,
            { company_names: companyNames },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );
          
          console.log(`🔍 Growjo companies API response:`, lookupResponse.data);
          console.log(`🔍 Response status:`, lookupResponse.status);
          console.log(`🔍 Response has data:`, !!lookupResponse.data);
          console.log(`🔍 Response has company_batch_results:`, !!lookupResponse.data?.company_batch_results);
          console.log(`🔍 Company batch results length:`, lookupResponse.data?.company_batch_results?.length || 0);

          if (lookupResponse.data && lookupResponse.data.company_batch_results) {
            console.log(`🔍 Processing ${lookupResponse.data.company_batch_results.length} results from Growjo companies API`);
            for (const company of companiesNeedingEnrichment) {
              const lookupResult = lookupResponse.data.company_batch_results.find(
                (r: any) => r.company_name === company.company
              );
              console.log(`🔍 Looking for company: ${company.company}`);
              console.log(`🔍 Found lookup result:`, lookupResult);
              
              if (lookupResult && lookupResult.items && lookupResult.items.length > 0) {
                // Use the first item from the results
                const companyData = lookupResult.items[0];
                companiesWithIds.push({
                  ...company,
                  growjo_company_id: companyData.company_id,
                  growjo_company_data: companyData // Store the full company data for direct enrichment
                });
                console.log(`✅ Found company data for ${company.company} with company_id ${companyData.company_id}`);
              } else {
                companiesWithoutIds.push(company);
                console.log(`⚠️ No company data found for ${company.company}`);
              }
            }
          } else {
            console.log(`⚠️ Growjo companies API response missing data or company_batch_results`);
            console.log(`  - Response data:`, lookupResponse.data);
            console.log(`  - Has company_batch_results:`, !!lookupResponse.data?.company_batch_results);
            
            // 🆕 CHECK: Maybe the response structure is different?
            console.log(`🔍 Checking for alternative response structures:`);
            console.log(`  - Has 'data' key:`, !!lookupResponse.data?.data);
            console.log(`  - Has 'data.company_batch_results':`, !!lookupResponse.data?.data?.company_batch_results);
            console.log(`  - Has 'companies':`, !!lookupResponse.data?.companies);
            console.log(`  - Has 'items':`, !!lookupResponse.data?.items);
            console.log(`  - All top-level keys:`, Object.keys(lookupResponse.data || {}));
            
            // Try alternative response structures
            let alternativeResults = null;
            if (lookupResponse.data?.data?.company_batch_results) {
              alternativeResults = lookupResponse.data.data.company_batch_results;
              console.log(`🔄 Found results in data.data.company_batch_results:`, alternativeResults);
            } else if (lookupResponse.data?.companies) {
              alternativeResults = lookupResponse.data.companies;
              console.log(`🔄 Found results in data.companies:`, alternativeResults);
            } else if (lookupResponse.data?.items) {
              alternativeResults = lookupResponse.data.items;
              console.log(`🔄 Found results in data.items:`, alternativeResults);
            }
            
            if (alternativeResults) {
              console.log(`🔄 Processing ${alternativeResults.length} results from alternative structure`);
              for (const company of companiesNeedingEnrichment) {
                const lookupResult = alternativeResults.find(
                  (r: any) => r.company_name === company.company || r.name === company.company
                );
                console.log(`🔍 Looking for company: ${company.company} in alternative results`);
                console.log(`🔍 Found lookup result:`, lookupResult);
                
                if (lookupResult && lookupResult.items && lookupResult.items.length > 0) {
                  const companyData = lookupResult.items[0];
                  companiesWithIds.push({
                    ...company,
                    growjo_company_id: companyData.company_id,
                    growjo_company_data: companyData
                  });
                  console.log(`✅ Found company data for ${company.company} with company_id ${companyData.company_id} in alternative results`);
                } else {
                  companiesWithoutIds.push(company);
                  console.log(`⚠️ No company data found for ${company.company} in alternative results`);
                }
              }
            }
          }
        } catch (err) {
          console.error("❌ Company lookup failed:", err);
          companiesWithoutIds = companiesNeedingEnrichment; // Fallback to all
          console.log(`🔄 Fallback: All ${companiesNeedingEnrichment.length} companies will go to Apollo due to Growjo companies API failure`);
        }
        
        // 🆕 SAFETY CHECK: If no companies were categorized, force all to Apollo
        if (companiesWithIds.length === 0 && companiesWithoutIds.length === 0) {
          console.log(`⚠️ SAFETY CHECK: No companies were categorized by Growjo companies API!`);
          console.log(`🔄 Forcing all ${companiesNeedingEnrichment.length} companies to Apollo as fallback`);
          companiesWithoutIds = [...companiesNeedingEnrichment];
        }
        
        // 🆕 DEBUG: Log what happened with the Growjo companies API
        console.log(`🔍 Growjo companies API results:`);
        console.log(`  - Total companies needing enrichment: ${companiesNeedingEnrichment.length}`);
        console.log(`  - Companies with IDs (for Growjo): ${companiesWithIds.length}`);
        console.log(`  - Companies without IDs (for Apollo): ${companiesWithoutIds.length}`);
        
        if (companiesWithoutIds.length > 0) {
          console.log(`🔍 Companies that will go to Apollo (no IDs):`);
          companiesWithoutIds.forEach((company, index) => {
            console.log(`  ${index + 1}. ${company.company} (lead_id: ${company.lead_id || 'none'}, website: ${company.website || 'none'})`);
          });
        }
        
                  // Companies without IDs will be processed in the main Apollo flow below
        if (companiesWithoutIds.length > 0) {
          console.log(`📋 ${companiesWithoutIds.length} companies without IDs will be processed in main Apollo flow`);
        }
      }

      // Step 3: Call Growjo API for companies with company_ids
      console.log("🔍 Step 3: Calling Growjo API for companies with company_ids...");
      let growjoResults: any[] = [];
      let companiesStillNeedingEnrichment: any[] = [];

      for (const company of companiesWithIds) {
        try {
          console.log(`🔄 Calling Growjo company API for ${company.company} with company_id: ${company.growjo_company_id}`);
          console.log(`🌐 Endpoint: ${BACKEND_URL}/growjo/company/${company.growjo_company_id}`);
          
          const growjoResponse = await axios.post(
            `${BACKEND_URL}/growjo/company/${company.growjo_company_id}`,
            {},
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );

          if (growjoResponse.data && growjoResponse.data.success) {
            const result = growjoResponse.data.company;
            console.log(`✅ Found company data from Growjo for ${company.company}:`, result);
            
            // Map Growjo data like second enrichment does
            const growjoData = await mapGrowjoCompanyData(result);
            console.log(`🔍 Processing mapped Growjo data for ${company.company}:`, growjoData);
          
          // 🆕 UPDATED: Check only core datapoints (year, revenue, employees)
          const missingCoreFields = [];
          if (!growjoData.year_founded || growjoData.year_founded === "N/A") missingCoreFields.push("year_founded");
          if (!growjoData.revenue || growjoData.revenue === "N/A") missingCoreFields.push("revenue");
          if (!growjoData.employee_count || growjoData.employee_count === "N/A") missingCoreFields.push("employee_count");
          
          const hasCompleteDataAfterGrowjo = missingCoreFields.length === 0;
          
          // 🆕 NEW: Check if we have additional enrichment data
          const hasAdditionalEnrichment = 
            growjoData.product_category && growjoData.product_category !== "N/A" &&
            growjoData.business_type && growjoData.business_type !== "N/A";
          
          console.log(`🔍 Data completeness check for ${company.company}:`);
          console.log(`  - Core datapoints: ${hasCompleteDataAfterGrowjo ? '✅' : '❌'} ${!hasCompleteDataAfterGrowjo ? `(missing: ${missingCoreFields.join(", ")})` : ''}`);
          console.log(`  - Additional enrichment: ${hasAdditionalEnrichment ? '✅' : '❌'}`);
          console.log(`  - Revenue: ${growjoData.revenue || 'missing'}`);
          console.log(`  - Employees: ${growjoData.employee_count || 'missing'}`);
          console.log(`  - Year Founded: ${growjoData.year_founded || 'missing'}`);
          console.log(`  - Website: ${growjoData.website || 'missing'}`);
          console.log(`  - Product Category: ${growjoData.product_category || 'missing'}`);
          console.log(`  - Business Type: ${growjoData.business_type || 'missing'}`);

          if (hasCompleteDataAfterGrowjo) {
            // Growjo successfully enriched this company using mapped data
            const enrichedCompany = {
              ...company,
              // 🆕 UPDATED: Keep original/database values for these fields (no changes)
              city: company.city,
              state: company.state,
              country: company.country,
              industry: company.industry,
              product_category: company.product_category,
              business_type: company.business_type,
              bbb_rating: company.bbb_rating,
              street: company.street,
              
              // 🆕 UPDATED: Apply improved logic for these fields (pick best value)
              revenue: growjoData.revenue || company.revenue,
              employees: (() => {
                if (growjoData.employee_count) {
                  const processedEmployees = processEmployeeRange(growjoData.employee_count);
                  console.log(`📊 Batch enrichment - Growjo employees processed for ${company.company}: "${growjoData.employee_count}" → "${processedEmployees}"`);
                  return processedEmployees;
                }
                return company.employees;
              })(),
              year_founded: growjoData.year_founded || company.year_founded,
              company_linkedin: growjoData.company_linkedin || company.company_linkedin,
              company_phone: growjoData.business_phone || company.company_phone,
              
              // 🆕 UPDATED: Website priority - database first, then fallbacks
              website: company.website || growjoData.website,
              
              // 🆕 UPDATED: Owner info - preserve original when available
              owner_first_name: growjoData.decider_name?.split(' ')[0] || company.owner_first_name,
              owner_last_name: growjoData.decider_name?.split(' ').slice(1).join(' ') || company.owner_last_name,
              owner_title: growjoData.decider_title || company.owner_title,
              owner_email: growjoData.decider_email || company.owner_email,
              owner_phone_number: growjoData.decider_phone || company.owner_phone_number,
              owner_linkedin: growjoData.decider_linkedin || company.owner_linkedin,
              source: "Growjo (Batch API)"
            };

              // 🤖 NEW: Call business type decider BEFORE upload/draft/deduct
              console.log(`🤖 Calling business type decider for Growjo-enriched company: ${company.company}`);
              const products = enrichedCompany.product_category || "";
              const industry = enrichedCompany.industry || company.company || "";
              const businessType = await callBusinessTypeDecider(products, industry);
              enrichedCompany.business_type = businessType;
              console.log(`✅ Updated ${company.company} with business type: ${businessType}`);

              // 🆕 NEW: Immediately process Growjo-enriched companies (upload, draft, credit deduction)
              let lead_id = company.lead_id;
              const basePayload = {
                user_id,
                lead_id,
                company: enrichedCompany.company,
                website: enrichedCompany.website,
                industry: enrichedCompany.industry,
                product_category: enrichedCompany.product_category,
                business_type: enrichedCompany.business_type,
                employees: enrichedCompany.employees,
                revenue: formatRevenueForDisplay(enrichedCompany.revenue),
                year_founded: enrichedCompany.year_founded || "",
                bbb_rating: enrichedCompany.bbb_rating || "",
                street: enrichedCompany.street || "",
                city: enrichedCompany.city,
                state: enrichedCompany.state,
                country: enrichedCompany.country || searchParams.get("country") || "",
                company_phone: enrichedCompany.company_phone || "",
                company_linkedin: enrichedCompany.company_linkedin || "",
                source: enrichedCompany.source,
                contacts: [],
                owner_linkedin: enrichedCompany.owner_linkedin || ""
              };

              // 1. Upload lead
              try {
                const uploadRes = await axios.post(
                  `${DATABASE_URL}/upload_leads`,
                  JSON.stringify([basePayload]),
                  { headers: { "Content-Type": "application/json" }, withCredentials: true }
                );
                const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
                const leadFromResponse = detailedResults[0] || {};
                if (!lead_id && leadFromResponse.lead_id) {
                  lead_id = leadFromResponse.lead_id;
                  basePayload.lead_id = lead_id;
                }
                console.log(`✅ Uploaded Growjo-enriched company ${company.company}`);
              } catch (uploadErr) {
                console.error("❌ Failed to upload Growjo-enriched lead:", basePayload, uploadErr);
              }

              // 2. Create draft
              let draft_id = null;
              try {
                const draftRes = await axios.post(
                  `${DATABASE_URL}/leads/drafts`,
                  {
                    lead_id,
                    draft_data: basePayload,
                    change_summary: "Smart enrichment from Growjo",
                  },
                  {
                    headers: { "Content-Type": "application/json" },
                    withCredentials: true,
                  }
                );
                draft_id = draftRes.data?.draft_id;
                console.log(`✅ Created draft for Growjo-enriched company ${company.company}, draft_id: ${draft_id}`);
              } catch (draftErr) {
                console.error("❌ Failed to create draft for Growjo-enriched company:", draftErr);
              }

              // 3. Deduct credit
              try {
                if (lead_id) {
                  await axios.post(
                    `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                    { type: generateDeductType('first enrichment', 'companies', 'growjo') },
                    { withCredentials: true }
                  );
                  console.log(`✅ Deducted credit for Growjo-enriched company ${company.company}`);
                }
              } catch (deductErr) {
                console.error(`❌ Credit deduction failed for Growjo-enriched lead ${lead_id}`, deductErr);
              }

            growjoResults.push(toCamelCase({ ...enrichedCompany, source_type: "scraped", draft_id }));
            console.log(`✅ ${company.company} successfully enriched via Growjo and processed`);
          } else {
            // Growjo didn't fill all missing data, still needs enrichment
            companiesStillNeedingEnrichment.push(company);
            console.log(`⚠️ ${company.company} still needs enrichment after Growjo API call`);
          }
          } else {
            // Growjo API call failed or returned no data
            companiesStillNeedingEnrichment.push(company);
            console.log(`⚠️ ${company.company} - Growjo API call failed or returned no data`);
          }
        } catch (err) {
          console.error(`❌ Error calling Growjo API for ${company.company}:`, err);
          companiesStillNeedingEnrichment.push(company);
        }
      }

      // Add companies without company_ids to the list needing enrichment
      // This ensures Apollo is called for ALL companies that need enrichment, regardless of lead_id status
      companiesStillNeedingEnrichment = [...companiesStillNeedingEnrichment, ...companiesWithoutIds];

      // Step 4: Call Apollo API for remaining companies (ensuring Apollo is always called as fallback)
      // Apollo is the final fallback - it will be called for ALL companies that still need enrichment,
      // regardless of whether they have lead_id or whether the Growjo companies API worked
      console.log("🔍 Step 4: Calling Apollo API for remaining companies...");
      console.log(`📊 Companies still needing enrichment: ${companiesStillNeedingEnrichment.length}`);
      console.log(`📊 Companies with lead_id: ${companiesStillNeedingEnrichment.filter(c => c.lead_id).length}`);
      console.log(`📊 Companies without lead_id: ${companiesStillNeedingEnrichment.filter(c => !c.lead_id).length}`);
      
      // 🆕 DEBUG: Log each company that will be processed by Apollo
      console.log("🔍 Companies to be processed by Apollo:");
      companiesStillNeedingEnrichment.forEach((company, index) => {
        console.log(`  ${index + 1}. ${company.company} (lead_id: ${company.lead_id || 'none'}, website: ${company.website || 'none'})`);
      });
      
      // 🆕 DEBUG: Log the backend URL being used
      console.log(`🌐 Backend URL: ${BACKEND_URL}`);
      console.log(`🌐 Full Apollo endpoint: ${DATABASE_URL}/apollo/enrich/apollo-enrich-company or ${DATABASE_URL}/apollo/enrich/apollo-search-company`);
      
      let apolloResults: any[] = [];
      
      // 🆕 DEBUG: Check if we actually have companies to process
      if (companiesStillNeedingEnrichment.length === 0) {
        console.log("⚠️ WARNING: companiesStillNeedingEnrichment is empty! This means no companies will be processed by Apollo.");
        console.log("🔍 Debug info:");
        console.log("  - companiesWithIds length:", companiesWithIds.length);
        console.log("  - companiesWithoutIds length:", companiesWithoutIds.length);
        console.log("  - companiesStillNeedingEnrichment length:", companiesStillNeedingEnrichment.length);
      } else {
        console.log(`✅ Proceeding with Apollo enrichment for ${companiesStillNeedingEnrichment.length} companies`);
      }

      for (const company of companiesStillNeedingEnrichment) {
        try {
          // Log whether this company has lead_id or not
          if (!company.lead_id) {
            console.log(`🔄 Calling Apollo for company without lead_id: ${company.company}`);
          } else {
            console.log(`🔄 Calling Apollo for company with lead_id: ${company.company} (${company.lead_id})`);
          }
          
          // 🆕 FIXED: Handle companies without website (common for companies without lead_id)
          let website = company.website || "";
          let domain = "";
          
          if (website && website.trim() !== "" && website !== "N/A") {
            // Company has a website, extract domain
            let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
            domain = normalizeWebsite(cleanDomain);
            console.log(`🌐 Using website for ${company.company}: ${website} → domain: ${domain}`);
          } else {
            // Company has no website, use company name for Apollo enrichment
            // Apollo can still enrich company data even without a domain
            domain = "";
            console.log(`⚠️ No website for ${company.company}, will search by company name first`);
          }
          
          // 🆕 DEBUG: Log the exact payload being sent to Apollo
          const apolloPayload = { 
            domain: domain || undefined, // Only send domain if we have one
            organization_name: company.company // Pass company name for better Apollo enrichment
          };
          console.log(`🚀 Calling Apollo API for ${company.company}`);
          console.log(`🌐 Apollo endpoint: ${DATABASE_URL}/apollo/enrich/apollo-enrich-company or ${DATABASE_URL}/apollo/enrich/apollo-search-company`);
          
          const apollo = await apolloEnrichCompany(company);
          
          console.log(`✅ Apollo API call completed for ${company.company}. Response:`, apollo);

          if (!apollo || Object.keys(apollo).length === 0) {
            setHasErrors(true);
            hasErrorsRef.current = true;
            showNotification(`No data found for ${company.company} in Apollo. Skipping this company.`, "error");
            continue;
          }
          const enrichmentData = buildEnrichedCompany({ ...company, website }, {}, apollo, {}, revenueMap);
          
          // 🤖 NEW: Call business type decider BEFORE upload/draft/deduct
          console.log(`🤖 Calling business type decider for Apollo-enriched company: ${company.company}`);
          const products = enrichmentData.productCategory || "";
          const industry = enrichmentData.industry || company.company || "";
          const businessType = await callBusinessTypeDecider(products, industry);
          enrichmentData.businessType = businessType;
          console.log(`✅ Updated ${company.company} with business type: ${businessType}`);
          
          // Create payload and upload
          let lead_id = company.lead_id;
          const basePayload = {
            user_id,
            lead_id,
            company: enrichmentData.company,
            website: enrichmentData.website,
            industry: enrichmentData.industry,
            product_category: enrichmentData.productCategory || "",
            business_type: enrichmentData.businessType || "",
            employees: enrichmentData.employees || "",
            revenue: formatRevenueForDisplay(enrichmentData.revenue || ""),
            year_founded: enrichmentData.yearFounded || "",
            bbb_rating: enrichmentData.bbbRating || "",
            street: enrichmentData.street || "",
            city: enrichmentData.city || "",
            state: enrichmentData.state || "",
            country: enrichmentData.country || "",
            company_phone: enrichmentData.companyPhone || "",
            company_linkedin: enrichmentData.companyLinkedin || "",
            source: enrichmentData.source,
            contacts: [],
            owner_linkedin: ""
          };

          // Upload lead
          try {
            const uploadRes = await axios.post(
              `${DATABASE_URL}/upload_leads`,
              JSON.stringify([basePayload]),
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
            const leadFromResponse = detailedResults[0] || {};
            if (!lead_id && leadFromResponse.lead_id) {
              lead_id = leadFromResponse.lead_id;
              basePayload.lead_id = lead_id;
            }
          } catch (uploadErr) {
            console.error("❌ Failed to upload lead:", basePayload, uploadErr);
          }

          // Create draft
          let draft_id = null;
          try {
            const draftRes = await axios.post(
              `${DATABASE_URL}/leads/drafts`,
              {
                lead_id,
                draft_data: basePayload,
                change_summary: "Smart enrichment from Apollo",
              },
              {
                headers: { "Content-Type": "application/json" },
                withCredentials: true,
              }
            );
            draft_id = draftRes.data?.draft_id;
            console.log(`✅ Created draft for Apollo-enriched company ${basePayload.company}, draft_id: ${draft_id}`);
          } catch (draftErr) {
            console.error("❌ Failed to create draft:", draftErr);
          }

          // Deduct credit
          try {
            if (lead_id) {
              await axios.post(
                `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                { type: generateDeductType('first enrichment', 'companies', 'apollo') },
                { withCredentials: true }
              );
            }
          } catch (deductErr) {
            console.error(`❌ Credit deduction failed for lead ${lead_id}`, deductErr);
          }

          apolloResults.push(toCamelCase({ ...basePayload, source_type: "scraped", draft_id }));
          console.log(`✅ ${company.company} enriched via Apollo`);

        } catch (err: any) {
          // 🆕 DEBUG: Log detailed error information
          console.error(`❌ Apollo API call failed for ${company.company}:`, err);
          console.error(`❌ Error details:`, {
            message: err.message,
            response: err.response?.data,
            status: err.response?.status,
            statusText: err.response?.statusText
          });
          
          if (err.response && err.response.data && err.response.data.error) {
            // Handle different types of Apollo errors with more informative messages
            if (err.response.data.error.includes("Status 422")) {
              showNotification(`Apollo service temporarily unavailable for ${company.company}. Please try again later.`, "error");
            } else if (err.response.data.error.includes("No company found")) {
              showNotification(`No company found in Apollo for ${company.company}. This company may not be in their database.`, "error");
            } else if (err.response.data.error.includes("Rate limit")) {
              showNotification(`Apollo rate limit exceeded. Please wait a moment and try again.`, "error");
            } else {
              showNotification(`Apollo error for ${company.company}: ${err.response.data.error}`, "error");
            }
            continue;
          }
          showNotification(`Failed to reach Apollo for ${company.company}. Please try again later.`, "error");
          continue;
        }
      }

      // NEW: Process companies with complete data through upload/draft/deduct flow
      console.log("🔍 Step 5: Processing companies with complete data through upload/draft/deduct flow...");
      let completeDataResults: any[] = [];
      
      for (const company of companiesWithCompleteData) {
        try {
          console.log(`🔄 Processing company with complete data: ${company.company}`);
          
          // Get the database data for this company (match by lead_id OR company name for companies without lead_id)
          const dbLead = completeDataDbLeads.find((l: any) => 
            l.lead_id === company.lead_id || 
            (company.lead_id ? false : l.company?.toLowerCase() === company.company?.toLowerCase())
          );
          
          console.log(`🔍 Complete data matching for "${company.company}" (lead_id: ${company.lead_id || 'none'}):`, {
            found: !!dbLead,
            dbLead: dbLead ? { company: dbLead.company, lead_id: dbLead.lead_id } : null,
            availableDbLeads: completeDataDbLeads.map((l: any) => ({ company: l.company, lead_id: l.lead_id }))
          });
          
          if (!dbLead) {
            console.log(`⚠️ No database data found for ${company.company}, skipping`);
            continue;
          }
          
          // 🤖 NEW: Check if business_type already exists, if not call business type decider
          let businessType = dbLead.business_type || dbLead.businessType || "";
          if (!businessType || businessType === "N/A" || businessType.trim() === "") {
            console.log(`🤖 Calling business type decider for database-enriched company: ${company.company} (no existing business_type)`);
            const products = dbLead.product_category || dbLead.productCategory || "";
            const industry = dbLead.industry || company.company || "";
            businessType = await callBusinessTypeDecider(products, industry);
            console.log(`✅ Updated ${company.company} with business type: ${businessType}`);
          } else {
            console.log(`✅ ${company.company} already has business type: ${businessType}, skipping API call`);
          }

          let lead_id = company.lead_id;
          const basePayload = {
            id: company.id, // Preserve the original ID to avoid duplication
            user_id,
            lead_id,
            company: dbLead.company,
            website: dbLead.website,
            industry: dbLead.industry,
            product_category: dbLead.product_category || dbLead.productCategory || "",
            business_type: businessType,
            employees: dbLead.employees || "",
            revenue: formatRevenueForDisplay(dbLead.revenue || ""),
            year_founded: dbLead.year_founded || dbLead.yearFounded || "",
            bbb_rating: dbLead.bbb_rating || dbLead.bbbRating || "",
            street: dbLead.street || "",
            city: dbLead.city || "",
            state: dbLead.state || "",
            country: dbLead.country || "",
            company_phone: dbLead.company_phone || dbLead.companyPhone || dbLead.business_phone || "",
            company_linkedin: dbLead.company_linkedin || dbLead.companyLinkedin || "",
            source: "Database (Complete Data)",
            contacts: [],
            owner_linkedin: ""
          };

          // 1. Upload lead
          try {
            const uploadRes = await axios.post(
              `${DATABASE_URL}/upload_leads`,
              JSON.stringify([basePayload]),
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
            const leadFromResponse = detailedResults[0] || {};
            if (!lead_id && leadFromResponse.lead_id) {
              lead_id = leadFromResponse.lead_id;
              basePayload.lead_id = lead_id;
            }
            console.log(`✅ Uploaded company with complete data: ${company.company}`);
          } catch (uploadErr) {
            console.error("❌ Failed to upload company with complete data:", basePayload, uploadErr);
          }

          // 2. Create draft
          try {
            await axios.post(
              `${DATABASE_URL}/leads/drafts`,
              {
                lead_id,
                draft_data: basePayload,
                change_summary: "Company enrichment (complete data from database)",
              },
              {
                headers: { "Content-Type": "application/json" },
                withCredentials: true,
              }
            );
            console.log(`✅ Created draft for company with complete data: ${company.company}`);
          } catch (draftErr) {
            console.error("❌ Failed to create draft for company with complete data:", draftErr);
          }

          // 3. Deduct credit
          try {
            if (lead_id) {
              await axios.post(
                `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                { type: generateDeductType('first enrichment', 'companies', 'db') },
                { withCredentials: true }
              );
              console.log(`✅ Deducted credit for company with complete data: ${company.company}`);
            }
          } catch (deductErr) {
            console.error(`❌ Credit deduction failed for company with complete data ${lead_id}`, deductErr);
          }

          completeDataResults.push(toCamelCase({ ...basePayload, source_type: "database" }));
          console.log(`✅ ${company.company} processed through upload/draft/deduct flow`);
          
        } catch (err) {
          console.error(`❌ Failed to process company with complete data ${company.company}:`, err);
        }
      }

      // Update results - combine database, Growjo, Apollo, and complete data results
      // Filter out any duplicates between dbRows and completeDataResults
      const uniqueCompleteDataResults = completeDataResults.filter(completeCompany => 
        !dbRows.some(dbCompany => dbCompany.company === completeCompany.company)
      );
      
      // 🆕 FIXED: Append results instead of replacing to allow cumulative enrichment
      // This allows users to add more companies to existing results
      setDbEnrichedCompanies(prev => {
        const newResults = [...dbRows, ...uniqueCompleteDataResults];
        // Filter out duplicates based on company name to prevent adding the same company twice
        const existingCompanies = new Set(prev.map(company => company.company));
        const uniqueNewResults = newResults.filter(company => !existingCompanies.has(company.company));
        return [...prev, ...uniqueNewResults];
      });
      
      setScrapedEnrichedCompanies(prev => {
        const newResults = [...growjoResults, ...apolloResults];
        // Filter out duplicates based on company name
        const existingCompanies = new Set(prev.map(company => company.company));
        const uniqueNewResults = newResults.filter(company => !existingCompanies.has(company.company));
        return [...prev, ...uniqueNewResults];
      });
      setFirstEnrichmentType("company");
      setHasFirstEnrichment(true);

      setShowResults(true);
      setHasEnrichedOnce(true);
      
      // Set initial enrichment type if not already set
      if (!initialEnrichmentType) {
        setInitialEnrichmentType("company");
      }

      // Check for empty results and show banner if needed
      const hasEmptyResults = checkForEmptyResults("company", [...dbRows, ...uniqueCompleteDataResults], [...growjoResults, ...apolloResults]);
      
      // Show success notification only if we have results
      if ((growjoResults.length > 0 || apolloResults.length > 0 || uniqueCompleteDataResults.length > 0 || dbRows.length > 0) && !hasErrorsRef.current) {
        showNotification("Smart company enrichment completed successfully!");
      } else if (hasEmptyResults) {
        // Show error notification for complete failure
        showNotification("Enrichment completed but no results were found. Check the banner above for details.", "error");
      }

      // 🆕 SUMMARY: This enrichment function ensures maximum data coverage through fallback mechanisms:
      // 1. Companies without lead_id → Always processed by Apollo as fallback
      // 2. Companies where Growjo companies API failed → Always processed by Apollo as fallback
      // 3. Companies where Growjo failed → Always processed by Apollo as fallback
      // 4. Apollo is the final safety net that ensures no company is left unenriched
      // 5. 🆕 NEW: Companies with complete data → Always processed through upload/draft/deduct flow
      // 
      // 🆕 KEY FIX: Companies without websites are now properly handled:
      // - Website field is safely extracted with fallback to empty string
      // - Apollo API calls work even without domain (uses company name)
      // - Validation is more lenient for companies without websites
      //
      // 🆕 KEY FIX: ALL companies now go through upload/draft/deduct flow regardless of data completeness

    } catch (err) {
      console.error("Smart enrichment failed:", err);
      showNotification("Smart enrichment failed. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  };

  // Helper functions for dropdown enrichment (keeping for now but will be replaced)
  const handleStartEnrichmentDropdown = (type: "company" | "people" | "both", dataSource?: "growjo" | "apollo" | "both") => {
    // Restrict enrich people and enrich both to non-free tier users
    // if ((type === "people" || type === "both") && isFreeTierUser()) {
    //   showNotification("Enrich People and Enrich Both are only available for paid plans or team members. Please upgrade your plan or join a team.", "error");
    //   return;
    // }
    
      // 🆕 CLEAR RESULTS: Clear previous enrichment results when switching types
  // This ensures that when switching between enrichment types, previous results are cleared
  // so users only see results relevant to their current enrichment type
  if (type === "people") {
    // Clear company results when switching to people enrichment
    console.log("🧹 Clearing company results - switching to people enrichment");
    setDbEnrichedCompanies([]);
    setScrapedEnrichedCompanies([]);
    setEnrichedCompanies([]);
    setShowResults(false);
    setHasEnrichedOnce(false);
  } else if (type === "company") {
    // Clear people results when switching to company enrichment
    console.log("🧹 Clearing people results - switching to company enrichment");
    setDbPeopleResults([]);
    setScrapedPeopleResults([]);
    setEnrichedCompanies([]);
    setShowResults(false);
    setHasEnrichedOnce(false);
  } else if (type === "both") {
    // Clear all results when switching to both enrichment
    console.log("🧹 Clearing all results - switching to both enrichment");
    setDbEnrichedCompanies([]);
    setDbPeopleResults([]);
    setScrapedPeopleResults([]);
    setEnrichedCompanies([]);
    setShowResults(false);
    setHasEnrichedOnce(false);
  }
    
    setEnrichmentType(type);
    setEnrichmentViewType(type);
    if (dataSource) {
      setSelectedDataSource(dataSource);
    }
    // Pass dataSource directly to handleStartEnrichment
    handleStartEnrichment(false, null, dataSource);
  };

  // Add state to track people enrichment results by source
  const [dbPeopleResults, setDbPeopleResults] = useState<any[]>([]);
  const [scrapedPeopleResults, setScrapedPeopleResults] = useState<any[]>([]);
  const [peopleFromDatabase, setPeopleFromDatabase] = useState<string[]>([]); // lowercase company names

  // 🆕 NEW: Clear result functions
  const clearFirstEnrichmentResults = () => {
    console.log("🧹 Clearing first enrichment results...");
    
    // Clear first enrichment state
    setDbEnrichedCompanies([]);
    setScrapedEnrichedCompanies([]);
    setHasFirstEnrichment(false);
    setFirstEnrichmentType(null);
    
    // Clear people results if they exist
    setDbPeopleResults([]);
    setScrapedPeopleResults([]);
    setPeopleFromDatabase([]);
    
    // Clear selection states
    setSelectedEnrichedResults([]);
    setSelectedEnrichedPeople([]);
    
    // Clear banner states
    setShowEmptyResultsBanner(false);
    setShowNotFoundBanner(false);
    setNotFoundCompanies([]);
    
    // Clear enriched companies from context
    setEnrichedCompanies([]);
    
    showNotification("First enrichment results cleared successfully!", "success");
  };

  const clearSecondEnrichmentResults = () => {
    console.log("🧹 Clearing second enrichment results...");
    
    // Clear second enrichment state
    setSecondDbEnrichedCompanies([]);
    setSecondScrapedEnrichedCompanies([]);
    setSecondEnrichmentResults([]);
    setHasSecondEnrichment(false);
    setShowSecondEnrichmentResults(false);
    setSecondEnrichmentType(null);
    
    // Clear selection states
    setSelectedEnrichedResults([]);
    setSelectedEnrichedPeople([]);
    
    showNotification("Second enrichment results cleared successfully!", "success");
  };

  // New state for tracking not found companies during re-enrichment
  const [notFoundCompanies, setNotFoundCompanies] = useState<string[]>([]);
  const [showNotFoundBanner, setShowNotFoundBanner] = useState(false);
  
  // State for tracking empty results and fallback status
  const [showEmptyResultsBanner, setShowEmptyResultsBanner] = useState(false);
  const [emptyResultsInfo, setEmptyResultsInfo] = useState({
    hasDatabaseResults: false,
    hasScrapedResults: false,
    totalCompanies: 0,
    enrichmentType: "company" as "company" | "people" | "both"
  });

  // --- REFACTOR: Helper for DB enrichment flow ---
  async function enrichFromDatabase(
    company: any,
    user_id: any,
    enrichmentType: any,
    dataSource: any
  ) {
    // 1. Call DB API
    let dbLead = null;
    try {
      const dbLeads = await fetchCompaniesWithFallback([company.lead_id], [company.company]);
      dbLead = dbLeads.find((l: any) => l.lead_id === company.lead_id) || null;
    } catch (err) {
      console.error("❌ Failed to fetch from DB for lead_id", company.lead_id, err);
      return null;
    }
    if (!dbLead) return null;

    // 2. Call drafts API
    try {
      await axios.post(
        `${DATABASE_URL}/leads/drafts`,
        {
          lead_id: company.lead_id,
          draft_data: dbLead,
          change_summary: "Restored from DB",
        },
        {
          headers: { "Content-Type": "application/json" },
          withCredentials: true,
        }
      );
    } catch (err) {
      console.error("❌ Failed to create draft for DB lead:", err);
    }

    // 3. Call deduct credit API
    try {
      await axios.post(
        `${DATABASE_URL}/user/deduct_credit/${company.lead_id}`,
        { type: generateDeductType('first enrichment', 'companies', 'db') },
        { withCredentials: true }
      );
    } catch (err) {
      console.error(`❌ Credit deduction failed for DB lead ${company.lead_id}`, err);
    }

    // 4. Track this company as coming from database
    setFromDatabaseLeads(prev => [...prev, company.company.toLowerCase()]);

    // 5. If this is a "both" enrichment type and we have contacts, return them as people
    if (enrichmentType === "both" && Array.isArray(dbLead.contacts) && dbLead.contacts.length > 0) {
      // Convert contacts to people format for display - keep the original contact structure
      const people = dbLead.contacts.map((contact: any, idx: number) => ({
        id: `${dbLead.lead_id || dbLead.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        // Keep the original contact structure that the display logic expects
        owner_first_name: contact.owner_first_name || '',
        owner_last_name: contact.owner_last_name || '',
        owner_title: contact.owner_title || '',
        owner_email: contact.owner_email || '',
        owner_phone_number: contact.owner_phone_number || '',
        owner_linkedin: contact.owner_linkedin || '',
        // Also include the flattened format for compatibility
        name: `${contact.owner_first_name || ''} ${contact.owner_last_name || ''}`.trim(),
        title: contact.owner_title || '',
        email: contact.owner_email || '',
        phone: contact.owner_phone_number || dbLead.phone || '',
        linkedin: contact.owner_linkedin || '',
        company: dbLead.company,
        website: dbLead.website,
        industry: dbLead.industry,
        sourceType: "database"
      }));

      // Return the first contact as the main company record, but also include people array
      return {
        ...dbLead,
        people: people
      };
    }

    return dbLead;
  }

  // --- REFACTOR: Helper for enrichment+upload flow ---
  async function enrichAndUpload(
    company: any,
    user_id: any,
    enrichmentType: any,
    dataSource: any
  ) {
    let enrichmentData: any = {};
    let website = company.website;

    if (enrichmentType === "both") {
      let growjo = {}, apollo = {}, people: any[] = [];
      // --- Company enrichment ---
      if (dataSource === "apollo") {
        let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        const domain = normalizeWebsite(cleanDomain);
        try {
          const apollo = await apolloEnrichCompany(company);
          if (!apollo || Object.keys(apollo).length === 0) {
            setHasErrors(true); // Set error flag
            hasErrorsRef.current = true; // Set ref immediately
            showNotification(`No data found for ${company.company} in Apollo. Skipping this company.`, "error");
            return null;
          }
        } catch (err: any) {
          if (err.response && err.response.data && err.response.data.error && err.response.data.error.includes("Status 422")) {
            showNotification(`Apollo returned error 422 for ${company.company}. Apollo service may be temporarily unavailable.`, "error");
            return null;
          }
          showNotification(`Failed to reach Apollo for ${company.company}. Please try again later.`, "error");
          return null;
        }
      } else if (dataSource === "both") {
        let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        const domain = normalizeWebsite(cleanDomain);
        try {
          const apollo = await apolloEnrichCompany(company);
          if (!apollo || Object.keys(apollo).length === 0) {
            setHasErrors(true); // Set error flag
            hasErrorsRef.current = true; // Set ref immediately
            showNotification(`No data found for ${company.company} in Apollo. Skipping this company.`, "error");
            return null;
          }
        } catch (err: any) {
          if (err.response && err.response.data && err.response.data.error) {
            // Handle different types of Apollo errors with more informative messages
            if (err.response.data.error.includes("Status 422")) {
              showNotification(`Apollo service temporarily unavailable for ${company.company}. Please try again later.`, "error");
            } else if (err.response.data.error.includes("No company found")) {
              showNotification(`No company found in Apollo for ${company.company}. This company may not be in their database.`, "error");
            } else if (err.response.data.error.includes("Rate limit")) {
              showNotification(`Apollo rate limit exceeded for ${company.company}. Please wait a moment and try again.`, "error");
            } else {
              showNotification(`Apollo error for ${company.company}: ${err.response.data.error}`, "error");
            }
            return null;
          }
          showNotification(`Failed to reach Apollo for ${company.company}. Please try again later.`, "error");
          return null;
        }
      }

      if (dataSource === "apollo" || dataSource === "both") {
        try {
          let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
          const domain = normalizeWebsite(cleanDomain);
          const res = await axios.post(`${DATABASE_URL}/apollo/enrich/apollo-scrape-people-enhancement`, { domain }, { withCredentials: true });
          if (res.data.people && Array.isArray(res.data.people) && res.data.people.length > 0) {
            people = people.concat(res.data.people);
          }
        } catch (err) {
          console.error(`❌ Apollo people enrichment failed for ${company.company}:`, err);
        }
      }
      // Deduplicate people by name
      const seenNames = new Set();
      const contacts = people.filter(person => {
        const name = person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim();
        if (seenNames.has(name.toLowerCase())) return false;
        seenNames.add(name.toLowerCase());
        return true;
      }).map((person: any) => ({
        owner_first_name: person.name?.split(' ')[0] || person.first_name || "",
        owner_last_name: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
        owner_title: person.title || "",
        owner_email: person.email || "",
        owner_phone_number: person.phone || person.phone_number || "",
        owner_linkedin: person.linkedin || person.linkedin_url || ""
      }));
      // --- Build merged enrichmentData ---
      enrichmentData = buildEnrichedCompany({ ...company, website }, growjo, apollo, {}, revenueMap);
      // --- Always use the correct payload format ---
      let lead_id = company.lead_id;
      const basePayload = {
        user_id,
        lead_id,
        company: enrichmentData.company,
        website: enrichmentData.website,
        industry: enrichmentData.industry,
        product_category: enrichmentData.productCategory || "",
        business_type: enrichmentData.businessType || "",
        employees: enrichmentData.employees || "",
        revenue: formatRevenueForDisplay(enrichmentData.revenue || ""),
        year_founded: enrichmentData.yearFounded || "",
        bbb_rating: enrichmentData.bbbRating || "",
        street: enrichmentData.street || "",
        city: enrichmentData.city || "",
        state: enrichmentData.state || "",
        country: enrichmentData.country || "",
        company_phone: enrichmentData.companyPhone || "",
        company_linkedin: enrichmentData.companyLinkedin || "",
        source: enrichmentData.source,
        contacts: contacts,
        owner_linkedin: contacts[0]?.owner_linkedin || enrichmentData.ownerLinkedin || ""
      };
      const uploadPayload = basePayload;
      try {
        const uploadRes = await axios.post(
          `${DATABASE_URL}/upload_leads`,
          JSON.stringify([uploadPayload]),
          { headers: { "Content-Type": "application/json" }, withCredentials: true }
        );
        const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
        const leadFromResponse = detailedResults[0] || {};
        if (!lead_id && leadFromResponse.lead_id) {
          lead_id = leadFromResponse.lead_id;
          uploadPayload.lead_id = lead_id;
        }
      } catch (uploadErr) {
        console.error("❌ Failed to upload lead:", uploadPayload, uploadErr);
      }
      // 3. Call drafts API
      try {
        await axios.post(
          `${DATABASE_URL}/leads/drafts`,
          {
            lead_id,
            draft_data: uploadPayload,
            change_summary: "Initial enrichment draft",
          },
          {
            headers: { "Content-Type": "application/json" },
            withCredentials: true,
          }
        );
      } catch (draftErr) {
        console.error("❌ Failed to create draft:", draftErr);
      }
      // 4. Call deduct credit API
      try {
        if (lead_id) {
          await axios.post(
            `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
            { type: generateDeductType('first enrichment', 'people', dataSource) },
            { withCredentials: true }
          );
        }
      } catch (deductErr) {
        console.error(`❌ Credit deduction failed for lead ${lead_id}`, deductErr);
      }
      return { ...uploadPayload, lead_id, people: contacts };
    } else if (enrichmentType === "company") {
      let growjo = {}, apollo = {};
      if (dataSource === "apollo") {
        let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        const domain = normalizeWebsite(cleanDomain);
        const apollo = await apolloEnrichCompany(company);
        // Check if Apollo returned any data at all
        if (!apollo || Object.keys(apollo).length === 0) {
          setHasErrors(true); // Set error flag
          showNotification(`No data found for ${company.company} in Apollo. Skipping this company.`, "error");
          return null;
        }
      } else if (dataSource === "both") {
        let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        const domain = normalizeWebsite(cleanDomain);
        const apollo = await apolloEnrichCompany(company);
        // Check if Apollo returned any data at all
        if (!apollo || Object.keys(apollo).length === 0) {
          setHasErrors(true); // Set error flag
          showNotification(`No data found for ${company.company} in Apollo. Skipping this company.`, "error");
          return null;
        }
      }
      enrichmentData = buildEnrichedCompany({ ...company, website }, growjo, apollo, {}, revenueMap);
      // --- Always use the correct payload format ---
      let lead_id = company.lead_id;
      const basePayload = {
        user_id,
        lead_id,
        company: enrichmentData.company,
        website: enrichmentData.website,
        industry: enrichmentData.industry,
        product_category: enrichmentData.productCategory || "",
        business_type: enrichmentData.businessType || "",
        employees: enrichmentData.employees || "",
        revenue: formatRevenueForDisplay(enrichmentData.revenue || ""),
        year_founded: enrichmentData.yearFounded || "",
        bbb_rating: enrichmentData.bbbRating || "",
        street: enrichmentData.street || "",
        city: enrichmentData.city || "",
        state: enrichmentData.state || "",
        country: enrichmentData.country || "",
        company_phone: enrichmentData.companyPhone || "",
        company_linkedin: enrichmentData.companyLinkedin || "",
        source: enrichmentData.source,
        contacts: [],
        owner_linkedin: ""
      };
      const uploadPayload = basePayload;
      try {
        const uploadRes = await axios.post(
          `${DATABASE_URL}/upload_leads`,
          JSON.stringify([uploadPayload]),
          { headers: { "Content-Type": "application/json" }, withCredentials: true }
        );
        const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
        const leadFromResponse = detailedResults[0] || {};
        if (!lead_id && leadFromResponse.lead_id) {
          lead_id = leadFromResponse.lead_id;
          uploadPayload.lead_id = lead_id;
        }
      } catch (uploadErr) {
        console.error("❌ Failed to upload lead:", uploadPayload, uploadErr);
      }
      // 3. Call drafts API
      try {
        await axios.post(
          `${DATABASE_URL}/leads/drafts`,
          {
            lead_id,
            draft_data: uploadPayload,
            change_summary: "Initial enrichment draft",
          },
          {
            headers: { "Content-Type": "application/json" },
            withCredentials: true,
          }
        );
      } catch (draftErr) {
        console.error("❌ Failed to create draft:", draftErr);
      }
      // 4. Call deduct credit API
      try {
        if (lead_id) {
          await axios.post(
            `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
            { type: generateDeductType('first enrichment', 'companies', dataSource) },
            { withCredentials: true }
          );
        }
      } catch (deductErr) {
        console.error(`❌ Credit deduction failed for lead ${lead_id}`, deductErr);
      }
      return { ...uploadPayload, lead_id, people: [] };
    }
  }

  const handlePeopleEnrichment = async (dataSource: "growjo" | "apollo" | "both") => {
    console.log(`🚀 Starting People Enrichment with data source: ${dataSource}`);
    
    // Restrict enrich people and enrich both to non-free tier users
    // if (isFreeTierUser()) {
    //   showNotification("Enrich People is only available for paid plans or team members. Please upgrade your plan or join a team.", "error");
    //   return;
    // }
    const user = JSON.parse(sessionStorage.getItem("user") || "{}");
    setSelectedDataSource(dataSource);
    setEnrichmentType("people");
    setEnrichmentViewType("people");
    setShowPeopleResults(true);
    setLoading(true);

    // 🆕 NEW: Clear previous banner state when starting new enrichment
    setShowEmptyResultsBanner(false);
    setEmptyResultsInfo({
      hasDatabaseResults: false,
      hasScrapedResults: false,
      totalCompanies: 0,
      enrichmentType: "people"
    });

    // 🆕 NEW: Initialize local variable to track not found companies
    let notFoundCompaniesList: string[] = [];

    // Reset results and views
    setDbPeopleResults([]);
    setScrapedPeopleResults([]);
    setPeopleFromDatabase([]);

    // Get selected companies
    const selected = normalizedLeads.filter(c => selectedCompanies.includes(c.id));
    console.log("🔍 Selected companies for people enrichment:", selected);

    let allPeople: any[] = [];
    let companiesToScrape: typeof selected = [];

    // --- New: DB/upload/draft/credit flow for each company ---
    let dbCompanyNames: string[] = [];
    let dbPeople: any[] = [];
    let companiesToScrapeArr: typeof selected = [];
    
    // 🆕 NEW: Initialize companiesWithPeople array for all companies (DB + scraped)
    let companiesWithPeople: any[] = [];

    // --- Instead of /api/contacts/all, use multiple_leads API ---
    const leadIds = selected.map(c => c.lead_id).filter((id): id is string => Boolean(id));
    const companyNames = selected.map(c => c.company).filter((name): name is string => Boolean(name));
    
    // Always try database lookup, even with empty leadIds (will use search_companies)
    try {
      const dbLeads = await fetchCompaniesWithFallback(leadIds, companyNames);
      for (const company of selected) {
        // For companies without lead_id, try to find by company name
        const dbLead = dbLeads.find((l: any) => 
          l.lead_id === company.lead_id || 
          (company.lead_id ? false : l.company === company.company)
        );
          if (dbLead) {
            // Map people/contacts from dbLead
            if (Array.isArray(dbLead.people) && dbLead.people.length > 0) {
              const mappedPeople = dbLead.people.map((p: any, idx: number) => ({
                ...p,
                company: dbLead.company,
                website: dbLead.website,
                industry: dbLead.industry,
                id: p.id || `${dbLead.lead_id || dbLead.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                sourceType: "database"
              }));
              dbPeople = dbPeople.concat(mappedPeople);
              dbCompanyNames.push(company.company.toLowerCase());
              
              // 🆕 NEW: Also process database companies through upload/draft/credit flow
              const contacts = mappedPeople.map((person: any) => ({
                owner_first_name: person.name?.split(' ')[0] || person.first_name || "",
                owner_last_name: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
                owner_title: person.title || "",
                owner_email: person.email || "",
                owner_phone_number: person.phone || person.phone_number || "",
                owner_linkedin: person.linkedin || person.linkedin_url || ""
              }));
              
              const companyData = {
                user_id: user.user_id || "",
                lead_id: company.lead_id || "",
                company: dbLead.company,
                website: dbLead.website,
                industry: dbLead.industry,
                owner_linkedin: (contacts[0]?.owner_linkedin) || dbLead.owner_linkedin || "N/A",
                source: "Database",
                contacts: contacts
              };
              
              // Add to companies that need processing
              companiesWithPeople.push(companyData);
            } else if (
              dbLead.owner_first_name ||
              dbLead.owner_last_name ||
              dbLead.owner_email ||
              dbLead.owner_title ||
              dbLead.owner_phone_number ||
              dbLead.owner_linkedin
            ) {
              const ownerPerson = {
                name: `${dbLead.owner_first_name || ''} ${dbLead.owner_last_name || ''}`.trim(),
                title: dbLead.owner_title || '',
                email: dbLead.owner_email || '',
                phone: dbLead.owner_phone_number || dbLead.phone || '',
                linkedin: dbLead.owner_linkedin || '',
                company: dbLead.company,
                website: dbLead.website,
                industry: dbLead.industry,
                id: `${dbLead.lead_id || dbLead.id}-owner`,
                sourceType: "database"
              };
              dbPeople.push(ownerPerson);
              dbCompanyNames.push(company.company.toLowerCase());
              
              // 🆕 NEW: Also process database companies with owner data through upload/draft/credit flow
              const contacts = [{
                owner_first_name: dbLead.owner_first_name || "",
                owner_last_name: dbLead.owner_last_name || "",
                owner_title: dbLead.owner_title || "",
                owner_email: dbLead.owner_email || "",
                owner_phone_number: dbLead.owner_phone_number || "",
                owner_linkedin: dbLead.owner_linkedin || ""
              }];
              
              const companyData = {
                user_id: user.user_id || "",
                lead_id: company.lead_id || "",
                company: dbLead.company,
                website: dbLead.website,
                industry: dbLead.industry,
                owner_linkedin: dbLead.owner_linkedin || "N/A",
                source: "Database",
                contacts: contacts
              };
              
              // Add to companies that need processing
              companiesWithPeople.push(companyData);
            } else {
              companiesToScrapeArr.push(company);
            }
          } else {
            companiesToScrapeArr.push(company);
          }
        }
      } catch (err) {
        console.error("❌ Failed to fetch people from multiple_leads API:", err);
        companiesToScrapeArr = selected;
      }
    setDbPeopleResults(dbPeople);
    setPeopleFromDatabase(dbCompanyNames);
    allPeople = allPeople.concat(dbPeople);
    companiesToScrape = companiesToScrapeArr;
    console.log("🔍 Companies to scrape (not in DB):", companiesToScrape.map(c => c.company));

    // --- Continue with scraping logic for people as before ---
    // ... existing scraping logic ...

    // 4. For companies not found in DB, immediately call the scraping API
    console.log("🔍 Starting scraping for companies:", companiesToScrape.map(c => c.company));

    let scrapedPeople: any[] = [];

    // Group companies by their people data for batch upload
    // 🆕 MODIFIED: Use existing companiesWithPeople array instead of redeclaring

    for (const company of companiesToScrape) {
      try {
        let people: any[] = [];
        if (dataSource === "apollo") {
          // 🆕 NEW: Use apollo-enrich-people endpoint with smart domain search logic
          console.log(`🚀 Calling Apollo people enrichment for ${company.company}`);
          
          const apolloData = await apolloEnrichPeople(company);
          console.log("🔍 Apollo people enrichment response for", company.company, ":", apolloData);

          // The helper function returns the data directly
          if (apolloData && Object.keys(apolloData).length > 0) {
            // 🆕 NEW: Check if the response contains meaningful data (not just N/A values)
            const hasMeaningfulData = (
              (apolloData as any).name && (apolloData as any).name !== "N/A" && (apolloData as any).name !== "None None" &&
              (apolloData as any).title && (apolloData as any).title !== "N/A" &&
              (apolloData as any).email && (apolloData as any).email !== "N/A" &&
              (apolloData as any).phone && (apolloData as any).phone !== "N/A" &&
              (apolloData as any).linkedin && (apolloData as any).linkedin !== "N/A"
            );
            
            if (hasMeaningfulData) {
              // Create a person object from the enriched data
              const apolloPerson = {
                name: (apolloData as any).name || `${(apolloData as any).first_name || ''} ${(apolloData as any).last_name || ''}`.trim(),
                first_name: (apolloData as any).first_name || '',
                last_name: (apolloData as any).last_name || '',
                title: (apolloData as any).title || '',
                email: (apolloData as any).email || '',
                phone: (apolloData as any).phone || '',
                phone_number: (apolloData as any).phone || '',
                linkedin: (apolloData as any).linkedin || '',
                linkedin_url: (apolloData as any).linkedin || '',
                source: "Apollo (New Endpoint)"
              };
              
              people = [apolloPerson];
              console.log(`✅ Found 1 person from NEW Apollo API for ${company.company}`);
            } else {
              // 🆕 NEW: No meaningful data found
              console.log(`⚠️ Apollo apollo-enrich-people returned no meaningful data for ${company.company}:`, apolloData);
              people = [];
              notFoundCompaniesList.push(company.company);
            }
          } else {
            console.log(`❌ No people found for ${company.company} via NEW Apollo API`);
            people = [];
          }
        } else if (dataSource === "both") {
          // Try both Growjo and Apollo, combine results
          let growjoPeople: any[] = [];
          let apolloPeople: any[] = [];

          // Note: Growjo scraping by company name is no longer available in the new API structure
          // The new API only supports enrichment by company ID from batch lookup results
          console.log(`ℹ️ Skipping Growjo people scraping for ${company.company} - requires company ID from batch lookup`);

          // Try Apollo using NEW apollo-enrich-people endpoint with smart domain search
          try {
            console.log(`🚀 Calling Apollo people enrichment for ${company.company}`);
            
            const apolloData = await apolloEnrichPeople(company);
            console.log("🔍 Apollo people enrichment response for", company.company, ":", apolloData);

            if (apolloData && Object.keys(apolloData).length > 0) {
              // 🆕 NEW: Check if the response contains meaningful data (not just N/A values)
              const hasMeaningfulData = (
                (apolloData as any).name && (apolloData as any).name !== "N/A" && (apolloData as any).name !== "None None" &&
                (apolloData as any).title && (apolloData as any).title !== "N/A" &&
                (apolloData as any).email && (apolloData as any).email !== "N/A" &&
                (apolloData as any).phone && (apolloData as any).phone !== "N/A" &&
                (apolloData as any).linkedin && (apolloData as any).linkedin !== "N/A"
              );
              
              if (hasMeaningfulData) {
                // Create a person object from the enriched data
                const apolloPerson = {
                  name: (apolloData as any).name || `${(apolloData as any).first_name || ''} ${(apolloData as any).last_name || ''}`.trim(),
                  first_name: (apolloData as any).first_name || '',
                  last_name: (apolloData as any).last_name || '',
                  title: (apolloData as any).title || '',
                  email: (apolloData as any).email || '',
                  phone: (apolloData as any).phone || '',
                  phone_number: (apolloData as any).phone || '',
                  linkedin: (apolloData as any).linkedin || '',
                  linkedin_url: (apolloData as any).linkedin || '',
                  source: "Apollo (New Endpoint)"
                };
                
                apolloPeople = [apolloPerson];
                console.log(`✅ Found 1 person from NEW Apollo API for ${company.company}`);
              } else {
                // 🆕 NEW: No meaningful data found
                console.log(`⚠️ Apollo apollo-enrich-people returned no meaningful data for ${company.company}:`, apolloData);
                apolloPeople = [];
                notFoundCompaniesList.push(company.company);
              }
            }
          } catch (apolloErr) {
            console.error(`❌ Apollo apollo-enrich-people failed for ${company.company}:`, apolloErr);
          }

          // Combine and deduplicate people (simple name-based deduplication)
          const allPeopleCombined = [...apolloPeople]; // Only Apollo people available now
          const seenNames = new Set();
          people = allPeopleCombined.filter(person => {
            const name = person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim();
            if (seenNames.has(name.toLowerCase())) {
              return false;
            }
            seenNames.add(name.toLowerCase());
            return true;
          });

          console.log(`✅ Found ${apolloPeople.length} people from NEW Apollo API for ${company.company}`);
        }
        console.log("🔍 Scraped people for", company.company, ":", people.length);

        // Map people to the correct format
        const mappedPeople = people.map((p: any, idx: number) => ({
          ...p,
          company: company.company,
          website: company.website,
          industry: company.industry,
          id: p.id || `${company.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          sourceType: "scraped"
        }));

        // 🆕 NEW: Prepare company data with contacts array for batch upload
        if (mappedPeople.length > 0) {
          console.log(`📤 Preparing ${mappedPeople.length} people for batch upload for ${company.company}`);

          // Convert people to contacts format
          const contacts = mappedPeople.map((person: any) => {
            return {
              owner_first_name: person.name?.split(' ')[0] || person.first_name || "",
              owner_last_name: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
              owner_title: person.title || "",
              owner_email: person.email || "",
              owner_phone_number: person.phone || person.phone_number || "",
              owner_linkedin: person.linkedin || person.linkedin_url || ""
              // Do NOT include 'phone' here
            };
          });

          const companyData = {
            user_id: user.user_id || "", // Use existing user_id if available
            lead_id: company.lead_id || "", // Use existing lead_id if available
            company: company.company,
            website: company.website,
            industry: company.industry,
            owner_linkedin: (contacts[0]?.owner_linkedin) || ("owner_linkedin" in company ? (company as any).owner_linkedin : "N/A"),
            source: "Apollo", // Only Apollo available for people scraping now
            contacts: contacts
          };

          companiesWithPeople.push(companyData);
        }

        scrapedPeople = scrapedPeople.concat(mappedPeople);
        allPeople = allPeople.concat(mappedPeople);
      } catch (err) {
        console.error(`❌ Failed to enrich people for ${company.company}:`, err);
      }
    }

    // 🆕 NEW: Batch upload all companies with their contacts
    if (companiesWithPeople.length > 0) {
      console.log(`📤 Batch uploading ${companiesWithPeople.length} companies with contacts`);

      try {
        // Upload each company one by one (not in bulk)
        for (const companyData of companiesWithPeople) {
          try {
            // 🆕 FIXED: Ensure the upload payload matches the expected format exactly
            const uploadPayload = [{
              user_id: companyData.user_id,
              lead_id: companyData.lead_id || "", // Empty string as shown in your example
              company: companyData.company,
              website: companyData.website,
              industry: companyData.industry,
              owner_linkedin: companyData.owner_linkedin,
              source: companyData.source,
              contacts: companyData.contacts
            }];
            
            console.log(`📤 Uploading company ${companyData.company} with payload:`, JSON.stringify(uploadPayload, null, 2));
            
            const uploadRes = await axios.post(
              `${DATABASE_URL}/upload_leads`,
              JSON.stringify(uploadPayload),
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            
            console.log(`📤 Upload response for ${companyData.company}:`, uploadRes.data);
            
            const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
            const leadFromResponse = detailedResults[0] || {};
            const lead_id = leadFromResponse.lead_id || companyData.lead_id;
            
            console.log(`🔍 Extracted lead_id for ${companyData.company}:`, lead_id, 'from response:', leadFromResponse);

            // 🆕 CONFIRM: Upload completed, now calling drafts API
            console.log(`🔄 STEP 2: Calling /leads/drafts API for ${companyData.company} immediately after upload`);

            // 2. Create draft for this company - ALWAYS call drafts API after upload
            console.log(`📝 Creating draft for company ${companyData.company}`);
            
            // 🆕 FIXED: Always create draft, use fallback lead_id if needed
            const draftLeadId = lead_id || companyData.lead_id || `temp-${Date.now()}`;
            console.log(`📝 Using lead_id for draft:`, draftLeadId);
            
            const draftPayload = {
              lead_id: draftLeadId,
              draft_data: {
                user_id: companyData.user_id,
                lead_id: draftLeadId,
                company: companyData.company,
                website: companyData.website,
                industry: companyData.industry,
                owner_linkedin: companyData.owner_linkedin,
                source: companyData.source,
                contacts: companyData.contacts
              },
              change_summary: `People enrichment from Apollo`
            };
            
            console.log(`📝 Draft payload for ${companyData.company}:`, JSON.stringify(draftPayload, null, 2));
            
            try {
              const draftRes = await axios.post(
                `${DATABASE_URL}/leads/drafts`,
                draftPayload,
                {
                  headers: { "Content-Type": "application/json" },
                  withCredentials: true,
                }
              );
              const draft_id = draftRes.data?.draft_id;
              if (draft_id) {
                console.log(`✅ Created draft ${draft_id} for company ${companyData.company}`);
              } else {
                console.log(`⚠️ Draft created but no draft_id returned for company ${companyData.company}`);
              }
            } catch (draftErr: any) {
              console.error(`❌ Failed to create draft for company ${companyData.company}:`, draftErr);
              console.error(`❌ Draft error details:`, draftErr.response?.data || draftErr.message);
            }
            
            // 🆕 CONFIRM: Draft completed, now calling credit deduction API
            console.log(`🔄 STEP 3: Calling credit deduction API for ${companyData.company} after draft creation`);
            
            // 3. Deduct credit
            if (lead_id) {
              console.log(`💳 Deducting credit for company ${companyData.company} with lead_id:`, lead_id);
              try {
                await axios.post(
                  `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                  { type: generateDeductType('first enrichment', 'people', 'growjo') },
                  { withCredentials: true }
                );
                console.log(`✅ Deducted 1 credit for company ${companyData.company}`);
              } catch (deductErr: any) {
                console.error(`❌ Credit deduction failed for company ${companyData.company}:`, deductErr);
                console.error(`❌ Credit deduction error details:`, deductErr.response?.data || deductErr.message);
              }
            } else {
              console.error(`❌ No lead_id available for company ${companyData.company} - cannot deduct credit`);
            }
          } catch (uploadErr) {
            console.error(`❌ Failed to upload company ${companyData.company}:`, uploadErr);
            showNotification(`Failed to upload company ${companyData.company}`, "error");
          }
        }

        showNotification(`Successfully uploaded ${companiesWithPeople.length} companies with ${companiesWithPeople.reduce((sum, c) => sum + c.contacts.length, 0)} total contacts`, "success");

      } catch (uploadErr) {
        console.error("❌ Batch upload failed:", uploadErr);
        showNotification("Failed to upload people data", "error");
      }
    }

    setScrapedPeopleResults(scrapedPeople);

    // 🆕 FIXED: Create company objects with people arrays for UI display
    const allPeopleData = [...dbPeople, ...scrapedPeople];
    
    // Group people by company to create company objects
    const groupedByCompany = allPeopleData.reduce((acc: Record<string, any>, person: any) => {
      const companyKey = person.company;
      if (!acc[companyKey]) {
        acc[companyKey] = {
          id: person.id || `${companyKey}-company-${Date.now()}`,
          lead_id: person.lead_id || "",
          company: person.company,
          website: person.website,
          industry: person.industry,
          city: person.city || "",
          state: person.state || "",
          country: person.country || "",
          employees: person.employees || "",
          revenue: person.revenue || "",
          description: person.description || "",
          ownerFirstName: "",
          ownerLastName: "",
          ownerTitle: "",
          ownerEmail: "",
          ownerPhoneNumber: "",
          ownerLinkedin: "",
          source: person.source || "Unknown",
          sourceType: person.sourceType || "unknown",
          people: []
        };
      }
      acc[companyKey].people.push(person);
      return acc;
    }, {});
    
    // Convert grouped results to array and populate owner fields from first person
    const companyResults = Object.values(groupedByCompany).map((company: any) => {
      // Populate owner fields from the first person in the people array
      if (company.people && company.people.length > 0) {
        const firstPerson = company.people[0];
        return {
          ...company,
          ownerFirstName: firstPerson.name?.split(' ')[0] || firstPerson.first_name || "",
          ownerLastName: firstPerson.name?.split(' ').slice(1).join(' ') || firstPerson.last_name || "",
          ownerTitle: firstPerson.title || "",
          ownerEmail: firstPerson.email || "",
          ownerPhoneNumber: firstPerson.phone || firstPerson.phone_number || "",
          ownerLinkedin: firstPerson.linkedin || firstPerson.linkedin_url || ""
        };
      }
      return company;
    });
    
    // Set the company results in the correct state variables
    const dbResults = companyResults.filter(r => r.sourceType === "database");
    const scrapedResults = companyResults.filter(r => r.sourceType === "scraped");
    
    // 🆕 FIXED: Append results instead of replacing to allow cumulative enrichment
    setDbEnrichedCompanies(prev => {
      // Filter out duplicates based on company name to prevent adding the same company twice
      const existingCompanies = new Set(prev.map(company => company.company));
      const uniqueNewResults = dbResults.filter(company => !existingCompanies.has(company.company));
      return [...prev, ...uniqueNewResults];
    });
    
    setScrapedEnrichedCompanies(prev => {
      // Filter out duplicates based on company name
      const existingCompanies = new Set(prev.map(company => company.company));
      const uniqueNewResults = scrapedResults.filter(company => !existingCompanies.has(company.company));
      return [...prev, ...uniqueNewResults];
    });

    // 🆕 NEW: Update not found companies state and show banner if needed
    if (notFoundCompaniesList.length > 0) {
      setNotFoundCompanies(notFoundCompaniesList);
      setShowNotFoundBanner(true);
      console.log(`⚠️ ${notFoundCompaniesList.length} companies had no meaningful people data:`, notFoundCompaniesList);
    }

    // Check for empty results and show banner if needed
    const hasEmptyResults = checkForEmptyResults("people", dbPeople, scrapedPeople);
    
    // Show success notification only if we have results
    if (allPeople.length > 0) {
      showNotification(`People enrichment completed successfully! Found ${allPeople.length} people.`);
    } else if (hasEmptyResults) {
      // Show error notification for complete failure
      showNotification("People enrichment completed but no results were found. Check the banner above for details.", "error");
    }

    // Don't set peopleEnrichmentResults here - let the button control it
    console.log("🔍 Final people rows:", allPeople.length, allPeople);
    setLoading(false);
  };

  // Add re-enrich function for people
  const handleReEnrichPeople = async (dataSource: "growjo" | "apollo" | "both") => {
    setLoading(true);

    // Get companies that were from database
    const toReselect = normalizedLeads.filter(c =>
      peopleFromDatabase.includes(c.company.toLowerCase())
    );

    console.log("🔍 Re-enriching people for companies:", toReselect.map(c => c.company));

    // Clear previous results
    setDbPeopleResults([]);
    setScrapedPeopleResults([]);
    setPeopleFromDatabase([]);
    setNotFoundCompanies([]);
    setShowNotFoundBanner(false);

    // 🆕 NEW: Clear previous banner state when starting new enrichment
    setShowEmptyResultsBanner(false);
    setEmptyResultsInfo({
      hasDatabaseResults: false,
      hasScrapedResults: false,
      totalCompanies: 0,
      enrichmentType: "people"
    });

    let allPeople: any[] = [];
    let notFoundCompaniesList: string[] = [];

    // Instead, treat all companies as needing to be scraped
    const companiesToScrapeArr = toReselect;
    const user = JSON.parse(sessionStorage.getItem("user") || "{}");
    // 4. For companies not found in DB, immediately call the scraping API
    console.log("🔍 Starting scraping for companies:", companiesToScrapeArr.map(c => c.company));

    let scrapedPeople: any[] = [];

    // Group companies by their people data for batch upload
    const companiesWithPeople: any[] = [];

    for (const company of companiesToScrapeArr) {
      try {
        let people: any[] = [];
        if (dataSource === "growjo") {
          // Only call people API
          const res = await axios.post(`${BACKEND_URL}/scrape-growjo-people`, { company: company.company });
          console.log("🔍 Growjo people response for", company.company, ":", res.data);
          if (res.data.people && Array.isArray(res.data.people) && res.data.people.length > 0) {
            people = res.data.people.map((p: any) => ({ ...p, company: company.company, website: company.website }));
            console.log(`✅ Found ${people.length} people from Growjo API for ${company.company}`);
          } else {
            console.log(`❌ No people or owner found for ${company.company}`);
            notFoundCompaniesList.push(company.company);
          }
        } else if (dataSource === "apollo") {
          // 🆕 NEW: Use enhanced apollo-enrich-people function with BACKEND_URL fallback
          console.log(`🚀 Calling enhanced Apollo people enrichment for ${company.company}`);
          
          const apolloData: any = await apolloEnrichPeople(company);

          if (apolloData && Object.keys(apolloData).length > 0) {
            
            // Create a person object from the enriched data
            const apolloPerson = {
              name: apolloData.name || `${apolloData.first_name || ''} ${apolloData.last_name || ''}`.trim(),
              first_name: apolloData.first_name || '',
              last_name: apolloData.last_name || '',
              title: apolloData.title || '',
              email: apolloData.email || '',
              phone: apolloData.phone || '',
              phone_number: apolloData.phone || '',
              linkedin: apolloData.linkedin || '',
              linkedin_url: apolloData.linkedin || '',
              source: "Apollo (Enhanced)"
            };
            
            people = [apolloPerson];
            console.log(`✅ Found 1 person from enhanced Apollo API for ${company.company}`);
          } else {
            console.log(`⚠️ No people found for ${company.company} from enhanced Apollo enrichment (both DATABASE_URL and BACKEND_URL failed)`);
            people = [];
            notFoundCompaniesList.push(company.company);
          }
        } else if (dataSource === "both") {
          // Try Apollo only (Growjo removed) using NEW apollo-enrich-people endpoint
          let apolloPeople: any[] = [];

          // Try Apollo using enhanced function
          try {
            console.log(`🚀 Calling enhanced Apollo people enrichment for ${company.company}`);
            
            const apolloData: any = await apolloEnrichPeople(company);

            if (apolloData && Object.keys(apolloData).length > 0) {
              // Create a person object from the enriched data
              const apolloPerson = {
                name: apolloData.name || `${apolloData.first_name || ''} ${apolloData.last_name || ''}`.trim(),
                first_name: apolloData.first_name || '',
                last_name: apolloData.last_name || '',
                title: apolloData.title || '',
                email: apolloData.email || '',
                phone: apolloData.phone || '',
                phone_number: apolloData.phone || '',
                linkedin: apolloData.linkedin || '',
                linkedin_url: apolloData.linkedin || '',
                source: "Apollo (Enhanced)"
              };
              
              apolloPeople = [apolloPerson];
              console.log(`✅ Found 1 person from enhanced Apollo API for ${company.company}`);
            } else {
              console.log(`⚠️ No people found for ${company.company} from enhanced Apollo enrichment (both DATABASE_URL and BACKEND_URL failed)`);
            }
          } catch (apolloErr) {
            console.error(`❌ Apollo apollo-enrich-people failed for ${company.company}:`, apolloErr);
          }

          // Use Apollo people
          people = apolloPeople;

          console.log(`✅ Found ${people.length} people from NEW Apollo for ${company.company}`);
        }
        console.log("🔍 Scraped people for", company.company, ":", people.length);

        // Map people to the correct format
        const mappedPeople = people.map((p: any, idx: number) => ({
          ...p,
          company: company.company,
          website: company.website,
          industry: company.industry,
          id: p.id || `${company.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          sourceType: "scraped"
        }));

        // 🆕 NEW: Prepare company data with contacts array for batch upload
        if (mappedPeople.length > 0) {
          console.log(`📤 Preparing ${mappedPeople.length} people for batch upload for ${company.company}`);

          // Convert people to contacts format
          const contacts = mappedPeople.map((person: any) => {
            return {
              owner_first_name: person.name?.split(' ')[0] || person.first_name || "",
              owner_last_name: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
              owner_title: person.title || "",
              owner_email: person.email || "",
              owner_phone_number: person.phone || person.phone_number || "",
              owner_linkedin: person.linkedin || person.linkedin_url || ""
              // Do NOT include 'phone' here
            };
          });

          const companyData = {
            user_id: user.user_id || "", // Use existing user_id if available
            lead_id: company.lead_id || "", // Use existing lead_id if available
            company: company.company,
            website: company.website,
            industry: company.industry,
            owner_linkedin: (contacts[0]?.owner_linkedin) || ("owner_linkedin" in company ? (company as any).owner_linkedin : "N/A"),
            source: "Apollo", // Only Apollo available for people scraping now
            contacts: contacts
          };

          companiesWithPeople.push(companyData);
        }

        scrapedPeople = scrapedPeople.concat(mappedPeople);
        allPeople = allPeople.concat(mappedPeople);
      } catch (err) {
        console.error(`❌ Failed to enrich people for ${company.company}:`, err);
        notFoundCompaniesList.push(company.company);
      }
    }

    // 🆕 NEW: Batch upload all companies with their contacts
    if (companiesWithPeople.length > 0) {
      console.log(`📤 Batch uploading ${companiesWithPeople.length} companies with contacts`);

      try {
        // Upload each company one by one (not in bulk)
        for (const companyData of companiesWithPeople) {
          try {
            // 🆕 FIXED: Ensure the upload payload matches the expected format exactly
            const uploadPayload = [{
              user_id: companyData.user_id,
              lead_id: companyData.lead_id || "", // Empty string as shown in your example
              company: companyData.company,
              website: companyData.website,
              industry: companyData.industry,
              owner_linkedin: companyData.owner_linkedin,
              source: companyData.source,
              contacts: companyData.contacts
            }];
            
            console.log(`📤 Uploading company ${companyData.company} with payload:`, JSON.stringify(uploadPayload, null, 2));
            
            const uploadRes = await axios.post(
              `${DATABASE_URL}/upload_leads`,
              JSON.stringify(uploadPayload),
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            
            console.log(`📤 Upload response for ${companyData.company}:`, uploadRes.data);
            
            const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
            const leadFromResponse = detailedResults[0] || {};
            const lead_id = leadFromResponse.lead_id || companyData.lead_id;
            
            console.log(`🔍 Extracted lead_id for ${companyData.company}:`, lead_id, 'from response:', leadFromResponse);

            // 2. Create draft for this company - ALWAYS call drafts API after upload
            console.log(`📝 Creating draft for company ${companyData.company}`);
            
            // 🆕 FIXED: Always create draft, use fallback lead_id if needed
            const draftLeadId = lead_id || companyData.lead_id || `temp-${Date.now()}`;
            console.log(`📝 Using lead_id for draft:`, draftLeadId);
            
            const draftPayload = {
              lead_id: draftLeadId,
              draft_data: {
                user_id: companyData.user_id,
                lead_id: draftLeadId,
                company: companyData.company,
                website: companyData.website,
                industry: companyData.industry,
                owner_linkedin: companyData.owner_linkedin,
                source: companyData.source,
                contacts: companyData.contacts
              },
              change_summary: `People re-enrichment from Apollo`
            };
            
            console.log(`📝 Draft payload for ${companyData.company}:`, JSON.stringify(draftPayload, null, 2));
            
            try {
              const draftRes = await axios.post(
                `${DATABASE_URL}/leads/drafts`,
                draftPayload,
                {
                  headers: { "Content-Type": "application/json" },
                  withCredentials: true,
                }
              );
              const draft_id = draftRes.data?.draft_id;
              if (draft_id) {
                console.log(`✅ Created draft ${draft_id} for company ${companyData.company}`);
              }
            } catch (draftErr: any) {
              console.error(`❌ Failed to create draft for company ${companyData.company}:`, draftErr);
              console.error(`❌ Draft error details:`, draftErr.response?.data || draftErr.message);
            }
            // 3. Deduct credit
            if (lead_id) {
              console.log(`💳 Deducting credit for company ${companyData.company} with lead_id:`, lead_id);
              try {
                await axios.post(
                  `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                  { type: generateDeductType('first enrichment', 'people', 'apollo') },
                  { withCredentials: true }
                );
                console.log(`✅ Deducted 1 credit for company ${companyData.company}`);
              } catch (deductErr: any) {
                console.error(`❌ Credit deduction failed for company ${companyData.company}:`, deductErr);
              }
            }
          } catch (uploadErr) {
            console.error(`❌ Failed to upload company ${companyData.company}:`, uploadErr);
            showNotification(`Failed to upload company ${companyData.company}`, "error");
          }
        }

        showNotification(`Successfully re-uploaded ${companiesWithPeople.length} companies with ${companiesWithPeople.reduce((sum, c) => sum + c.contacts.length, 0)} total contacts`, "success");

      } catch (uploadErr) {
        console.error("❌ Batch upload failed:", uploadErr);
        showNotification("Failed to upload people data", "error");
      }
    }

    // Update results
    setScrapedPeopleResults(allPeople);

    // Update not found companies state
    setNotFoundCompanies(notFoundCompaniesList);
    setShowNotFoundBanner(notFoundCompaniesList.length > 0);

    // 🆕 NEW: Check for empty results and show banner if needed
    const hasEmptyResults = checkForEmptyResults("people", [], allPeople);
    if (hasEmptyResults) {
      console.log("⚠️ No results found, showing empty results banner");
    }

    setLoading(false);
  };

  // New function to fetch database results for not found companies
  const handleFetchDatabaseResults = async () => {
    if (notFoundCompanies.length === 0) return;

    setLoading(true);

    try {
      // Get the lead_ids for not found companies
      const notFoundLeads = normalizedLeads.filter(c =>
        notFoundCompanies.includes(c.company)
      );
      const lead_ids = notFoundLeads.map(c => c.lead_id).filter((id): id is string => Boolean(id));
      const companyNames = notFoundLeads.map(c => c.company).filter((name): name is string => Boolean(name));

              if (lead_ids.length > 0) {
          const dbLeads = await fetchCompaniesWithFallback(lead_ids, companyNames);
        let dbPeople: any[] = [];

        // Process each lead from DB
        for (const lead of dbLeads) {
          // First check if there's a people array (from scraping)
          if (Array.isArray(lead.people) && lead.people.length > 0) {
            const mappedPeople = lead.people.map((p: any, idx: number) => ({
              ...p,
              company: lead.company,
              website: lead.website,
              industry: lead.industry,
              id: p.id || `${lead.lead_id || lead.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              sourceType: "database"
            }));
            dbPeople = dbPeople.concat(mappedPeople);
          }
          // If no people array, check for owner fields and map them as a person
          else if (
            lead.owner_first_name ||
            lead.owner_last_name ||
            lead.owner_email ||
            lead.owner_title ||
            lead.owner_phone_number ||
            lead.owner_linkedin
          ) {
            const ownerPerson = {
              name: `${lead.owner_first_name || ''} ${lead.owner_last_name || ''}`.trim(),
              title: lead.owner_title || '',
              email: lead.owner_email || '',
              phone: lead.owner_phone_number || lead.phone || '',
              linkedin: lead.owner_linkedin || '',
              company: lead.company,
              website: lead.website,
              industry: lead.industry,
              id: `${lead.lead_id || lead.id}-owner`,
              sourceType: "database"
            };
            dbPeople.push(ownerPerson);
          }
        }

        // Update database results
        setDbPeopleResults(dbPeople);

        // Update people from database list
        const dbCompanyNames = dbLeads.map((l: any) => l.company?.toLowerCase());
        setPeopleFromDatabase(dbCompanyNames);

        // Clear not found companies that were found in database
        const foundInDb = dbLeads.map((l: any) => l.company);
        setNotFoundCompanies(prev => prev.filter(company => !foundInDb.includes(company)));
        setShowNotFoundBanner(notFoundCompanies.filter(company => !foundInDb.includes(company)).length > 0);

        showNotification(`Found ${dbPeople.length} people from database for ${dbLeads.length} companies`, "success");
      }
    } catch (err) {
      console.error("❌ Failed to fetch database results:", err);
      showNotification("Failed to fetch database results", "error");
    }

    setLoading(false);
  };

  const handleBackFromPeopleResults = () => {
    setShowPeopleResults(false)
  }

  const handleStartEnrichment = async (
    forceScrape = false,
    overrideCompanies: any[] | null = null,
    dataSourceOverride?: "growjo" | "apollo" | "both",
    skipDatabaseCheck = false
  ) => {
    const user = JSON.parse(sessionStorage.getItem("user") || "{}")
    const user_id = user.user_id || "";
    setLoading(true);

    // Determine if this is first or second enrichment
    const isFirstEnrichment = !hasFirstEnrichment;
    
    if (isFirstEnrichment) {
      // First enrichment - set the type and clear first enrichment state
      setFirstEnrichmentType(enrichmentType);
      setHasFirstEnrichment(true);
    if (!forceScrape) {
      setDbEnrichedCompanies([]);
      setScrapedEnrichedCompanies([]);
      setFromDatabaseLeads([]); // Clear database companies tracking
    }
    } else {
      // Second enrichment - set the type and clear second enrichment state
      setSecondEnrichmentType(enrichmentType);
      setHasSecondEnrichment(true);
      if (!forceScrape) {
        setSecondDbEnrichedCompanies([]);
        setSecondScrapedEnrichedCompanies([]);
      }
    }
    
    setHasErrors(false); // Reset error flag at start
    hasErrorsRef.current = false; // Reset ref as well

    // Set enrichment view type based on enrichment type
    if (enrichmentType === "people") {
      setEnrichmentViewType("people");
    } else {
      setEnrichmentViewType("company");
    }

    try {
      const selected = overrideCompanies ?? normalizedLeads.filter(c =>
        selectedCompanies.includes(c.id)
      );
      // ── Step 1: Check credits ──
      try {
        const { data: subscriptionInfo } = await axios.get(
          `${DATABASE_URL}/user/subscription_info`,
          { withCredentials: true }
        );

        const plan = subscriptionInfo?.plan;
        const isUnlimited =
          plan?.initial_credits === null ||
          (plan?.features_json && plan.features_json.includes("Unlimited Credits"));

        if (!isUnlimited) {
          const availableCredits = subscriptionInfo?.subscription?.credits_remaining ?? 0;
          const requiredCredits = selected.length;
          if (availableCredits < requiredCredits) {
            setShowTokenPopup(true);
            setLoading(false);
            return;
          }
        }
        // If unlimited, always allow
      } catch (checkErr) {
        console.error("❌ Failed to verify subscription:", checkErr);
        alert("Failed to verify your subscription. Please try again later.");
        setLoading(false);
        return;
      }

      // ── Step 2: Enrich each company according to flow ──
      let dbRows: any[] = [];
      let scrapedRows: any[] = [];
      // Use the override if provided, otherwise the state
      const effectiveDataSource = dataSourceOverride || selectedDataSource;
      for (const company of selected) {
        let result = null;
        // Always call enrichAndUpload directly based on data source
        if (effectiveDataSource === "growjo") {
          // For Saasquatch Leads, call database enrichment
          result = await enrichFromDatabase(company, user_id, enrichmentType, effectiveDataSource);
          if (result) dbRows.push(toCamelCase({ ...result, source_type: "database" }));
        } else {
          // For Apollo or Both, call scraping enrichment
          result = await enrichAndUpload(company, user_id, enrichmentType, effectiveDataSource);
          if (result) scrapedRows.push(toCamelCase({ ...result, source_type: "scraped" }));
        }
      }
      // Store results in appropriate state based on enrichment order
      if (isFirstEnrichment) {
      setDbEnrichedCompanies(dbRows);
      setScrapedEnrichedCompanies(scrapedRows);
      } else {
        setSecondDbEnrichedCompanies(dbRows);
        setSecondScrapedEnrichedCompanies(scrapedRows);
      }
      setShowResults(true);
      setHasEnrichedOnce(true);
    } catch (err) {
      console.error("Enrichment failed:", err);
      stopProgressSimulation(0);
    } finally {
      stopProgressSimulation(100);
      setLoading(false);
    }

    // Only show success if we actually enriched some companies AND no errors occurred
    const hasResults = isFirstEnrichment 
      ? (scrapedEnrichedCompanies.length > 0 || dbEnrichedCompanies.length > 0)
      : (secondScrapedEnrichedCompanies.length > 0 || secondDbEnrichedCompanies.length > 0);
    
    if (hasResults && !hasErrorsRef.current) {
      showNotification("Data successfully enriched!");
    }
  };

  // Helper to filter company object to only allowed columns for free users
  // const allowedBasic = [
  //   "company",
  //   "industry",
  //   "street",
  //   "city",
  //   "state",
  //   "bbb_rating",
  //   "business_phone",
  //   "website"
  // ];
  // function filterToAllowedBasic(company: any) {
  //   const out: any = {};
  //   allowedBasic.forEach(key => {
  //     if (company[key] !== undefined) out[key] = company[key];
  //   });
  //   return out;
  // }

  // Helper to build the correct payload for basic enrichment (free tier)
  // function buildBasicPayload(company: any, user_id: string) {
  //   return {
  //     user_id,
  //     lead_id: "",
  //     company: company.company || "N/A",
  //     website: company.website || "N/A",
  //     industry: company.industry || "N/A",
  //     owner_linkedin: company.owner_linkedin || "N/A",
  //     source: company.source || "N/A",
  //     contacts: [
  //       {
  //         owner_first_name: company.owner_first_name || "N/A",
  //         owner_last_name: company.owner_last_name || "N/A",
  //         owner_title: company.owner_title || "N/A",
  //         owner_email: company.owner_email || "N/A",
  //         owner_phone_number: company.owner_phone_number || "N/A",
  //         owner_linkedin: company.owner_linkedin || "N/A"
  //       }
  //     ]
  //   };
  // }

  const [dropdownOpen, setDropdownOpen] = useState(false);

  // Second enrichment functions

  // Unified prioritization function for consistent data merging across all enrichment steps
  const prioritizeData = (newValue: any, existingValue: any, defaultValue: string = "") => {
    // If new value is meaningful (not null, undefined, empty string, or "N/A"), use it
    if (newValue !== null && newValue !== undefined && newValue !== "" && newValue !== "N/A") {
      return newValue;
    }
    // Otherwise, keep existing value or use default
    return existingValue || defaultValue;
  };

  // Map Apollo data to consistent format for prioritization
  const mapApolloData = (apolloData: any) => ({
    city: apolloData.city,
    state: apolloData.state,
    country: apolloData.country,
    street: apolloData.street_address,
    company_linkedin: apolloData.linkedin_url,
    company_phone: apolloData.phone,
    revenue: apolloData.organization_revenue || apolloData.annual_revenue_printed,
    employees: apolloData.employees,
    year_founded: apolloData.founded_year,
    website: apolloData.website_url || apolloData.primary_domain,
    industry: apolloData.industry,
    product_category: apolloData.product_category,
    business_type: apolloData.business_type
  });

  // Helper function to extract people data from enriched companies for contacts array
  const getPeopleFromEnrichedData = (companyName: string, enrichedData?: any[]) => {
    if (!enrichedData || enrichedData.length === 0) return [];
    
    const enrichedCompany = enrichedData.find(company => 
      company.company === companyName || company.company?.toLowerCase() === companyName?.toLowerCase()
    );
    
    if (!enrichedCompany || !enrichedCompany.people || !Array.isArray(enrichedCompany.people)) {
      return [];
    }
    
    // Convert people data to contacts format
    return enrichedCompany.people.map((person: any) => ({
      owner_first_name: person.ownerFirstName || person.owner_first_name || person.first_name || person.name?.split(' ')[0] || "",
      owner_last_name: person.ownerLastName || person.owner_last_name || person.last_name || person.name?.split(' ').slice(1).join(' ') || "",
      owner_title: person.ownerTitle || person.owner_title || person.title || "",
      owner_email: person.ownerEmail || person.owner_email || person.email || "",
      owner_phone_number: person.ownerPhoneNumber || person.owner_phone_number || person.phone || person.phone_number || "",
      owner_linkedin: person.ownerLinkedin || person.owner_linkedin || person.linkedin || person.linkedin_url || ""
    }));
  };

  // Second enrichment functions with full flow like initial enrichment
  const handleSecondCompanyEnrichment = async (companyIds: number[], enrichedData?: any[]) => {
    console.log(`🚀 Starting Second Company Enrichment for ${companyIds.length} companies...`);
    
    if (companyIds.length === 0) {
      showNotification("Please select companies to enrich", "error");
      return;
    }

    if (companyIds.length > 25) {
      showNotification("Maximum 25 leads allowed for enrichment", "error");
      return;
    }
    
    if (secondEnrichmentLoading) {
      showNotification("Second enrichment already in progress. Please wait.", "info");
      return;
    }
    
    const user = JSON.parse(sessionStorage.getItem("user") || "{}");
    const user_id = user.user_id || "";
    setSecondEnrichmentLoading(true);
    setHasErrors(false);
    hasErrorsRef.current = false;

    try {
      // Use enriched data if provided, otherwise fall back to original leads
      const selected = enrichedData || normalizedLeads.filter(c => companyIds.includes(c.id));
      
      // Check credits first
      try {
        const { data: subscriptionInfo } = await axios.get(
          `${DATABASE_URL}/user/subscription_info`,
          { withCredentials: true }
        );

        const plan = subscriptionInfo?.plan;
        const isUnlimited =
          plan?.initial_credits === null ||
          (plan?.features_json && plan.features_json.includes("Unlimited Credits"));

        if (!isUnlimited) {
          const availableCredits = subscriptionInfo?.subscription?.credits_remaining ?? 0;
          const requiredCredits = selected.length;
          if (availableCredits < requiredCredits) {
            setShowTokenPopup(true);
            setSecondEnrichmentLoading(false);
            return;
          }
        }
      } catch (checkErr) {
        console.error("❌ Failed to verify subscription:", checkErr);
        alert("Failed to verify your subscription. Please try again later.");
        setSecondEnrichmentLoading(false);
        return;
      }

      // Step 1: Check database for existing data
      console.log("🔍 Step 1: Checking database for existing data...");
      let dbRows: any[] = [];
      let companiesNeedingEnrichment: any[] = [];
      let companiesWithCompleteData: any[] = [];
      let completeDataDbLeads: any[] = [];

      const leadIds = selected.map(c => c.lead_id).filter((id): id is string => Boolean(id));
      const companyNames = selected.map(c => c.company).filter((name): name is string => Boolean(name));
      
      // Always try database lookup, even with empty leadIds (will use search_companies)
      try {
        const dbLeads = await fetchCompaniesWithFallback(leadIds, companyNames);

        for (const company of selected) {
          // For companies without lead_id, try to find by company name (case insensitive)
          const dbLead = dbLeads.find((l: any) => 
            l.lead_id === company.lead_id || 
            (company.lead_id ? false : l.company?.toLowerCase() === company.company?.toLowerCase())
          );
          
          if (dbLead) {
            // Check if this company needs enrichment based on missing core datapoints (year, revenue, employees)
            const missingFields = [];
            if (!dbLead.year_founded || dbLead.year_founded === "N/A") missingFields.push("year_founded");
            if (!dbLead.revenue || dbLead.revenue === "N/A") missingFields.push("revenue");
            if (!dbLead.employees || dbLead.employees === "N/A") missingFields.push("employees");
            
            const hasCompleteData = missingFields.length === 0;

            if (hasCompleteData) {
              companiesWithCompleteData.push(company);
              completeDataDbLeads.push(dbLead);
              console.log(`✅ ${company.company} has complete data in database`);
            } else {
              companiesNeedingEnrichment.push(company);
              console.log(`⚠️ ${company.company} needs enrichment - missing: ${missingFields.join(", ")}`);
            }
          } else {
            companiesNeedingEnrichment.push(company);
            console.log(`⚠️ ${company.company} not found in database, needs enrichment`);
          }
        }
      } catch (err) {
        console.error("❌ Failed to fetch from database:", err);
        companiesNeedingEnrichment = selected;
      }

      // Step 2: Company lookup to get company_ids for Growjo
      console.log("🔍 Step 2: Company lookup to get company_ids...");
      let companiesWithIds: any[] = [];
      let companiesWithoutIds: any[] = [];

      if (companiesNeedingEnrichment.length > 0) {
        try {
          const companyNames = companiesNeedingEnrichment.map(c => c.company);
          const lookupResponse = await axios.post(
            `${DATABASE_URL}/growjo/companies`,
            { company_names: companyNames },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );

          if (lookupResponse.data && lookupResponse.data.company_batch_results) {
            console.log(`🔍 Processing ${lookupResponse.data.company_batch_results.length} results from Growjo companies API`);
            
            for (const company of companiesNeedingEnrichment) {
              const lookupResult = lookupResponse.data.company_batch_results.find(
                (r: any) => r.company_name === company.company
              );
              console.log(`🔍 Looking for company: ${company.company}`);
              console.log(`🔍 Found lookup result:`, lookupResult);
              
              if (lookupResult && lookupResult.items && lookupResult.items.length > 0) {
                // Use the first item from the results
                const companyData = lookupResult.items[0];
                companiesWithIds.push({
                  ...company,
                  growjo_company_id: companyData.company_id,
                  growjo_company_data: companyData // Store the full company data for direct enrichment
                });
                console.log(`✅ Found company data for ${company.company} with company_id ${companyData.company_id}`);
              } else {
                companiesWithoutIds.push(company);
                console.log(`⚠️ No company data found for ${company.company}`);
              }
            }
          } else {
            console.log("⚠️ No company data returned from Growjo companies API");
            companiesWithoutIds = companiesNeedingEnrichment;
          }
        } catch (err) {
          console.error("❌ Growjo companies API failed:", err);
          companiesWithoutIds = companiesNeedingEnrichment; // Fallback to all
          console.log(`🔄 Fallback: All ${companiesNeedingEnrichment.length} companies will go to Apollo due to Growjo companies API failure`);
        }
        
        // 🆕 SAFETY CHECK: If no companies were categorized, force all to Apollo (same as first enrichment)
        if (companiesWithIds.length === 0 && companiesWithoutIds.length === 0) {
          console.log(`⚠️ SAFETY CHECK: No companies were categorized by Growjo companies API!`);
          console.log(`🔄 Forcing all ${companiesNeedingEnrichment.length} companies to Apollo as fallback`);
          companiesWithoutIds = [...companiesNeedingEnrichment];
        }
        
        // 🆕 DEBUG: Log what happened with the Growjo companies API (same as first enrichment)
        console.log(`🔍 Growjo companies API results:`);
        console.log(`  - Total companies needing enrichment: ${companiesNeedingEnrichment.length}`);
        console.log(`  - Companies with IDs (for Growjo): ${companiesWithIds.length}`);
        console.log(`  - Companies without IDs (for Apollo): ${companiesWithoutIds.length}`);
        
        if (companiesWithoutIds.length > 0) {
          console.log(`🔍 Companies that will go to Apollo (no IDs):`);
          companiesWithoutIds.forEach((company, index) => {
            console.log(`  ${index + 1}. ${company.company} (lead_id: ${company.lead_id || 'none'}, website: ${company.website || 'none'})`);
          });
        }
      }

      // Step 3: Process companies with complete data from database
      console.log("🔍 Step 3: Processing companies with complete data from database...");
      if (companiesWithCompleteData.length > 0) {
        for (const company of companiesWithCompleteData) {
          const dbLead = completeDataDbLeads.find(l => l.lead_id === company.lead_id);
          if (dbLead) {
            // 🤖 NEW: Check if business_type already exists, if not call business type decider (same as first enrichment)
            let businessType = dbLead.business_type || dbLead.businessType || "";
            if (!businessType || businessType === "N/A" || businessType.trim() === "") {
              console.log(`🤖 Calling business type decider for second enrichment database-enriched company: ${company.company} (no existing business_type)`);
              const products = dbLead.product_category || dbLead.productCategory || "";
              const industry = dbLead.industry || company.company || "";
              businessType = await callBusinessTypeDecider(products, industry);
              console.log(`✅ Updated ${company.company} with business type: ${businessType}`);
            } else {
              console.log(`✅ ${company.company} already has business type: ${businessType}, skipping API call`);
            }
            
            // 🆕 FIXED: Use proper prioritization logic for database enrichment
            // Merge database data into company object with correct prioritization
            const companyWithDbData = {
              ...company,
              website: prioritizeData(dbLead.website, company.website),
              business_phone: prioritizeData(dbLead.business_phone, company.business_phone || company.company_phone),
              company_phone: prioritizeData(dbLead.business_phone, company.business_phone || company.company_phone),
              revenue: prioritizeData(dbLead.revenue, company.revenue),
              employees: prioritizeData(dbLead.employees, company.employees),
              year_founded: prioritizeData(dbLead.year_founded, company.year_founded),
              product_category: prioritizeData(dbLead.product_category, company.product_category),
              business_type: prioritizeData(dbLead.business_type, company.business_type),
              industry: prioritizeData(dbLead.industry, company.industry),
              company_linkedin: prioritizeData(dbLead.company_linkedin, company.company_linkedin),
              bbb_rating: prioritizeData(dbLead.bbb_rating, company.bbb_rating),
              street: prioritizeData(dbLead.street, company.street),
              city: prioritizeData(dbLead.city, company.city),
              state: prioritizeData(dbLead.state, company.state)
            };
            const enrichmentData = buildEnrichedCompany(companyWithDbData, {}, {}, { ...dbLead, businessType }, revenueMap);
            
            // 🔍 DEBUG: Log phone and LinkedIn data for database-enriched companies
            console.log(`🔍 DEBUG - Database-enriched company phone data for ${company.company}:`);
            console.log(`  - CompanyWithDbData business_phone: ${companyWithDbData.business_phone}`);
            console.log(`  - CompanyWithDbData company_phone: ${companyWithDbData.company_phone}`);
            console.log(`  - EnrichmentData companyPhone: ${enrichmentData.companyPhone}`);
            console.log(`  - EnrichmentData companyLinkedin: ${enrichmentData.companyLinkedin}`);
            
            const enrichedCompany = toCamelCase({ ...enrichmentData, source_type: "database" });
            
            // 🔍 DEBUG: Log final enriched company data for database
            console.log(`🔍 DEBUG - Final database-enriched company data for ${company.company}:`);
            console.log(`  - Final companyPhone: ${enrichedCompany.companyPhone}`);
            console.log(`  - Final companyLinkedin: ${enrichedCompany.companyLinkedin}`);
            
            dbRows.push(enrichedCompany);
            console.log(`✅ Added complete data for ${company.company} from database with proper revenue handling`);
          }
        }
      }

      // Step 4: Call Growjo API for companies with IDs (same as first enrichment)
      console.log("🔍 Step 4: Calling Growjo API for companies with IDs...");
      let growjoResults: any[] = [];
      if (companiesWithIds.length > 0) {
        for (const company of companiesWithIds) {
          try {
            console.log(`🔄 Calling Growjo company API for ${company.company} with company_id: ${company.growjo_company_id}`);
            console.log(`🌐 Endpoint: ${BACKEND_URL}/growjo/company/${company.growjo_company_id}`);
            
            const growjoResponse = await axios.post(
              `${BACKEND_URL}/growjo/company/${company.growjo_company_id}`,
              {},
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );

            if (growjoResponse.data && growjoResponse.data.success) {
              const result = growjoResponse.data.company;
              console.log(`✅ Found company data from Growjo for ${company.company}:`, result);
              
              // Map Growjo data like first enrichment does
              const mappedGrowjoData = await mapGrowjoCompanyData(result);
              console.log(`🔍 Mapped Growjo data for ${company.company}:`, mappedGrowjoData);
              
              // 🔍 DEBUG: Log data before mapping for second enrichment
              console.log(`🔍 DEBUG - Second enrichment data mapping for ${company.company}:`);
              console.log(`  - Original company.city: ${company.city}`);
              console.log(`  - Original company.state: ${company.state}`);
              console.log(`  - Original company.street: ${company.street}`);
              console.log(`  - Original company.company_linkedin: ${company.company_linkedin}`);
              console.log(`  - Original company.company_phone: ${company.company_phone}`);
              console.log(`  - Mapped Growjo city: ${mappedGrowjoData.city}`);
              console.log(`  - Mapped Growjo state: ${mappedGrowjoData.state}`);
              console.log(`  - Mapped Growjo street: ${mappedGrowjoData.street}`);
              console.log(`  - Mapped Growjo company_linkedin: ${mappedGrowjoData.company_linkedin}`);
              console.log(`  - Mapped Growjo business_phone: ${mappedGrowjoData.business_phone}`);

              // Use unified prioritization function for consistent data merging
              const enrichedCompany = {
                ...company,
                // Use mapped Growjo data for location fields, fallback to original if not available
                city: prioritizeData(mappedGrowjoData.city, company.city),
                state: prioritizeData(mappedGrowjoData.state, company.state),
                country: prioritizeData(mappedGrowjoData.country, company.country),
                street: prioritizeData(mappedGrowjoData.street, company.street),
                
                // Keep original values for these fields (no changes)
                industry: company.industry,
                bbb_rating: company.bbb_rating,
                
                // Apply improved logic for these fields (pick best value)
                revenue: prioritizeData(mappedGrowjoData.revenue, company.revenue),
                employees: prioritizeData(mappedGrowjoData.employee_count, company.employees),
                year_founded: prioritizeData(mappedGrowjoData.year_founded, company.year_founded),
                company_linkedin: prioritizeData(mappedGrowjoData.company_linkedin, company.company_linkedin),
                company_phone: prioritizeData(mappedGrowjoData.business_phone, company.company_phone || company.business_phone),
                
                // Use mapped data from Growjo for website and product_category
                website: prioritizeData(mappedGrowjoData.website, company.website),
                product_category: prioritizeData(mappedGrowjoData.product_category, company.product_category),
                
                // Owner info - preserve original when available
                owner_first_name: prioritizeData(mappedGrowjoData.decider_name?.split(' ')[0], company.owner_first_name),
                owner_last_name: prioritizeData(mappedGrowjoData.decider_name?.split(' ').slice(1).join(' '), company.owner_last_name),
                owner_title: prioritizeData(mappedGrowjoData.decider_title, company.owner_title),
                owner_email: prioritizeData(mappedGrowjoData.decider_email, company.owner_email),
                owner_phone_number: prioritizeData(mappedGrowjoData.decider_phone, company.owner_phone_number),
                owner_linkedin: prioritizeData(mappedGrowjoData.decider_linkedin, company.owner_linkedin),
                source: "Growjo (Second Enrichment)"
              };

              // 🔍 DEBUG: Log final enriched company data
              console.log(`🔍 DEBUG - Final enriched company data for ${company.company}:`);
              console.log(`  - Final city: ${enrichedCompany.city}`);
              console.log(`  - Final state: ${enrichedCompany.state}`);
              console.log(`  - Final street: ${enrichedCompany.street}`);
              console.log(`  - Final company_linkedin: ${enrichedCompany.company_linkedin}`);
              console.log(`  - Final company_phone: ${enrichedCompany.company_phone}`);

              // 🤖 NEW: Call business type decider BEFORE upload/draft/deduct (same as first enrichment)
              console.log(`🤖 Calling business type decider for second enrichment Growjo-enriched company: ${company.company}`);
              const products = enrichedCompany.product_category || "";
              const industry = enrichedCompany.industry || company.company || "";
              const businessType = await callBusinessTypeDecider(products, industry);
              enrichedCompany.business_type = businessType;
              console.log(`✅ Updated ${company.company} with business type: ${businessType}`);
              
              // Convert to camelCase for display (draft_id will be added later)
              const enrichedCompanyCamelCase = toCamelCase({ ...enrichedCompany, source_type: "scraped", lead_id: company.lead_id || "" });
              growjoResults.push(enrichedCompanyCamelCase);
              
                // Use same API calls as first enrichment with proper data mapping
                try {
                  let lead_id = company.lead_id || "";
                  
                  // Get people data from first enrichment
                  const peopleFromFirstEnrichment = getPeopleFromEnrichedData(company.company, enrichedData);
                  console.log(`🔍 Found ${peopleFromFirstEnrichment.length} people from first enrichment for ${company.company}`);
                  
                  const basePayload = {
                    user_id,
                    lead_id,
                    company: enrichedCompany.company,
                    website: enrichedCompany.website,
                    industry: enrichedCompany.industry,
                    product_category: enrichedCompany.product_category || "",
                    business_type: enrichedCompany.business_type || "",
                    employees: enrichedCompany.employees || "",
                    revenue: formatRevenueForDisplay(enrichedCompany.revenue || ""),
                    year_founded: enrichedCompany.year_founded || "",
                    bbb_rating: enrichedCompany.bbb_rating || "",
                    street: enrichedCompany.street || "",
                    city: enrichedCompany.city || "",
                    state: enrichedCompany.state || "",
                    country: enrichedCompany.country || "",
                    company_phone: enrichedCompany.company_phone || "",
                    company_linkedin: enrichedCompany.company_linkedin || "",
                    source: enrichedCompany.source,
                    contacts: peopleFromFirstEnrichment,
                    owner_linkedin: peopleFromFirstEnrichment[0]?.owner_linkedin || ""
                  };
                const uploadPayloadGrowjo = basePayload;
                
                // 1. Call upload_leads API (same as first enrichment)
                try {
                  const uploadRes = await axios.post(
                    `${DATABASE_URL}/upload_leads`,
                    JSON.stringify([uploadPayloadGrowjo]),
                    { headers: { "Content-Type": "application/json" }, withCredentials: true }
                  );
                  const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
                  const leadFromResponse = detailedResults[0] || {};
                  if (!lead_id && leadFromResponse.lead_id) {
                    lead_id = leadFromResponse.lead_id;
                    uploadPayloadGrowjo.lead_id = lead_id;
                  }
                  console.log(`✅ Uploaded enriched data for ${company.company}`);
                } catch (uploadErr) {
                  console.error("❌ Failed to upload lead:", uploadPayloadGrowjo, uploadErr);
                }
                
                // 2. Call drafts API (same as first enrichment)
                let draft_id = null;
                try {
                  const draftRes = await axios.post(
                    `${DATABASE_URL}/leads/drafts`,
                    {
                      lead_id,
                      draft_data: uploadPayloadGrowjo,
                      change_summary: "Second enrichment draft",
                    },
                    {
                      headers: { "Content-Type": "application/json" },
                      withCredentials: true,
                    }
                  );
                  draft_id = draftRes.data?.draft_id;
                  console.log(`✅ Created draft for enriched company ${company.company}, draft_id: ${draft_id}`);
                } catch (draftErr) {
                  console.error("❌ Failed to create draft:", draftErr);
                }
                
                // 3. Call deduct credit API (same as first enrichment)
                try {
                  if (lead_id) {
                    await axios.post(
                      `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                      { type: generateDeductType('second enrichment', 'companies', 'growjo') },
                      { withCredentials: true }
                    );
                    console.log(`✅ Deducted credit for enriched company ${company.company}`);
                  }
                } catch (deductErr) {
                  console.error(`❌ Credit deduction failed for lead ${lead_id}`, deductErr);
                }
                
                // Update the growjoResults with draft_id
                const lastIndex = growjoResults.length - 1;
                if (lastIndex >= 0) {
                  growjoResults[lastIndex] = { ...growjoResults[lastIndex], draft_id };
                }
              } catch (uploadErr) {
                console.error(`❌ Failed to upload enriched data for ${company.company}:`, uploadErr);
              }
            } else {
              console.log(`⚠️ No company data found for ${company.company} from Growjo`);
            }
          } catch (err) {
            console.error(`❌ Growjo company API failed for ${company.company}:`, err);
          }
        }
      }

      // Step 5: Call Apollo API for remaining companies (ensuring Apollo is always called as fallback)
      // Apollo is the final fallback - it will be called for ALL companies that still need enrichment,
      // regardless of whether they have lead_id or whether the Growjo companies API worked
      console.log("🔍 Step 5: Calling Apollo API for remaining companies...");
      console.log(`📊 Companies still needing enrichment: ${companiesWithoutIds.length}`);
      console.log(`📊 Companies with lead_id: ${companiesWithoutIds.filter(c => c.lead_id).length}`);
      console.log(`📊 Companies without lead_id: ${companiesWithoutIds.filter(c => !c.lead_id).length}`);
      
      // 🆕 DEBUG: Log each company that will be processed by Apollo (same as first enrichment)
      console.log("🔍 Companies to be processed by Apollo:");
      companiesWithoutIds.forEach((company, index) => {
        console.log(`  ${index + 1}. ${company.company} (lead_id: ${company.lead_id || 'none'}, website: ${company.website || 'none'})`);
      });
      
      let apolloResults: any[] = [];
      const companiesStillNeedingEnrichment = [...companiesWithoutIds];
      
      if (companiesStillNeedingEnrichment.length > 0) {
        try {
          // Process each company individually using enhanced Apollo function
          for (const company of companiesStillNeedingEnrichment) {
            console.log(`🚀 Calling enhanced Apollo company enrichment for ${company.company}`);
            
            const result = await apolloEnrichCompany(company);

            if (result && Object.keys(result).length > 0) {
              
              // Map Apollo data to consistent format
              const mappedApolloData = mapApolloData(result);
              console.log(`🔍 Mapped Apollo data for ${company.company}:`, mappedApolloData);
              
              // Use unified prioritization function for consistent data merging
              const enrichedCompany = {
                ...company,
                // Use mapped Apollo data for location fields, fallback to original if not available
                city: prioritizeData(mappedApolloData.city, company.city),
                state: prioritizeData(mappedApolloData.state, company.state),
                country: prioritizeData(mappedApolloData.country, company.country),
                street: prioritizeData(mappedApolloData.street, company.street),
                
                // Keep original values for these fields (no changes)
                industry: company.industry,
                bbb_rating: company.bbb_rating,
                
                // Apply improved logic for these fields (pick best value)
                revenue: prioritizeData(mappedApolloData.revenue, company.revenue),
                employees: prioritizeData(mappedApolloData.employees, company.employees),
                year_founded: prioritizeData(mappedApolloData.year_founded, company.year_founded),
                company_linkedin: prioritizeData(mappedApolloData.company_linkedin, company.company_linkedin),
                company_phone: prioritizeData(mappedApolloData.company_phone, company.company_phone || company.business_phone),
                
                // Use mapped data from Apollo for website and product_category
                website: prioritizeData(mappedApolloData.website, company.website),
                product_category: prioritizeData(mappedApolloData.product_category, company.product_category),
                business_type: prioritizeData(mappedApolloData.business_type, company.business_type),
                
                source: "Apollo (Second Enrichment)"
              };
              
              // Convert to camelCase for display (draft_id will be added later)
              const enrichedCompanyCamelCase = toCamelCase({ ...enrichedCompany, source_type: "scraped", lead_id: company.lead_id });
              apolloResults.push(enrichedCompanyCamelCase);
              
              // Use same API calls as first enrichment with proper data mapping
              let lead_id = company.lead_id;
              
              // Get people data from first enrichment
              const peopleFromFirstEnrichment = getPeopleFromEnrichedData(company.company, enrichedData);
              console.log(`🔍 Found ${peopleFromFirstEnrichment.length} people from first enrichment for ${company.company}`);
              
              const basePayload = {
                user_id,
                lead_id,
                company: enrichedCompany.company,
                website: enrichedCompany.website,
                industry: enrichedCompany.industry,
                product_category: enrichedCompany.product_category || "",
                business_type: enrichedCompany.business_type || "",
                employees: enrichedCompany.employees || "",
                revenue: formatRevenueForDisplay(enrichedCompany.revenue || ""),
                year_founded: enrichedCompany.year_founded || "",
                bbb_rating: enrichedCompany.bbb_rating || "",
                street: enrichedCompany.street || "",
                city: enrichedCompany.city || "",
                state: enrichedCompany.state || "",
                country: enrichedCompany.country || "",
                company_phone: enrichedCompany.company_phone || "",
                company_linkedin: enrichedCompany.company_linkedin || "",
                source: enrichedCompany.source,
                contacts: peopleFromFirstEnrichment,
                owner_linkedin: peopleFromFirstEnrichment[0]?.owner_linkedin || ""
              };
              const uploadPayloadApollo = basePayload;
              
              // 1. Call upload_leads API (same as first enrichment)
              try {
                const uploadRes = await axios.post(
                  `${DATABASE_URL}/upload_leads`,
                  JSON.stringify([uploadPayloadApollo]),
                  { headers: { "Content-Type": "application/json" }, withCredentials: true }
                );
                const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
                const leadFromResponse = detailedResults[0] || {};
                if (!lead_id && leadFromResponse.lead_id) {
                  lead_id = leadFromResponse.lead_id;
                  uploadPayloadApollo.lead_id = lead_id;
                }
                console.log(`✅ Uploaded Apollo enriched data for ${(result as any).company}`);

                // 2. Call drafts API (same as first enrichment)
                let draft_id = null;
                try {
                  const draftRes = await axios.post(
                    `${DATABASE_URL}/leads/drafts`,
                    {
                      lead_id,
                      draft_data: uploadPayloadApollo,
                      change_summary: "Second enrichment draft",
                    },
                    {
                      headers: { "Content-Type": "application/json" },
                      withCredentials: true,
                    }
                  );
                  draft_id = draftRes.data?.draft_id;
                  console.log(`✅ Created draft for Apollo enriched company ${(result as any).company}, draft_id: ${draft_id}`);

                  // 3. Call deduct credit API (same as first enrichment)
                  try {
                    if (lead_id) {
                      await axios.post(
                        `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                        { type: generateDeductType('second enrichment', 'companies', 'apollo') },
                        { withCredentials: true }
                      );
                      console.log(`💳 Deducted credit for Apollo enriched company ${(result as any).company}`);
                    }
                  } catch (deductErr) {
                    console.error(`❌ Credit deduction failed for lead ${lead_id}`, deductErr);
                  }
                  
                  // Update the apolloResults with draft_id
                  const lastIndex = apolloResults.length - 1;
                  if (lastIndex >= 0) {
                    apolloResults[lastIndex] = { ...apolloResults[lastIndex], draft_id };
                  }
                } catch (draftErr) {
                  console.error(`❌ Failed to create draft for Apollo enriched company:`, draftErr);
                }
              } catch (uploadErr) {
                console.error(`❌ Failed to upload Apollo enriched data for ${(result as any).company}:`, uploadErr);
              }
            } else {
              console.log(`⚠️ No data found for ${company.company} from enhanced Apollo enrichment (both DATABASE_URL and BACKEND_URL failed)`);
            }
          }
        } catch (err) {
          console.error("❌ Apollo enrichment failed:", err);
        }
      }

      // Combine all results
      const allResults = [...dbRows, ...growjoResults, ...apolloResults];
      setSecondEnrichmentResults(allResults);
      setShowSecondEnrichmentResults(true);
      
      // 🆕 FIXED: Set second enrichment results directly without merging (same as first enrichment)
      const dbResults = allResults.filter(r => r.sourceType === "database");
      const scrapedResults = allResults.filter(r => r.sourceType === "scraped");
      
      setSecondDbEnrichedCompanies(dbResults);
      setSecondScrapedEnrichedCompanies(scrapedResults);
      setSecondEnrichmentType("company");
      setHasSecondEnrichment(true);
      
      showNotification(`Successfully enriched ${allResults.length} companies!`, "success");
      
    } catch (error) {
      console.error("Second company enrichment error:", error);
      showNotification("Second enrichment failed. Please try again.", "error");
      hasErrorsRef.current = true;
      setHasErrors(true);
    } finally {
      setSecondEnrichmentLoading(false);
    }
  };

  const handleSecondPeopleEnrichment = async (companyIds: number[], enrichedData?: any[]) => {
    console.log(`🚀 Starting Second People Enrichment for ${companyIds.length} companies...`);
    
    if (companyIds.length === 0) {
      showNotification("Please select companies to enrich people data", "error");
      return;
    }

    if (companyIds.length > 25) {
      showNotification("Maximum 25 leads allowed for enrichment", "error");
      return;
    }
    
    if (secondEnrichmentLoading) {
      showNotification("Second enrichment already in progress. Please wait.", "info");
      return;
    }

    const user = JSON.parse(sessionStorage.getItem("user") || "{}");
    const user_id = user.user_id || "";
    setSecondEnrichmentLoading(true);
    setHasErrors(false);
    hasErrorsRef.current = false;

    try {
      // Use enriched data if provided, otherwise fall back to original leads
      const selected = enrichedData || normalizedLeads.filter(c => companyIds.includes(c.id));
      
      // Check credits first
      try {
        const { data: subscriptionInfo } = await axios.get(
          `${DATABASE_URL}/user/subscription_info`,
          { withCredentials: true }
        );

        const plan = subscriptionInfo?.plan;
        const isUnlimited =
          plan?.initial_credits === null ||
          (plan?.features_json && plan.features_json.includes("Unlimited Credits"));

        if (!isUnlimited) {
          const availableCredits = subscriptionInfo?.subscription?.credits_remaining ?? 0;
          const requiredCredits = selected.length;
          if (availableCredits < requiredCredits) {
            setShowTokenPopup(true);
            setSecondEnrichmentLoading(false);
            return;
          }
        }
      } catch (checkErr) {
        console.error("❌ Failed to verify subscription:", checkErr);
        showNotification("Failed to verify your subscription. Please try again later.", "error");
        setSecondEnrichmentLoading(false);
        return;
      }

      // Step 1: Check database for existing people data
      console.log("🔍 Step 1: Checking database for existing people data...");
      let dbRows: any[] = [];
      let companiesNeedingEnrichment: any[] = [];

      const leadIds = selected.map(c => c.lead_id).filter((id): id is string => Boolean(id));
      const companyNames = selected.map(c => c.company).filter((name): name is string => Boolean(name));
      
      // Always try database lookup, even with empty leadIds (will use search_companies)
      try {
        const dbLeads = await fetchCompaniesWithFallback(leadIds, companyNames);

        for (const company of selected) {
          // For companies without lead_id, try to find by company name (case insensitive)
          const dbLead = dbLeads.find((l: any) => 
            l.lead_id === company.lead_id || 
            (company.lead_id ? false : l.company?.toLowerCase() === company.company?.toLowerCase())
          );
            if (dbLead) {
              // Check if this company has people data
              const hasPeopleData = 
                dbLead.owner_first_name && dbLead.owner_first_name !== "N/A" &&
                dbLead.owner_last_name && dbLead.owner_last_name !== "N/A" &&
                dbLead.owner_email && dbLead.owner_email !== "N/A";

              if (hasPeopleData) {
                // 🤖 NEW: Check if business_type already exists, if not call business type decider (same as first enrichment)
                let businessType = dbLead.business_type || dbLead.businessType || "";
                if (!businessType || businessType === "N/A" || businessType.trim() === "") {
                  console.log(`🤖 Calling business type decider for second enrichment people database company: ${company.company} (no existing business_type)`);
                  const products = dbLead.product_category || dbLead.productCategory || "";
                  const industry = dbLead.industry || company.company || "";
                  businessType = await callBusinessTypeDecider(products, industry);
                  console.log(`✅ Updated ${company.company} with business type: ${businessType}`);
                } else {
                  console.log(`✅ ${company.company} already has business type: ${businessType}, skipping API call`);
                }
                
                const enrichedCompany = toCamelCase({ ...dbLead, businessType, source_type: "database" });
                console.log(`🔍 DEBUG: Database data for ${company.company}:`, JSON.stringify(enrichedCompany, null, 2));
                dbRows.push(enrichedCompany);
                console.log(`✅ ${company.company} has people data in database`);
                
                // 🆕 NEW: Process database companies through upload/draft/credit flow (same as first enrichment)
                try {
                  // Get people data from first enrichment first
                  const peopleFromFirstEnrichment = getPeopleFromEnrichedData(company.company, enrichedData);
                  console.log(`🔍 Found ${peopleFromFirstEnrichment.length} people from first enrichment for ${company.company}`);
                  
                  // Map people/contacts from dbLead (same as first enrichment)
                  const contacts = [...peopleFromFirstEnrichment]; // Start with first enrichment people
                  
                  if (Array.isArray(dbLead.people) && dbLead.people.length > 0) {
                    // Add database people if available (avoid duplicates)
                    const dbContacts = dbLead.people.map((person: any) => ({
                      owner_first_name: person.name?.split(' ')[0] || person.first_name || "",
                      owner_last_name: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
                      owner_title: person.title || "",
                      owner_email: person.email || "",
                      owner_phone_number: person.phone || person.phone_number || "",
                      owner_linkedin: person.linkedin || person.linkedin_url || ""
                    }));
                    
                    // Add database contacts that don't already exist
                    dbContacts.forEach((dbContact: any) => {
                      const exists = contacts.some(existing => 
                        existing.owner_first_name === dbContact.owner_first_name &&
                        existing.owner_last_name === dbContact.owner_last_name
                      );
                      if (!exists) {
                        contacts.push(dbContact);
                      }
                    });
                  } else if (dbLead.owner_first_name || dbLead.owner_last_name || dbLead.owner_email) {
                    // Add owner fields if people array not available and not already in first enrichment
                    const ownerContact = {
                      owner_first_name: dbLead.owner_first_name || "",
                      owner_last_name: dbLead.owner_last_name || "",
                      owner_title: dbLead.owner_title || "",
                      owner_email: dbLead.owner_email || "",
                      owner_phone_number: dbLead.owner_phone_number || "",
                      owner_linkedin: dbLead.owner_linkedin || ""
                    };
                    
                    const exists = contacts.some(existing => 
                      existing.owner_first_name === ownerContact.owner_first_name &&
                      existing.owner_last_name === ownerContact.owner_last_name
                    );
                    if (!exists) {
                      contacts.push(ownerContact);
                    }
                  }
                  
                  if (contacts.length > 0) {
                    // Use enriched data from first enrichment, fallback to dbLead for missing fields
                    const companyData = {
                      user_id: user_id,
                      lead_id: company.lead_id || "",
                      company: company.company || dbLead.company,
                      website: company.website || dbLead.website,
                      industry: company.industry || dbLead.industry,
                      product_category: company.productCategory || company.product_category || dbLead.product_category || "",
                      business_type: company.businessType || company.business_type || dbLead.business_type || "",
                      employees: company.employees || dbLead.employees || "",
                      revenue: company.revenue || dbLead.revenue || "",
                      year_founded: company.yearFounded || company.year_founded || dbLead.year_founded || "",
                      bbb_rating: company.bbbRating || company.bbb_rating || dbLead.bbb_rating || "",
                      street: company.street || dbLead.street || "",
                      city: company.city || dbLead.city || "",
                      state: company.state || dbLead.state || "",
                      country: company.country || dbLead.country || "",
                      company_phone: company.companyPhone || company.company_phone || dbLead.company_phone || "",
                      company_linkedin: company.companyLinkedin || company.company_linkedin || dbLead.company_linkedin || "",
                      owner_linkedin: contacts[0]?.owner_linkedin || company.ownerLinkedin || company.owner_linkedin || dbLead.owner_linkedin || "N/A",
                      source: "Database (Second Enrichment)",
                      contacts: contacts
                    };
                    
                    // Upload each company one by one (same as first enrichment)
                    const uploadPayload = [{
                      user_id: companyData.user_id,
                      lead_id: companyData.lead_id || "",
                      company: companyData.company,
                      website: companyData.website,
                      industry: companyData.industry,
                      product_category: companyData.product_category,
                      business_type: companyData.business_type,
                      employees: companyData.employees,
                      revenue: companyData.revenue,
                      year_founded: companyData.year_founded,
                      bbb_rating: companyData.bbb_rating,
                      street: companyData.street,
                      city: companyData.city,
                      state: companyData.state,
                      country: companyData.country,
                      company_phone: companyData.company_phone,
                      company_linkedin: companyData.company_linkedin,
                      owner_linkedin: companyData.owner_linkedin,
                      source: companyData.source,
                      contacts: companyData.contacts
                    }];
                    
                    const uploadRes = await axios.post(
                      `${DATABASE_URL}/upload_leads`,
                      JSON.stringify(uploadPayload),
                      { headers: { "Content-Type": "application/json" }, withCredentials: true }
                    );
                    
                    const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
                    const leadFromResponse = detailedResults[0] || {};
                    const lead_id = leadFromResponse.lead_id || companyData.lead_id;
                    
                    // Create draft (same as first enrichment)
                    const draftPayload = {
                      lead_id: lead_id,
                      draft_data: {
                        user_id: companyData.user_id,
                        lead_id: lead_id,
                        company: companyData.company,
                        website: companyData.website,
                        industry: companyData.industry,
                        product_category: companyData.product_category,
                        business_type: companyData.business_type,
                        employees: companyData.employees,
                        revenue: companyData.revenue,
                        year_founded: companyData.year_founded,
                        bbb_rating: companyData.bbb_rating,
                        street: companyData.street,
                        city: companyData.city,
                        state: companyData.state,
                        country: companyData.country,
                        company_phone: companyData.company_phone,
                        company_linkedin: companyData.company_linkedin,
                        owner_linkedin: companyData.owner_linkedin,
                        source: companyData.source,
                        contacts: companyData.contacts
                      },
                      change_summary: `Second enrichment people from database`
                    };
                    
                    await axios.post(
                      `${DATABASE_URL}/leads/drafts`,
                      draftPayload,
                      {
                        headers: { "Content-Type": "application/json" },
                        withCredentials: true,
                      }
                    );
                    
                    // Deduct credit (same as first enrichment)
                    if (lead_id) {
                      await axios.post(
                        `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                        { type: generateDeductType('second enrichment', 'companies', 'db') },
                        { withCredentials: true }
                      );
                      console.log(`✅ Deducted credit for database company ${companyData.company}`);
                    }
                    
                    console.log(`✅ Processed database company ${companyData.company} through upload/draft/credit flow`);
                  }
                } catch (dbProcessErr) {
                  console.error(`❌ Failed to process database company ${company.company} through upload/draft/credit flow:`, dbProcessErr);
                }
              } else {
                companiesNeedingEnrichment.push(company);
                console.log(`⚠️ ${company.company} needs people enrichment - missing people data`);
              }
            } else {
              companiesNeedingEnrichment.push(company);
              console.log(`⚠️ ${company.company} not found in database, needs people enrichment`);
            }
          }
        } catch (err) {
          console.error("❌ Failed to fetch from database:", err);
          companiesNeedingEnrichment = selected;
        }

      // Step 2: Company lookup to get company_ids for Growjo
      console.log("🔍 Step 2: Company lookup to get company_ids...");
      let companiesWithIds: any[] = [];
      let companiesWithoutIds: any[] = [];

      if (companiesNeedingEnrichment.length > 0) {
        try {
          const companyNames = companiesNeedingEnrichment.map(c => c.company);
          const lookupResponse = await axios.post(
            `${DATABASE_URL}/growjo/companies`,
            { company_names: companyNames },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );

          if (lookupResponse.data && lookupResponse.data.company_batch_results) {
            const lookupResult = lookupResponse.data.company_batch_results;

            for (const company of companiesNeedingEnrichment) {
              // 🆕 FIXED: Handle the correct data structure - company_batch_results is an array
              const found = lookupResult.find((batch: any) => 
                batch.company_name?.toLowerCase() === company.company.toLowerCase()
              )?.items?.[0];
              
              if (found) {
                companiesWithIds.push({
                  ...company,
                  growjo_company_id: found.company_id,
                  growjo_company_data: found
                });
                console.log(`✅ Found company data for ${company.company} with company_id ${found.company_id}`);
              } else {
                companiesWithoutIds.push(company);
                console.log(`⚠️ No company data found for ${company.company}`);
              }
            }
          } else {
            companiesWithoutIds = companiesNeedingEnrichment;
          }
        } catch (err) {
          console.error("❌ Growjo companies API failed:", err);
          companiesWithoutIds = companiesNeedingEnrichment;
        }
      }

      // Step 3: Call Growjo API for people enrichment (same as first enrichment)
      console.log("🔍 Step 3: Calling Growjo API for people enrichment...");
      let growjoResults: any[] = [];
      let companiesWithPeople: any[] = [];
      
      if (companiesWithIds.length > 0) {
        for (const company of companiesWithIds) {
          try {
            console.log(`🔄 Calling Growjo people API for ${company.company} with company_id: ${company.growjo_company_id}`);
            console.log(`🌐 Endpoint: ${BACKEND_URL}/growjo/people/${company.growjo_company_id}`);
            
            const growjoResponse = await axios.post(
              `${BACKEND_URL}/growjo/people/${company.growjo_company_id}`,
              {},
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );

            if (growjoResponse.data && growjoResponse.data.data && growjoResponse.data.data.people && Array.isArray(growjoResponse.data.data.people)) {
              const people = growjoResponse.data.data.people;
              console.log(`✅ Found ${people.length} people from Growjo for ${company.company}`);
              
              // Map people to the correct format (same as first enrichment)
              const mappedPeople = people.map((p: any, idx: number) => ({
                ...p,
                company: company.company,
                website: company.website,
                industry: company.industry,
                id: p.id || `${company.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                sourceType: "scraped"
              }));

              growjoResults = growjoResults.concat(mappedPeople);

              // Prepare company data with contacts array for upload (same as first enrichment)
              if (mappedPeople.length > 0) {
                console.log(`📤 Preparing ${mappedPeople.length} people for upload for ${company.company}`);

                // Convert people to contacts format
                const contacts = mappedPeople.map((person: any) => ({
                  owner_first_name: person.name?.split(' ')[0] || person.first_name || "",
                  owner_last_name: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
                  owner_title: person.title || "",
                  owner_email: person.email || "",
                  owner_phone_number: person.phone || person.phone_number || "",
                  owner_linkedin: person.linkedin || person.linkedin_url || ""
                }));

                const companyData = {
                  user_id: user_id,
                  lead_id: company.lead_id || "",
                  company: company.company,
                  website: company.website,
                  industry: company.industry,
                  product_category: company.productCategory || company.product_category || "",
                  business_type: company.businessType || company.business_type || "",
                  employees: company.employees || "",
                  revenue: company.revenue || "",
                  year_founded: company.yearFounded || company.year_founded || "",
                  bbb_rating: company.bbbRating || company.bbb_rating || "",
                  street: company.street || "",
                  city: company.city || "",
                  state: company.state || "",
                  country: company.country || "",
                  company_phone: company.companyPhone || company.company_phone || "",
                  company_linkedin: company.companyLinkedin || company.company_linkedin || "",
                  owner_linkedin: (contacts[0]?.owner_linkedin) || company.ownerLinkedin || company.owner_linkedin || "N/A",
                  source: "Growjo",
                  contacts: contacts
                };

                companiesWithPeople.push(companyData);
              }
            } else {
              console.log(`⚠️ No people data found for ${company.company} from Growjo, but still processing through upload/draft/credit`);
              
              // 🆕 FIXED: Even when no people data, still process through upload/draft/credit
              const companyData = {
                user_id: user_id,
                lead_id: company.lead_id || "",
                company: company.company,
                website: company.website,
                industry: company.industry,
                product_category: company.productCategory || company.product_category || "",
                business_type: company.businessType || company.business_type || "",
                employees: company.employees || "",
                revenue: company.revenue || "",
                year_founded: company.yearFounded || company.year_founded || "",
                bbb_rating: company.bbbRating || company.bbb_rating || "",
                street: company.street || "",
                city: company.city || "",
                state: company.state || "",
                country: company.country || "",
                company_phone: company.companyPhone || company.company_phone || "",
                company_linkedin: company.companyLinkedin || company.company_linkedin || "",
                owner_linkedin: company.ownerLinkedin || company.owner_linkedin || "N/A",
                source: "Growjo (No People Data)",
                contacts: [] // Empty contacts array
              };

              companiesWithPeople.push(companyData);
            }
          } catch (err) {
            console.error(`❌ Growjo people API failed for ${company.company}:`, err);
          }
        }
      }

      // Upload all companies with people data (same as first enrichment)
      if (companiesWithPeople.length > 0) {
        console.log(`📤 Batch uploading ${companiesWithPeople.length} companies with contacts`);
        
        for (const companyData of companiesWithPeople) {
          try {
            // Upload each company one by one (same as first enrichment)
            const uploadPayload = [{
              user_id: companyData.user_id,
              lead_id: companyData.lead_id || "",
              company: companyData.company,
              website: companyData.website,
              industry: companyData.industry,
              product_category: companyData.product_category,
              business_type: companyData.business_type,
              employees: companyData.employees,
              revenue: companyData.revenue,
              year_founded: companyData.year_founded,
              bbb_rating: companyData.bbb_rating,
              street: companyData.street,
              city: companyData.city,
              state: companyData.state,
              country: companyData.country,
              company_phone: companyData.company_phone,
              company_linkedin: companyData.company_linkedin,
              owner_linkedin: companyData.owner_linkedin,
              source: companyData.source,
              contacts: companyData.contacts
            }];
            
            const uploadRes = await axios.post(
              `${DATABASE_URL}/upload_leads`,
              JSON.stringify(uploadPayload),
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            
            const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
            const leadFromResponse = detailedResults[0] || {};
            const lead_id = leadFromResponse.lead_id || companyData.lead_id;
            
            // Create draft (same as first enrichment)
            const draftPayload = {
              lead_id: lead_id,
              draft_data: {
                user_id: companyData.user_id,
                lead_id: lead_id,
                company: companyData.company,
                website: companyData.website,
                industry: companyData.industry,
                product_category: companyData.product_category,
                business_type: companyData.business_type,
                employees: companyData.employees,
                revenue: companyData.revenue,
                year_founded: companyData.year_founded,
                bbb_rating: companyData.bbb_rating,
                street: companyData.street,
                city: companyData.city,
                state: companyData.state,
                country: companyData.country,
                company_phone: companyData.company_phone,
                company_linkedin: companyData.company_linkedin,
                owner_linkedin: companyData.owner_linkedin,
                source: companyData.source,
                contacts: companyData.contacts
              },
              change_summary: `Second enrichment people from Growjo`
            };
            
            await axios.post(
              `${DATABASE_URL}/leads/drafts`,
              draftPayload,
              {
                headers: { "Content-Type": "application/json" },
                withCredentials: true,
              }
            );
            
            // Deduct credit (same as first enrichment)
            if (lead_id) {
              await axios.post(
                `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                { type: generateDeductType('second enrichment', 'people', 'growjo') },
                { withCredentials: true }
              );
              console.log(`✅ Deducted credit for ${companyData.company}`);
            }
            
            console.log(`✅ Uploaded people data for ${companyData.company}`);
          } catch (uploadErr) {
            console.error(`❌ Failed to upload people data for ${companyData.company}:`, uploadErr);
          }
        }
      }

      // Step 4: Call Apollo API for remaining companies (only for companies without Growjo company IDs)
      console.log("🔍 Step 4: Calling Apollo API for remaining companies...");
      let apolloResults: any[] = [];
      let apolloCompaniesWithPeople: any[] = [];
      
      // 🆕 FIXED: Only call Apollo for companies that never had Growjo company IDs
      // Companies with Growjo company IDs should go straight to upload/draft/credit regardless of results
      if (companiesWithoutIds.length > 0) {
        for (const company of companiesWithoutIds) {
          try {
            console.log(`🚀 Calling Apollo people enrichment for ${company.company}`);
            
            const apolloData = await apolloEnrichPeople(company);
            console.log("🔍 Apollo people enrichment response for", company.company, ":", apolloData);

            if (apolloData && Object.keys(apolloData).length > 0) {
              // Check if the response contains meaningful data (same as first enrichment)
              const hasMeaningfulData = (
                (apolloData as any).name && (apolloData as any).name !== "N/A" && (apolloData as any).name !== "None None" &&
                (apolloData as any).title && (apolloData as any).title !== "N/A" &&
                (apolloData as any).email && (apolloData as any).email !== "N/A" &&
                (apolloData as any).phone && (apolloData as any).phone !== "N/A" &&
                (apolloData as any).linkedin && (apolloData as any).linkedin !== "N/A"
              );
              
              if (hasMeaningfulData) {
                // Create a person object from the enriched data (same as first enrichment)
                const apolloPerson = {
                  name: (apolloData as any).name || `${(apolloData as any).first_name || ''} ${(apolloData as any).last_name || ''}`.trim(),
                  first_name: (apolloData as any).first_name || '',
                  last_name: (apolloData as any).last_name || '',
                  title: (apolloData as any).title || '',
                  email: (apolloData as any).email || '',
                  phone: (apolloData as any).phone || '',
                  phone_number: (apolloData as any).phone || '',
                  linkedin: (apolloData as any).linkedin || '',
                  linkedin_url: (apolloData as any).linkedin || '',
                  company: company.company,
                  website: company.website,
                  industry: company.industry,
                  id: `${company.id}-apollo-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                  sourceType: "scraped",
                  source: "Apollo (Second Enrichment)"
                };
                
                apolloResults.push(apolloPerson);
                console.log(`✅ Found 1 person from Apollo for ${company.company}`);

                // Prepare company data with contacts array for upload (same as first enrichment)
                const contacts = [{
                  owner_first_name: apolloPerson.first_name || "",
                  owner_last_name: apolloPerson.last_name || "",
                  owner_title: apolloPerson.title || "",
                  owner_email: apolloPerson.email || "",
                  owner_phone_number: apolloPerson.phone || "",
                  owner_linkedin: apolloPerson.linkedin || ""
                }];

                const companyData = {
                  user_id: user_id,
                  lead_id: company.lead_id || "",
                  company: company.company,
                  website: company.website,
                  industry: company.industry,
                  product_category: company.productCategory || company.product_category || "",
                  business_type: company.businessType || company.business_type || "",
                  employees: company.employees || "",
                  revenue: company.revenue || "",
                  year_founded: company.yearFounded || company.year_founded || "",
                  bbb_rating: company.bbbRating || company.bbb_rating || "",
                  street: company.street || "",
                  city: company.city || "",
                  state: company.state || "",
                  country: company.country || "",
                  company_phone: company.companyPhone || company.company_phone || "",
                  company_linkedin: company.companyLinkedin || company.company_linkedin || "",
                  owner_linkedin: apolloPerson.linkedin || company.ownerLinkedin || company.owner_linkedin || "N/A",
                  source: "Apollo (Second Enrichment)",
                  contacts: contacts
                };

                apolloCompaniesWithPeople.push(companyData);
              } else {
                console.log(`⚠️ Apollo returned no meaningful data for ${company.company}:`, apolloData);
              }
            } else {
              console.log(`❌ No people found for ${company.company} via Apollo`);
            }
          } catch (err) {
            console.error(`❌ Apollo people enrichment failed for ${company.company}:`, err);
          }
        }
      }

      // Upload all Apollo companies with people data (same as first enrichment)
      if (apolloCompaniesWithPeople.length > 0) {
        console.log(`📤 Batch uploading ${apolloCompaniesWithPeople.length} Apollo companies with contacts`);
        
        for (const companyData of apolloCompaniesWithPeople) {
          try {
            // Upload each company one by one (same as first enrichment)
            const uploadPayload = [{
              user_id: companyData.user_id,
              lead_id: companyData.lead_id || "",
              company: companyData.company,
              website: companyData.website,
              industry: companyData.industry,
              product_category: companyData.product_category,
              business_type: companyData.business_type,
              employees: companyData.employees,
              revenue: companyData.revenue,
              year_founded: companyData.year_founded,
              bbb_rating: companyData.bbb_rating,
              street: companyData.street,
              city: companyData.city,
              state: companyData.state,
              country: companyData.country,
              company_phone: companyData.company_phone,
              company_linkedin: companyData.company_linkedin,
              owner_linkedin: companyData.owner_linkedin,
              source: companyData.source,
              contacts: companyData.contacts
            }];
            
            const uploadRes = await axios.post(
              `${DATABASE_URL}/upload_leads`,
              JSON.stringify(uploadPayload),
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            
            const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
            const leadFromResponse = detailedResults[0] || {};
            const lead_id = leadFromResponse.lead_id || companyData.lead_id;
            
            // Create draft (same as first enrichment)
            const draftPayload = {
              lead_id: lead_id,
              draft_data: {
                user_id: companyData.user_id,
                lead_id: lead_id,
                company: companyData.company,
                website: companyData.website,
                industry: companyData.industry,
                product_category: companyData.product_category,
                business_type: companyData.business_type,
                employees: companyData.employees,
                revenue: companyData.revenue,
                year_founded: companyData.year_founded,
                bbb_rating: companyData.bbb_rating,
                street: companyData.street,
                city: companyData.city,
                state: companyData.state,
                country: companyData.country,
                company_phone: companyData.company_phone,
                company_linkedin: companyData.company_linkedin,
                owner_linkedin: companyData.owner_linkedin,
                source: companyData.source,
                contacts: companyData.contacts
              },
              change_summary: `Second enrichment people from Apollo`
            };
            
            await axios.post(
              `${DATABASE_URL}/leads/drafts`,
              draftPayload,
              {
                headers: { "Content-Type": "application/json" },
                withCredentials: true,
              }
            );
            
            // Deduct credit (same as first enrichment)
            if (lead_id) {
              await axios.post(
                `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                { type: generateDeductType('second enrichment', 'people', 'apollo') },
                { withCredentials: true }
              );
              console.log(`✅ Deducted credit for ${companyData.company}`);
            }
            
            console.log(`✅ Uploaded Apollo people data for ${companyData.company}`);
          } catch (uploadErr) {
            console.error(`❌ Failed to upload Apollo people data for ${companyData.company}:`, uploadErr);
          }
        }
      }

      // Combine all results - handle database results differently since they're already company objects
      const allPeopleResults = [...growjoResults, ...apolloResults];
      
      // 🆕 FIXED: Group people by company and create company objects with people arrays (same as first enrichment)
      const groupedByCompany = allPeopleResults.reduce((acc: Record<string, any>, person: any) => {
        const companyKey = person.company;
        if (!acc[companyKey]) {
          acc[companyKey] = {
            id: person.id || `${companyKey}-company-${Date.now()}`,
            lead_id: person.lead_id || "",
            company: person.company,
            website: person.website || "",
            industry: person.industry || "",
            productCategory: "",
            businessType: person.businessType || "",
            employees: null,
            revenue: "",
            yearFounded: "",
            bbbRating: "",
            street: "",
            city: "",
            state: "",
            companyPhone: "",
            companyLinkedin: "",
            // 🆕 FIXED: Populate owner fields from the first person (same as first enrichment)
            ownerFirstName: person.name?.split(' ')[0] || person.first_name || "",
            ownerLastName: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
            ownerTitle: person.title || "",
            ownerEmail: person.email || "",
            ownerPhoneNumber: person.phone || person.phone_number || "",
            ownerLinkedin: person.linkedin || person.linkedin_url || "",
            source: person.source || "Second Enrichment",
            sourceType: person.sourceType || "scraped",
            people: []
          };
        }
        // 🆕 FIXED: Create personData with simple mapping (same as first enrichment)
        const personData = {
          name: person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim(),
          title: person.title || '',
          email: person.email || '',
          phone: person.phone || person.phone_number || '',
          linkedin: person.linkedin || person.linkedin_url || '',
          company: person.company,
          website: person.website,
          industry: person.industry,
          id: person.id || `${person.company}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          source: person.source || "Second Enrichment",
          sourceType: person.sourceType || "scraped"
        };
        console.log(`🔍 DEBUG: personData for ${person.company}:`, JSON.stringify(personData, null, 2));
        acc[companyKey].people.push(personData);
        return acc;
      }, {});
      
      // 🆕 FIXED: Add database results directly to the final results (they're already company objects)
      const dbCompanyResults = dbRows.map((dbCompany: any) => {
        // Create people array from the database company data
        const people = [];
        if (dbCompany.people && Array.isArray(dbCompany.people)) {
          people.push(...dbCompany.people);
        } else if (dbCompany.ownerFirstName || dbCompany.ownerLastName || dbCompany.ownerEmail) {
          // Create a person object from owner fields
          people.push({
            name: `${dbCompany.ownerFirstName || ''} ${dbCompany.ownerLastName || ''}`.trim(),
            first_name: dbCompany.ownerFirstName || '',
            last_name: dbCompany.ownerLastName || '',
            title: dbCompany.ownerTitle || '',
            email: dbCompany.ownerEmail || '',
            phone: dbCompany.ownerPhoneNumber || '',
            linkedin: dbCompany.ownerLinkedin || '',
            company: dbCompany.company,
            website: dbCompany.website,
            industry: dbCompany.industry,
            id: `${dbCompany.company}-db-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            source: dbCompany.source || "Database (Second Enrichment)",
            sourceType: "database"
          });
        }
        
        return {
          ...dbCompany,
          people: people
        };
      });
      
      // Add database results to the grouped results
      dbCompanyResults.forEach((dbCompany: any) => {
        groupedByCompany[dbCompany.company] = dbCompany;
      });
      
      // Convert grouped results to array and populate owner fields from first person
      const companyResults = Object.values(groupedByCompany).map((company: any) => {
        // 🆕 FIXED: Populate owner fields from the first person in the people array (same as first enrichment)
        if (company.people && company.people.length > 0) {
          const firstPerson = company.people[0];
          return {
            ...company,
            ownerFirstName: firstPerson.name?.split(' ')[0] || firstPerson.first_name || "",
            ownerLastName: firstPerson.name?.split(' ').slice(1).join(' ') || firstPerson.last_name || "",
            ownerTitle: firstPerson.title || "",
            ownerEmail: firstPerson.email || "",
            ownerPhoneNumber: firstPerson.phone || firstPerson.phone_number || "",
            ownerLinkedin: firstPerson.linkedin || firstPerson.linkedin_url || ""
          };
        }
        return company;
      });
      
      // 🆕 FIXED: Set results in the correct state variables (same as first enrichment)
      const dbResults = companyResults.filter(r => r.sourceType === "database");
      const scrapedResults = companyResults.filter(r => r.sourceType === "scraped");
      
      console.log(`🔍 DEBUG: Final companyResults:`, JSON.stringify(companyResults, null, 2));
      console.log(`🔍 DEBUG: dbResults:`, JSON.stringify(dbResults, null, 2));
      console.log(`🔍 DEBUG: scrapedResults:`, JSON.stringify(scrapedResults, null, 2));
      
      // 🆕 FIXED: Only set second enrichment specific state variables (don't touch first enrichment results)
      setSecondDbEnrichedCompanies(dbResults);
      setSecondScrapedEnrichedCompanies(scrapedResults);
      
      // Also set the people results state variables for compatibility
      setDbPeopleResults(dbResults);
      setScrapedPeopleResults(scrapedResults);
      
      // Also set the second enrichment results for compatibility
      setSecondEnrichmentResults(companyResults);
      setShowSecondEnrichmentResults(true);
      
      // Update main results to show second enrichment results
      // For people enrichment, merge with existing company data
      const existingResults = [...dbEnrichedCompanies, ...scrapedEnrichedCompanies];
      const mergedResults = companyResults.map(newResult => {
        const existing = existingResults.find(existing => existing.company === newResult.company);
        if (existing) {
          // Merge people data with existing company data
          return {
            ...existing,
            ...newResult,
            // Keep the source type from the new enrichment
            sourceType: newResult.sourceType
          };
        }
        return newResult;
      });
      
      // Update the second enrichment results with merged data
      const mergedDbResults = mergedResults.filter(r => r.sourceType === "database");
      const mergedScrapedResults = mergedResults.filter(r => r.sourceType === "scraped");
      
      setSecondDbEnrichedCompanies(mergedDbResults);
      setSecondScrapedEnrichedCompanies(mergedScrapedResults);
      setSecondEnrichmentType("people");
      setHasSecondEnrichment(true);
      
      // 🆕 FIXED: Set the enrichment view type to people so the UI shows the people table
      setEnrichmentViewType("people");
      setShowPeopleResults(true);
      
      // Show success notification only if we have results (same as first enrichment)
      if (companyResults.length > 0) {
        showNotification(`Second people enrichment completed successfully! Found people for ${companyResults.length} companies.`);
      } else {
        showNotification("Second people enrichment completed but no results were found.", "error");
      }
      
    } catch (error) {
      console.error("Second people enrichment error:", error);
      showNotification("Second people enrichment failed. Please try again.", "error");
      hasErrorsRef.current = true;
      setHasErrors(true);
    } finally {
      setSecondEnrichmentLoading(false);
    }
  };


  // Smart people enrichment function using new apollo-enrich-people endpoint
  // This function ensures Apollo is always called as a fallback when:
  // 1. Company doesn't have lead_id, OR
  // 2. Growjo companies API fails, OR  
  // 3. Growjo enrichment fails
  // 
  // IMPORTANT: Apollo will be called for ALL companies that need people enrichment,
  // regardless of whether they have lead_id or whether the Growjo companies API worked.
  const handleSmartPeopleEnrichment = async () => {
    if (selectedCompanies.length === 0) {
      showNotification("Please select companies to enrich people data", "error");
      return;
    }

    if (selectedCompanies.length > 25) {
      showNotification("Maximum 25 leads allowed for enrichment", "error");
      return;
    }
    
    // 🆕 NEW: Prevent multiple enrichment functions from running simultaneously
    if (loading) {
      showNotification("Enrichment already in progress. Please wait.", "info");
      return;
    }

    // Get user info from session storage
    const user = JSON.parse(sessionStorage.getItem("user") || "{}");
    const user_id = user.user_id || "";

    // Check user credits
    try {
      const { data: subscriptionInfo } = await axios.get(
        `${DATABASE_URL}/user/subscription_info`,
        { withCredentials: true }
      );

      const plan = subscriptionInfo?.plan;
      const isUnlimited =
        plan?.initial_credits === null ||
        (plan?.features_json && plan.features_json.includes("Unlimited Credits"));

      if (!isUnlimited) {
        const availableCredits = subscriptionInfo?.subscription?.credits_remaining ?? 0;
        const requiredCredits = selectedCompanies.length;
        if (availableCredits < requiredCredits) {
          setShowTokenPopup(true);
          setLoading(false);
          return;
        }
      }
    } catch (checkErr) {
      console.error("❌ Failed to verify subscription:", checkErr);
      showNotification("Failed to verify your subscription. Please try again later.", "error");
      setLoading(false);
      return;
    }

    setLoading(true);
    setHasErrors(false);
    hasErrorsRef.current = false;
    
    // 🆕 NEW: Clear previous banner state when starting new enrichment
    setShowEmptyResultsBanner(false);
    setEmptyResultsInfo({
      hasDatabaseResults: false,
      hasScrapedResults: false,
      totalCompanies: 0,
      enrichmentType: "people"
    });
    
    // 🆕 REMOVED: Don't clear previous results to allow cumulative enrichment
    // Users can now add more companies to existing people enrichment results
    console.log("🔄 Starting people enrichment - will append to existing results");

    try {
      console.log("🚀 Starting Smart People Enrichment using new apollo-enrich-people endpoint...");
      
      // 🆕 NEW: Initialize local variable to track not found companies
      let notFoundCompaniesList: string[] = [];
      
      // Step 1: Check database for existing people data
      console.log("🔍 Step 1: Checking database for existing people data...");
      const companiesNeedingPeopleEnrichment: any[] = [];
      const databasePeopleResults: any[] = []; // Store database results for fallback
      
      // Get the actual company objects from normalizedLeads
      const selectedCompanyObjects = normalizedLeads.filter(c => selectedCompanies.includes(c.id));
      
      // Fetch data from database for selected companies
      const leadIds = selectedCompanyObjects.map(c => c.lead_id).filter((id): id is string => Boolean(id));
      const companyNames = selectedCompanyObjects.map(c => c.company).filter((name): name is string => Boolean(name));
      
      // Always try database lookup, even with empty leadIds (will use search_companies)
      try {
        const dbLeads = await fetchCompaniesWithFallback(leadIds, companyNames);

        for (const company of selectedCompanyObjects) {
          // For companies without lead_id, try to find by company name (case insensitive)
          const dbLead = dbLeads.find((l: any) => 
            l.lead_id === company.lead_id || 
            (company.lead_id ? false : l.company?.toLowerCase() === company.company?.toLowerCase())
          );
            if (dbLead) {
              // Check if we have meaningful people data (at least name and email)
              const hasMeaningfulPeopleData = 
                dbLead.owner_first_name && dbLead.owner_first_name !== "N/A" &&
                dbLead.owner_last_name && dbLead.owner_last_name !== "N/A" &&
                dbLead.owner_email && dbLead.owner_email !== "N/A";

              // Debug logging
              console.log(`🔍 ${company.company} people data check:`, {
                owner_first_name: dbLead.owner_first_name,
                owner_last_name: dbLead.owner_last_name,
                owner_email: dbLead.owner_email,
                owner_phone_number: dbLead.owner_phone_number,
                owner_title: dbLead.owner_title,
                hasMeaningfulPeopleData
              });

              if (!hasMeaningfulPeopleData) {
                companiesNeedingPeopleEnrichment.push(company);
                console.log(`⚠️ ${company.company} needs people enrichment - missing essential contact data`);
              } else {
                // Store database result for potential fallback (only if not already added)
                const existingPerson = databasePeopleResults.find(p => 
                  p.company === company.company && p.email === dbLead.owner_email
                );
                
                if (!existingPerson) {
                  const databasePerson = {
                    id: `${company.company}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                    lead_id: dbLead.lead_id, // Include the actual lead_id from database
                    name: `${dbLead.owner_first_name} ${dbLead.owner_last_name}`,
                    first_name: dbLead.owner_first_name,
                    last_name: dbLead.owner_last_name,
                    title: dbLead.owner_title || "N/A",
                    email: dbLead.owner_email,
                    phone: dbLead.owner_phone_number || "N/A",
                    phone_number: dbLead.owner_phone_number || "N/A",
                    linkedin: dbLead.owner_linkedin || "N/A",
                    linkedin_url: dbLead.owner_linkedin || "N/A",
                    company: company.company,
                    website: company.website,
                    industry: company.industry,
                    source: "Database"
                  };
                  databasePeopleResults.push(databasePerson);
                }
                console.log(`✅ ${company.company} has meaningful people data in database, stored for fallback`);
              }
            } else {
              // Company not in database, needs enrichment
              companiesNeedingPeopleEnrichment.push(company);
              console.log(`⚠️ ${company.company} not found in database, needs people enrichment`);
            }
          }
        } catch (err) {
          console.error("❌ Failed to fetch from database:", err);
          companiesNeedingPeopleEnrichment.push(...selectedCompanyObjects); // Fallback to enriching all
        }

      if (companiesNeedingPeopleEnrichment.length === 0) {
        // 🆕 FIXED: Even if no enrichment needed, we should still show the database results
        if (databasePeopleResults.length > 0) {
          console.log(`✅ All companies have complete people data, showing ${databasePeopleResults.length} database results`);
          
          // Set the database results in state
          setDbPeopleResults(databasePeopleResults);
          
          // Convert database results to the format expected by the table
          const groupedByCompany = databasePeopleResults.reduce((acc: Record<string, any>, person: any) => {
            const companyKey = person.company;
            if (!acc[companyKey]) {
              acc[companyKey] = {
                id: `company-${Date.now()}-${Math.random()}`,
                lead_id: person.lead_id, // Include the lead_id from the person data
                company: person.company,
                website: person.website,
                industry: person.industry,
                productCategory: "",
                businessType: "",
                employees: null,
                revenue: "",
                yearFounded: "",
                bbbRating: "",
                street: "",
                city: "",
                state: "",
                companyPhone: "",
                companyLinkedin: "",
                ownerFirstName: "",
                ownerLastName: "",
                ownerTitle: "",
                ownerLinkedin: "",
                ownerPhoneNumber: "",
                ownerEmail: "",
                source: "Database",
                sourceType: "database" as const,
                people: []
              };
            }
            // Convert person format to match what EnrichmentResults expects
            const personData = {
              name: person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim(),
              title: person.title || '',
              email: person.email || '',
              phone: person.phone || person.phone_number || '',
              linkedin: person.linkedin || person.linkedin_url || '',
              company: person.company,
              website: person.website,
              industry: person.industry,
              id: `${person.company}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              source: person.source || "Database",
              // Also include the original contact fields for compatibility
              owner_first_name: person.first_name || '',
              owner_last_name: person.last_name || '',
              owner_title: person.title || '',
              owner_email: person.email || '',
              owner_phone_number: person.phone || person.phone_number || '',
              owner_linkedin: person.linkedin || person.linkedin_url || ''
            };
            acc[companyKey].people.push(personData);
            return acc;
          }, {} as Record<string, any>);

          const enrichedPeopleData = Object.values(groupedByCompany) as EnrichedCompany[];
          
          // 🆕 NEW: Process database people data through upload/draft/deduct flow
          console.log("🔍 Processing database people data through upload/draft/deduct flow...");
          let processedPeopleResults: any[] = [];
          
          for (const company of enrichedPeopleData) {
            try {
              // Prepare contacts array for upload
              const contacts = company.people?.map((person: any) => ({
                owner_first_name: person.owner_first_name || person.name?.split(' ')[0] || person.first_name || "",
                owner_last_name: person.owner_last_name || person.name?.split(' ').slice(1).join(' ') || "",
                owner_title: person.owner_title || person.title || "",
                owner_email: person.owner_email || person.email || "",
                owner_phone_number: person.owner_phone_number || person.phone || person.phone_number || "",
                owner_linkedin: person.owner_linkedin || person.linkedin || person.linkedin_url || ""
              })) || [];

              // Get the real lead_id from the company object
              const realLeadId = company.lead_id;
              
              // Prepare upload payload
              const basePayload = {
                user_id,
                lead_id: realLeadId || `temp-${Date.now()}-${Math.random()}`,
                company: company.company,
                website: company.website || "",
                industry: company.industry || "",
                owner_linkedin: contacts[0]?.owner_linkedin || "",
                product_category: company.productCategory || "",
                business_type: company.businessType || "",
                employees: company.employees || 0,
                revenue: company.revenue || 0,
                year_founded: company.yearFounded || 0,
                bbb_rating: company.bbbRating || "",
                street: company.street || "",
                city: company.city || "",
                state: company.state || "",
                company_phone: company.companyPhone || "",
                company_linkedin: company.companyLinkedin || "",
                source: company.source || "Database People Enrichment",
                contacts: contacts
              };

              // 1. Upload lead
              let lead_id = basePayload.lead_id;
              try {
                const uploadRes = await axios.post(
                  `${DATABASE_URL}/upload_leads`,
                  JSON.stringify([basePayload]),
                  { headers: { "Content-Type": "application/json" }, withCredentials: true }
                );
                
                if (uploadRes.data?.stats?.detailed_results?.[0]?.lead_id) {
                  lead_id = uploadRes.data.stats.detailed_results[0].lead_id;
                  console.log(`✅ Uploaded database people data for ${company.company}, lead_id: ${lead_id}`);
                }
              } catch (uploadErr) {
                console.error(`❌ Failed to upload database people data for ${company.company}:`, uploadErr);
              }

              // 2. Create draft
              try {
                await axios.post(
                  `${DATABASE_URL}/leads/drafts`,
                  {
                    lead_id,
                    draft_data: { ...basePayload, lead_id },
                    change_summary: "Database people enrichment completed"
                  },
                  { withCredentials: true }
                );
                console.log(`✅ Created draft for database people data: ${company.company}`);
              } catch (draftErr) {
                console.error(`❌ Failed to create draft for database people data ${company.company}:`, draftErr);
              }

              // 3. Deduct credit
              try {
                if (lead_id && !lead_id.startsWith('temp-')) {
                  await axios.post(
                    `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                    { type: generateDeductType('first enrichment', 'people', 'db') },
                    { withCredentials: true }
                  );
                  console.log(`✅ Deducted credit for database people enrichment: ${company.company}`);
                }
              } catch (deductErr) {
                console.error(`❌ Credit deduction failed for database people enrichment ${lead_id}:`, deductErr);
              }

              processedPeopleResults.push({ ...basePayload, lead_id, people: contacts });
              
            } catch (err) {
              console.error(`❌ Failed to process database people data for ${company.company}:`, err);
            }
          }
          
          // Update the state to show results - append instead of replace
          setEnrichedCompanies(prev => {
            const existingCompanies = new Set(prev.map(company => company.company));
            const uniqueNewResults = enrichedPeopleData.filter(company => !existingCompanies.has(company.company));
            return [...prev, ...uniqueNewResults];
          });
          setDbEnrichedCompanies(prev => {
            const existingCompanies = new Set(prev.map(company => company.company));
            const uniqueNewResults = enrichedPeopleData.filter(company => !existingCompanies.has(company.company));
            return [...prev, ...uniqueNewResults];
          });
          setScrapedEnrichedCompanies(prev => {
            // Keep existing scraped results and don't clear them
            return prev;
          });
          setFirstEnrichmentType("people");
          setHasFirstEnrichment(true);
            setShowResults(true);
            setEnrichmentViewType("people");
            setHasEnrichedOnce(true);
            
            // Set initial enrichment type if not already set
            if (!initialEnrichmentType) {
              setInitialEnrichmentType("people");
            }
            
            showNotification(`Database people enrichment completed! `, "success");
        } else {
          showNotification("All selected companies already have complete people data!", "success");
        }
        setLoading(false);
        return;
      }

      console.log(`📋 Found ${companiesNeedingPeopleEnrichment.length} companies needing people enrichment`);

      // Step 2: Company lookup to get company_ids for Growjo
      console.log("🔍 Step 2: Getting company_ids for Growjo people enrichment...");
      const growjoCompanyNames = companiesNeedingPeopleEnrichment.map(c => c.company);
      
      const lookupResponse = await axios.post(
        `${DATABASE_URL}/growjo/companies`,
        { company_names: growjoCompanyNames },
        { headers: { "Content-Type": "application/json" } }
      );

      // Debug logging for company lookup response
      console.log("🔍 Growjo companies API response:", lookupResponse.data);

      if (!lookupResponse.data || !lookupResponse.data.company_batch_results) {
        showNotification("Failed to get company data for people enrichment", "error");
        setLoading(false);
        return;
      }

      // Process the results to find companies with growjo_company_id
      let companiesWithIds: any[] = [];
      let companiesWithoutIds: any[] = [];

      for (const company of companiesNeedingPeopleEnrichment) {
        const lookupResult = lookupResponse.data.company_batch_results.find(
          (r: any) => r.company_name === company.company
        );
        if (lookupResult && lookupResult.items && lookupResult.items.length > 0) {
          const companyData = lookupResult.items[0];
          companiesWithIds.push({
            ...company,
            growjo_company_id: companyData.company_id,
            growjo_company_data: companyData
          });
          console.log(`✅ Found company data for ${company.company} with company_id ${companyData.company_id}`);
        } else {
          companiesWithoutIds.push(company);
          console.log(`⚠️ No company data found for ${company.company}, will use Apollo fallback`);
        }
      }

      console.log(`✅ Found ${companiesWithIds.length} companies with Growjo IDs, ${companiesWithoutIds.length} without`);

      // Step 3: Call Growjo API for companies with company_ids
      console.log("🔍 Step 3: Calling Growjo API for people enrichment...");
      let growjoPeopleResults: any[] = [];
      let companiesStillNeedingPeopleEnrichment: any[] = [];

      for (const company of companiesWithIds) {
        try {
          // 🆕 NEW: Check if we have people data from the batch response
          // Note: The current batch API doesn't include people data, so we'll still need to call the people API
          // But we can use the mapped company data for better context
          // Skip business type decider for people enrichment since it's not needed
          const mappedCompanyData = company.growjo_company_data ? await mapGrowjoCompanyData(company.growjo_company_data, true) : {};
          
          console.log(`🔄 Calling Growjo people API for ${company.company} with company_id: ${company.growjo_company_id}`);
          console.log(`🌐 Endpoint: ${BACKEND_URL}/growjo/people/${company.growjo_company_id}`);
          
          const growjoResponse = await axios.post(
            `${BACKEND_URL}/growjo/people/${company.growjo_company_id}`,
            {},
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );

          console.log(`✅ Growjo response for ${company.company}:`, growjoResponse.data);

          if (growjoResponse.data && growjoResponse.data.success) {
            const growjoData = growjoResponse.data.data;
            
            // Check if Growjo filled people data (using correct field names)
            const hasCompletePeopleDataAfterGrowjo = 
              growjoData.people && 
              Array.isArray(growjoData.people) && 
              growjoData.people.length > 0 &&
              growjoData.people.some((person: any) => 
                person.name && person.name !== "N/A" &&
                person.title && person.title !== "N/A" &&
                (person.email && person.email !== "N/A" || person.phone_number && person.phone_number !== "N/A")
              );
            
            console.log(`🔍 Growjo people data check for ${company.company}:`, {
              totalPeople: growjoData.people?.length || 0,
              samplePerson: growjoData.people?.[0],
              hasCompletePeopleDataAfterGrowjo
            });

            if (hasCompletePeopleDataAfterGrowjo) {
              // Growjo successfully enriched people data with proper field mapping
              const enrichedPeople = growjoData.people.map((person: any) => ({
                ...person,
                // Map phone_number to phone for compatibility
                phone: person.phone_number || person.phone || "N/A",
                phone_number: person.phone_number || person.phone || "N/A",
                // Ensure all required fields are present
                name: person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim() || "N/A",
                email: person.email || "N/A",
                title: person.title || "N/A",
                linkedin_url: person.linkedin || person.linkedin_url || "N/A",
                linkedin: person.linkedin || person.linkedin_url || "N/A",
                // Company context
                company: company.company,
                website: mappedCompanyData.website || company.website,
                industry: mappedCompanyData.industry || company.industry,
                source: "Growjo (Batch + People API)"
              }));

              growjoPeopleResults = [...growjoPeopleResults, ...enrichedPeople];
              console.log(`✅ ${company.company} successfully enriched people via Growjo: ${growjoData.people.length} people found`);
            } else {
              // Growjo didn't fill all missing people data, still needs enrichment
              companiesStillNeedingPeopleEnrichment.push(company);
              console.log(`⚠️ ${company.company} still needs people enrichment after Growjo`);
            }
          } else {
            // Growjo failed, add to companies still needing enrichment
            companiesStillNeedingPeopleEnrichment.push(company);
            console.error(`❌ Growjo people enrichment failed for ${company.company}:`, growjoResponse.data?.error);
          }
        } catch (err) {
          console.error(`❌ Growjo people API call failed for ${company.company}:`, err);
          companiesStillNeedingPeopleEnrichment.push(company);
        }
      }

      // Add companies without company_ids to the list needing enrichment
      companiesStillNeedingPeopleEnrichment = [...companiesStillNeedingPeopleEnrichment, ...companiesWithoutIds];

      // Step 4: Call NEW Apollo API for remaining companies using apollo-enrich-people endpoint
      console.log("🔍 Step 4: Calling NEW Apollo API (apollo-enrich-people) for remaining companies...");
      let apolloPeopleResults: any[] = [];

      for (const company of companiesStillNeedingPeopleEnrichment) {
        try {
          // 🆕 NEW: Use apollo-enrich-people endpoint with smart domain search logic
          console.log(`🚀 Calling Apollo people enrichment for ${company.company}`);
          
          const apolloData = await apolloEnrichPeople(company);
          console.log("🔍 Apollo people enrichment response for", company.company, ":", apolloData);

          if (apolloData && Object.keys(apolloData).length > 0) {
            // 🆕 NEW: Check if the response contains meaningful data (not just N/A values)
            const hasMeaningfulData = (
              (apolloData as any).name && (apolloData as any).name !== "N/A" && (apolloData as any).name !== "None None" &&
              (apolloData as any).title && (apolloData as any).title !== "N/A" &&
              (apolloData as any).email && (apolloData as any).email !== "N/A" &&
              (apolloData as any).phone && (apolloData as any).phone !== "N/A" &&
              (apolloData as any).linkedin && (apolloData as any).linkedin !== "N/A"
            );
            
            if (hasMeaningfulData) {
              // Create a person object from the enriched data
              const apolloPerson = {
                name: (apolloData as any).name || `${(apolloData as any).first_name || ''} ${(apolloData as any).last_name || ''}`.trim(),
                first_name: (apolloData as any).first_name || '',
                last_name: (apolloData as any).last_name || '',
                title: (apolloData as any).title || '',
                email: (apolloData as any).email || '',
                phone: (apolloData as any).phone || '',
                phone_number: (apolloData as any).phone || '',
                linkedin: (apolloData as any).linkedin || '',
                linkedin_url: (apolloData as any).linkedin || '',
                company: company.company,
                website: company.website,
                industry: company.industry,
                source: "Apollo (New Endpoint)"
              };

              apolloPeopleResults.push(apolloPerson);
              console.log(`✅ ${company.company} enriched people via NEW Apollo endpoint:`, apolloPerson);
            } else {
              // 🆕 NEW: No meaningful data found, add to not found companies
              console.log(`⚠️ Apollo apollo-enrich-people returned no meaningful data for ${company.company}:`, apolloData);
              notFoundCompaniesList.push(company.company);
            }
          } else {
            console.log(`⚠️ Apollo apollo-enrich-people returned no data for ${company.company}`);
          }
        } catch (err) {
          console.error(`❌ Apollo apollo-enrich-people failed for ${company.company}:`, err);
        }
      }

      // 🆕 NEW: Update not found companies state and show banner if needed
      if (notFoundCompaniesList.length > 0) {
        setNotFoundCompanies(notFoundCompaniesList);
        console.log(`⚠️ ${notFoundCompaniesList.length} companies had no meaningful people data:`, notFoundCompaniesList);
      }

      // Combine all results, including database results as fallback
      let allEnrichedPeople = [...growjoPeopleResults, ...apolloPeopleResults];
      
      // 🆕 FIXED: Set database people results in state so checkForEmptyResults can find them
      if (databasePeopleResults.length > 0) {
        setDbPeopleResults(databasePeopleResults);
        console.log(`✅ Set ${databasePeopleResults.length} database people results in state`);
      }
      
      // If no enrichment results but we have database results, use those
      if (allEnrichedPeople.length === 0 && databasePeopleResults.length > 0) {
        console.log(`🔄 No enrichment results found, falling back to database results:`, databasePeopleResults.length);
        allEnrichedPeople = [...databasePeopleResults];
        
        // 🆕 NEW: Process database people results through upload/draft/deduct flow
        console.log("🔍 Processing database people results through upload/draft/deduct flow...");
        
        // Group database people by company
        const groupedByCompany = databasePeopleResults.reduce((acc: Record<string, any>, person: any) => {
          const companyKey = person.company;
          if (!acc[companyKey]) {
            acc[companyKey] = {
              id: `company-${Date.now()}-${Math.random()}`,
              company: person.company,
              website: person.website || "",
              industry: person.industry || "",
              productCategory: "",
              businessType: "",
              employees: null,
              revenue: "",
              yearFounded: "",
              bbbRating: "",
              street: "",
              city: "",
              state: "",
              companyPhone: "",
              companyLinkedin: "",
              ownerFirstName: "",
              ownerLastName: "",
              ownerTitle: "",
              ownerLinkedin: "",
              ownerPhoneNumber: "",
              ownerEmail: "",
              source: "Database (Fallback)",
              sourceType: "database" as const,
              people: []
            };
          }
          acc[companyKey].people.push(person);
          return acc;
        }, {} as Record<string, any>);

        const enrichedPeopleData = Object.values(groupedByCompany) as EnrichedCompany[];
        
        // Process each company through upload/draft/deduct flow
        let processedPeopleResults: any[] = [];
        
        for (const company of enrichedPeopleData) {
          try {
            // Prepare contacts array for upload
            const contacts = company.people?.map((person: any) => ({
              owner_first_name: person.owner_first_name || person.name?.split(' ')[0] || person.first_name || "",
              owner_last_name: person.owner_last_name || person.name?.split(' ').slice(1).join(' ') || "",
              owner_title: person.owner_title || person.title || "",
              owner_email: person.owner_email || person.email || "",
              owner_phone_number: person.owner_phone_number || person.phone || person.phone_number || "",
              owner_linkedin: person.owner_linkedin || person.linkedin || person.linkedin_url || ""
            })) || [];

            // Prepare upload payload
            const basePayload = {
              user_id,
              lead_id: company.lead_id || `temp-${Date.now()}-${Math.random()}`,
              company: company.company,
              website: company.website || "",
              industry: company.industry || "",
              owner_linkedin: contacts[0]?.owner_linkedin || "",
              product_category: company.productCategory || "",
              business_type: company.businessType || "",
              employees: company.employees || 0,
              revenue: company.revenue || 0,
              year_founded: company.yearFounded || 0,
              bbb_rating: company.bbbRating || "",
              street: company.street || "",
              city: company.city || "",
              state: company.state || "",
              company_phone: company.companyPhone || "",
              company_linkedin: company.companyLinkedin || "",
              source: company.source || "Database People Enrichment",
              contacts: contacts
            };

            // 1. Upload lead
            let lead_id = basePayload.lead_id;
            try {
              const uploadRes = await axios.post(
                `${DATABASE_URL}/upload_leads`,
                JSON.stringify([basePayload]),
                { headers: { "Content-Type": "application/json" }, withCredentials: true }
              );
              
              if (uploadRes.data?.stats?.detailed_results?.[0]?.lead_id) {
                lead_id = uploadRes.data.stats.detailed_results[0].lead_id;
                console.log(`✅ Uploaded database people data for ${company.company}, lead_id: ${lead_id}`);
              }
            } catch (uploadErr) {
              console.error(`❌ Failed to upload database people data for ${company.company}:`, uploadErr);
            }

            // 2. Create draft
            try {
              await axios.post(
                `${DATABASE_URL}/leads/drafts`,
                {
                  lead_id,
                  draft_data: { ...basePayload, lead_id },
                  change_summary: "Database people enrichment completed"
                },
                { withCredentials: true }
              );
              console.log(`✅ Created draft for database people data: ${company.company}`);
            } catch (draftErr) {
              console.error(`❌ Failed to create draft for database people data ${company.company}:`, draftErr);
            }

            // 3. Deduct credit
            try {
              if (lead_id && !lead_id.startsWith('temp-')) {
                await axios.post(
                  `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                  { type: generateDeductType('second enrichment', 'people', 'db') },
                  { withCredentials: true }
                );
                console.log(`✅ Deducted credit for database people enrichment: ${company.company}`);
              }
            } catch (deductErr) {
              console.error(`❌ Credit deduction failed for database people enrichment ${lead_id}:`, deductErr);
            }

            processedPeopleResults.push({ ...basePayload, lead_id, people: contacts });
            
          } catch (err) {
            console.error(`❌ Failed to process database people data for ${company.company}:`, err);
          }
        }
        
        console.log(`✅ Processed ${processedPeopleResults.length} companies from database people results through upload/draft/deduct flow`);
      }
      
      console.log(`🔍 Final enrichment results:`, {
        growjoPeopleCount: growjoPeopleResults.length,
        apolloPeopleCount: apolloPeopleResults.length,
        databasePeopleCount: databasePeopleResults.length,
        totalEnrichedPeople: allEnrichedPeople.length
      });
      
      if (allEnrichedPeople.length > 0) {
        // Process and upload the enriched people data
        console.log(`🎉 People enrichment completed! Found ${allEnrichedPeople.length} people total`);
        
                    // Convert to contacts format for upload
            const contacts = allEnrichedPeople.map((person: any) => ({
              owner_first_name: person.name?.split(' ')[0] || person.first_name || "",
              owner_last_name: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
              owner_title: person.title || "",
              owner_email: person.email || "",
              owner_phone_number: person.phone || person.phone_number || "",
              owner_linkedin: person.linkedin || person.linkedin_url || "",
              company: person.company,
              website: person.website,
              industry: person.industry,
              source: person.source || "Unknown" // Preserve the source information
            }));

        console.log(`📋 Converted ${contacts.length} people to contacts format:`, contacts.slice(0, 2)); // Show first 2 for debugging

        // Upload enriched people data - FIXED: Send proper company structure with contacts
        try {
          // Group contacts by company and create proper upload payload
          const companiesToUpload = contacts.reduce((acc: Record<string, any>, contact: any) => {
            const companyKey = contact.company;
            if (!acc[companyKey]) {
              acc[companyKey] = {
                user_id: user_id,
                lead_id: "", // Empty string as shown in your example
                company: contact.company,
                website: contact.website,
                industry: contact.industry,
                owner_linkedin: contact.owner_linkedin || "N/A",
                source: contact.source || "Unknown",
                contacts: []
              };
            }
            acc[companyKey].contacts.push({
              owner_first_name: contact.owner_first_name,
              owner_last_name: contact.owner_last_name,
              owner_title: contact.owner_title,
              owner_email: contact.owner_email,
              owner_phone_number: contact.owner_phone_number,
              owner_linkedin: contact.owner_linkedin
            });
            return acc;
          }, {} as Record<string, any>);

          const uploadPayload = Object.values(companiesToUpload);
          console.log(`📤 Uploading ${uploadPayload.length} companies with proper structure:`, JSON.stringify(uploadPayload, null, 2));

          const uploadRes = await axios.post(
            `${DATABASE_URL}/upload_leads`,
            JSON.stringify(uploadPayload),
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );

          if (uploadRes.data?.stats?.detailed_results) {
            showNotification(`Successfully enriched ${allEnrichedPeople.length} people!`, "success");
            
            // 🆕 NEW: Process upload response to create drafts and deduct credits
            console.log(`🔄 Processing upload response for drafts and credit deduction...`);
            const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
            
            // Process each company that was uploaded
            for (let i = 0; i < Math.min(uploadPayload.length, detailedResults.length); i++) {
              const companyData = uploadPayload[i];
              const uploadResult = detailedResults[i];
              const lead_id = uploadResult.lead_id;
              
              if (lead_id) {
                console.log(`📝 Creating draft for company ${companyData.company} with lead_id: ${lead_id}`);
                
                // Create draft
                try {
                  const draftPayload = {
                    lead_id: lead_id,
                    draft_data: {
                      user_id: companyData.user_id,
                      lead_id: lead_id,
                      company: companyData.company,
                      website: companyData.website,
                      industry: companyData.industry,
                      owner_linkedin: companyData.owner_linkedin,
                      source: companyData.source,
                      contacts: companyData.contacts
                    },
                    change_summary: "People enrichment from Smart People Enrichment"
                  };
                  
                  console.log(`📝 Draft payload for ${companyData.company}:`, JSON.stringify(draftPayload, null, 2));
                  
                  const draftRes = await axios.post(
                    `${DATABASE_URL}/leads/drafts`,
                    draftPayload,
                    {
                      headers: { "Content-Type": "application/json" },
                      withCredentials: true,
                    }
                  );
                  
                  const draft_id = draftRes.data?.draft_id;
                  if (draft_id) {
                    console.log(`✅ Created draft ${draft_id} for company ${companyData.company}`);
                  }
                } catch (draftErr: any) {
                  console.error(`❌ Failed to create draft for company ${companyData.company}:`, draftErr);
                }
                
                // Deduct credit
                try {
                  await axios.post(
                    `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                    { type: generateDeductType('first enrichment', 'people', 'db') },
                    { withCredentials: true }
                  );
                  console.log(`✅ Deducted 1 credit for company ${companyData.company}`);
                } catch (deductErr: any) {
                  console.error(`❌ Credit deduction failed for company ${companyData.company}:`, deductErr);
                }
              } else {
                console.error(`❌ No lead_id returned for company ${companyData.company}`);
              }
            }
            
            // Group contacts by company for proper display
            const groupedByCompany = contacts.reduce((acc: Record<string, any>, contact: any) => {
              const companyKey = contact.company;
              if (!acc[companyKey]) {
                acc[companyKey] = {
                  id: `company-${Date.now()}-${Math.random()}`,
                  company: contact.company,
                  website: contact.website,
                  industry: contact.industry,
                  productCategory: "",
                  businessType: "",
                  employees: null,
                  revenue: "",
                  yearFounded: "",
                  bbbRating: "",
                  street: "",
                  city: "",
                  state: "",
                  companyPhone: "",
                  companyLinkedin: "",
                  ownerFirstName: "",
                  ownerLastName: "",
                  ownerTitle: "",
                  ownerLinkedin: "",
                  ownerPhoneNumber: "",
                  ownerEmail: "",
                  source: "People Enrichment",
                  sourceType: "scraped" as const,
                  people: []
                };
              }
              // Convert contact format to match what EnrichmentResults expects
              const personData = {
                name: `${contact.owner_first_name || ''} ${contact.owner_last_name || ''}`.trim(),
                title: contact.owner_title || '',
                email: contact.owner_email || '',
                phone: contact.owner_phone_number || '',
                linkedin: contact.owner_linkedin || '',
                company: contact.company,
                website: contact.website,
                industry: contact.industry,
                id: `${contact.company}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                source: contact.source || "Unknown", // Preserve source for banner display
                // Also include the original contact fields for compatibility
                owner_first_name: contact.owner_first_name || '',
                owner_last_name: contact.owner_last_name || '',
                owner_title: contact.owner_title || '',
                owner_email: contact.owner_email || '',
                owner_phone_number: contact.owner_phone_number || '',
                owner_linkedin: contact.owner_linkedin || ''
              };
              acc[companyKey].people.push(personData);
              return acc;
            }, {} as Record<string, any>);

            const enrichedPeopleData = Object.values(groupedByCompany) as EnrichedCompany[];
            
            // Update the state to show results - append instead of replace
            setEnrichedCompanies(prev => {
              const existingCompanies = new Set(prev.map(company => company.company));
              const uniqueNewResults = enrichedPeopleData.filter(company => !existingCompanies.has(company.company));
              return [...prev, ...uniqueNewResults];
            });
            console.log(`✅ Updated enriched companies state with ${enrichedPeopleData.length} companies containing ${contacts.length} total contacts`);
            console.log(`🔍 Final enrichedPeopleData:`, enrichedPeopleData);
            
            // Update local state so the component renders - append instead of replace
            setDbEnrichedCompanies(prev => {
              const existingCompanies = new Set(prev.map(company => company.company));
              const uniqueNewResults = enrichedPeopleData.filter(company => !existingCompanies.has(company.company));
              return [...prev, ...uniqueNewResults];
            });
            setScrapedEnrichedCompanies(prev => {
              // Keep existing scraped results and don't clear them
              return prev;
            });
            setFirstEnrichmentType("people");
            setHasFirstEnrichment(true);
            
            // 🆕 FIXED: Set the people results state variables that checkForEmptyResults checks
            setScrapedPeopleResults(enrichedPeopleData);
            
            // Set the display state to show results
            setShowResults(true);
            setEnrichmentViewType("people");
            setHasEnrichedOnce(true);
            
            // Set initial enrichment type if not already set
            if (!initialEnrichmentType) {
              setInitialEnrichmentType("people");
            }
            
            // 🆕 FIXED: Pass actual results directly to checkForEmptyResults to avoid state timing issues
            const hasEmptyResults = checkForEmptyResults("people", databasePeopleResults, enrichedPeopleData);
            if (hasEmptyResults) {
              console.log("⚠️ No results found, showing empty results banner");
            } else {
              console.log("✅ Results found, hiding empty results banner");
            }
            
            // 🆕 REMOVED: Old credit deduction logic since we now do it per company above
          }
        } catch (uploadErr) {
          console.error("Failed to upload enriched people data:", uploadErr);
          showNotification("Failed to upload enriched people data", "error");
        }
      } else {
        // 🆕 FIXED: Handle case where no people data found at all
        console.log(`⚠️ No people data found for any companies`);
        
        // Check if we have any database results to show as fallback
        if (databasePeopleResults.length > 0) {
          console.log(`🔄 No enrichment results, but showing ${databasePeopleResults.length} database results as fallback`);
          
          // Set the database results in state
          setDbPeopleResults(databasePeopleResults);
          
          // Convert database results to the format expected by the table
          const groupedByCompany = databasePeopleResults.reduce((acc: Record<string, any>, person: any) => {
            const companyKey = person.company;
            if (!acc[companyKey]) {
              acc[companyKey] = {
                id: `company-${Date.now()}-${Math.random()}`,
                company: person.company,
                website: person.website,
                industry: person.industry,
                productCategory: "",
                businessType: "",
                employees: null,
                revenue: "",
                yearFounded: "",
                bbbRating: "",
                street: "",
                city: "",
                state: "",
                companyPhone: "",
                companyLinkedin: "",
                ownerFirstName: "",
                ownerLastName: "",
                ownerTitle: "",
                ownerLinkedin: "",
                ownerPhoneNumber: "",
                ownerEmail: "",
                source: "Database (Fallback)",
                sourceType: "database" as const,
                people: []
              };
            }
            // Convert person format to match what EnrichmentResults expects
            const personData = {
              name: person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim(),
              title: person.title || '',
              email: person.email || '',
              phone: person.phone || person.phone_number || '',
              linkedin: person.linkedin || person.linkedin_url || '',
              company: person.company,
              website: person.website,
              industry: person.industry,
              id: `${person.company}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              source: person.source || "Database (Fallback)",
              // Also include the original contact fields for compatibility
              owner_first_name: person.first_name || '',
              owner_last_name: person.last_name || '',
              owner_title: person.title || '',
              owner_email: person.email || '',
              owner_phone_number: person.phone || person.phone_number || '',
              owner_linkedin: person.linkedin || person.linkedin_url || ''
            };
            acc[companyKey].people.push(personData);
            return acc;
          }, {} as Record<string, any>);

          const enrichedPeopleData = Object.values(groupedByCompany) as EnrichedCompany[];
          
          // 🆕 NEW: Process enriched people data through upload/draft/deduct flow
          console.log("🔍 Step 6: Processing enriched people data through upload/draft/deduct flow...");
          let processedPeopleResults: any[] = [];
          
          for (const company of enrichedPeopleData) {
            try {
              // Prepare contacts array for upload
              const contacts = company.people?.map((person: any) => ({
                owner_first_name: person.owner_first_name || person.name?.split(' ')[0] || person.first_name || "",
                owner_last_name: person.owner_last_name || person.name?.split(' ').slice(1).join(' ') || "",
                owner_title: person.owner_title || person.title || "",
                owner_email: person.owner_email || person.email || "",
                owner_phone_number: person.owner_phone_number || person.phone || person.phone_number || "",
                owner_linkedin: person.owner_linkedin || person.linkedin || person.linkedin_url || ""
              })) || [];

              // Prepare upload payload
              const basePayload = {
                user_id,
                lead_id: company.lead_id || `temp-${Date.now()}-${Math.random()}`,
                company: company.company,
                website: company.website || "",
                industry: company.industry || "",
                owner_linkedin: contacts[0]?.owner_linkedin || "",
                product_category: company.productCategory || "",
                business_type: company.businessType || "",
                employees: company.employees || 0,
                revenue: company.revenue || 0,
                year_founded: company.yearFounded || 0,
                bbb_rating: company.bbbRating || "",
                street: company.street || "",
                city: company.city || "",
                state: company.state || "",
                company_phone: company.companyPhone || "",
                company_linkedin: company.companyLinkedin || "",
                source: company.source || "People Enrichment",
                contacts: contacts
              };

              // 1. Upload lead
              let lead_id = basePayload.lead_id;
              try {
                const uploadRes = await axios.post(
                  `${DATABASE_URL}/upload_leads`,
                  JSON.stringify([basePayload]),
                  { headers: { "Content-Type": "application/json" }, withCredentials: true }
                );
                
                if (uploadRes.data?.stats?.detailed_results?.[0]?.lead_id) {
                  lead_id = uploadRes.data.stats.detailed_results[0].lead_id;
                  console.log(`✅ Uploaded people data for ${company.company}, lead_id: ${lead_id}`);
                }
              } catch (uploadErr) {
                console.error(`❌ Failed to upload people data for ${company.company}:`, uploadErr);
              }

              // 2. Create draft
              try {
                await axios.post(
                  `${DATABASE_URL}/leads/drafts`,
                  {
                    lead_id,
                    draft_data: { ...basePayload, lead_id },
                    change_summary: "People enrichment completed"
                  },
                  { withCredentials: true }
                );
                console.log(`✅ Created draft for people data: ${company.company}`);
              } catch (draftErr) {
                console.error(`❌ Failed to create draft for people data ${company.company}:`, draftErr);
              }

              // 3. Deduct credit
              try {
                if (lead_id && !lead_id.startsWith('temp-')) {
                  await axios.post(
                    `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                    { type: generateDeductType('second enrichment', 'people', 'db') },
                    { withCredentials: true }
                  );
                  console.log(`✅ Deducted credit for people enrichment: ${company.company}`);
                }
              } catch (deductErr) {
                console.error(`❌ Credit deduction failed for people enrichment ${lead_id}:`, deductErr);
              }

              processedPeopleResults.push({ ...basePayload, lead_id, people: contacts });
              
            } catch (err) {
              console.error(`❌ Failed to process people data for ${company.company}:`, err);
            }
          }
          
          // Update the state to show results - append instead of replace
          setEnrichedCompanies(prev => {
            const existingCompanies = new Set(prev.map(company => company.company));
            const uniqueNewResults = enrichedPeopleData.filter(company => !existingCompanies.has(company.company));
            return [...prev, ...uniqueNewResults];
          });
          setDbEnrichedCompanies(prev => {
            const existingCompanies = new Set(prev.map(company => company.company));
            const uniqueNewResults = enrichedPeopleData.filter(company => !existingCompanies.has(company.company));
            return [...prev, ...uniqueNewResults];
          });
          setScrapedEnrichedCompanies(prev => {
            // Keep existing scraped results and don't clear them
            return prev;
          });
          setFirstEnrichmentType("people");
          setHasFirstEnrichment(true);
          setShowResults(true);
          setEnrichmentViewType("people");
          setHasEnrichedOnce(true);
          
          // Set initial enrichment type if not already set
          if (!initialEnrichmentType) {
            setInitialEnrichmentType("people");
          }
          
          showNotification(`People enrichment completed! Processed ${processedPeopleResults.length} companies through upload/draft/deduct flow.`, "success");
        } else {
          showNotification("No people data found for the selected companies", "info");
        }
      }

    } catch (error) {
      console.error("❌ Smart people enrichment failed:", error);
      showNotification("People enrichment failed. Please try again.", "error");
      setHasErrors(true);
    } finally {
      // 🆕 SUMMARY: This people enrichment function ensures maximum data coverage through fallback mechanisms:
      // 1. Companies without lead_id → Always processed by Apollo as fallback
      // 2. Companies where Growjo companies API failed → Always processed by Apollo as fallback
      // 3. Companies where Growjo failed → Always processed by Apollo as fallback
      // 4. Apollo is the final safety net that ensures no company is left unenriched
      setLoading(false);
    }
  };

  // Smart both enrichment function (company + people) - SEQUENTIAL PROCESSING
  // This function processes each company completely (Growjo + Apollo + Upload + Draft + Deduct) before moving to the next
  // Smart both enrichment function (company + people) - SEQUENTIAL PROCESSING
  // This function processes each company completely (Growjo + Apollo + Upload + Draft + Deduct) before moving to the next
  const handleSmartBothEnrichment = async () => {
    console.log(`🚀 Starting Smart Both Enrichment (Company + People)...`);
    
    // Set the view type to "both" for card display
    setEnrichmentViewType("both");
    
    if (selectedCompanies.length === 0) {
      showNotification("Please select companies to enrich", "error");
      return;
    }

    if (selectedCompanies.length > 25) {
      showNotification("Maximum 25 leads allowed for enrichment", "error");
      return;
    }
    
    // Prevent multiple enrichment functions from running simultaneously
    if (loading) {
      showNotification("Enrichment already in progress. Please wait.", "info");
      return;
    }

    // Get user info from session storage
    const user = JSON.parse(sessionStorage.getItem("user") || "{}");
    const user_id = user.user_id || "";

    // Check user credits
    try {
      const { data: subscriptionInfo } = await axios.get(
        `${DATABASE_URL}/user/subscription_info`,
        { withCredentials: true }
      );

      const plan = subscriptionInfo?.plan;
      const isUnlimited =
        plan?.initial_credits === null ||
        (plan?.features_json && plan.features_json.includes("Unlimited Credits"));

      if (!isUnlimited) {
        const availableCredits = subscriptionInfo?.subscription?.credits_remaining ?? 0;
        const requiredCredits = selectedCompanies.length * 2; // 2 credits per company for both enrichment
        if (availableCredits < requiredCredits) {
          setShowTokenPopup(true);
          setLoading(false);
          return;
        }
      }
    } catch (checkErr) {
      console.error("❌ Failed to verify subscription:", checkErr);
      showNotification("Failed to verify your subscription. Please try again later.", "error");
      setLoading(false);
      return;
    }

    setLoading(true);
    setHasErrors(false);
    hasErrorsRef.current = false;
    
    // Clear previous banner state when starting new enrichment
    setShowEmptyResultsBanner(false);
    setEmptyResultsInfo({
      hasDatabaseResults: false,
      hasScrapedResults: false,
      totalCompanies: 0,
      enrichmentType: "both"
    });
    
    // Clear previous results to prevent duplicates
    setDbEnrichedCompanies([]);
    setScrapedEnrichedCompanies([]);
    setEnrichedCompanies([]);
    setFirstEnrichmentType("both");
    setHasFirstEnrichment(true);
    
    // Clear revenueMap to prevent old estimated values from overriding Apollo data
    // setRevenueMap({});
    // sessionStorage.removeItem("revenueMap");
    
    // Clear previous results when starting new both enrichment
    console.log("🧹 Clearing previous results - starting new both enrichment");
    setDbPeopleResults([]);
    setScrapedPeopleResults([]);
    setShowResults(false);
    setHasEnrichedOnce(false);
      
    // Clear real-time processing states
    clearRealTimeStates();
      
    // Reset both results pagination and filters
    setBothResultsCurrentPage(1);
    setBothResultsSearchTerm("");
    setBothResultsShowFilters(false);
    setBothResultsSortConfig(null);
    setBothResultsEmployeesFilter("");
    setBothResultsRevenueFilter("");
    setBothResultsBusinessTypeFilter("");
    setBothResultsProductFilter("");
    setBothResultsYearFoundedFilter("");
    setBothResultsBbbRatingFilter("");
    setBothResultsStreetFilter("");
    setBothResultsCityFilter("");
    setBothResultsStateFilter("");

    // Reset people results pagination and filters
    setPeopleResultsCurrentPage(1);
    setPeopleResultsSearchTerm("");
    setPeopleResultsShowFilters(false);
    setPeopleResultsSortConfig(null);
    setPeopleResultsNameFilter("");
    setPeopleResultsTitleFilter("");
    setPeopleResultsEmailFilter("");
    setPeopleResultsPhoneFilter("");
    setPeopleResultsLinkedinFilter("");
    setPeopleResultsCompanyFilter("");
    setPeopleResultsIndustryFilter("");

    try {
      console.log("🚀 Starting Smart Both Enrichment (Company + People)...");
      
      // Initialize local variable to track not found companies
      let notFoundCompaniesList: string[] = [];
      
      // Get the actual company objects from normalizedLeads
      const selectedCompanyObjects = normalizedLeads.filter(c => selectedCompanies.includes(c.id));
      
      // Step 1: Check database for existing data (both company and people)
      console.log("🔍 Step 1: Checking database for existing company and people data...");
      const companiesNeedingEnrichment: any[] = [];
      
      // Fetch data from database for selected companies
      const leadIds = selectedCompanyObjects.map(c => c.lead_id).filter((id): id is string => Boolean(id));
      const companyNames = selectedCompanyObjects.map(c => c.company).filter((name): name is string => Boolean(name));
      
      // Always try database lookup, even with empty leadIds (will use search_companies)
      try {
        const dbLeads = await fetchCompaniesWithFallback(leadIds, companyNames);

        for (const company of selectedCompanyObjects) {
          // For companies without lead_id, try to find by company name (case insensitive)
          const dbLead = dbLeads.find((l: any) => 
            l.lead_id === company.lead_id || 
            (company.lead_id ? false : l.company?.toLowerCase() === company.company?.toLowerCase())
          );
            if (dbLead) {
              // Always enrich if we have database data, to get additional Apollo/Growjo insights
              // Even if database has complete data, Apollo might have additional company details (revenue, phone, etc.)
              // and we want to preserve the database owner info while getting enhanced company data
              
              // Check if we have complete company data
              const hasCompleteCompanyData = 
                dbLead.revenue && dbLead.revenue !== "N/A" &&
                dbLead.employees && dbLead.employees !== "N/A" &&
                dbLead.website && dbLead.website !== "N/A" &&
                dbLead.product_category && dbLead.product_category !== "N/A" &&
                dbLead.business_type && dbLead.business_type !== "N/A";

              // Check if we have complete people data
              const hasCompletePeopleData = 
                dbLead.owner_first_name && dbLead.owner_first_name !== "N/A" &&
                dbLead.owner_last_name && dbLead.owner_last_name !== "N/A" &&
                dbLead.owner_email && dbLead.owner_email !== "N/A" &&
                dbLead.owner_phone_number && dbLead.owner_phone_number !== "N/A" &&
                dbLead.owner_title && dbLead.owner_title !== "N/A";

              // Always enrich to get additional insights, but preserve database owner info
              if (hasCompleteCompanyData && hasCompletePeopleData) {
                console.log(`✅ ${company.company} has complete data in database, but will enrich for additional insights`);
                // Still add to enrichment list to get Apollo/Growjo insights
                companiesNeedingEnrichment.push({
                  ...company,
                  // Preserve database data for merging later
                  databaseData: dbLead
                });
              } else {
                companiesNeedingEnrichment.push({
                  ...company,
                  // Preserve database data for merging later
                  databaseData: dbLead
                });
                console.log(`⚠️ ${company.company} needs enrichment - missing company data: ${!hasCompleteCompanyData}, missing people data: ${!hasCompletePeopleData}`);
              }
            } else {
              // Company not in database, needs enrichment
              companiesNeedingEnrichment.push(company);
              console.log(`⚠️ ${company.company} not found in database, needs enrichment`);
            }
          }
        } catch (err) {
          console.error("❌ Failed to fetch from database:", err);
          companiesNeedingEnrichment.push(...selectedCompanyObjects); // Fallback to enriching all
        }

      if (companiesNeedingEnrichment.length === 0) {
        showNotification("No companies found for enrichment", "info");
        setLoading(false);
        return;
      }

      console.log(`📋 Found ${companiesNeedingEnrichment.length} companies needing enrichment`);

      // Step 2: Process each company completely (Growjo + Apollo + Upload + Draft + Deduct) before moving to next
      console.log("🔍 Step 2: Processing each company completely through ALL APIs...");
      let finalResults: any[] = []; // Single array for final results

      // Process each company completely (Growjo + Apollo) before moving to next
      for (let i = 0; i < companiesNeedingEnrichment.length; i++) {
        const company = companiesNeedingEnrichment[i];
        const leadNumber = i + 1;
        const totalLeads = companiesNeedingEnrichment.length;
        
        // Set current processing lead
        setProcessingLead(company.company);
        console.log(`🔄 Processing lead ${leadNumber}/${totalLeads}: ${company.company} - Starting complete processing`);
        
        try {
          // ===== GROWJO PROCESSING =====
          console.log(`📞 Step 1: Calling Growjo companies API for ${company.company}...`);
          let growjoCompanyId = null;
          let growjoCompanyData: any = {};
          let growjoPeopleData: any = { people: [] };
          
          try {
            const lookupResponse = await axios.post(
              `${DATABASE_URL}/growjo/companies`,
              { company_names: [company.company] },
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );

            if (lookupResponse.data && lookupResponse.data.company_batch_results && lookupResponse.data.company_batch_results.length > 0) {
              const lookupResult = lookupResponse.data.company_batch_results[0];
              if (lookupResult && lookupResult.items && lookupResult.items.length > 0) {
                const companyData = lookupResult.items[0];
                growjoCompanyId = companyData.company_id;
                growjoCompanyData = companyData;
                console.log(`✅ Found company data for ${company.company} with company_id ${companyData.company_id}`);
              } else {
                console.log(`⚠️ No company data found for ${company.company} via Growjo companies API`);
              }
            } else {
              console.log(`⚠️ No company data found for ${company.company} via Growjo companies API`);
            }
          } catch (err) {
            console.error(`❌ Growjo companies API failed for ${company.company}:`, err);
          }

          // Process Growjo company data if we have a company ID
          if (growjoCompanyId) {
            let companyEnriched = false;
            let peopleEnriched = false;

            // Map company data
            const mappedCompanyData = growjoCompanyData ? await mapGrowjoCompanyData(growjoCompanyData) : {};
          
            const hasCompleteCompanyDataAfterGrowjo = 
              mappedCompanyData.revenue && mappedCompanyData.revenue !== "N/A" &&
              mappedCompanyData.employee_count && mappedCompanyData.employee_count !== "N/A" &&
              mappedCompanyData.website && mappedCompanyData.website !== "N/A";

            if (hasCompleteCompanyDataAfterGrowjo) {
              companyEnriched = true;
              growjoCompanyData = mappedCompanyData;
              console.log(`✅ ${company.company} company data enriched via Growjo lookup API`);
            } else {
              // Fallback to individual Growjo company API
              try {
                console.log(`📞 Calling Growjo individual company API for ${company.company}...`);
                const growjoCompanyResponse = await axios.post(
                  `${BACKEND_URL}/growjo/company/${growjoCompanyId}`,
                  {},
                  { headers: { "Content-Type": "application/json" }, withCredentials: true }
                );

                if (growjoCompanyResponse.data && growjoCompanyResponse.data.success) {
                  growjoCompanyData = growjoCompanyResponse.data.data;
                  
                  const hasCompleteCompanyDataAfterIndividualAPI = 
                    growjoCompanyData.revenue && growjoCompanyData.revenue !== "N/A" &&
                    growjoCompanyData.employee_count && growjoCompanyData.employee_count !== "N/A" &&
                    growjoCompanyData.website && growjoCompanyData.website !== "N/A";

                  if (hasCompleteCompanyDataAfterIndividualAPI) {
                    companyEnriched = true;
                    console.log(`✅ ${company.company} company data enriched via Growjo individual API`);
                  }
                }
              } catch (err) {
                console.error(`❌ Growjo company enrichment failed for ${company.company}:`, err);
              }
            }

            // Now try people enrichment
            try {
              console.log(`📞 Step 2: Calling Growjo people API for ${company.company}...`);
              const growjoPeopleResponse = await axios.post(
                `${BACKEND_URL}/growjo/people/${growjoCompanyId}`,
                {},
                { headers: { "Content-Type": "application/json" }, withCredentials: true }
              );

              if (growjoPeopleResponse.data && growjoPeopleResponse.data.success) {
                growjoPeopleData = growjoPeopleResponse.data.data;
                
                const hasCompletePeopleDataAfterGrowjo = 
                  growjoPeopleData.people && 
                  Array.isArray(growjoPeopleData.people) && 
                  growjoPeopleData.people.length > 0 &&
                  growjoPeopleData.people.some((person: any) => 
                    person.name && person.name !== "N/A" &&
                    person.title && person.title !== "N/A" &&
                    (person.email && person.email !== "N/A" || person.phone_number && person.phone_number !== "N/A")
                  );
                
                if (hasCompletePeopleDataAfterGrowjo) {
                  peopleEnriched = true;
                  console.log(`✅ ${company.company} people data enriched via Growjo: ${growjoPeopleData.people.length} people found`);
                }
              }
            } catch (err) {
              console.error(`❌ Growjo people enrichment failed for ${company.company}:`, err);
            }

            // If Growjo provided useful data, use it, but still try Apollo for additional data
            if (companyEnriched || peopleEnriched) {
              console.log(`✅ ${company.company} got useful data from Growjo, but will still try Apollo for additional insights`);
            }
          }

          // ===== APOLLO PROCESSING =====
          console.log(`📞 Step 3: Calling Apollo company API for ${company.company}...`);
          let apolloCompanyData: any = {};
          let apolloPeopleData: any = { people: [] };

          // Try Apollo company enrichment
          try {
            apolloCompanyData = await apolloEnrichCompany(company);
            if (apolloCompanyData && Object.keys(apolloCompanyData).length > 0) {
              console.log(`✅ ${company.company} company data enriched via Apollo`);
            }
          } catch (err) {
            console.error(`❌ Apollo company enrichment failed for ${company.company}:`, err);
          }

          // Try Apollo people enrichment
          try {
            console.log(`📞 Step 4: Calling Apollo people API for ${company.company}...`);
            const apolloPersonData = await apolloEnrichPeople(company);
            console.log("🔍 Apollo people enrichment response for", company.company, ":", apolloPersonData);

            if (apolloPersonData && Object.keys(apolloPersonData).length > 0) {
              const hasMeaningfulData = (
                (apolloPersonData as any).name && (apolloPersonData as any).name !== "N/A" && (apolloPersonData as any).name !== "None None" &&
                (apolloPersonData as any).title && (apolloPersonData as any).title !== "N/A" &&
                (apolloPersonData as any).email && (apolloPersonData as any).email !== "N/A" &&
                (apolloPersonData as any).phone && (apolloPersonData as any).phone !== "N/A" &&
                (apolloPersonData as any).linkedin && (apolloPersonData as any).linkedin !== "N/A"
              );
              
              if (hasMeaningfulData) {
                apolloPeopleData = {
                  people: [{
                    name: (apolloPersonData as any).name || `${(apolloPersonData as any).first_name || ''} ${(apolloPersonData as any).last_name || ''}`.trim(),
                    first_name: (apolloPersonData as any).first_name || '',
                    last_name: (apolloPersonData as any).last_name || '',
                    title: (apolloPersonData as any).title || '',
                    email: (apolloPersonData as any).email || '',
                    phone: (apolloPersonData as any).phone || '',
                    phone_number: (apolloPersonData as any).phone || '',
                    linkedin: (apolloPersonData as any).linkedin || '',
                    linkedin_url: (apolloPersonData as any).linkedin || '',
                    source: "Apollo (New Endpoint)"
                  }]
                };
                
                console.log(`✅ ${company.company} people data enriched via Apollo: 1 person found`);
              } else {
                console.log(`⚠️ Apollo people enrichment returned no meaningful people data for ${company.company}`);
                apolloPeopleData = { people: [] };
              }
            } else {
              console.log(`⚠️ Apollo people enrichment returned no people data for ${company.company}`);
            }
          } catch (err) {
            console.error(`❌ Apollo people enrichment failed for ${company.company}:`, err);
          }

          // ===== COMBINE ALL DATA =====
          console.log(`🔄 Step 5: Combining all data for ${company.company}...`);
          
          // Combine Growjo and Apollo data (Growjo takes priority)
          const combinedCompanyData = {
            ...company,
            // Keep original/database values for these fields
            city: company.databaseData?.city || company.city,
            state: company.databaseData?.state || company.state,
            country: company.databaseData?.country || company.country,
            industry: company.databaseData?.industry || company.industry,
            bbb_rating: company.databaseData?.bbb_rating || company.bbb_rating,
            street: company.databaseData?.street || company.street,
            
            // Apply priority order for business fields: Apollo → Growjo → Database
            product_category: (() => {
              if (apolloCompanyData.product_category) return apolloCompanyData.product_category;
              if (growjoCompanyData?.product_category) return growjoCompanyData.product_category;
              if (company.databaseData?.product_category) return company.databaseData.product_category;
              return company.product_category;
            })(),
            business_type: (() => {
              if (apolloCompanyData.business_type) return apolloCompanyData.business_type;
              if (growjoCompanyData?.business_type) return growjoCompanyData.business_type;
              if (company.databaseData?.business_type) return company.databaseData.business_type;
              return company.business_type;
            })(),
            
            // Apply priority order: Apollo → Growjo → Database
            revenue: (() => {
              if (apolloCompanyData.organization_revenue) return apolloCompanyData.organization_revenue / 1000000;
              if (apolloCompanyData.annual_revenue_printed) return apolloCompanyData.annual_revenue_printed;
              if (growjoCompanyData?.revenue) return growjoCompanyData.revenue;
              if (company.databaseData?.revenue) return company.databaseData.revenue;
              return company.revenue;
            })(),
            employees: (() => {
              if (apolloCompanyData.employees) return apolloCompanyData.employees;
              if (growjoCompanyData?.employee_count) {
                const processedEmployees = processEmployeeRange(growjoCompanyData.employee_count);
                console.log(`📊 Individual API - Growjo employees processed for ${company.company}: "${growjoCompanyData.employee_count}" → "${processedEmployees}"`);
                return processedEmployees;
              }
              if (company.databaseData?.employees) return company.databaseData.employees;
              return company.employees;
            })(),
            year_founded: (() => {
              if (apolloCompanyData.founded_year) return apolloCompanyData.founded_year;
              if (growjoCompanyData?.year_founded) return growjoCompanyData.year_founded;
              if (company.databaseData?.year_founded) return company.databaseData.year_founded;
              return company.year_founded;
            })(),
            company_linkedin: (() => {
              if (apolloCompanyData.linkedin_url) return apolloCompanyData.linkedin_url;
              if (growjoCompanyData?.company_linkedin) return growjoCompanyData.company_linkedin;
              if (company.databaseData?.company_linkedin) return company.databaseData.company_linkedin;
              return company.company_linkedin;
            })(),
            company_phone: (() => {
              if (apolloCompanyData.phone) return apolloCompanyData.phone;
              if (growjoCompanyData?.business_phone) return growjoCompanyData.business_phone;
              if (company.databaseData?.company_phone) return company.databaseData.company_phone;
              return company.company_phone;
            })(),
            
            // Website priority - database first
            website: company.databaseData?.website || company.website,
            
            // Owner info - preserve database owner info
            owner_first_name: company.databaseData?.owner_first_name || company.owner_first_name,
            owner_last_name: company.databaseData?.owner_last_name || company.owner_last_name,
            owner_title: company.databaseData?.owner_title || company.owner_title,
            owner_email: company.databaseData?.owner_email || company.owner_email,
            owner_phone_number: company.databaseData?.owner_phone_number || company.owner_phone_number,
            owner_linkedin: company.databaseData?.owner_linkedin || company.owner_linkedin,
            source: "Growjo + Apollo",
            
            // Combine people data
            people: (() => {
              const growjoPeople = (growjoPeopleData.people || []).map((person: any) => ({
                ...person,
                source: "Growjo"
              }));
              
              const apolloPeople = (apolloPeopleData.people || []).map((person: any) => ({
                ...person,
                source: "Apollo"
              }));
              
              // If Apollo people enrichment returned empty but we have database owner info, create a person from owner fields
              if (apolloPeople.length === 0 && (company.databaseData?.owner_first_name || company.databaseData?.owner_last_name)) {
                const ownerPerson = {
                  name: `${company.databaseData.owner_first_name || ''} ${company.databaseData.owner_last_name || ''}`.trim(),
                  first_name: company.databaseData.owner_first_name || '',
                  last_name: company.databaseData.owner_last_name || '',
                  title: company.databaseData.owner_title || '',
                  email: company.databaseData.owner_email || '',
                  phone: company.databaseData.owner_phone_number || '',
                  phone_number: company.databaseData.owner_phone_number || '',
                  linkedin: company.databaseData.owner_linkedin || '',
                  linkedin_url: company.databaseData.owner_linkedin || '',
                  source: "Database (Owner Info)"
                };
                return [...growjoPeople, ownerPerson];
              }
              
              // Also check if company object has owner fields as fallback
              if (apolloPeople.length === 0 && growjoPeople.length === 0 && (company.owner_first_name || company.owner_last_name)) {
                const ownerPerson = {
                  name: `${company.owner_first_name || ''} ${company.owner_last_name || ''}`.trim(),
                  first_name: company.owner_first_name || '',
                  last_name: company.owner_last_name || '',
                  title: company.owner_title || '',
                  email: company.owner_email || '',
                  phone: company.owner_phone_number || '',
                  phone_number: company.owner_phone_number || '',
                  linkedin: company.owner_linkedin || '',
                  linkedin_url: company.owner_linkedin || '',
                  source: "Company (Owner Info)"
                };
                return [ownerPerson];
              }
              
              // Combine and deduplicate people
              const allPeople = [...growjoPeople, ...apolloPeople];
              
              // Deduplicate people based on email
              const uniquePeople = allPeople.reduce((acc: any[], person: any) => {
                const email = person.email || person.owner_email;
                if (!email) return [...acc, person];
                
                const existingPerson = acc.find(p => (p.email || p.owner_email) === email);
                if (!existingPerson) {
                  acc.push(person);
                } else {
                  // Merge data from different sources
                  const mergedPerson = { ...existingPerson };
                  Object.keys(person).forEach(key => {
                    if (person[key] && person[key] !== "N/A" && (!mergedPerson[key] || mergedPerson[key] === "N/A")) {
                      mergedPerson[key] = person[key];
                    }
                  });
                  const index = acc.findIndex(p => (p.email || p.owner_email) === email);
                  acc[index] = mergedPerson;
                }
                return acc;
              }, []);
              
              return uniquePeople;
            })()
          };

          // ===== BUSINESS TYPE DECIDER =====
          console.log(`🤖 Step 5.5: Calling business type decider for ${company.company}...`);
          let businessType = combinedCompanyData.business_type || "";
          if (!businessType || businessType === "N/A" || businessType.trim() === "") {
            const products = combinedCompanyData.product_category || "";
            const industry = combinedCompanyData.industry || company.company || "";
            businessType = await callBusinessTypeDecider(products, industry);
            combinedCompanyData.business_type = businessType;
            console.log(`✅ Updated ${company.company} with business type: ${businessType}`);
          } else {
            console.log(`✅ ${company.company} already has business type: ${businessType}, skipping API call`);
          }

          // ===== UPLOAD, DRAFT, AND DEDUCT CREDITS =====
          console.log(`📤 Step 6: Uploading, creating draft, and deducting credits for ${company.company}...`);
          
          const enrichedCompanyResult = toCamelCase({ ...combinedCompanyData, source_type: "scraped" });
          finalResults.push(enrichedCompanyResult);
          
          // Immediately add to completed leads for real-time display
          addCompletedLead(enrichedCompanyResult);
          
          // Upload lead
          let lead_id = company.lead_id;
          const basePayload = {
            user_id,
            lead_id,
            company: combinedCompanyData.company,
            website: combinedCompanyData.website,
            industry: combinedCompanyData.industry,
            product_category: combinedCompanyData.product_category,
            business_type: combinedCompanyData.business_type,
            employees: combinedCompanyData.employees,
            revenue: formatRevenueForDisplay(combinedCompanyData.revenue),
            year_founded: combinedCompanyData.year_founded || "",
            bbb_rating: combinedCompanyData.bbb_rating || "",
            street: combinedCompanyData.street || "",
            city: combinedCompanyData.city,
            state: combinedCompanyData.state,
            country: combinedCompanyData.country || "",
            company_phone: combinedCompanyData.company_phone || "",
            company_linkedin: combinedCompanyData.company_linkedin || "",
            source: combinedCompanyData.source,
            contacts: (combinedCompanyData.people || []).map((person: any) => ({
              owner_first_name: person.name?.split(' ')[0] || person.first_name || "",
              owner_last_name: person.name?.split(' ').slice(1).join(' ') || person.last_name || "",
              owner_title: person.title || "",
              owner_email: person.email || "",
              owner_phone_number: person.phone || person.phone_number || "",
              owner_linkedin: person.linkedin || person.linkedin_url || ""
            })),
            owner_linkedin: combinedCompanyData.owner_linkedin || ""
          };

          // 1. Upload lead
          try {
            const uploadRes = await axios.post(
              `${DATABASE_URL}/upload_leads`,
              JSON.stringify([basePayload]),
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
            const leadFromResponse = detailedResults[0] || {};
            if (!lead_id && leadFromResponse.lead_id) {
              lead_id = leadFromResponse.lead_id;
              basePayload.lead_id = lead_id;
            }
            console.log(`✅ Uploaded enriched company ${company.company}`);
          } catch (uploadErr) {
            console.error("❌ Failed to upload enriched lead:", basePayload, uploadErr);
          }

          // 2. Create draft
          try {
            await axios.post(
              `${DATABASE_URL}/leads/drafts`,
              {
                lead_id,
                draft_data: basePayload,
                change_summary: "Smart both enrichment from Growjo + Apollo",
              },
              {
                headers: { "Content-Type": "application/json" },
                withCredentials: true,
              }
            );
            console.log(`✅ Created draft for enriched company ${company.company}`);
          } catch (draftErr: any) {
            console.error(`❌ Failed to create draft for enriched company:`, draftErr);
          }

          // 3. Deduct 2 credits for both enrichment (company + people)
          try {
            if (lead_id) {
              // Deduct first credit for company enrichment
              await axios.post(
                `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                { type: generateDeductType('first enrichment', 'companies', 'db') },
                { withCredentials: true }
              );
              console.log(`💳 Deducted 1st credit for company enrichment: ${company.company}`);
              
              // Deduct second credit for people enrichment
              await axios.post(
                `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
                { type: generateDeductType('first enrichment', 'people', 'db') },
                { withCredentials: true }
              );
              console.log(`💳 Deducted 2nd credit for people enrichment: ${company.company}`);
              
              console.log(`✅ Deducted 2 credits total for enriched company ${company.company}`);
            }
          } catch (deductErr: any) {
            console.error(`❌ Credit deduction failed for enriched lead ${lead_id}`, deductErr);
          }

          console.log(`✅ Completed processing ${company.company} - all APIs called, uploaded, drafted, and credits deducted`);
          
          // Add delay before processing next company
          console.log(`⏳ Waiting before processing next company...`);
          await new Promise(resolve => setTimeout(resolve, 1000));
          
        } catch (err) {
          console.error(`❌ Processing failed for ${company.company}:`, err);
        }
      }

      // Final results are already set in real-time via addCompletedLead
      console.log(`✅ Smart Both Enrichment completed! Processed ${finalResults.length} companies`);
      showNotification(`Successfully enriched ${finalResults.length} companies!`, "success");

    } catch (err) {
      console.error("Smart both enrichment failed:", err);
      showNotification("Smart both enrichment failed. Please try again.", "error");
    } finally {
      setLoading(false);
    }
  };
;

  // 🆕 NEW: Apollo enrichment helper function with smart logic
  const apolloEnrichCompany = async (company: any) => {
    try {
      console.log(`🚀 Apollo enrichment for ${company.company}`);
      
      // Handle website safely
      let website = company.website || "";
      let domain = "";
      

      
      if (website && website.trim() !== "" && website !== "N/A") {
        let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        domain = normalizeWebsite(cleanDomain);
        console.log(`🌐 Using website for ${company.company}: ${website} → domain: ${domain}`);
      } else {
        domain = "";
        console.log(`⚠️ No website for ${company.company}, will search by company name first`);
      }
      
      let apolloData = {};
      
      // If we have a valid domain, try direct enrichment first
      if (domain && domain.trim() !== "") {
        console.log(`🎯 Direct enrichment for ${company.company} with domain: ${domain}`);
        try {
          const enrichResponse = await axios.post(
            `${DATABASE_URL}/apollo/enrich/apollo-enrich-company`,
            { domain },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );
          
          if (enrichResponse.data && enrichResponse.data.success) {
            apolloData = enrichResponse.data.data || {};
            console.log(`✅ Direct enrichment successful for ${company.company}`);
            return apolloData;
          } else {
            console.log(`⚠️ Direct enrichment failed for ${company.company}, falling back to search`);
          }
        } catch (enrichError) {
          console.log(`⚠️ Direct enrichment error for ${company.company}, falling back to search:`, enrichError);
        }
      }
      
      // If no domain or direct enrichment failed, search by company name first
      console.log(`🔍 Searching for ${company.company} by name using apollo-search-company`);
      try {
        const searchResponse = await axios.post(
          `${DATABASE_URL}/apollo/enrich/apollo-search-company`,
          { company_name: company.company, per_page: 1 },
          { headers: { "Content-Type": "application/json" }, withCredentials: true }
        );
        
        if (searchResponse.data && searchResponse.data.success && searchResponse.data.companies?.length > 0) {
          const foundCompany = searchResponse.data.companies[0];
          const foundDomain = foundCompany.primary_domain;
          
          if (foundDomain && foundDomain.trim() !== "") {
            console.log(`✅ Found domain ${foundDomain} for ${company.company}, now enriching with apollo-enrich-company`);
            // Now enrich with the found domain
            const enrichResponse = await axios.post(
              `${DATABASE_URL}/apollo/enrich/apollo-enrich-company`,
              { domain: foundDomain },
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            
            if (enrichResponse.data && enrichResponse.data.success) {
              apolloData = enrichResponse.data.data || {};
              console.log(`✅ Search + enrichment successful for ${company.company}`);
            } else {
              console.log(`⚠️ Search successful but enrichment failed for ${company.company}`);
            }
          } else {
            console.log(`⚠️ Company found but no domain available for ${company.company}`);
          }
        } else {
          console.log(`⚠️ No company found by name for ${company.company}`);
        }
      } catch (searchError) {
        console.error(`❌ Search failed for ${company.company}:`, searchError);
      }
      
      console.log(`❌ DATABASE_URL Apollo failed for ${company.company}, trying BACKEND_URL fallback...`);
      
      // Try BACKEND_URL fallback
      const fallbackResult = await apolloEnrichCompanyFallback(company);
      if (fallbackResult && Object.keys(fallbackResult).length > 0) {
        console.log(`✅ BACKEND_URL fallback successful for ${company.company}`);
        return fallbackResult;
      }
      
      console.log(`❌ No data found for ${company.company} from both DATABASE_URL and BACKEND_URL`);
      return apolloData;
      
    } catch (error: any) {
      console.error(`❌ Apollo enrichment failed for ${company.company}:`, error);
      
      // Try BACKEND_URL fallback even if DATABASE_URL throws an error
      try {
        console.log(`🔄 Trying BACKEND_URL fallback after error for ${company.company}...`);
        const fallbackResult = await apolloEnrichCompanyFallback(company);
        if (fallbackResult && Object.keys(fallbackResult).length > 0) {
          console.log(`✅ BACKEND_URL fallback successful for ${company.company} after error`);
          return fallbackResult;
        }
      } catch (fallbackError) {
        console.error(`❌ BACKEND_URL fallback also failed for ${company.company}:`, fallbackError);
      }
      
      return {};
    }
  };

  // 🆕 NEW: Apollo people enrichment helper function with smart domain search logic
  const apolloEnrichPeople = async (company: any) => {
    try {
      console.log(`🚀 Apollo people enrichment for ${company.company}`);
      
      // Handle website safely
      let website = company.website || "";
      let domain = "";
      
      if (website && website.trim() !== "" && website !== "N/A") {
        let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        domain = normalizeWebsite(cleanDomain);
        console.log(`🌐 Using website for ${company.company}: ${website} → domain: ${domain}`);
      } else {
        domain = "";
        console.log(`⚠️ No website for ${company.company}, will search by company name first`);
      }
      
      let apolloData = {};
      
      // If we have a valid domain, try direct people enrichment first
      if (domain && domain.trim() !== "") {
        console.log(`🎯 Direct people enrichment for ${company.company} with domain: ${domain}`);
        try {
          const enrichResponse = await axios.post(
            `${DATABASE_URL}/apollo/enrich/apollo-enrich-people`,
            { domain },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );
          
          if (enrichResponse.data && enrichResponse.data.success) {
            apolloData = enrichResponse.data.data || {};
            console.log(`✅ Direct people enrichment successful for ${company.company}`);
            return apolloData;
          } else {
            console.log(`⚠️ Direct people enrichment failed for ${company.company}, falling back to search`);
          }
        } catch (enrichError) {
          console.log(`⚠️ Direct people enrichment error for ${company.company}, falling back to search:`, enrichError);
        }
      }
      
      // If no domain or direct enrichment failed, search by company name first
      console.log(`🔍 Searching for ${company.company} by name using apollo-search-company`);
      try {
        const searchResponse = await axios.post(
          `${DATABASE_URL}/apollo/enrich/apollo-search-company`,
          { company_name: company.company, per_page: 1 },
          { headers: { "Content-Type": "application/json" }, withCredentials: true }
        );
        
        if (searchResponse.data && searchResponse.data.success && searchResponse.data.companies?.length > 0) {
          const foundCompany = searchResponse.data.companies[0];
          const foundDomain = foundCompany.primary_domain;
          
          if (foundDomain && foundDomain.trim() !== "") {
            console.log(`✅ Found domain ${foundDomain} for ${company.company}, now enriching people with apollo-enrich-people`);
            // Now enrich people with the found domain
            const enrichResponse = await axios.post(
              `${DATABASE_URL}/apollo/enrich/apollo-enrich-people`,
              { domain: foundDomain },
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            
            if (enrichResponse.data && enrichResponse.data.success) {
              apolloData = enrichResponse.data.data || {};
              console.log(`✅ Search + people enrichment successful for ${company.company}`);
            } else {
              console.log(`⚠️ Search successful but people enrichment failed for ${company.company}`);
            }
          } else {
            console.log(`⚠️ Company found but no domain available for ${company.company}`);
          }
        } else {
          console.log(`⚠️ No company found by name for ${company.company}`);
        }
      } catch (searchError) {
        console.error(`❌ Search failed for ${company.company}:`, searchError);
      }
      
      console.log(`❌ DATABASE_URL Apollo people failed for ${company.company}, trying BACKEND_URL fallback...`);
      
      // Try BACKEND_URL fallback
      const fallbackResult = await apolloEnrichPeopleFallback(company);
      if (fallbackResult && Object.keys(fallbackResult).length > 0) {
        console.log(`✅ BACKEND_URL people fallback successful for ${company.company}`);
        return fallbackResult;
      }
      
      console.log(`❌ No people data found for ${company.company} from both DATABASE_URL and BACKEND_URL`);
      return apolloData;
      
    } catch (error: any) {
      console.error(`❌ Apollo people enrichment failed for ${company.company}:`, error);
      
      // Try BACKEND_URL fallback even if DATABASE_URL throws an error
      try {
        console.log(`🔄 Trying BACKEND_URL people fallback after error for ${company.company}...`);
        const fallbackResult = await apolloEnrichPeopleFallback(company);
        if (fallbackResult && Object.keys(fallbackResult).length > 0) {
          console.log(`✅ BACKEND_URL people fallback successful for ${company.company} after error`);
          return fallbackResult;
        }
      } catch (fallbackError) {
        console.error(`❌ BACKEND_URL people fallback also failed for ${company.company}:`, fallbackError);
      }
      
      return {};
    }
  };

  // 🆕 NEW: Fallback Apollo functions using BACKEND_URL
  const apolloEnrichCompanyFallback = async (company: any) => {
    try {
      console.log(`🔄 BACKEND_URL Apollo company enrichment fallback for ${company.company}`);
      
      // Handle website safely
      let website = company.website || "";
      let domain = "";
      
      if (website && website.trim() !== "" && website !== "N/A") {
        let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        domain = normalizeWebsite(cleanDomain);
        console.log(`🌐 BACKEND_URL Using website for ${company.company}: ${website} → domain: ${domain}`);
      } else {
        domain = "";
        console.log(`⚠️ BACKEND_URL No website for ${company.company}, will search by company name first`);
      }
      
      let apolloData = {};
      
      // If we have a valid domain, try direct enrichment first
      if (domain && domain.trim() !== "") {
        console.log(`🎯 BACKEND_URL Direct enrichment for ${company.company} with domain: ${domain}`);
        try {
          const enrichResponse = await axios.post(
            `${BACKEND_URL}/apollo-enrich-company`,
            { domain },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );
          
          if (enrichResponse.data && enrichResponse.data.success) {
            apolloData = enrichResponse.data.data || {};
            console.log(`✅ BACKEND_URL Direct enrichment successful for ${company.company}`);
            return apolloData;
          } else {
            console.log(`⚠️ BACKEND_URL Direct enrichment failed for ${company.company}, falling back to search`);
          }
        } catch (enrichError) {
          console.log(`⚠️ BACKEND_URL Direct enrichment error for ${company.company}, falling back to search:`, enrichError);
        }
      }
      
      // If no domain or direct enrichment failed, search by company name first
      console.log(`🔍 BACKEND_URL Searching for ${company.company} by name using apollo-search-company`);
      try {
        const searchResponse = await axios.post(
          `${BACKEND_URL}/apollo-search-company`,
          { company_name: company.company, per_page: 1 },
          { headers: { "Content-Type": "application/json" }, withCredentials: true }
        );
        
        if (searchResponse.data && searchResponse.data.success && searchResponse.data.companies?.length > 0) {
          const foundCompany = searchResponse.data.companies[0];
          const foundDomain = foundCompany.website_url || foundCompany.domain || foundCompany.website;
          
          if (foundDomain && foundDomain.trim() !== "") {
            console.log(`✅ BACKEND_URL Found domain ${foundDomain} for ${company.company}, now enriching with apollo-enrich-company`);
            // Now enrich with the found domain
            const enrichResponse = await axios.post(
              `${BACKEND_URL}/apollo-enrich-company`,
              { domain: foundDomain },
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            
            if (enrichResponse.data && enrichResponse.data.success) {
              apolloData = enrichResponse.data.data || {};
              console.log(`✅ BACKEND_URL Enrichment successful for ${company.company} with found domain`);
              return apolloData;
            }
          }
        }
      } catch (searchError) {
        console.log(`⚠️ BACKEND_URL Search error for ${company.company}:`, searchError);
      }
      
      console.log(`❌ BACKEND_URL No data found for ${company.company}`);
      return apolloData;
      
    } catch (error: any) {
      console.error(`❌ BACKEND_URL Apollo company enrichment failed for ${company.company}:`, error);
      return {};
    }
  };

  const apolloEnrichPeopleFallback = async (company: any) => {
    try {
      console.log(`🔄 BACKEND_URL Apollo people enrichment fallback for ${company.company}`);
      
      // Handle website safely
      let website = company.website || "";
      let domain = "";
      
      if (website && website.trim() !== "" && website !== "N/A") {
        let cleanDomain = website.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
        domain = normalizeWebsite(cleanDomain);
        console.log(`🌐 BACKEND_URL Using website for ${company.company}: ${website} → domain: ${domain}`);
      } else {
        domain = "";
        console.log(`⚠️ BACKEND_URL No website for ${company.company}, will search by company name first`);
      }
      
      let apolloData = {};
      
      // If we have a valid domain, try direct people enrichment first
      if (domain && domain.trim() !== "") {
        console.log(`🎯 BACKEND_URL Direct people enrichment for ${company.company} with domain: ${domain}`);
        try {
          const enrichResponse = await axios.post(
            `${BACKEND_URL}/apollo-enrich-people`,
            { domain },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );
          
          if (enrichResponse.data && enrichResponse.data.success) {
            apolloData = enrichResponse.data.data || {};
            console.log(`✅ BACKEND_URL Direct people enrichment successful for ${company.company}`);
            return apolloData;
          } else {
            console.log(`⚠️ BACKEND_URL Direct people enrichment failed for ${company.company}, falling back to search`);
          }
        } catch (enrichError) {
          console.log(`⚠️ BACKEND_URL Direct people enrichment error for ${company.company}, falling back to search:`, enrichError);
        }
      }
      
      // If no domain or direct enrichment failed, search by company name first
      console.log(`🔍 BACKEND_URL Searching for ${company.company} by name using apollo-search-company`);
      try {
        const searchResponse = await axios.post(
          `${BACKEND_URL}/apollo-search-company`,
          { company_name: company.company, per_page: 1 },
          { headers: { "Content-Type": "application/json" }, withCredentials: true }
        );
        
        if (searchResponse.data && searchResponse.data.success && searchResponse.data.companies?.length > 0) {
          const foundCompany = searchResponse.data.companies[0];
          const foundDomain = foundCompany.website_url || foundCompany.domain || foundCompany.website;
          
          if (foundDomain && foundDomain.trim() !== "") {
            console.log(`✅ BACKEND_URL Found domain ${foundDomain} for ${company.company}, now enriching people with apollo-enrich-people`);
            // Now enrich people with the found domain
            const enrichResponse = await axios.post(
              `${BACKEND_URL}/apollo-enrich-people`,
              { domain: foundDomain },
              { headers: { "Content-Type": "application/json" }, withCredentials: true }
            );
            
            if (enrichResponse.data && enrichResponse.data.success) {
              apolloData = enrichResponse.data.data || {};
              console.log(`✅ BACKEND_URL People enrichment successful for ${company.company} with found domain`);
              return apolloData;
            }
          }
        }
      } catch (searchError) {
        console.log(`⚠️ BACKEND_URL Search error for ${company.company}:`, searchError);
      }
      
      console.log(`❌ BACKEND_URL No people data found for ${company.company}`);
      return apolloData;
      
    } catch (error: any) {
      console.error(`❌ BACKEND_URL Apollo people enrichment failed for ${company.company}:`, error);
      return {};
    }
  };

  // 🆕 NEW: Database fallback helper function for company lookups
  const fetchCompaniesWithFallback = async (leadIds: string[], companyNames: string[]) => {
    // If no lead_ids, go directly to search_companies
    if (leadIds.length === 0) {
      console.log(`🔍 No lead_ids provided, using search_companies for ${companyNames.length} companies...`);
      const searchResults = [];
      for (const companyName of companyNames) {
        try {
          console.log(`🔍 Searching for company: ${companyName}`);
          const { data: searchRes } = await axios.post(
            `${DATABASE_URL}/leads/search_companies`,
            { company_name: companyName },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );
          if (searchRes.companies && searchRes.companies.length > 0) {
            console.log(`✅ Found ${searchRes.companies.length} companies for "${companyName}"`);
            console.log(`🔍 search_companies response for ${companyName}:`, searchRes.companies);
            searchResults.push(...searchRes.companies);
          } else {
            console.log(`⚠️ No companies found for "${companyName}"`);
          }
        } catch (searchError) {
          console.error(`❌ search_companies failed for ${companyName}:`, searchError);
        }
      }
      console.log(`🔄 search_companies completed, found ${searchResults.length} total companies`);
      return searchResults;
    }

    // If lead_ids exist, try leads/multiple first, then fallback to search_companies
    try {
      console.log(`🔍 Attempting database lookup with leads/multiple for ${leadIds.length} companies`);
      // First attempt: leads/multiple
      const { data: dbRes } = await axios.get(
        `${DATABASE_URL}/leads/multiple?lead_ids=${leadIds.join(",")}`,
        { headers: { "Content-Type": "application/json" }, withCredentials: true }
      );
      console.log(`✅ leads/multiple successful, found ${(dbRes.results || []).length} companies`);
      return dbRes.results || [];
    } catch (error) {
      console.log(`⚠️ leads/multiple failed, trying search_companies fallback for ${companyNames.length} companies...`);
      console.error("leads/multiple error:", error);
      
      // Fallback: search_companies for each company
      const fallbackResults = [];
      for (const companyName of companyNames) {
        try {
          console.log(`🔍 Searching for company: ${companyName}`);
          const { data: searchRes } = await axios.post(
            `${DATABASE_URL}/leads/search_companies`,
            { company_name: companyName },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          );
          if (searchRes.companies && searchRes.companies.length > 0) {
            console.log(`✅ Found ${searchRes.companies.length} companies for "${companyName}"`);
            fallbackResults.push(...searchRes.companies);
          } else {
            console.log(`⚠️ No companies found for "${companyName}"`);
          }
        } catch (fallbackError) {
          console.error(`❌ search_companies failed for ${companyName}:`, fallbackError);
        }
      }
      console.log(`🔄 Fallback completed, found ${fallbackResults.length} total companies`);
      return fallbackResults;
    }
  };

  // 🆕 NEW: Data mapper function to transform Growjo companies API response to expected format
  const mapGrowjoCompanyData = async (growjoData: any, skipBusinessTypeDecider: boolean = false) => {
    if (!growjoData) return {};
    
    // Handle nested company structure from Growjo API
    const companyData = growjoData.company || growjoData;
    
    // 🔍 DEBUG: Log the raw data structure
    console.log(`🔍 DEBUG - mapGrowjoCompanyData input:`, growjoData);
    console.log(`🔍 DEBUG - companyData extracted:`, companyData);
    console.log(`🔍 DEBUG - companyData.website:`, companyData.website);
    console.log(`🔍 DEBUG - companyData.product_category:`, companyData.product_category);
    console.log(`🔍 DEBUG - companyData.employees:`, companyData.employees);
    
    const mapped: any = {};
    
    // Revenue mapping - convert range to mean value and store in millions for display
    if (companyData.revenue_range) {
      const revenueValue = parseRevenueRange(companyData.revenue_range);
      if (revenueValue !== null) {
        // Store revenue in millions for proper table display
        const revenueInMillions = (revenueValue / 1000000).toFixed(1);
        mapped.revenue = revenueInMillions;
        console.log(`💰 Revenue mapping: "${companyData.revenue_range}" → ${revenueValue.toLocaleString()} → ${revenueInMillions}M`);
      }
    } else if (companyData.revenue) {
      // Handle direct revenue value
      mapped.revenue = companyData.revenue;
    }
    
    // Employee count mapping
    if (companyData.employee_number) {
      mapped.employee_count = companyData.employee_number;
    } else if (companyData.employees) {
      mapped.employee_count = companyData.employees;
    }
    
    // Website mapping
    console.log(`🔍 DEBUG - Website mapping check:`);
    console.log(`  - companyData.url: ${companyData.url}`);
    console.log(`  - companyData.website: ${companyData.website}`);
    if (companyData.url) {
      mapped.website = companyData.url;
      console.log(`✅ Mapped website from url: ${companyData.url}`);
    } else if (companyData.website) {
      mapped.website = companyData.website;
      console.log(`✅ Mapped website from website: ${companyData.website}`);
    } else {
      console.log(`❌ No website data found`);
    }
    
    // Industry mapping
    if (companyData.Industry) {
      mapped.industry = companyData.Industry;
    } else if (companyData.industry) {
      mapped.industry = companyData.industry;
    }
    
    // 🆕 NEW: Product category mapping from tags or product_category
    console.log(`🔍 DEBUG - Product category mapping check:`);
    console.log(`  - companyData.tags: ${companyData.tags}`);
    console.log(`  - companyData.product_category: ${companyData.product_category}`);
    if (companyData.tags) {
      // Use first few relevant tags as product category
      const tags = companyData.tags.split(',').map((tag: string) => tag.trim());
      const relevantTags = tags.slice(0, 3).join(' & '); // Take first 3 tags
      mapped.product_category = relevantTags;
      console.log(`✅ Mapped product_category from tags: ${relevantTags}`);
    } else if (companyData.product_category) {
      mapped.product_category = companyData.product_category;
      console.log(`✅ Mapped product_category from product_category: ${companyData.product_category}`);
    } else {
      console.log(`❌ No product category data found`);
    }
    
    // 🆕 NEW: Business type mapping using AI decider (skip if not needed for people enrichment)
    if ((companyData.tags || companyData.product_category) && !skipBusinessTypeDecider) {
      try {
        const products = companyData.tags || companyData.product_category;
        const businessTypeResponse = await axios.post(
          `${BACKEND_URL}/business-type-decider`,
          { products },
          { headers: { "Content-Type": "application/json" }, withCredentials: true }
        );
        
        if (businessTypeResponse.data && businessTypeResponse.data.success) {
          mapped.business_type = businessTypeResponse.data.business_type;
          console.log(`🤖 AI determined business type for ${companyData.name || companyData.company_name || 'company'}: ${businessTypeResponse.data.business_type} (confidence: ${businessTypeResponse.data.confidence})`);
        } else {
          console.warn(`⚠️ Business type decider failed for ${companyData.name || companyData.company_name || 'company'}:`, businessTypeResponse.data?.error);
          // Fallback: make educated guess based on tags or product_category
          const productsText = (companyData.tags || companyData.product_category || '').toLowerCase();
          if (productsText.includes('consulting') || productsText.includes('enterprise') || productsText.includes('b2b')) {
            mapped.business_type = "B2B";
          } else if (productsText.includes('consumer') || productsText.includes('retail')) {
            mapped.business_type = "B2C";
          } else {
            mapped.business_type = "B2B"; // Default for most tech companies
          }
        }
      } catch (error) {
        console.warn(`⚠️ Business type decider API call failed for ${companyData.name || companyData.company_name || 'company'}:`, error);
        // Fallback: make educated guess based on tags or product_category
        const productsText = (companyData.tags || companyData.product_category || '').toLowerCase();
        if (productsText.includes('consulting') || productsText.includes('enterprise') || productsText.includes('b2b')) {
          mapped.business_type = "B2B";
        } else if (productsText.includes('consumer') || productsText.includes('retail')) {
          mapped.business_type = "B2C";
        } else {
          mapped.business_type = "B2B"; // Default for most tech companies
        }
      }
    }
    
    // Location mapping - handle null/empty values properly
    if (companyData.city !== null && companyData.city !== undefined && companyData.city !== "") {
      mapped.city = companyData.city;
    }
    if (companyData.state !== null && companyData.state !== undefined && companyData.state !== "") {
      mapped.state = companyData.state;
    }
    if (companyData.country_code) {
      mapped.country = companyData.country_code;
    } else if (companyData.country) {
      mapped.country = companyData.country;
    }
    if (companyData.zip) {
      mapped.zip = companyData.zip;
    } else if (companyData.zip_code) {
      mapped.zip = companyData.zip_code;
    }
    
    // Contact mapping - handle null/empty values properly
    if (companyData.phone !== null && companyData.phone !== undefined && companyData.phone !== "") {
      mapped.business_phone = companyData.phone;
    }
    if (companyData.linkedin_url !== null && companyData.linkedin_url !== undefined && companyData.linkedin_url !== "") {
      mapped.company_linkedin = companyData.linkedin_url;
    }
    
    // Year founded mapping
    if (companyData.year_founded) {
      mapped.year_founded = companyData.year_founded;
    }
    
    // Address mapping - handle null/empty values properly
    if (companyData.address1 !== null && companyData.address1 !== undefined && companyData.address1 !== "") {
      mapped.street = companyData.address1;
    } else if (companyData.address !== null && companyData.address !== undefined && companyData.address !== "") {
      mapped.street = companyData.address;
      if (companyData.address2) {
        mapped.street += `, ${companyData.address2}`;
      }
    }
    
    // Tags mapping
    if (companyData.tags) {
      mapped.tags = companyData.tags;
    }
    
    // Bio/LinkedIn description
    if (companyData.bio_LI) {
      mapped.description = companyData.bio_LI;
    } else if (companyData.bio) {
      mapped.description = companyData.bio;
    }
    
    // 🔍 DEBUG: Log final mapped data
    console.log(`🔍 DEBUG - Final mapped data:`, mapped);
    console.log(`🔍 DEBUG - Final mapped.website:`, mapped.website);
    console.log(`🔍 DEBUG - Final mapped.product_category:`, mapped.product_category);
    console.log(`🔍 DEBUG - Final mapped.employee_count:`, mapped.employee_count);
    
    return mapped;
  };
  
  // Helper function to parse revenue ranges and calculate mean
  const parseRevenueRange = (revenueRange: string): number | null => {
    if (!revenueRange || revenueRange === "N/A") return null;
    
    try {
      // Handle different revenue range formats
      const range = revenueRange.toLowerCase();
      
      if (range.includes("million")) {
        const numbers = range.match(/(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*million/i);
        if (numbers) {
          const min = parseFloat(numbers[1]);
          const max = parseFloat(numbers[2]);
          return Math.round((min + max) / 2 * 1000000); // Convert to actual number
        }
        
        // Single value like "50 Million"
        const single = range.match(/(\d+(?:\.\d+)?)\s*million/i);
        if (single) {
          return Math.round(parseFloat(single[1]) * 1000000);
        }
      }
      
      if (range.includes("billion")) {
        const numbers = range.match(/(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*billion/i);
        if (numbers) {
          const min = parseFloat(numbers[1]);
          const max = parseFloat(numbers[2]);
          return Math.round((min + max) / 2 * 1000000000);
        }
        
        const single = range.match(/(\d+(?:\.\d+)?)\s*billion/i);
        if (single) {
          return Math.round(parseFloat(single[1]) * 1000000000);
        }
      }
      
      if (range.includes("thousand")) {
        const numbers = range.match(/(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*thousand/i);
        if (numbers) {
          const min = parseFloat(numbers[1]);
          const max = parseFloat(numbers[2]);
          return Math.round((min + max) / 2 * 1000);
        }
        
        const single = range.match(/(\d+(?:\.\d+)?)\s*thousand/i);
        if (single) {
          return Math.round(parseFloat(single[1]) * 1000);
        }
      }
      
      return null;
    } catch (error) {
      console.warn(`Failed to parse revenue range: ${revenueRange}`, error);
      return null;
    }
  };
  

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center mb-4">
          <Button
            onClick={handleBack}
            className="text-sm text-blue-600 hover:underline mr-4"
          >
            Back
          </Button>
          <div className="flex-1" />
        </div>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">Data Enhancement</h1>
            {/* Team membership indicator */}
            {!teamMembershipLoading && isTeamMember && (
              <div className="flex items-center gap-2 px-3 py-1 bg-green-100 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-xs text-green-700 dark:text-green-300 font-medium">Team Access</span>
              </div>
            )}
          </div>
          <p className="text-muted-foreground">Enrich company data with additional information</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Companies</CardTitle>
            <CardDescription>Select companies to enrich with additional data</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="search"
                    placeholder="Search companies..."
                    className="pl-8"
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                  />
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => setShowFilters(!showFilters)}
                >
                  <Filter className="h-4 w-4" />
                  {showFilters ? "Hide Filters" : "Show Filters"}
                </Button>
              </div>
              {showFilters && (
                <div className="flex flex-wrap gap-4 my-4">
                  <Input
                    placeholder="Industry (e.g. Software)"
                    value={industryFilter}
                    onChange={(e) => setIndustryFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <div className="relative flex items-center">
                    <Input
                      placeholder="Estimated Revenue (e.g., >5M)"
                      value={revenueFilter}
                      onChange={(e) => setRevenueFilter(e.target.value)}
                      className="w-[240px] pr-8"
                    />
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="absolute right-2.5 top-2.5 h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="bg-popover text-popover-foreground p-2 rounded-md shadow-lg max-w-xs text-sm z-50">
                          <p className="font-bold mb-1">Accepted Formats:</p>
                          <ul className="list-disc list-inside">
                            <li>`500K`, `10M`, `1B`</li>
                            <li>`>10M` (Greater than)</li>
                            <li>`&lt;1B` (Less than)</li>
                            <li>`1M-5M` (Range)</li>
                          </ul>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <Input
                    placeholder="City (e.g. Los Angeles)"
                    value={cityFilter}
                    onChange={(e) => setCityFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="State (e.g. CA)"
                    value={stateFilter}
                    onChange={(e) => setStateFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="BBB Rating (e.g. A+)"
                    value={bbbRatingFilter}
                    onChange={(e) => setBbbRatingFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setIndustryFilter("")
                      setCityFilter("")
                      setStateFilter("")
                      setBbbRatingFilter("")
                      setRevenueFilter("")
                    }}
                  >
                    <X className="h-4 w-4 mr-1" />
                    Clear Filters
                  </Button>
                </div>
              )}

              <div className="w-full overflow-x-auto rounded-md border">
                <Table className="w-full table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12 bg-background sticky left-0 z-40">
                          <Checkbox
                            onCheckedChange={handleSelectAll}
                            checked={selectedCompanies.length > 0 ? "indeterminate" : false}
                            aria-label="Select all on page or clear all selections"
                          />
                        </TableHead>

                      <TableHead
                        className="cursor-pointer hover:bg-muted/50 bg-background sticky left-12 z-30 min-w-[200px] border-r"
                        onClick={() => requestSort('company')}
                      >
                        <div className="flex items-center">
                          Company
                          {sortConfig?.key === 'company' && (
                            <span className="ml-2">
                              {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </TableHead>

                      <TableHead
                        className="cursor-pointer hover:bg-muted/50 bg-background min-w-[160px]"
                        onClick={() => requestSort('industry')}
                      >
                        <div className="flex items-center">
                          Industry
                          {sortConfig?.key === 'industry' && (
                            <span className="ml-2">
                              {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </TableHead>

                      <TableHead
                        className="cursor-pointer hover:bg-muted/50 bg-background"
                        onClick={() => requestSort('street')}
                      >
                        <div className="flex items-center">
                          Street
                          {sortConfig?.key === 'street' && (
                            <span className="ml-2">
                              {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </TableHead>

                      <TableHead
                        className="cursor-pointer hover:bg-muted/50 bg-background"
                        onClick={() => requestSort('city')}
                      >
                        <div className="flex items-center">
                          City
                          {sortConfig?.key === 'city' && (
                            <span className="ml-2">
                              {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </TableHead>

                      <TableHead
                        className="cursor-pointer hover:bg-muted/50 bg-background"
                        onClick={() => requestSort('state')}
                      >
                        <div className="flex items-center">
                          State
                          {sortConfig?.key === 'state' && (
                            <span className="ml-2">
                              {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </TableHead>

                      <TableHead
                        className="cursor-pointer hover:bg-muted/50 bg-background"
                        onClick={() => requestSort('bbb_rating')}
                      >
                        <div className="flex items-center">
                          BBB Rating
                          {sortConfig?.key === 'bbb_rating' && (
                            <span className="ml-2">
                              {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </TableHead>

                      <TableHead
                        className="cursor-pointer hover:bg-muted/50 bg-background"
                        onClick={() => requestSort('business_phone')}
                      >
                        <div className="flex items-center">
                          Company Phone
                          {sortConfig?.key === 'business_phone' && (
                            <span className="ml-2">
                              {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </TableHead>

                      <TableHead
                        className="cursor-pointer hover:bg-muted/50 bg-background"
                        onClick={() => requestSort('website')}
                      >
                        <div className="flex items-center">
                          Website
                          {sortConfig?.key === 'website' && (
                            <span className="ml-2">
                              {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </TableHead>

                      {hasEstimatedRevenue && (
                        <TableHead
                          className="cursor-pointer hover:bg-muted/50 bg-background min-w-[160px] max-w-[240px]"
                          onClick={() => requestSort('revenue')}>
                          <div className="flex items-center">
                            Estimated Revenue
                            {sortConfig?.key === 'revenue' && (
                              <span className="ml-2">
                                {sortConfig.direction === 'ascending' ? '↑' : '↓'}
                              </span>
                            )}
                          </div>
                        </TableHead>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <>
                      {currentItems.length > 0 &&
                        currentItems.map((company) => (
                          <TableRow key={company.id ?? `${company.company}-${Math.random()}`}>
                            <TableCell className="sticky left-0 z-20 bg-inherit w-12">
                              <Checkbox
                                checked={selectedCompanies.includes(company.id)}
                                onCheckedChange={() => handleSelectCompany(company.id)}
                                disabled={!selectedCompanies.includes(company.id) && selectedCompanies.length >= 25}
                                aria-label={`Select ${company.company}`}
                                className={!selectedCompanies.includes(company.id) && selectedCompanies.length >= 25 ? "opacity-50 cursor-not-allowed" : ""}
                              />
                            </TableCell>
                            <TableCell className="sticky left-12 z-10 bg-inherit font-medium max-w-[240px] align-top border-r">{company.company}</TableCell>
                            <TableCell>{company.industry}</TableCell>
                            <TableCell>{company.street}</TableCell>
                            <TableCell>{company.city}</TableCell>
                            <TableCell>{company.state}</TableCell>
                            <TableCell>{company.bbb_rating}</TableCell>
                            <TableCell>{company.business_phone}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2 max-w-[200px] truncate underline">
                                {company.website && company.website !== "N/A" && company.website !== "NA" ? (
                                  <a
                                    href={
                                      company.website.toString().startsWith("http")
                                        ? company.website
                                        : `https://${company.website}`
                                    }
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-500 hover:text-blue-700"
                                    title="Open website in new tab"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {cleanUrlForDisplay(company.website)}
                                  </a>
                                ) : (
                                  <span className="text-gray-500">N/A</span>
                                )}
                              </div>
                            </TableCell>
                            {hasEstimatedRevenue && (
                              <TableCell className="px-6 py-2 max-w-[240px] align-top text-sm">
                                {company.revenue ? (
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium text-foreground">
                                      {formatRevenueForDisplay(company.revenue)}
                                    </span>
                                    {company.revenue_confidence && (
                                      <TooltipProvider delayDuration={100}>
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <span className="flex items-center gap-1 cursor-help">
                                              <span
                                                className={`text-xs font-medium px-1.5 py-0.5 rounded-full text-center ${
                                                  company.revenue_confidence === "high"
                                                    ? "bg-green-100 text-green-700"
                                                    : company.revenue_confidence === "medium"
                                                    ? "bg-blue-100 text-blue-700"
                                                    : "bg-yellow-100 text-yellow-700"
                                                }`}
                                              >
                                                {company.revenue_confidence.charAt(0).toUpperCase() + 
                                                 company.revenue_confidence.slice(1).toLowerCase()} confidence
                                              </span>
                                              <sup className="text-muted-foreground">*</sup>
                                            </span>
                                          </TooltipTrigger>
                                          <TooltipContent>
                                            <p>This is an estimated value and may not reflect actual revenue.</p>
                                          </TooltipContent>
                                        </Tooltip>
                                      </TooltipProvider>
                                    )}
                                  </div>
                                ) : (
                                  "N/A"
                                )}
                              </TableCell>
                            )}
                          </TableRow>
                        ))}

                      {!loading && currentItems.length === 0 && (
                        <TableRow key="no-results">
                          <TableCell colSpan={9} className="text-center">
                            No results found.
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  </TableBody>
                </Table>
              </div>


              {/* Pagination controls */}
              {sortedFilteredLeads.length > 0 && (
                <div className="mb-4 flex items-center justify-between">
                  <div className="text-sm text-muted-foreground">
                    Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, sortedFilteredLeads.length)} of {sortedFilteredLeads.length} results for {searchCriteria.industry} in {searchCriteria.location}, {searchCriteria.country}
                  </div>

                  <div className="flex items-center gap-4">
                    <Select value={itemsPerPage.toString()} onValueChange={(value) => {
                      setItemsPerPage(Number(value));
                      setCurrentPage(1); // Reset to first page when changing items per page
                    }}>
                      <SelectTrigger className="w-[120px]">
                        <SelectValue placeholder="Items per page" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="25">25 per page</SelectItem>
                        <SelectItem value="50">50 per page</SelectItem>
                        <SelectItem value="100">100 per page</SelectItem>
                      </SelectContent>
                    </Select>

                    <Pagination>
                      <PaginationContent>
                        <PaginationItem>
                          <PaginationPrevious
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                            aria-disabled={currentPage === 1}
                            className={currentPage === 1 ? "pointer-events-none opacity-50" : ""}
                          />
                        </PaginationItem>

                        {getPageNumbers().map((page, index) => (
                          <PaginationItem key={index}>
                            {page === 'ellipsis' ? (
                              <PaginationEllipsis />
                            ) : (
                              <PaginationLink
                                isActive={page === currentPage}
                                onClick={() => setCurrentPage(Number(page))}
                              >
                                {page}
                              </PaginationLink>
                            )}
                          </PaginationItem>
                        ))}

                        <PaginationItem>
                          <PaginationNext
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            aria-disabled={currentPage === totalPages}
                            className={currentPage === totalPages ? "pointer-events-none opacity-50" : ""}
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  </div>
                </div>
              )}
              {/* Results section */}
            </div>
          </CardContent>

        </Card>
        <div className="flex flex-col items-end mt-4 gap-2 relative">
          {/* Enrichment button and optional progress */}
          <div className="flex items-center gap-4 relative">
            {loading && (
              <div className="text-sm font-medium text-muted-foreground">
                {/* Progress: {progress}% */}
              </div>
            )}

            {/* Custom Dropdown Implementation */}
            {teamMembershipLoading ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                <span className="text-sm text-muted-foreground">Checking access...</span>
              </div>
            ) : (
              // Always show premium dropdown - free tier concept removed
              // Original condition: !isFreeTierUser() ? (
              <div className="relative">
                <Button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  disabled={selectedCompanies.length === 0 || loading}
                  className="bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed gap-2 min-w-[180px]"
                >
                  <Database className="h-4 w-4" />
                  {loading ? "Enriching..." : "Enrich"}
                  <ChevronDown className={`h-4 w-4 transition-transform ${dropdownOpen ? "rotate-180" : ""}`} />
                </Button>

                {dropdownOpen && (
                  <div className="absolute bottom-full right-0 mb-2 w-56 bg-[#1A2133] border border-[#2E3A59] rounded-md shadow-lg z-50 animate-fadeIn">
                    <div className="py-1">
                      {/* Company Enrichment */}
                        <button
                        onClick={() => {
                          setDropdownOpen(false);
                          handleSmartCompanyEnrichment();
                        }}
                          className="w-full px-3 py-2 text-left hover:bg-[#2A3349] text-gray-300 hover:text-white transition-colors flex items-start gap-2"
                        >
                          <Building className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
                          <div className="flex-1">
                            <div className="text-sm font-medium">Enrich Companies</div>
                            <div className="text-xs text-gray-400">-1 credit per lead</div>
                          </div>
                        </button>

                      {/* People Enrichment */}
                              <button
                        onClick={() => {
                          setDropdownOpen(false);
                          handleSmartPeopleEnrichment();
                        }}
                          className="w-full px-3 py-2 text-left hover:bg-[#2A3349] text-gray-300 hover:text-white transition-colors flex items-start gap-2"
                        >
                          <Users className="h-4 w-4 text-green-400 mt-0.5 flex-shrink-0" />
                          <div className="flex-1">
                            <div className="text-sm font-medium">Enrich People</div>
                            <div className="text-xs text-gray-400">-1 credit per lead</div>
                          </div>
                        </button>

                    </div>
                  </div>
                )}
              </div>
            )
            // Removed free tier basic enrichment UI - all users now get same experience
            // Original else block with Basic Enrichment (Free) button was here
            }
          </div>
          {/* Selection summary */}
          <div className="text-sm text-muted-foreground">
            <span className="text-foreground font-semibold">{selectedCompanies.length}</span>
            <span className="mx-1">of</span>
            <span className="text-foreground">{sortedFilteredLeads.length}</span> selected
            <span className="ml-2 text-orange-600 font-medium">
              (Max: 25)
            </span>
            {selectedCompanies.length >= 25 && (
              <span className="ml-2 text-red-600 font-medium">
                • Limit reached
              </span>
            )}
          </div>
          
          {/* Click outside to close dropdown */}
          {dropdownOpen && (
            <div
              className="fixed inset-0 z-40"
              onClick={() => setDropdownOpen(false)}
            />
          )}
          
        </div>

        {/* ── ENRICHMENT RESULTS ── */}
        <div className="mt-6 space-y-8">
          {/* ── LOADER BANNER ── */}
          {loading && (
            <div className="flex flex-col items-center py-4">
              <Loader />
              <p className="mt-2 text-sm text-muted-foreground">
                Scraping and enriching data… please wait
              </p>
            </div>
          )}
          
          {/* ── EMPTY RESULTS BANNER ── */}
          {showEmptyResultsBanner && (
            <EmptyResultsBanner
              enrichmentType={emptyResultsInfo.enrichmentType}
              hasDatabaseResults={emptyResultsInfo.hasDatabaseResults}
              hasScrapedResults={emptyResultsInfo.hasScrapedResults}
              totalCompanies={emptyResultsInfo.totalCompanies}
              onRetry={() => {
                // Retry the last enrichment operation
                if (enrichmentType === "company") {
                  handleSmartCompanyEnrichment();
                } else if (enrichmentType === "people") {
                  handlePeopleEnrichment(selectedDataSource);
                } else if (enrichmentType === "both") {
                  handleStartEnrichmentDropdown("both", selectedDataSource);
                }
              }}
              onViewDatabaseResults={() => {
                // Show database results if available
                if (emptyResultsInfo.hasDatabaseResults) {
                  setShowEmptyResultsBanner(false);
                  // The results should already be visible, but we can ensure they're shown
                }
              }}
            />
          )}

          {/* ── FIRST ENRICHMENT RESULTS ── */}
          {hasFirstEnrichment && (dbEnrichedCompanies.length > 0 || scrapedEnrichedCompanies.length > 0) && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-3xl font-bold">
                  {firstEnrichmentType === "company" ? "Company Enrichment Results" : 
                   firstEnrichmentType === "people" ? "People Enrichment Results" : 
                   "Enrichment Results"}
                </h2>
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={clearFirstEnrichmentResults}
                  className="flex items-center gap-2"
                >
                  <X className="h-4 w-4" />
                  Clear Results
                </Button>
              </div>
              
              {/* Show nested table for people enrichment, unified table for company enrichment, grouped for both enrichment */}
              {firstEnrichmentType === "people" ? (
                // People enrichment: Show nested table with company checkboxes
                (() => {
                const allEnrichedCompanies = [...dbEnrichedCompanies, ...scrapedEnrichedCompanies];
                
                // Group by company name to show per-company nested tables
                const groupedByCompany = allEnrichedCompanies.reduce((acc: Record<string, any>, company: any) => {
                  const companyKey = company.company || 'Unknown Company';
                  if (!acc[companyKey]) {
                    acc[companyKey] = [];
                  }
                  acc[companyKey].push(company);
                  return acc;
                }, {});

                // Convert grouped data to array for filtering and sorting
                let groupedEntries = Object.entries(groupedByCompany);

                // Apply search filter
                if (peopleResultsSearchTerm) {
                  groupedEntries = groupedEntries.filter(([companyName, companies]) => {
                    return companies.some((company: any) => 
                      company.company?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                      company.website?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                      company.industry?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                      company.city?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                      company.state?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                      // Search in people data
                      (company.people && company.people.some((person: any) => 
                        person.name?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                        person.title?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                        person.email?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                        person.phone?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase()) ||
                        person.linkedin?.toLowerCase().includes(peopleResultsSearchTerm.toLowerCase())
                      ))
                    );
                  });
                }

                // Calculate pagination for people results
                const peopleResultsTotalPages = Math.ceil(groupedEntries.length / peopleResultsItemsPerPage);
                const peopleResultsIndexOfLastItem = peopleResultsCurrentPage * peopleResultsItemsPerPage;
                const peopleResultsIndexOfFirstItem = peopleResultsIndexOfLastItem - peopleResultsItemsPerPage;
                const currentPeopleResultsItems = groupedEntries.slice(peopleResultsIndexOfFirstItem, peopleResultsIndexOfLastItem);

                return (
                  <div>
                    {/* Search, Filter, Sort, and Export Controls - Top of People Results */}
                    <div className="space-y-4 mb-6">
                      {/* Top Row: Search, Filter, Sort, Export */}
                      <div className="flex items-center gap-4">
                        {/* Search Bar */}
                        <div className="relative flex-1 max-w-md">
                          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                          <Input
                            type="search"
                            placeholder="Search people and companies..."
                            className="pl-8"
                            value={peopleResultsSearchTerm}
                            onChange={(e) => {
                              setPeopleResultsSearchTerm(e.target.value);
                              setPeopleResultsCurrentPage(1); // Reset to first page when searching
                            }}
                          />
                        </div>

                        {/* Filter Button */}
                        <Button
                          variant="outline"
                          onClick={() => setPeopleResultsShowFilters(!peopleResultsShowFilters)}
                          className="flex items-center gap-2"
                        >
                          <Filter className="h-4 w-4" />
                          Filters
                        </Button>

                        {/* Sort Dropdown */}
                        <Select
                          value={peopleResultsSortConfig ? `${peopleResultsSortConfig.key}-${peopleResultsSortConfig.direction}` : ""}
                          onValueChange={(value) => {
                            if (value) {
                              const [key, direction] = value.split('-');
                              setPeopleResultsSortConfig({ key, direction: direction as 'ascending' | 'descending' });
                              setPeopleResultsCurrentPage(1); // Reset to first page when sorting
                            } else {
                              setPeopleResultsSortConfig(null);
                            }
                          }}
                        >
                          <SelectTrigger className="w-48">
                            <SelectValue placeholder="Sort by..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="company-ascending">Company Name (A-Z)</SelectItem>
                            <SelectItem value="company-descending">Company Name (Z-A)</SelectItem>
                            <SelectItem value="industry-ascending">Industry (A-Z)</SelectItem>
                            <SelectItem value="industry-descending">Industry (Z-A)</SelectItem>
                          </SelectContent>
                        </Select>

                        {/* Export All Button */}
                        <div className="flex items-center gap-2">
                          <Button
                            onClick={async () => {
                              const allDataForExport = allEnrichedCompanies.flatMap(company => {
                                if (Array.isArray((company as any).people) && (company as any).people.length > 0) {
                                  return (company as any).people.map((person: any, idx: number) => {
                                    const { id, lead_id, ...companyWithoutIds } = company;
                                    return {
                                      ...companyWithoutIds,
                                      ownerFirstName: person.owner_first_name || person.name?.split(' ')[0] || person.first_name || "",
                                      ownerLastName: person.owner_last_name || person.name?.split(' ').slice(1).join(' ') || "",
                                      ownerTitle: person.owner_title || person.title || "",
                                      ownerEmail: person.owner_email || person.email || "",
                                      ownerPhoneNumber: person.owner_phone_number || person.phone || person.phone_number || "",
                                      ownerLinkedin: person.owner_linkedin || person.linkedin || person.linkedin_url || "",
                                    };
                                  });
                                } else {
                                  const { id, lead_id, ...companyWithoutIds } = company;
                                  return [companyWithoutIds];
                                }
                              });

                              if (allDataForExport.length === 0) {
                                showNotification("No data to export.", "info");
                                return;
                              }

                              downloadCSV(allDataForExport, "enrich_people_all_results.csv");
                              showNotification(`Successfully exported all ${allDataForExport.length} items.`, "success");
                            }}
                            variant="outline"
                            className="flex items-center gap-2"
                          >
                            <Download className="h-4 w-4" />
                            Export All ({allEnrichedCompanies.length} companies)
                          </Button>

                          {/* <ForwardDropdown
                            selectedCompanies={selectedEnrichedResults}
                            onForwardComplete={() => {
                              // Optional: Add any cleanup or refresh logic here
                            }}
                            onNotification={showNotification}
                            scrapingHistory={allEnrichedCompanies}
                          /> */}
                        </div>
                      </div>
                    </div>

                    {/* Nested Table Structure */}
                    <div className="space-y-2">
                      {currentPeopleResultsItems.map(([companyName, companies]: [string, any]) => {
                        const company = companies[0]; // Use first company as representative
                        const peopleCount = company.people?.length || 0;
                        const hasGrowjoData = company.people?.some((p: any) => p.source === "Growjo");
                        const hasApolloData = company.people?.some((p: any) => p.source === "Apollo");
                        
                        // Check if company is selected (for enrichment purposes)
                        const isCompanySelected = selectedEnrichedResults.includes(company.id);
                        
                        // Get all people IDs for this company
                        const allPeopleIds = companies.flatMap((c: any) => c.people?.map((p: any) => p.id) || []).filter(Boolean);
                        const selectedPeopleCount = allPeopleIds.filter((id: any) => selectedEnrichedPeople.includes(id)).length;
                        const isAllPeopleSelected = allPeopleIds.length > 0 && selectedPeopleCount === allPeopleIds.length;

                        return (
                          <div key={companyName} className="border rounded-lg overflow-hidden">
                            {/* Company Row with Checkbox */}
                            <div className="bg-background border-b p-4">
                              <div className="flex items-center gap-3">
                                <Checkbox
                                  checked={isCompanySelected}
                                  onCheckedChange={(checked) => {
                                    if (checked) {
                                      // Select only the company for enrichment purposes
                                      const newSelection = [...selectedEnrichedResults, company.id];
                                      setSelectedEnrichedResults(newSelection);
                                    } else {
                                      // Deselect only the company
                                      const newSelection = selectedEnrichedResults.filter(id => id !== company.id);
                                      setSelectedEnrichedResults(newSelection);
                                    }
                                  }}
                                />
                                <div className="flex-1">
                                  <h3 className="text-lg font-semibold">{companyName}</h3>
                                  <div className="flex items-center gap-4 text-sm text-gray-600">
                                    <span>{peopleCount} people</span>
                                    <span>•</span>
                                    <span>{company.industry || 'Unknown Industry'}</span>
                                    {company.website && (
                                      <>
                                        <span>•</span>
                                        <span className="font-mono">{company.website}</span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                            
                            {/* People Table */}
                            {peopleCount > 0 && (
                              <div className="p-0">
                                <EnrichmentResults
                                  enrichedCompanies={companies}
                                  enrichmentViewType="people"
                                  selectedCompanies={selectedEnrichedResults}
                                  onSelectionChange={setSelectedEnrichedResults}
                                  selectedPeople={selectedEnrichedPeople}
                                  onPeopleSelectionChange={setSelectedEnrichedPeople}
                                  rowClassName={(person, index) => {
                                    // Color code based on source type
                                    if (person.sourceType === "database") return "bg-teal-50";
                                    if (person.sourceType === "scraped") return "bg-yellow-50";
                                    return "";
                                  }}
                                />
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Pagination Controls for People Results */}
                    {groupedEntries.length > peopleResultsItemsPerPage && (
                      <div className="flex items-center justify-between mt-6">
                        <div className="flex items-center gap-4">
                          <Select value={peopleResultsItemsPerPage.toString()} onValueChange={(value) => {
                            setPeopleResultsItemsPerPage(Number(value));
                            setPeopleResultsCurrentPage(1); // Reset to first page when changing items per page
                          }}>
                            <SelectTrigger className="w-20">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="10">10</SelectItem>
                              <SelectItem value="25">25</SelectItem>
                              <SelectItem value="50">50</SelectItem>
                              <SelectItem value="100">100</SelectItem>
                            </SelectContent>
                          </Select>
                          <p className="text-sm text-gray-600">
                            Showing {peopleResultsIndexOfFirstItem + 1} to {Math.min(peopleResultsIndexOfLastItem, groupedEntries.length)} of {groupedEntries.length} companies
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <Pagination>
                            <PaginationContent>
                              <PaginationItem>
                                <PaginationPrevious
                                  onClick={() => setPeopleResultsCurrentPage(prev => Math.max(prev - 1, 1))}
                                  aria-disabled={peopleResultsCurrentPage === 1}
                                  className={peopleResultsCurrentPage === 1 ? "pointer-events-none opacity-50" : ""}
                                />
                              </PaginationItem>

                              {(() => {
                                const pageNumbers = [];
                                if (peopleResultsTotalPages <= 7) {
                                  for (let i = 1; i <= peopleResultsTotalPages; i++) {
                                    pageNumbers.push(i);
                                  }
                                } else {
                                  pageNumbers.push(1);
                                  let startPage = Math.max(2, peopleResultsCurrentPage - 2);
                                  let endPage = Math.min(peopleResultsTotalPages - 1, peopleResultsCurrentPage + 2);
                                  
                                  if (peopleResultsCurrentPage <= 4) {
                                    endPage = 5;
                                  } else if (peopleResultsCurrentPage >= peopleResultsTotalPages - 3) {
                                    startPage = peopleResultsTotalPages - 4;
                                  }
                                  
                                  if (startPage > 2) {
                                    pageNumbers.push('ellipsis');
                                  }
                                  
                                  for (let i = startPage; i <= endPage; i++) {
                                    pageNumbers.push(i);
                                  }
                                  
                                  if (endPage < peopleResultsTotalPages - 1) {
                                    pageNumbers.push('ellipsis');
                                  }
                                  
                                  pageNumbers.push(peopleResultsTotalPages);
                                }

                                return pageNumbers.map((page, index) => (
                                  <PaginationItem key={index}>
                                    {page === 'ellipsis' ? (
                                      <PaginationEllipsis />
                                    ) : (
                                      <PaginationLink
                                        isActive={page === peopleResultsCurrentPage}
                                        onClick={() => setPeopleResultsCurrentPage(Number(page))}
                                      >
                                        {page}
                                      </PaginationLink>
                                    )}
                                  </PaginationItem>
                                ));
                              })()}

                              <PaginationItem>
                                <PaginationNext
                                  onClick={() => setPeopleResultsCurrentPage(prev => Math.min(prev + 1, peopleResultsTotalPages))}
                                  aria-disabled={peopleResultsCurrentPage === peopleResultsTotalPages}
                                  className={peopleResultsCurrentPage === peopleResultsTotalPages ? "pointer-events-none opacity-50" : ""}
                                />
                              </PaginationItem>
                            </PaginationContent>
                          </Pagination>
                        </div>
                      </div>
                    )}
                  </div>
                );
                })()
              ) : firstEnrichmentType === "both" ? (
                // Both enrichment: Use EnrichmentResults component with raw data
              <EnrichmentResults
                  enrichedCompanies={[...completedLeads]}
                  enrichmentViewType="both"
                selectedCompanies={selectedEnrichedResults}
                onSelectionChange={setSelectedEnrichedResults}
                selectedPeople={selectedEnrichedPeople}
                onPeopleSelectionChange={setSelectedEnrichedPeople}
                rowClassName={(company, index) => {
                  // Color code based on source type
                    if ((company as any).isProcessing) return "bg-blue-50";
                  if (company.sourceType === "database") return "bg-teal-50";
                  if (company.sourceType === "scraped") return "bg-yellow-50";
                  return "";
                }}
              />
              ) : (
                // Company enrichment: Show unified table without banners
              <EnrichmentResults
                  enrichedCompanies={[...dbEnrichedCompanies, ...scrapedEnrichedCompanies]}
                  enrichmentViewType={firstEnrichmentType || "company"}
                selectedCompanies={selectedEnrichedResults}
                onSelectionChange={setSelectedEnrichedResults}
                selectedPeople={selectedEnrichedPeople}
                onPeopleSelectionChange={setSelectedEnrichedPeople}
                rowClassName={(company, index) => {
                  // Color code based on source type
                  if (company.sourceType === "database") return "bg-teal-50";
                  if (company.sourceType === "scraped") return "bg-yellow-50";
                  return "";
                }}
              />
          )}

          {/* Second Enrichment Button - Shows complementary enrichment type */}
          {initialEnrichmentType && (
            <div className="flex flex-col items-end mt-6 gap-2">
                  <Button
                    onClick={async () => {
                      // Map enriched companies back to original leads for enrichment
                      // Only use company selections, not people selections
                      const enrichedCompanies = [...dbEnrichedCompanies, ...scrapedEnrichedCompanies];
                      const selectedEnrichedData = enrichedCompanies.filter(company => 
                        selectedEnrichedResults.includes(company.id)
                      );
                      // Update selectedCompanies to match the enriched selection
                      const originalIds = selectedEnrichedData.map(company => 
                        normalizedLeads.find(lead => lead.company === company.company)?.id
                      ).filter((id): id is number => id !== undefined);
                      setSelectedCompanies(originalIds);
                      
                      // Perform second enrichment based on complementary type
                      const complementaryType = getComplementaryEnrichmentType(initialEnrichmentType);
                      if (complementaryType === "company") {
                        await handleSecondCompanyEnrichment(originalIds, selectedEnrichedData);
                      } else if (complementaryType === "people") {
                        await handleSecondPeopleEnrichment(originalIds, selectedEnrichedData);
                      }
                    }}
                    disabled={selectedEnrichedResults.length === 0 || secondEnrichmentLoading}
                    className="bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600 text-white border-0 disabled:opacity-50 disabled:cursor-not-allowed gap-2 min-w-[180px] flex flex-col items-center py-3"
                  >
                    <div className="flex items-center gap-2">
                      {initialEnrichmentType === "company" ? (
                        <Users className="h-4 w-4" />
                      ) : (
                        <Building className="h-4 w-4" />
                      )}
                      <span className="text-sm font-medium">
                        {secondEnrichmentLoading ? "Enriching..." : `Enrich ${getComplementaryEnrichmentType(initialEnrichmentType)}`}
                      </span>
                    </div>
                    <div className="text-xs text-gray-300 -mt-1.5 text-center">-1 credit per lead</div>
                  </Button>
                  
                  {/* Selection summary for results - positioned below the button */}
                  <div className="text-sm text-muted-foreground">
                    <span className="text-foreground font-semibold">{selectedEnrichedResults.length}</span>
                    <span className="mx-1">of</span>
                    <span className="text-foreground">{[...dbEnrichedCompanies, ...scrapedEnrichedCompanies].length}</span> selected
                    <span className="ml-2 text-orange-600 font-medium">
                      (Max: 25)
                    </span>
                    {selectedEnrichedResults.length >= 25 && (
                      <span className="ml-2 text-red-600 font-medium">
                        • Limit reached
                      </span>
                    )}
                  </div>
                  
                </div>
              )}
              
              {/* Second enrichment loading animation - same size as main loading */}
              {secondEnrichmentLoading && (
                <div className="flex flex-col items-center py-4">
                  <Loader />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Second Enrichment Results Section */}
        {hasSecondEnrichment && (secondDbEnrichedCompanies.length > 0 || secondScrapedEnrichedCompanies.length > 0) && (
          <div className="mt-8 space-y-8">
            <div className="border-t pt-8">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-3xl font-bold text-foreground">
                  Combined Enrichment Results
                </h3>
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={clearSecondEnrichmentResults}
                  className="flex items-center gap-2"
                >
                  <X className="h-4 w-4" />
                  Clear Results
                </Button>
              </div>
              
              {/* Always show combined format for second enrichment results - merge with first enrichment data */}
              <EnrichmentResults
                enrichedCompanies={(() => {
                  // Get first enrichment results
                  const firstEnrichmentResults = [...dbEnrichedCompanies, ...scrapedEnrichedCompanies];
                  // Get second enrichment results
                  const secondEnrichmentResults = [...secondDbEnrichedCompanies, ...secondScrapedEnrichedCompanies];
                  
                  // Filter first enrichment results to only include selected companies for second enrichment
                  const selectedFirstEnrichmentResults = firstEnrichmentResults.filter(company => 
                    selectedEnrichedResults.includes(company.id)
                  );
                  
                  // Merge the results by company name
                  const mergedResults = [...selectedFirstEnrichmentResults];
                  
                  secondEnrichmentResults.forEach(secondResult => {
                    const existingIndex = mergedResults.findIndex(existing => existing.company === secondResult.company);
                    if (existingIndex >= 0) {
                      // Merge with existing company data
                      const existing = mergedResults[existingIndex];
                      mergedResults[existingIndex] = {
                        ...existing,
                        ...secondResult,
                        // Preserve people data from both enrichments
                        people: [
                          ...(existing.people || []),
                          ...(secondResult.people || [])
                        ].filter((person, index, self) => 
                          // Remove duplicates based on email or name
                          index === self.findIndex(p => 
                            (p.ownerEmail && p.ownerEmail === person.ownerEmail) ||
                            (p.email && p.email === person.email) ||
                            (p.ownerFirstName && p.ownerLastName && 
                             p.ownerFirstName === person.ownerFirstName && 
                             p.ownerLastName === person.ownerLastName)
                          )
                        )
                      };
                    } else {
                      // Add new company if not found in first enrichment
                      mergedResults.push(secondResult);
                    }
                  });
                  
                  return mergedResults;
                })()}
                enrichmentViewType="both"
                selectedCompanies={selectedEnrichedResults}
                onSelectionChange={setSelectedEnrichedResults}
                selectedPeople={selectedEnrichedPeople}
                onPeopleSelectionChange={setSelectedEnrichedPeople}
                rowClassName={(company, index) => {
                  // Color code based on source type
                  if (company.sourceType === "database") return "bg-teal-50";
                  if (company.sourceType === "scraped") return "bg-yellow-50";
                  return "";
                }}
              />
            </div>
          </div>
        )}


        <div className="flex justify-end mb-4">
          <Button
            onClick={() => {
              sessionStorage.removeItem("leads");
              // sessionStorage.removeItem("enrichedResults");
              sessionStorage.removeItem("subscriptionInfo");
              sessionStorage.removeItem("leadToDraftMap");
              sessionStorage.removeItem("revenueMap");
              router.push("/");
            }}
          >
            Finish and Go Back to Home
          </Button>
        </div>
        <Popup show={showTokenPopup} onClose={() => setShowTokenPopup(false)}>
          <h2 className="text-lg font-bold mb-2">Insufficient Credits</h2>
          <p className="text-sm text-muted-foreground mb-4">
            You don't have enough enrichment tokens to continue. Please upgrade your plan or deselect some companies.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setShowTokenPopup(false)}>
              Cancel
            </Button>
            <Button onClick={() => router.push("/subscription")}>Upgrade Plan</Button>
          </div>
        </Popup>

        <Notif
          show={notif.show}
          message={notif.message}
          type={notif.type}
          onClose={() => setNotif(prev => ({ ...prev, show: false }))}
        />

      </div>
    </>
  )
}