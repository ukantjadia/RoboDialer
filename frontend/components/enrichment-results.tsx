"use client"

import React from "react"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card"
import { Button } from "../components/ui/button"
import { Input } from "../components/ui/input"
import { Checkbox } from "../components/ui/checkbox"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import type { FC } from "react"
import { Search, Download, ArrowLeft, Filter, X, ExternalLink } from "lucide-react"
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
import { useEnrichment } from "@/components/EnrichmentProvider"
import Notif from "@/components/ui/notif"
import axios from "axios"
import { SortDropdown } from "@/components/ui/sort-dropdown"
import ForwardDropdown from "@/components/ui/ForwardDropdown"


interface EnrichmentResultsProps {
  enrichedCompanies: EnrichedCompany[]
  loading?: boolean
  rowClassName?: (company: EnrichedCompany, index: number) => string
  enrichmentViewType: "company" | "people" | "both"
  // Selection state props
  selectedCompanies?: string[]
  onSelectionChange?: (selectedIds: string[]) => void
  // Separate selection for companies vs people
  selectedPeople?: string[]
  onPeopleSelectionChange?: (selectedIds: string[]) => void
}
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;
const DATABASE_URL_NOAPI = DATABASE_URL?.replace(/\/api\/?$/, "");

export interface EnrichedCompany {
  id: string
  lead_id?: string;
  draft_id?: string;
  company: string
  website: string
  industry: string
  productCategory: string
  businessType: string
  employees: number | null
  revenue: string | number
  yearFounded: string
  bbbRating: string
  street: string
  city: string
  state: string
  companyPhone: string
  companyLinkedin: string
  ownerFirstName: string
  ownerLastName: string
  ownerTitle: string
  ownerLinkedin: string
  ownerPhoneNumber: string
  ownerEmail: string
  source: string
  sourceType?: "database" | "scraped";
  people?: any[] // Allow people array for people enrichment
}


// 🆕 NEW: Utility function to format revenue for display
const formatRevenueForDisplay = (revenue: string | number): string => {
  console.log(`🔍 formatRevenueForDisplay (enrichment-results) - Input: ${revenue}, type: ${typeof revenue}`);
  
  if (!revenue || revenue === "N/A" || revenue === "") {
    console.log(`🔍 formatRevenueForDisplay (enrichment-results) - Returning N/A (empty/invalid)`);
    return "N/A";
  }
  
  // If revenue is already formatted (contains $), return as is
  if (typeof revenue === 'string' && revenue.includes('$')) {
    console.log(`🔍 formatRevenueForDisplay (enrichment-results) - Already formatted, returning: ${revenue}`);
    return revenue;
  }
  
  const numRevenue = typeof revenue === 'string' ? parseFloat(revenue) : revenue;
  console.log(`🔍 formatRevenueForDisplay (enrichment-results) - Parsed number: ${numRevenue}`);
  
  if (isNaN(numRevenue)) {
    console.log(`🔍 formatRevenueForDisplay (enrichment-results) - Returning N/A (NaN)`);
    return "N/A";
  }
  
  let result;
  if (numRevenue >= 1000) {
    result = `$${(numRevenue / 1000).toFixed(1)}M`;  // 4.3 → $4.3M
  } else if (numRevenue >= 1) {
    result = `$${numRevenue.toFixed(1)}M`;            // 0.5 → $0.5M
  } else {
    result = `$${(numRevenue * 1000).toFixed(0)}K`;  // 0.002 → $2K
  }
  
  console.log(`🔍 formatRevenueForDisplay (enrichment-results) - Final result: ${result}`);
  return result;
};

export const EnrichmentResults: FC<EnrichmentResultsProps> = ({
  enrichedCompanies,
  loading,
  rowClassName,
  enrichmentViewType,
  selectedCompanies: propSelectedCompanies,
  onSelectionChange,
  selectedPeople: propSelectedPeople,
  onPeopleSelectionChange,
}) => {
  const [notif, setNotif] = useState({
    show: false,
    message: "",
    type: "success" as "success" | "error" | "info",
  });
  const showNotification = (message: string, type: "success" | "error" | "info" = "success") => {
    setNotif({ show: true, message, type });

    // Automatically hide after X seconds (let Notif handle it visually)
    // Optional if Notif itself auto-hides — but helpful as backup
    setTimeout(() => {
      setNotif(prev => ({ ...prev, show: false }));
    }, 3500);
  };

  const [editableCompanies, setEditableCompanies] = useState<EnrichedCompany[]>([])
  const [editingCell, setEditingCell] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  // const { enrichedCompanies, loading } = useEnrichment()
  const router = useRouter()
  
  // Use props if provided, otherwise fall back to internal state
  const [internalSelectedCompanies, setInternalSelectedCompanies] = useState<string[]>([])
  const [internalSelectedPeople, setInternalSelectedPeople] = useState<string[]>([])
  const [selectAll, setSelectAll] = useState(true)
  
  const selectedCompanies = propSelectedCompanies ?? internalSelectedCompanies
  const selectedPeople = propSelectedPeople ?? internalSelectedPeople
  const [searchTerm, setSearchTerm] = useState("")
  const [employeesFilter, setEmployeesFilter] = useState("")
  const [revenueFilter, setRevenueFilter] = useState("")
  const [businessTypeFilter, setBusinessTypeFilter] = useState("")
  const [productFilter, setProductFilter] = useState("")
  const [yearFoundedFilter, setYearFoundedFilter] = useState("")
  const [bbbRatingFilter, setBbbRatingFilter] = useState("")
  const [streetFilter, setStreetFilter] = useState("")
  const [cityFilter, setCityFilter] = useState("")
  const [stateFilter, setStateFilter] = useState("")

  const [hasSorted, setHasSorted] = useState(false);
  const [filteredCompanies, setFilteredCompanies] = useState<EnrichedCompany[]>([])
  const [showFilters, setShowFilters] = useState(false)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const handleFieldChange = (id: string, field: keyof EnrichedCompany, value: any) => {
    setEditableCompanies(prev =>
      prev.map(company =>
        company.id === id ? { ...company, [field]: value } : company
      )
    )
  }

  const handleDiscardChanges = () => {
    setEditableCompanies([...enrichedCompanies])
  }

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(25)


  // Reset to first page when search term or filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, employeesFilter, revenueFilter, businessTypeFilter, productFilter,
    yearFoundedFilter, bbbRatingFilter, streetFilter, cityFilter, stateFilter]);

  const downloadCSV = (data: any[], filename: string) => {
    let columns, keys;
    
    if (enrichmentViewType === "both") {
      // For "both" view, create a combined CSV with company info + people
      columns = [
        { key: "company", label: "Company" },
        { key: "website", label: "Website" },
        { key: "industry", label: "Industry" },
        { key: "employees", label: "Employees" },
        { key: "revenue", label: "Revenue" },
        { key: "yearFounded", label: "Year Founded" },
        { key: "productCategory", label: "Product/Service Category" },
        { key: "businessType", label: "Business Type" },
        { key: "bbbRating", label: "BBB Rating" },
        { key: "street", label: "Street" },
        { key: "city", label: "City" },
        { key: "state", label: "State" },
        { key: "companyPhone", label: "Company Phone" },
        { key: "companyLinkedin", label: "Company LinkedIn" },
        { key: "personName", label: "Person Name" },
        { key: "personTitle", label: "Person Title" },
        { key: "personEmail", label: "Person Email" },
        { key: "personPhone", label: "Person Phone" },
        { key: "personLinkedin", label: "Person LinkedIn" },
        { key: "personSource", label: "Person Source" }
      ];
      keys = columns.map(col => col.key);
    } else {
      // For other views, use existing logic
      columns = enrichmentViewType === "people" ? peopleColumns : companyColumns;
      keys = columns.map(col => col.key);
    }

    // Build CSV header
    const header = keys.join(",");
    
    // Build CSV rows
    let rows;
    if (enrichmentViewType === "both") {
      // For "both" view, flatten company + people data
      rows = data.flatMap(company => {
        const people = company.people || [];
        if (people.length > 0) {
          // If company has people, create a row for each person
          return people.map((person: any) => [
            company.company || "",
            company.website || "",
            company.industry || "",
            company.employees || "",
            company.revenue ? formatRevenueForDisplay(company.revenue) : "",
            company.yearFounded || "",
            company.productCategory || "",
            company.businessType || "",
            company.bbbRating || "",
            company.street || "",
            company.city || "",
            company.state || "",
            company.companyPhone || "",
            company.companyLinkedin || "",
            person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim() || "",
            person.title || "",
            person.email || "",
            person.phone || person.phone_number || "",
            person.linkedin || person.linkedin_url || "",
            person.source || ""
          ]);
        } else if (company.ownerFirstName || company.ownerLastName) {
          // If no people array but has owner info, create a row with owner data
          return [[
            company.company || "",
            company.website || "",
            company.industry || "",
            company.employees || "",
            company.revenue ? formatRevenueForDisplay(company.revenue) : "",
            company.yearFounded || "",
            company.productCategory || "",
            company.businessType || "",
            company.bbbRating || "",
            company.street || "",
            company.city || "",
            company.state || "",
            company.companyPhone || "",
            company.companyLinkedin || "",
            `${company.ownerFirstName || ''} ${company.ownerLastName || ''}`.trim() || "",
            company.ownerTitle || "",
            company.ownerEmail || "",
            company.ownerPhoneNumber || "",
            company.ownerLinkedin || "",
            "Database (Owner)"
          ]];
        } else {
          // If no people or owner info, create a row with just company data
          return [[
            company.company || "",
            company.website || "",
            company.industry || "",
            company.employees || "",
            company.revenue ? formatRevenueForDisplay(company.revenue) : "",
            company.yearFounded || "",
            company.productCategory || "",
            company.businessType || "",
            company.bbbRating || "",
            company.street || "",
            company.city || "",
            company.state || "",
            company.companyPhone || "",
            company.companyLinkedin || "",
            "", "", "", "", "", ""
          ]];
        }
      });
    } else {
      // For other views, use existing logic
      rows = data.map(row =>
        keys.map(key => {
          let value = row[key];
          
          // Format revenue field for CSV export
          if (key === 'revenue' && value && value !== "" && value !== "N/A") {
            value = formatRevenueForDisplay(value);
          }
          
          // Exclude objects/arrays (like 'people') from CSV
          if (typeof value === "object" && value !== null) return "";
          // Escape quotes and commas
          if (typeof value === "string") {
            value = value.replace(/"/g, '""');
            if (value.includes(",") || value.includes("\n")) {
              value = `"${value}"`;
            }
          }
          return value ?? "";
        })
      );
    }
    
    const csvContent = [header, ...rows.map(row => row.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };


  const parseRevenue = (revenueStr: string): number | null => {
    revenueStr = revenueStr.toLowerCase().trim().replace(/[$,]/g, "")
    let multiplier = 1

    if (revenueStr.endsWith("k")) {
      multiplier = 1_000
      revenueStr = revenueStr.slice(0, -1)
    } else if (revenueStr.endsWith("m")) {
      multiplier = 1_000_000
      revenueStr = revenueStr.slice(0, -1)
    } else if (revenueStr.endsWith("b")) {
      multiplier = 1_000_000_000
      revenueStr = revenueStr.slice(0, -1)
    } else {
      // If there's no suffix, treat as-is (e.g. user inputs "50000")
      multiplier = 1
    }

    const value = parseFloat(revenueStr)
    return isNaN(value) ? null : value * multiplier
  }

  const parseFilter = (filterStr: string, isRevenue = false) => {
    const result = { operation: "exact", value: null as number | null, upper: null as number | null }
    filterStr = filterStr.toLowerCase().trim()
    const rangeMatch = filterStr.match(/^(\d+(?:[kmb]?)?)\s*-\s*(\d+(?:[kmb]?)?)$/)
    if (rangeMatch) {
      const val1 = isRevenue ? parseRevenue(rangeMatch[1]) : parseInt(rangeMatch[1])
      const val2 = isRevenue ? parseRevenue(rangeMatch[2]) : parseInt(rangeMatch[2])
      return { operation: "between", value: val1, upper: val2 }
    }
    if (filterStr.startsWith(">=")) result.operation = "greater than or equal", filterStr = filterStr.slice(2)
    else if (filterStr.startsWith(">")) result.operation = "greater than", filterStr = filterStr.slice(1)
    else if (filterStr.startsWith("<=")) result.operation = "less than or equal", filterStr = filterStr.slice(2)
    else if (filterStr.startsWith("<")) result.operation = "less than", filterStr = filterStr.slice(1)
    result.value = isRevenue ? parseRevenue(filterStr) : parseInt(filterStr)
    return result
  }

  // Helper function to parse employee ranges
  const parseEmployeeRange = (employeeValue: any) => {
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

    return null;
  };

  // Helper function to check if a filter value matches an employee range
  const matchesEmployeeRange = (companyEmployees: any, filterValue: number) => {
    const parsed = parseEmployeeRange(companyEmployees);
    
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

  // Helper function to parse year founded ranges
  const parseYearRange = (yearValue: any) => {
    if (!yearValue) return null;
    
    const value = yearValue.toString().trim();
    
    // Handle single years (including with + suffix)
    const singleYearMatch = value.match(/^(\d{4})\+?$/);
    if (singleYearMatch) {
      return parseInt(singleYearMatch[1], 10);
    }

    // Handle ranges like "2020-2023", "2015-2020 founded", "2018-2022 years"
    const rangeMatch = value.match(/^(\d{4})\s*-\s*(\d{4})(?:\s+\w+)?$/);
    if (rangeMatch) {
      const min = parseInt(rangeMatch[1], 10);
      const max = parseInt(rangeMatch[2], 10);
      
      if (min <= max) {
        return { min, max, isRange: true };
      }
    }

    return null;
  };

  // Helper function to check if a filter value matches a year range
  const matchesYearRange = (companyYear: any, filterValue: number) => {
    const parsed = parseYearRange(companyYear);
    
    if (!parsed) return false;
    
    // If it's a single year
    if (typeof parsed === 'number') {
      return parsed === filterValue;
    }
    
    // If it's a range, check if filter value falls within the range
    if (parsed.isRange) {
      return filterValue >= parsed.min && filterValue <= parsed.max;
    }
    
    return false;
  };


  // Filtering and selection logic
  useEffect(() => {
    // For "both" view, we need to filter companies before grouping
    let filteredCompanies = [...enrichedCompanies];
    
    if (enrichmentViewType === "both") {
      // Apply filters to companies for "both" view
      if (searchTerm) {
        const term = searchTerm.toLowerCase()
        filteredCompanies = filteredCompanies.filter((company) => {
          return company.company?.toLowerCase().includes(term) ||
                 company.website?.toLowerCase().includes(term) ||
                 company.industry?.toLowerCase().includes(term) ||
                 company.productCategory?.toLowerCase().includes(term) ||
                 company.city?.toLowerCase().includes(term) ||
                 company.state?.toLowerCase().includes(term) ||
                 company.businessType?.toLowerCase().includes(term) ||
                 `${company.ownerFirstName ?? ""} ${company.ownerLastName ?? ""}`.toLowerCase().includes(term)
        })
      }

      if (employeesFilter) {
        const { operation, value, upper } = parseFilter(employeesFilter)
        if (value !== null) {
          filteredCompanies = filteredCompanies.filter((company) => {
            // Use new range matching logic for employees
            if (operation === "exact") {
              return matchesEmployeeRange(company.employees, value);
            }
            
            // For other operations, parse the company's employee value
            const parsed = parseEmployeeRange(company.employees);
            if (!parsed) return false; // Can't parse company employees
            
            // If company has a single number
            if (typeof parsed === 'number') {
              switch (operation) {
                case "less than": return parsed < value;
                case "greater than": return parsed > value;
                case "less than or equal": return parsed <= value;
                case "greater than or equal": return parsed >= value;
                case "between": return parsed >= value && parsed <= (upper ?? value);
                default: return parsed === value;
              }
            }
            
            // If company has a range, use the mean for comparison
            if (parsed.isRange) {
              const mean = (parsed.min + parsed.max) / 2;
              switch (operation) {
                case "less than": return mean < value;
                case "greater than": return mean > value;
                case "less than or equal": return mean <= value;
                case "greater than or equal": return mean >= value;
                case "between": return mean >= value && mean <= (upper ?? value);
                default: return mean === value;
              }
            }
            
            return false;
          })
        }
      }

      if (revenueFilter) {
        const { operation, value, upper } = parseFilter(revenueFilter, true)
        if (value !== null) {
          filteredCompanies = filteredCompanies.filter((company) => {
            const val = typeof company.revenue === "string"
              ? parseRevenue(company.revenue)
              : company.revenue ?? 0

            if (val === null) return false
            if (operation === "exact") return val === value
            if (operation === "less than") return val < value
            if (operation === "less than or equal") return val <= value
            if (operation === "greater than") return val > value
            if (operation === "greater than or equal") return val >= value
            if (operation === "between") return val >= value && val <= (upper ?? value)
            return true
          })
        }
      }

      if (businessTypeFilter) {
        filteredCompanies = filteredCompanies.filter((company) => 
          company.businessType?.toLowerCase().includes(businessTypeFilter.toLowerCase())
        )
      }
      
      if (productFilter) {
        filteredCompanies = filteredCompanies.filter((company) =>
          company.productCategory?.toLowerCase().includes(productFilter.toLowerCase())
        )
      }

      if (yearFoundedFilter) {
        const { operation, value, upper } = parseFilter(yearFoundedFilter)
        if (value !== null) {
          filteredCompanies = filteredCompanies.filter((company) => {
            // Use new range matching logic for year founded
            if (operation === "exact") {
              return matchesYearRange(company.yearFounded, value);
            }
            
            // For other operations, parse the company's year value
            const parsed = parseYearRange(company.yearFounded);
            if (!parsed) return false; // Can't parse company year
            
            // If company has a single year
            if (typeof parsed === 'number') {
              switch (operation) {
                case "less than": return parsed < value;
                case "greater than": return parsed > value;
                case "less than or equal": return parsed <= value;
                case "greater than or equal": return parsed >= value;
                case "between": return parsed >= value && parsed <= (upper ?? value);
                default: return parsed === value;
              }
            }
            
            // If company has a range, use the mean for comparison
            if (parsed.isRange) {
              const mean = (parsed.min + parsed.max) / 2;
              switch (operation) {
                case "less than": return mean < value;
                case "greater than": return mean > value;
                case "less than or equal": return mean <= value;
                case "greater than or equal": return mean >= value;
                case "between": return mean >= value && mean <= (upper ?? value);
                default: return mean === value;
              }
            }
            
            return false;
          })
        } else {
          // Fallback to string matching for non-numeric filters
          filteredCompanies = filteredCompanies.filter((company) =>
            company.yearFounded?.toLowerCase().includes(yearFoundedFilter.toLowerCase())
          )
        }
      }

      if (bbbRatingFilter) {
        filteredCompanies = filteredCompanies.filter((company) =>
          company.bbbRating?.toLowerCase().includes(bbbRatingFilter.toLowerCase())
        )
      }

      if (streetFilter) {
        filteredCompanies = filteredCompanies.filter((company) =>
          company.street?.toLowerCase().includes(streetFilter.toLowerCase())
        )
      }

      if (cityFilter) {
        filteredCompanies = filteredCompanies.filter((company) =>
          company.city?.toLowerCase().includes(cityFilter.toLowerCase())
        )
      }

      if (stateFilter) {
        filteredCompanies = filteredCompanies.filter((company) =>
          company.state?.toLowerCase().includes(stateFilter.toLowerCase())
        )
      }

      setFilteredCompanies(filteredCompanies)
      setEditableCompanies(filteredCompanies)
      
      return;
    }

    // Calculate the data that's actually displayed in the table for other views
    let displayData: any[] = [];
    if (enrichmentViewType === "company") {
      // Calculate companyRows inline to avoid dependency issues
      displayData = enrichedCompanies.flatMap(company => {
        // If company has a people array, expand it into multiple rows
        if (Array.isArray((company as any).people) && (company as any).people.length > 0) {
          return (company as any).people.map((person: any, idx: number) => ({
            ...company,
            id: `${company.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            // Map the contact structure to owner fields
            ownerFirstName: person.owner_first_name || person.name?.split(' ')[0] || person.first_name || "",
            ownerLastName: person.owner_last_name || person.name?.split(' ').slice(1).join(' ') || "",
            ownerTitle: person.owner_title || person.title || "",
            ownerEmail: person.owner_email || person.email || "",
            ownerPhoneNumber: person.owner_phone_number || person.phone || person.phone_number || "",
            ownerLinkedin: person.owner_linkedin || person.linkedin || person.linkedin_url || "",
          }));
        } else {
          // Single company row (no people array or empty people array)
          return [{
            ...company,
            id: company.id,
          }];
        }
      });
    } else if (enrichmentViewType === "people") {
      // Calculate peopleRows inline to avoid dependency issues
      displayData = enrichedCompanies.flatMap(company => {
        if (Array.isArray((company as any).people)) {
          return (company as any).people.map((person: any, idx: number) => ({
            ...person,
            // Map the person data to the expected display format
            name: person.name || `${person.owner_first_name || ''} ${person.owner_last_name || ''}`.trim(),
            title: person.title || person.owner_title || '',
            email: person.email || person.owner_email || '',
            phone: person.phone || person.owner_phone_number || '',
            linkedin: person.linkedin || person.owner_linkedin || '',
            company: company.company,
            website: company.website,
            industry: company.industry,
            id: person.id || `${company.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          }));
        } else if ((company as any).ownerFirstName || (company as any).ownerLastName) {
          // Fallback: treat owner fields as a single person
          return [{
            name: `${(company as any).ownerFirstName || ''} ${(company as any).ownerLastName || ''}`.trim(),
            title: (company as any).ownerTitle || '',
            email: (company as any).ownerEmail || '',
            phone: (company as any).ownerPhoneNumber || '',
            linkedin: (company as any).ownerLinkedin || '',
            company: company.company,
            website: company.website,
            industry: company.industry,
            id: `${company.id}-owner`,
          }];
        }
        return [];
      });
    } else {
      displayData = enrichedCompanies;
    }

    let filtered = [...displayData]

    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(
        (item) => {
          if (enrichmentViewType === "people") {
            return item.name?.toLowerCase().includes(term) ||
                   item.title?.toLowerCase().includes(term) ||
                   item.email?.toLowerCase().includes(term) ||
                   item.company?.toLowerCase().includes(term)
          } else {
            return item.company?.toLowerCase().includes(term) ||
                   item.website?.toLowerCase().includes(term) ||
                   item.industry?.toLowerCase().includes(term) ||
                   item.productCategory?.toLowerCase().includes(term) ||
                   `${item.ownerFirstName ?? ""} ${item.ownerLastName ?? ""}`.toLowerCase().includes(term)
          }
        }
      )
    }

    if (employeesFilter) {
      const { operation, value, upper } = parseFilter(employeesFilter)
      if (value !== null) {
        filtered = filtered.filter((item) => {
          // Use new range matching logic for employees
          if (operation === "exact") {
            return matchesEmployeeRange(item.employees, value);
          }
          
          // For other operations, parse the item's employee value
          const parsed = parseEmployeeRange(item.employees);
          if (!parsed) return false; // Can't parse item employees
          
          // If item has a single number
          if (typeof parsed === 'number') {
            switch (operation) {
              case "less than": return parsed < value;
              case "greater than": return parsed > value;
              case "less than or equal": return parsed <= value;
              case "greater than or equal": return parsed >= value;
              case "between": return parsed >= value && parsed <= (upper ?? value);
              default: return parsed === value;
            }
          }
          
          // If item has a range, use the mean for comparison
          if (parsed.isRange) {
            const mean = (parsed.min + parsed.max) / 2;
            switch (operation) {
              case "less than": return mean < value;
              case "greater than": return mean > value;
              case "less than or equal": return mean <= value;
              case "greater than or equal": return mean >= value;
              case "between": return mean >= value && mean <= (upper ?? value);
              default: return mean === value;
            }
          }
          
          return false;
        })
      }
    }

    if (revenueFilter) {
      const { operation, value, upper } = parseFilter(revenueFilter, true)
      if (value !== null) {
        filtered = filtered.filter((item) => {
          const val = typeof item.revenue === "string"
            ? parseRevenue(item.revenue)
            : item.revenue ?? 0

          if (val === null) return false
          if (operation === "exact") return val === value
          if (operation === "less than") return val < value
          if (operation === "less than or equal") return val <= value
          if (operation === "greater than") return val > value
          if (operation === "greater than or equal") return val >= value
          if (operation === "between") return val >= value && val <= (upper ?? value)
          return true
        })
      }
    }

    if (businessTypeFilter) {
      filtered = filtered.filter((item) => item.businessType?.toLowerCase().includes(businessTypeFilter.toLowerCase()))
    }
    if (productFilter) {
      filtered = filtered.filter((item) =>
        item.productCategory?.toLowerCase().includes(productFilter.toLowerCase())
      )
    }

    if (yearFoundedFilter) {
      const { operation, value, upper } = parseFilter(yearFoundedFilter)
      if (value !== null) {
        filtered = filtered.filter((item) => {
          // Use new range matching logic for year founded
          if (operation === "exact") {
            return matchesYearRange(item.yearFounded, value);
          }
          
          // For other operations, parse the item's year value
          const parsed = parseYearRange(item.yearFounded);
          if (!parsed) return false; // Can't parse item year
          
          // If item has a single year
          if (typeof parsed === 'number') {
            switch (operation) {
              case "less than": return parsed < value;
              case "greater than": return parsed > value;
              case "less than or equal": return parsed <= value;
              case "greater than or equal": return parsed >= value;
              case "between": return parsed >= value && parsed <= (upper ?? value);
              default: return parsed === value;
            }
          }
          
          // If item has a range, use the mean for comparison
          if (parsed.isRange) {
            const mean = (parsed.min + parsed.max) / 2;
            switch (operation) {
              case "less than": return mean < value;
              case "greater than": return mean > value;
              case "less than or equal": return mean <= value;
              case "greater than or equal": return mean >= value;
              case "between": return mean >= value && mean <= (upper ?? value);
              default: return mean === value;
            }
          }
          
          return false;
        })
      } else {
        // Fallback to string matching for non-numeric filters
        filtered = filtered.filter((item) =>
          item.yearFounded?.toLowerCase().includes(yearFoundedFilter.toLowerCase())
        )
      }
    }

    if (bbbRatingFilter) {
      filtered = filtered.filter((item) =>
        item.bbbRating?.toLowerCase().includes(bbbRatingFilter.toLowerCase())
      )
    }

    if (streetFilter) {
      filtered = filtered.filter((item) =>
        item.street?.toLowerCase().includes(streetFilter.toLowerCase())
      )
    }

    if (cityFilter) {
      filtered = filtered.filter((item) =>
        item.city?.toLowerCase().includes(cityFilter.toLowerCase())
      )
    }

    if (stateFilter) {
      filtered = filtered.filter((item) =>
        item.state?.toLowerCase().includes(stateFilter.toLowerCase())
      )
    }

    setEditableCompanies(filtered)
    setFilteredCompanies(filtered)

  }, [enrichedCompanies, enrichmentViewType, searchTerm, employeesFilter, revenueFilter, businessTypeFilter, productFilter, yearFoundedFilter, bbbRatingFilter, streetFilter, cityFilter, stateFilter])

  // Calculate pagination values
  const totalPages = Math.ceil(filteredCompanies.length / itemsPerPage)
  const indexOfLastItem = currentPage * itemsPerPage
  const indexOfFirstItem = indexOfLastItem - itemsPerPage
  const currentItems = editableCompanies.slice(indexOfFirstItem, indexOfLastItem)

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

  useEffect(() => {
    if (!hasSorted && filteredCompanies.length > 0) {
      handleSortBy("filled", "most");
      setHasSorted(true);
    }
  }, [filteredCompanies, hasSorted]);
  
  const handleSelectAll = () => {
    const newSelectAll = !selectAll
    const newSelectedCompanies = newSelectAll ? filteredCompanies.map((c) => c.id) : []
    
    if (onSelectionChange) {
      onSelectionChange(newSelectedCompanies)
    } else {
      setInternalSelectedCompanies(newSelectedCompanies)
    }
    
    setSelectAll(newSelectAll)
  }

  const handleSelectCompany = (id: string) => {
    let newSelectedCompanies: string[]
    let newSelectAll: boolean
    
    if (selectedCompanies.includes(id)) {
      newSelectedCompanies = selectedCompanies.filter((cid) => cid !== id)
      newSelectAll = false
    } else {
      newSelectedCompanies = [...selectedCompanies, id]
      newSelectAll = newSelectedCompanies.length === filteredCompanies.length
    }
    
    if (onSelectionChange) {
      onSelectionChange(newSelectedCompanies)
    } else {
      setInternalSelectedCompanies(newSelectedCompanies)
    }
    
    setSelectAll(newSelectAll)
  }

  const handleSelectPeople = (id: string) => {
    let newSelectedPeople: string[]
    
    if (selectedPeople.includes(id)) {
      newSelectedPeople = selectedPeople.filter((pid) => pid !== id)
    } else {
      newSelectedPeople = [...selectedPeople, id]
    }
    
    if (onPeopleSelectionChange) {
      onPeopleSelectionChange(newSelectedPeople)
    } else {
      setInternalSelectedPeople(newSelectedPeople)
    }
  }
  const normalizeDisplayValue = (value: any) => {
    if (
      value === null ||
      value === undefined ||
      value.toString().trim() === "" ||
      value.toString().trim().toUpperCase() === "NA" ||
      value.toString().trim().toUpperCase() === "N/A" ||
      value.toString().trim().toUpperCase() === "not" ||
      value.toString().trim().toUpperCase() === "found" ||
      value.toString().trim().toLowerCase() === "not found"
    ) {
      return "N/A"
    }

    return value
  }

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
      employees: "Employee count is unavailable.",
      decider_name: "No decision maker found.",
      decider_title: "Title information not found.",
      decider_email: "Email is currently unavailable.",
      decider_phone: "Phone number not listed.",
      decider_linkedin: "LinkedIn profile not available.",
      name: "Name not available",
      title: "Title not available",
      email: "Email not available",
      phone: "Phone not available",
      linkedin: "LinkedIn not available",
      ownerFirstName: "No decision maker found.",
      ownerLastName: "No decision maker found.",
      ownerTitle: "Title information not found.",
      ownerEmail: "Email is currently unavailable.",
      ownerPhoneNumber: "Phone number not listed.",
      ownerLinkedin: "LinkedIn profile not available.",
      companyPhone: "Phone number not listed.",
      companyLinkedin: "LinkedIn profile not available.",
      yearFounded: "Year founded not available.",
      bbbRating: "BBB rating not available.",
      street: "Street address not available.",
      city: "City not available.",
      state: "State not available.",
      productCategory: "Product category not available.",
      businessType: "Business type not available."
    };
    
    return fallbacks[fieldType as keyof typeof fallbacks] || "Information unavailable.";
  };

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

  const clearFilter = (type: "search" | "employees" | "revenue" | "business") => {
    if (type === "search") setSearchTerm("")
    if (type === "employees") setEmployeesFilter("")
    if (type === "revenue") setRevenueFilter("")
    if (type === "business") setBusinessTypeFilter("")
  }

  const handleExportCSVWithCredits = async () => {
    // Check subscription tier first
    try {
      const { data: subscriptionInfo } = await axios.get(
        `${DATABASE_URL}/user/subscription_info`,
        { withCredentials: true }
      );

      const planName = subscriptionInfo?.subscription?.plan_name?.toLowerCase() || "free";
      const role = JSON.parse(sessionStorage.getItem("user") || "{}").role || "";
      
      // Check if user has Bronze tier or above
      const allowedTiers = ["bronze", "silver", "gold", "platinum", "enterprise"];
      const isDeveloper = role === "developer";
      const hasAllowedTier = allowedTiers.includes(planName);

      if (!isDeveloper && !hasAllowedTier) {
        showNotification(
          "Export functionality requires Bronze tier or above. Please upgrade your plan.",
          "info"
        );
        return;
      }
    } catch (checkErr) {
      console.error("❌ Failed to verify subscription:", checkErr);
      showNotification(
        "Failed to verify your subscription. Please try again later.",
        "error"
      );
      return;
    }

    // Use the same displayData calculation logic as the main component
    let displayData: any[] = [];
    if (enrichmentViewType === "company") {
      displayData = enrichedCompanies.flatMap(company => {
        if (Array.isArray((company as any).people) && (company as any).people.length > 0) {
          return (company as any).people.map((person: any, idx: number) => ({
            ...company,
            id: `${company.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            ownerFirstName: person.owner_first_name || person.name?.split(' ')[0] || person.first_name || "",
            ownerLastName: person.owner_last_name || person.name?.split(' ').slice(1).join(' ') || "",
            ownerTitle: person.owner_title || person.title || "",
            ownerEmail: person.owner_email || person.email || "",
            ownerPhoneNumber: person.owner_phone_number || person.phone || person.phone_number || "",
            ownerLinkedin: person.owner_linkedin || person.linkedin || person.linkedin_url || "",
          }));
        } else {
          return [{ ...company, id: company.id }];
        }
      });
    } else if (enrichmentViewType === "people") {
      displayData = enrichedCompanies.flatMap(company => {
        if (Array.isArray((company as any).people)) {
          return (company as any).people.map((person: any, idx: number) => ({
            ...person,
            // Map the person data to the expected display format
            name: person.name || `${person.owner_first_name || ''} ${person.owner_last_name || ''}`.trim(),
            title: person.title || person.owner_title || '',
            email: person.email || person.owner_email || '',
            phone: person.phone || person.owner_phone_number || '',
            linkedin: person.linkedin || person.owner_linkedin || '',
            company: company.company,
            website: company.website,
            industry: company.industry,
            id: person.id || `${company.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          }));
        } else if ((company as any).ownerFirstName || (company as any).ownerLastName) {
          return [{
            name: `${(company as any).ownerFirstName || ''} ${(company as any).ownerLastName || ''}`.trim(),
            title: (company as any).ownerTitle || '',
            email: (company as any).ownerEmail || '',
            phone: (company as any).ownerPhoneNumber || '',
            linkedin: (company as any).ownerLinkedin || '',
            company: company.company,
            website: company.website,
            industry: company.industry,
            id: `${company.id}-owner`,
          }];
        } else if ((company as any).name || (company as any).email) {
          return [company];
        }
        return [];
      });
    } else {
      displayData = enrichedCompanies;
    }

    // Get selected data based on checkboxes from the displayed data
    // For export, we want both company and people selections
    const allSelectedIds = [...selectedCompanies, ...selectedPeople];
    const selectedData = displayData.filter((item) =>
      allSelectedIds.includes(item.id)
    );

    if (selectedData.length === 0) {
      showNotification("Please select at least one item to export.", "info");
      return;
    }

    downloadCSV(selectedData, "enriched_results.csv");
    showNotification(`Successfully exported ${selectedData.length} selected items.`, "success");
  };


  const handleToggleFiltersWithCheck = async () => {
    // Check subscription tier first
    try {
      const { data: subscriptionInfo } = await axios.get(
        `${DATABASE_URL}/user/subscription_info`,
        { withCredentials: true }
      );

      const planName = subscriptionInfo?.subscription?.plan_name?.toLowerCase() || "free";
      const role = JSON.parse(sessionStorage.getItem("user") || "{}").role || "";
      
      // Check if user has Bronze tier or above
      const allowedTiers = ["bronze", "silver", "gold", "platinum", "enterprise"];
      const isDeveloper = role === "developer";
      const hasAllowedTier = allowedTiers.includes(planName);

      if (!isDeveloper && !hasAllowedTier) {
        showNotification(
          "Advanced filters require Bronze tier or above. Please upgrade your plan.",
          "info"
        );
        return;
      }

      setShowFilters((prev) => !prev);
    } catch (err) {
      console.error("❌ Failed to verify subscription:", err);
      showNotification(
        "Failed to verify your subscription. Please try again later.",
        "error"
      );
    }
  };



  const handleBack = () => {
    router.push("?tab=data-enhancement")
    window.location.reload()
  }

  const handleSortBy = async (sortBy: string, direction: "most" | "least") => {
    // Check subscription tier first
    try {
      const { data: subscriptionInfo } = await axios.get(
        `${DATABASE_URL}/user/subscription_info`,
        { withCredentials: true }
      );

      const planName = subscriptionInfo?.subscription?.plan_name?.toLowerCase() || "free";
      const role = JSON.parse(sessionStorage.getItem("user") || "{}").role || "";
      
      // Check if user has Bronze tier or above
      const allowedTiers = ["bronze", "silver", "gold", "platinum", "enterprise"];
      const isDeveloper = role === "developer";
      const hasAllowedTier = allowedTiers.includes(planName);

      if (!isDeveloper && !hasAllowedTier) {
        showNotification(
          "Sorting functionality requires Bronze tier or above. Please upgrade your plan.",
          "info"
        );
        return;
      }
    } catch (err) {
      console.error("❌ Failed to verify subscription:", err);
      showNotification(
        "Failed to verify your subscription. Please try again later.",
        "error"
      );
      return;
    }

    const getFilledCount = (company: EnrichedCompany) => {
      return Object.entries(company).filter(([key, value]) => {
        if (
          ["id", "lead_id", "draft_id", "sourceType"].includes(key) ||
          value === null ||
          value === undefined ||
          normalizeDisplayValue(value) === "N/A"
        ) {
          return false;
        }
        return true;
      }).length;
    };

    const sorted = [...filteredCompanies].sort((a, b) => {
      const aCount = getFilledCount(a);
      const bCount = getFilledCount(b);
      return direction === "most" ? bCount - aCount : aCount - bCount;
    });

    setFilteredCompanies(sorted);
    setEditableCompanies(sorted);
    setCurrentPage(1); // reset pagination
  };


  const handleSaveEditedCompanies = async () => {
    const user = JSON.parse(sessionStorage.getItem("user") || "{}");
    const user_id = user.id || user.user_id || user._id;

    if (!user_id) {
      showNotification("User not found in session. Please re-login.", "error");
      return;
    }

    const draftMap = JSON.parse(sessionStorage.getItem("leadToDraftMap") || "{}");
    const companiesToSave = editableCompanies.filter((c) =>
      selectedCompanies.includes(c.id)
    );

    if (companiesToSave.length === 0) {
      showNotification("Please select at least one company to save.", "info");
      return;
    }

    console.log(`💾 Attempting to save ${companiesToSave.length} companies`);

    // Upload each company one by one (not in bulk)
    for (const [index, c] of companiesToSave.entries()) {
      try {
        const lead_id = c.lead_id || c.id;
        const draftId = draftMap[lead_id]?.draft_id;

        // Prepare contacts array: use people if available, else fallback to owner fields
        let contacts: any[] = [];
        if (Array.isArray(c.people) && c.people.length > 0) {
          contacts = c.people.map((person: any) => ({
            owner_first_name: person.ownerFirstName || person.first_name || person.name?.split(' ')[0] || "",
            owner_last_name: person.ownerLastName || person.last_name || person.name?.split(' ').slice(1).join(' ') || "",
            owner_title: person.ownerTitle || person.title || "",
            owner_email: person.ownerEmail || person.email || "",
            owner_phone_number: person.ownerPhoneNumber || person.phone || person.phone_number || "",
            owner_linkedin: person.ownerLinkedin || person.linkedin || person.linkedin_url || ""
          }));
        } else {
          contacts = [{
            owner_first_name: c.ownerFirstName || "",
            owner_last_name: c.ownerLastName || "",
            owner_title: c.ownerTitle || "",
            owner_email: c.ownerEmail || "",
            owner_phone_number: c.ownerPhoneNumber || "",
            owner_linkedin: c.ownerLinkedin || ""
          }];
        }

        // Prepare company data with contacts array
        const companyData = {
          user_id,
          lead_id: lead_id,
          company: c.company,
          website: c.website,
          industry: c.industry,
          owner_linkedin: (contacts[0]?.owner_linkedin) || c.ownerLinkedin || "N/A",
          product_category: c.productCategory,
          business_type: c.businessType,
          employees: typeof c.employees === "number" ? c.employees : parseInt(c.employees as any) || 0,
          revenue: typeof c.revenue === "string" ? parseFloat(c.revenue.replace(/[^0-9.]/g, "")) : c.revenue,
          year_founded: parseInt(c.yearFounded) || 0,
          bbb_rating: c.bbbRating,
          street: c.street,
          city: c.city,
          state: c.state,
          company_phone: c.companyPhone,
          company_linkedin: c.companyLinkedin,
          source: c.source,
          contacts: Array.isArray(contacts) && contacts.length > 0 ? contacts : []
        };

        // 1. Upload lead with contacts
        const uploadRes = await fetch(`${DATABASE_URL}/upload_leads`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify([companyData]),
        });
        const uploadText = await uploadRes.text();
        let lead_id_final = lead_id;
        try {
          const uploadJson = JSON.parse(uploadText);
          if (!uploadRes.ok || uploadJson.status === "error") {
            console.error("❌ Failed to upload company:", uploadJson);
            showNotification(`Failed to save company: ${c.company}`, "error");
            continue;
          }
          const detailedResults = uploadJson?.stats?.detailed_results ?? [];
          const leadFromResponse = detailedResults[0] || {};
          if (leadFromResponse.lead_id) {
            lead_id_final = leadFromResponse.lead_id;
          }
        } catch {
          console.error("❌ Invalid JSON from upload_leads");
          showNotification(`Unexpected response from upload for ${c.company}`, "error");
          continue;
        }

        // 2. Create or update draft for this company
        if (lead_id_final) {
          try {
            const draftRes = await fetch(`${DATABASE_URL}/leads/drafts`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "include",
              body: JSON.stringify({
                lead_id: lead_id_final,
                draft_data: { ...companyData, lead_id: lead_id_final },
                change_summary: "User edited company info",
              }),
            });
            const draftText = await draftRes.text();
            try {
              const draftJson = JSON.parse(draftText);
              if (draftJson.draft_id) {
                console.log(`📝 Created/updated draft ${draftJson.draft_id} for company ${companyData.company}`);
              }
            } catch {
              console.error("❌ Invalid JSON from draft creation");
            }
          } catch (draftErr) {
            console.error(`❌ Failed to create/update draft for company ${companyData.company}:`, draftErr);
          }
        }
      } catch (err) {
        console.error("❌ Error saving company:", err);
        showNotification(`Error saving ${c.company}`, "error");
      }
    }

    showNotification("Done saving selected companies.", "success");
  };

  // Helper to check if user is on free tier (updated to match data-enhancement logic)
  // function isFreeTierUser() {
  //   console.log("🔍 [enrichment-results] isFreeTierUser() called");
  //   
  //   // Check if user is a team member first (team members get premium access regardless of individual tier)
  //   try {
  //     const teamData = sessionStorage.getItem("team");
  //   console.log("🔍 [enrichment-results] teamData:", teamData);
  //   if (teamData) {
  //     const parsed = JSON.parse(teamData);
  //     // Check if user has any workspace membership (admin, manager, or member role)
  //     const hasTeamMembership = parsed.workspaces && parsed.workspaces.length > 0 &&
  //     parsed.workspaces.some((workspace: any) =>
  //       workspace.user_role &&
  //       ['admin', 'manager', 'member'].includes(workspace.user_role.toLowerCase())
  //     );
  //   console.log("🔍 [enrichment-results] hasTeamMembership:", hasTeamMembership);
  //   if (hasTeamMembership) {
  //     console.log("🔓 [enrichment-results] User has premium access through team membership - NO starring applied");
  //     return false; // Not free tier - has premium access through team membership
  //   }
  //   }
  //   } catch (e) {
  //     console.error("🔍 [enrichment-results] Error checking team data:", e);
  //   }

  //   // If user is NOT in a team, check their individual tier for starring
  //   try {
  //     const user = sessionStorage.getItem("user");
  //     if (user) {
  //       const parsedUser = JSON.parse(user);
  //       const tier = parsedUser?.tier?.toLowerCase() || "free";
  //       const role = parsedUser?.role?.toLowerCase() || "";
  //     console.log(`🔍 [enrichment-results] checking user tier: ${tier}`);
  //     console.log(`🔍 [enrichment-results] checking user role: ${role}`);
  //     if (role === "developer") return false;
  //     const result = tier === "free";
  //     console.log(`🔍 [enrichment-results] isFreeTierUser result: ${result}`);
  //     return result;
  //   }
  //   } catch (e) {
  //     console.error("🔍 [enrichment-results] Error parsing user data:", e);
  //   }
  //   console.log("🔍 [enrichment-results] Defaulting to free tier (true)");
  //   return true; // default to free if user not found
  //   }

  // const allowed = [
  //   "company",
  //   "industry",
  //   "street",
  //   "city",
  //   "state",
  //   "bbbRating",
  //   "companyPhone",
  //   "website"
  // ];

  // Define columns for each view type
  let companyColumns = [
    { key: "company", label: "Company" },
    { key: "website", label: "Website" },
    { key: "industry", label: "Industry" },
    { key: "employees", label: "Employees Count" },
    { key: "revenue", label: "Revenue" },
    { key: "yearFounded", label: "Year Founded" },
    { key: "productCategory", label: "Product/Service Category" },
    { key: "businessType", label: "Business Type" },
    { key: "bbbRating", label: "BBB Rating" },
    { key: "street", label: "Street" },
    { key: "city", label: "City" },
    { key: "state", label: "State" },
    { key: "companyPhone", label: "Company Phone" },
    { key: "companyLinkedin", label: "Company LinkedIn" },
  ];

  const peopleColumns = [
    { key: "name", label: "Name" },
    { key: "title", label: "Title" },
    { key: "email", label: "Email" },
    { key: "phone", label: "Phone Number" },
    { key: "linkedin", label: "LinkedIn" },
    { key: "company", label: "Company" },
    { key: "website", label: "Website" },
    { key: "industry", label: "Industry" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        {/* <div>
          <h1 className="text-3xl font-bold">Data Enhancement</h1>
          <p className="text-muted-foreground">Enrich company data with additional information</p>
        </div> */}
        {/* <Button variant="outline" onClick={handleBack} className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button> */}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Enrichment Results</CardTitle>
              <CardDescription>
                {enrichmentViewType === "company" && `${filteredCompanies.length} companies enriched successfully`}
                {enrichmentViewType === "people" && `${filteredCompanies.length} people enriched successfully`}
                {enrichmentViewType === "both" && `${filteredCompanies.length} companies enriched successfully`}
              </CardDescription>
            </div>
            <div className="flex items-center gap-4">
              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder={enrichmentViewType === "both" ? "Search companies..." : "Search companies..."}
                  className="w-80 pl-8"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
              
              {/* Actions */}
              <div className="flex items-center gap-2">
                {/* Sort and Filter */}
                <SortDropdown onApply={(sortBy, direction) => handleSortBy(sortBy, direction)} />
                
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleToggleFiltersWithCheck}
                  title={showFilters ? "Hide Filters" : "Show Filters"}
                >
                  <Filter className="h-4 w-4" />
                </Button>
                
                <Button
                  onClick={handleExportCSVWithCredits}
                  disabled={selectedCompanies.length === 0 && selectedPeople.length === 0}
                  variant="outline"
                  size="icon"
                  title={(selectedCompanies.length > 0 || selectedPeople.length > 0) ? `Export ${selectedCompanies.length + selectedPeople.length} selected items` : "Select items to export"}
                  className={`relative ${(selectedCompanies.length === 0 && selectedPeople.length === 0) ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  <Download className="h-4 w-4" />
                  {(selectedCompanies.length > 0 || selectedPeople.length > 0) && (
                    <span className="absolute -top-2 -right-2 text-xs bg-blue-500 text-white rounded-full px-1.5 py-0.5 min-w-[1.2rem] flex items-center justify-center">
                      {selectedCompanies.length + selectedPeople.length}
                    </span>
                  )}
                </Button>

                {/* <ForwardDropdown
                  selectedCompanies={selectedCompanies}
                  onForwardComplete={() => {
                    // Optional: Add any cleanup or refresh logic here
                  }}
                  onNotification={showNotification}
                  scrapingHistory={enrichedCompanies}
                /> */}

                {isEditing ? (
                  <>
                    <Button
                      variant="destructive"
                      size="icon"
                      onClick={() => {
                        setEditableCompanies([...enrichedCompanies]);
                        setIsEditing(false);
                      }}
                      title="Discard Changes"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      onClick={() => {
                        handleSaveEditedCompanies();
                        setIsEditing(false);
                      }}
                      title="Save Changes"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={() => setIsEditing(true)}
                    variant="outline"
                    size="icon"
                    title="Edit"
                  >
                    <Search className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>

          {/* Filter Section */}
          {showFilters && (
            <div className="flex flex-wrap gap-4 my-4">
              <Input
                placeholder="Employees (e.g. >1000, 50-200)"
                value={employeesFilter}
                onChange={(e) => setEmployeesFilter(e.target.value)}
                className="w-[240px]"
              />
              <Input
                placeholder="Revenue (e.g. >1M, 500K-2M)"
                value={revenueFilter}
                onChange={(e) => setRevenueFilter(e.target.value)}
                className="w-[240px]"
              />
              <Input
                placeholder="Business Type (e.g. B2B)"
                value={businessTypeFilter}
                onChange={(e) => setBusinessTypeFilter(e.target.value)}
                className="w-[240px]"
              />
              <Input
                placeholder="Product Category (e.g. SaaS)"
                value={productFilter}
                onChange={(e) => setProductFilter(e.target.value)}
                className="w-[240px]"
              />
              <Input
                placeholder="Year Founded (e.g. 2015, 2020-2023)"
                value={yearFoundedFilter}
                onChange={(e) => setYearFoundedFilter(e.target.value)}
                className="w-[240px]"
              />
              <Input
                placeholder="BBB Rating (e.g. A+)"
                value={bbbRatingFilter}
                onChange={(e) => setBbbRatingFilter(e.target.value)}
                className="w-[240px]"
              />
              <Input
                placeholder="Street"
                value={streetFilter}
                onChange={(e) => setStreetFilter(e.target.value)}
                className="w-[240px]"
              />
              <Input
                placeholder="City"
                value={cityFilter}
                onChange={(e) => setCityFilter(e.target.value)}
                className="w-[240px]"
              />
              <Input
                placeholder="State"
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                className="w-[240px]"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setEmployeesFilter("")
                  setRevenueFilter("")
                  setBusinessTypeFilter("")
                  setProductFilter("")
                  setYearFoundedFilter("")
                  setBbbRatingFilter("")
                  setStreetFilter("")
                  setCityFilter("")
                  setStateFilter("")
                }}
              >
                <X className="h-4 w-4 mr-1" />
                Clear All
              </Button>
            </div>
          )}
        </CardHeader>
        
        <CardContent>
          {/* Table container */}
          <div className="w-full overflow-x-auto relative border rounded-md">
            {enrichmentViewType === "company" && (
              <Table className="w-full overflow-x-auto">
                <TableHeader>
                  <TableRow>
                    {/* Sticky Checkbox Column */}
                    <TableHead className="sticky left-0 z-40 bg-background px-6 py-3 w-12 text-base font-bold text-foreground">
                      <Checkbox checked={selectAll} onCheckedChange={handleSelectAll} />
                    </TableHead>
                    {companyColumns.map((col, index) => (
                      <TableHead 
                        key={col.key} 
                        className={`px-6 py-3 text-base font-bold text-foreground whitespace-nowrap bg-background ${
                          index === 0 ? 'sticky left-12 z-30 border-r' : ''
                        }`}
                      >
                        {col.label}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {editableCompanies.length > 0 ? (
                    editableCompanies.map((company, i) => (
                      <TableRow key={company.id} className={rowClassName?.(company, i) ?? ""}>
                        {/* Sticky Checkbox Column */}
                        <TableCell className="sticky left-0 z-20 bg-inherit px-6 py-2 w-12">
                          <Checkbox
                            checked={selectedCompanies.includes(company.id)}
                            onCheckedChange={() => handleSelectCompany(company.id)}
                          />
                        </TableCell>
                        {companyColumns.map((col, index) => (
                          <TableCell 
                            key={col.key} 
                            className={`px-6 py-2 text-sm align-top whitespace-nowrap ${
                              index === 0 ? 'sticky left-12 z-20 bg-inherit border-r' : ''
                            }`}
                          >
                            {(() => {
                              let cellValue = (company as any)[col.key] ?? "N/A";
                              // const isFree = isFreeTierUser();
                              // const isAllowed = allowed.includes(col.key);
                              // if (isFree && !isAllowed) {
                              //   cellValue = "★";
                              //   console.log(`🔍 [enrichment-results] Starring column ${col.key} - isFree: ${isFree}, isAllowed: ${isAllowed}`);
                              // }
                              
                              // 🆕 NEW: Apply revenue formatting for display (not for payload)
                              let displayValue;
                              if (col.key === "revenue") {
                                displayValue = formatRevenueForDisplay(cellValue);
                              } else {
                                displayValue = getFriendlyFallback(normalizeDisplayValue(String(cellValue)), col.key);
                              }
                              
                              const isUrl = typeof cellValue === "string" && (cellValue.startsWith("http://") || cellValue.startsWith("https://"));
                              if (isUrl) {
                                return (
                                  <a
                                    href={String(cellValue)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-500 hover:text-blue-700 underline cursor-pointer"
                                    title={String(cellValue)}
                                    onClick={e => e.stopPropagation()}
                                  >
                                    Link
                                  </a>
                                );
                              }
                              // if (displayValue === "★") {
                              //   return <span className="text-gray-400 font-bold text-lg block text-center" aria-label="Masked for free users">★</span>;
                              // }
                              if (col.key === "productCategory") {
                                const rowKey = company.id;
                                const isExpanded = expandedRows.has(rowKey);
                                if (isExpanded) {
                                  return (
                                    <>
                                      <div className="whitespace-pre-line break-words overflow-hidden">
                                        {displayValue}
                                      </div>
                                      {displayValue.length > 10 && (
                                        <button
                                          onClick={() => {
                                            const newSet = new Set(expandedRows);
                                            isExpanded ? newSet.delete(rowKey) : newSet.add(rowKey);
                                            setExpandedRows(newSet);
                                          }}
                                          className="text-xs text-blue-500 hover:underline mt-1 block"
                                        >
                                          Show less
                                        </button>
                                      )}
                                    </>
                                  );
                                } else {
                                  const shortValue = displayValue.length > 10 ? displayValue.slice(0, 10) + '...' : displayValue;
                                  return (
                                    <>
                                      <div className="break-words overflow-hidden">
                                        {shortValue}
                                      </div>
                                      {displayValue.length > 10 && (
                                        <button
                                          onClick={() => {
                                            const newSet = new Set(expandedRows);
                                            isExpanded ? newSet.delete(rowKey) : newSet.add(rowKey);
                                            setExpandedRows(newSet);
                                          }}
                                          className="text-xs text-blue-500 hover:underline mt-1 block"
                                        >
                                          Show more
                                        </button>
                                      )}
                                    </>
                                  );
                                }
                              }
                              return displayValue;
                            })()}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={companyColumns.length + 1} className="text-center py-4">
                        No results found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
            {enrichmentViewType === "people" && (
              <Table className="w-full overflow-x-auto">
                <TableHeader>
                  <TableRow>
                    {/* Sticky Checkbox Column */}
                    <TableHead className="sticky left-0 z-40 bg-background px-6 py-3 w-12 text-base font-bold text-foreground">
                      <Checkbox checked={selectAll} onCheckedChange={handleSelectAll} />
                    </TableHead>
                    {peopleColumns.map((col, index) => (
                      <TableHead 
                        key={col.key} 
                        className={`px-6 py-3 text-base font-bold text-foreground whitespace-nowrap bg-background ${
                          index === 0 ? 'sticky left-12 z-30 border-r' : ''
                        }`}
                      >
                        {col.label}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {editableCompanies.length > 0 ? (
                    editableCompanies.map((person, i) => (
                      <TableRow key={person.id} className={rowClassName?.(person, i) ?? ""}>
                        {/* Sticky Checkbox Column */}
                        <TableCell className="sticky left-0 z-20 bg-inherit px-6 py-2 w-12">
                          <Checkbox
                            checked={selectedPeople.includes(person.id)}
                            onCheckedChange={() => handleSelectPeople(person.id)}
                          />
                        </TableCell>
                        {peopleColumns.map((col, index) => (
                          <TableCell 
                            key={col.key} 
                            className={`px-6 py-2 text-sm align-top whitespace-nowrap ${
                              index === 0 ? 'sticky left-12 z-20 bg-inherit border-r' : ''
                            }`}
                          >
                            {(() => {
                              const value = (person as any)[col.key] ?? "N/A";
                              
                              // 🆕 NEW: Apply revenue formatting for display (not for payload)
                              let displayValue;
                              if (col.key === "revenue") {
                                displayValue = formatRevenueForDisplay(value);
                              } else {
                                displayValue = getFriendlyFallback(normalizeDisplayValue(String(value)), col.key);
                              }
                              
                              const isUrl = typeof value === "string" && (value.startsWith("http://") || value.startsWith("https://"));
                              if (isUrl) {
                                return (
                                  <a
                                    href={String(value)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-500 hover:text-blue-700 underline cursor-pointer"
                                    title={String(value)}
                                    onClick={e => e.stopPropagation()}
                                  >
                                    Link
                                  </a>
                                );
                              }
                              return displayValue;
                            })()}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={peopleColumns.length + 1} className="text-center py-4">
                        No results found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            )}
            {enrichmentViewType === "both" && (
              <div className="space-y-6">
                {/* Group by company and show each company as its own card */}
                {(() => {
                  // Group companies by company name - use filteredCompanies for both view
                  const groupedByCompany = filteredCompanies.reduce((acc: Record<string, any>, company: any) => {
                    const companyKey = company.company || 'Unknown Company';
                    if (!acc[companyKey]) {
                      acc[companyKey] = [];
                    }
                    acc[companyKey].push(company);
                    return acc;
                  }, {});

                  // Convert grouped data to array for display
                  const groupedEntries = Object.entries(groupedByCompany);

                  return groupedEntries.map(([companyName, companies]: [string, any]) => (
                    <div key={companyName} className="mb-8">
                      
                      {/* Company Info Card */}
                      <Card className="bg-slate-800 border-slate-700 rounded-lg p-6">
                        <div className="flex items-start justify-between mb-6">
                          <h3 className="text-2xl font-bold text-white">
                            {isEditing ? (
                              <input
                                type="text"
                                className="w-full bg-transparent border-b border-slate-600 focus:outline-none text-2xl font-bold text-white"
                                value={String(companies[0].company)}
                                onChange={(e) =>
                                  handleFieldChange(companies[0].id, "company", e.target.value)
                                }
                              />
                            ) : (
                              normalizeDisplayValue(String(companies[0].company))
                            )}
                          </h3>
                          <Button
                            onClick={async () => {
                              // Check subscription tier first
                              try {
                                const { data: subscriptionInfo } = await axios.get(
                                  `${DATABASE_URL}/user/subscription_info`,
                                  { withCredentials: true }
                                );

                                const planName = subscriptionInfo?.subscription?.plan_name?.toLowerCase() || "free";
                                const role = JSON.parse(sessionStorage.getItem("user") || "{}").role || "";
                                
                                // Check if user has Bronze tier or above
                                const allowedTiers = ["bronze", "silver", "gold", "platinum", "enterprise"];
                                const isDeveloper = role === "developer";
                                const hasAllowedTier = allowedTiers.includes(planName);

                                if (!isDeveloper && !hasAllowedTier) {
                                  showNotification(
                                    "Export functionality requires Bronze tier or above. Please upgrade your plan.",
                                    "info"
                                  );
                                  return;
                                }
                              } catch (checkErr) {
                                console.error("❌ Failed to verify subscription:", checkErr);
                                showNotification(
                                  "Failed to verify your subscription. Please try again later.",
                                  "error"
                                );
                                return;
                              }

                              // Export just this company
                              const companyData = [companies[0]];
                              downloadCSV(companyData, `${companies[0].company?.replace(/[^a-zA-Z0-9]/g, '_')}_export.csv`);
                              showNotification(`Exported ${companies[0].company} data`, "success");
                            }}
                            variant="outline"
                            size="sm"
                            className="bg-slate-700 border-slate-600 text-white hover:bg-slate-600 hover:text-white"
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Export
                          </Button>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                          {/* Company Info */}
                          <div className="space-y-3">
                            <div className="text-sm font-semibold text-teal-400 uppercase tracking-wide">Company Info</div>
                            <div className="space-y-2 text-sm text-white">
                              <div className="flex items-center">
                                <span className="font-medium w-20">Website:</span> 
                                {companies[0].website ? (
                                  <a href={companies[0].website} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline ml-2">
                                    Link
                                  </a>
                                ) : (
                                  <span className="text-gray-400 ml-2">N/A</span>
                                )}
                              </div>
                              <div className="flex items-center">
                                <span className="font-medium w-20">Industry:</span> 
                                <span className="ml-2">{normalizeDisplayValue(String(companies[0].industry || "N/A"))}</span>
                              </div>
                              <div className="flex items-center">
                                <span className="font-medium w-20">Business Type:</span> 
                                <span className="ml-2">{normalizeDisplayValue(String(companies[0].businessType || "N/A"))}</span>
                              </div>
                            </div>
                          </div>
                          
                          {/* Contact */}
                          <div className="space-y-3">
                            <div className="text-sm font-semibold text-teal-400 uppercase tracking-wide">Contact</div>
                            <div className="space-y-2 text-sm text-white">
                              <div className="flex items-center">
                                <span className="font-medium w-20">Phone:</span> 
                                {companies[0].companyPhone ? (
                                  <a href={`tel:${companies[0].companyPhone}`} className="text-blue-400 hover:underline ml-2">
                                    {companies[0].companyPhone}
                                  </a>
                                ) : (
                                  <span className="text-gray-400 ml-2">N/A</span>
                                )}
                              </div>
                              <div className="flex items-center">
                                <span className="font-medium w-20">LinkedIn:</span> 
                                {companies[0].companyLinkedin ? (
                                  <a href={companies[0].companyLinkedin} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline ml-2">
                                    Link
                                  </a>
                                ) : (
                                  <span className="text-gray-400 ml-2">N/A</span>
                                )}
                              </div>
                              <div className="flex items-center">
                                <span className="font-medium w-20">BBB Rating:</span> 
                                <span className="ml-2">{normalizeDisplayValue(String(companies[0].bbbRating || "N/A"))}</span>
                              </div>
                            </div>
                          </div>
                          
                          {/* Metrics */}
                          <div className="space-y-3">
                            <div className="text-sm font-semibold text-teal-400 uppercase tracking-wide">Metrics</div>
                            <div className="space-y-2 text-sm text-white">
                              <div className="flex items-center">
                                <span className="font-medium w-20">Employees:</span> 
                                <span className="ml-2">{companies[0].employees || "N/A"}</span>
                              </div>
                              <div className="flex items-center">
                                <span className="font-medium w-20">Revenue:</span> 
                                <span className="ml-2">{formatRevenueForDisplay(companies[0].revenue)}</span>
                              </div>
                              <div className="flex items-center">
                                <span className="font-medium w-20">Founded:</span> 
                                <span className="ml-2">{companies[0].yearFounded || "N/A"}</span>
                              </div>
                            </div>
                          </div>
                          
                          {/* Location */}
                          <div className="space-y-3">
                            <div className="text-sm font-semibold text-teal-400 uppercase tracking-wide">Location</div>
                            <div className="space-y-2 text-sm text-white">
                              <div className="flex items-center">
                                <span className="font-medium w-20">City:</span> 
                                <span className="ml-2">{normalizeDisplayValue(String(companies[0].city || "N/A"))}</span>
                              </div>
                              <div className="flex items-center">
                                <span className="font-medium w-20">State:</span> 
                                <span className="ml-2">{normalizeDisplayValue(String(companies[0].state || "N/A"))}</span>
                              </div>
                              <div className="flex items-center">
                                <span className="font-medium w-20">Street:</span> 
                                <span className="ml-2">{normalizeDisplayValue(String(companies[0].street || "N/A"))}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </Card>

                      {/* Contact Info Table */}
                      <Card className="rounded-t-none">
                        <CardHeader>
                          <CardTitle className="text-lg">Contact Information</CardTitle>
                          <CardDescription>
                            People associated with the enriched companies
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <Table className="w-full table-fixed">
                            <TableHeader>
                              <TableRow>
                                <TableHead className="sticky left-0 z-40 bg-background px-6 py-3 w-12 text-base font-bold text-foreground">
                                  <Checkbox checked={selectAll} onCheckedChange={handleSelectAll} />
                                </TableHead>
                                <TableHead className="px-6 py-3 text-base font-bold text-foreground whitespace-nowrap bg-background sticky left-12 z-30 border-r">Name</TableHead>
                                <TableHead className="px-6 py-3 text-base font-bold text-foreground whitespace-nowrap bg-background">Title</TableHead>
                                <TableHead className="px-6 py-3 text-base font-bold text-foreground whitespace-nowrap bg-background">Email</TableHead>
                                <TableHead className="px-6 py-3 text-base font-bold text-foreground whitespace-nowrap bg-background">Phone</TableHead>
                                <TableHead className="px-6 py-3 text-base font-bold text-foreground whitespace-nowrap bg-background">LinkedIn</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {(() => {
                                // Flatten all people from this company
                                const allPeople = companies.flatMap((company: any) => {
                                  if (Array.isArray(company.people) && company.people.length > 0) {
                                    return company.people.map((person: any, idx: number) => ({
                                      ...person,
                                      companyName: company.company,
                                      companyId: company.id,
                                      id: person.id || `${company.id}-person-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                                    }));
                                  } else if (company.ownerFirstName || company.ownerLastName) {
                                    // Create person from owner info if no people array
                                    return [{
                                      name: `${company.ownerFirstName || ''} ${company.ownerLastName || ''}`.trim(),
                                      first_name: company.ownerFirstName || '',
                                      last_name: company.ownerLastName || '',
                                      title: company.ownerTitle || '',
                                      email: company.ownerEmail || '',
                                      phone: company.ownerPhoneNumber || '',
                                      phone_number: company.ownerPhoneNumber || '',
                                      linkedin: company.ownerLinkedin || '',
                                      linkedin_url: company.ownerLinkedin || '',
                                      source: "Database (Owner)",
                                      companyName: company.company,
                                      companyId: company.id,
                                      id: `${company.id}-owner`,
                                    }];
                                  }
                                  return [];
                                });

                                if (allPeople.length === 0) {
                                  return (
                                    <TableRow>
                                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                                        No contact information found for this company.
                                      </TableCell>
                                    </TableRow>
                                  );
                                }

                                return allPeople.map((person: any, idx: number) => (
                                  <TableRow key={person.id} className="hover:bg-muted/50">
                                    <TableCell className="sticky left-0 z-20 bg-inherit px-6 py-2 w-12">
                                      <Checkbox
                                        checked={selectedPeople.includes(person.id)}
                                        onCheckedChange={() => handleSelectPeople(person.id)}
                                      />
                                    </TableCell>
                                    <TableCell className="sticky left-12 z-10 bg-inherit font-medium px-6 py-2 border-r w-32" title={person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim() || 'N/A'}>
                                      <div className="truncate">
                                        {person.name || `${person.first_name || ''} ${person.last_name || ''}`.trim() || 'N/A'}
                                      </div>
                                    </TableCell>
                                    <TableCell className="px-6 py-2 w-24" title={person.title || 'N/A'}>
                                      <div className="truncate text-sm">
                                        {person.title || 'N/A'}
                                      </div>
                                    </TableCell>
                                    <TableCell className="px-6 py-2 w-40">
                                      {person.email ? (
                                        <a href={`mailto:${person.email}`} className="text-blue-600 hover:underline text-sm truncate block" title={person.email}>
                                          {person.email}
                                        </a>
                                      ) : 'N/A'}
                                    </TableCell>
                                    <TableCell className="px-6 py-2 w-28" title={person.phone || person.phone_number || person.owner_phone_number || 'N/A'}>
                                      <div className="truncate text-sm">
                                        {person.phone || person.phone_number || person.owner_phone_number || 'N/A'}
                                      </div>
                                    </TableCell>
                                    <TableCell className="px-6 py-2 w-40">
                                      {person.linkedin || person.linkedin_url || person.owner_linkedin ? (
                                        <a 
                                          href={person.linkedin || person.linkedin_url || person.owner_linkedin} 
                                          target="_blank" 
                                          rel="noopener noreferrer"
                                          className="text-blue-600 hover:underline text-sm truncate block"
                                          title={person.linkedin || person.linkedin_url || person.owner_linkedin}
                                        >
                                          {person.linkedin || person.linkedin_url || person.owner_linkedin}
                                        </a>
                                      ) : 'N/A'}
                                    </TableCell>
                                  </TableRow>
                                ));
                              })()}
                            </TableBody>
                          </Table>
                        </CardContent>
                      </Card>
                    </div>
                  ));
                })()}
              </div>
            )}
          </div>

          {/* Pagination at the bottom */}
          {filteredCompanies.length > 0 && (
            <div className="flex flex-col md:flex-row justify-between items-center mt-4 gap-4 px-4 py-2">
              <div className="text-sm text-muted-foreground">
                {enrichmentViewType === "both" ? (
                  // For both view, show company count instead of item count
                  (() => {
                    const groupedByCompany = filteredCompanies.reduce((acc: Record<string, any>, company: any) => {
                      const companyKey = company.company || 'Unknown Company';
                      if (!acc[companyKey]) {
                        acc[companyKey] = [];
                      }
                      acc[companyKey].push(company);
                      return acc;
                    }, {});
                    const companyCount = Object.keys(groupedByCompany).length;
                    return `Showing ${companyCount} compan${companyCount !== 1 ? 'ies' : 'y'} enriched successfully`;
                  })()
                ) : (
                  `Showing ${indexOfFirstItem + 1}-${Math.min(indexOfLastItem, filteredCompanies.length)} of ${filteredCompanies.length} results`
                )}
                {selectedCompanies.length > 0 && (
                  <span className="ml-2 text-blue-600">
                    ({selectedCompanies.length} selected)
                  </span>
                )}
              </div>

              {enrichmentViewType !== "both" && (
                <div className="flex items-center gap-3 px-3 py-2">
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
              )}
            </div>
          )}
        </CardContent>
      </Card>
      
      <Notif
        show={notif.show}
        message={notif.message}
        type={notif.type}
        onClose={() => setNotif(prev => ({ ...prev, show: false }))}
      />
    </div>
  )
}
