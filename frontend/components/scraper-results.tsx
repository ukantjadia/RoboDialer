"use client"

import { useState, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Download, Search, ArrowRight, ExternalLink, Save, Trash2 } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import * as XLSX from "xlsx"
import { Lead, useLeads } from "@/components/LeadsProvider"
import { toast } from "sonner";
import { Checkbox } from "@/components/ui/checkbox";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { parseRevenueStringToMillions } from "@/lib/leadUtils"
import { X, Filter, Loader2 } from "lucide-react";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import axios from "axios"

export function ScraperResults({ data, industry, location, country, isScrapingActive }: { data: string | any[], industry: string, location: string, country: 'USA' | 'CAN' | 'UK' | 'FRA', isScrapingActive: boolean }) {
  const router = useRouter()
  const [searchTerm, setSearchTerm] = useState("")
  const [leads, setLeads] = useState<any[]>([])
  const [exportFormat, setExportFormat] = useState("csv")
  const { setLeads: setGlobalLeads } = useLeads()
  const textareaRefs = useRef<(HTMLTextAreaElement | null)[]>([])

  // Updation state
  const [updatedLeads, setUpdatedLeads] = useState<{ id: number }[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const DATABASE_URL = `${process.env.NEXT_PUBLIC_DATABASE_URL}`

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(25)

  // Revenue Mapping state
  const [revenueMap, setRevenueMap] = useState<{ [leadId: string]: string }>({});
  const [isEstimating, setIsEstimating] = useState(false);
  const [userTier, setUserTier] = useState<string | null>(null);

  // Revenue filtering state
  const [showRevenueFilter, setShowRevenueFilter] = useState(false);
  const [confidenceFilter, setConfidenceFilter] = useState<string | null>(null);
  const [minRevenueInput, setMinRevenueInput] = useState("");
  const [maxRevenueInput, setMaxRevenueInput] = useState("");
  const [minRevenue, setMinRevenue] = useState<number | null>(null);
  const [maxRevenue, setMaxRevenue] = useState<number | null>(null);

  const [selectedCompanies, setSelectedCompanies] = useState<number[]>([])
  const [selectAll, setSelectAll] = useState(false)
  const [isIndeterminate, setIsIndeterminate] = useState(false)
  const [showCheckboxes, setShowCheckboxes] = useState(false)

  // Sorting state logic
  const [sortConfig, setSortConfig] = useState<{
    key: string;
    direction: 'ascending' | 'descending';
  } | null>(null);

  const requestSort = (key: string) => {
    let direction: 'ascending' | 'descending' = 'ascending';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  // Hover effect for header
  const getHeaderClass = (key: string) => {
    const base =
      "sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap cursor-pointer select-none";
    const active = sortConfig?.key === key ? "bg-muted text-foreground font-semibold" : "";
    const hover = "hover:bg-muted hover:text-foreground";
    const companyExtra = key === "company" ? "left-0 z-40 min-w-[200px]" : "";

    return `${base} ${active} ${hover} ${companyExtra}`;
  };

  // Add effect to handle indeterminate state
  useEffect(() => {
    setIsIndeterminate(
      selectedCompanies.length > 0 &&
      selectedCompanies.length < leads.length
    );
  }, [selectedCompanies, leads.length]);

  useEffect(() => {
    let parsedData;
    try {
      // Replace NaN with null in the JSON string if data is a string
      const sanitizedData = typeof data === "string" ? data.replace(/NaN/g, "null") : data;
      // Parse the sanitized data
      parsedData = typeof sanitizedData === "string" ? JSON.parse(sanitizedData) : sanitizedData;
      // Validate that parsedData is an array
      if (!Array.isArray(parsedData)) {
        console.error("Invalid data format: expected an array", parsedData);
        setLeads([]);
        return;
      }
    } catch (error) {
      console.error("Failed to parse data:", error);
      setLeads([]);
      return;
    }
    const defaultNA = (val: any) =>
      val === undefined || val === null || val === "" || val === "NA" || val === "n/a" ? "N/A" : val;

    // Normalize the data
    const normalizedWithoutIds = parsedData.map((item, idx) => ({
      id: typeof item.id !== "undefined" && item.id !== null ? item.id : idx + 1,  // Use 1-based index as ID
      lead_id: item.lead_id || "",
      company: defaultNA(item.Company || item.company),
      website: defaultNA(item.Website || item.website),
      industry: defaultNA(item.Industry || item.industry),
      street: defaultNA(item.Street || item.street),
      city: defaultNA(item.City || item.city),
      state: defaultNA(item.State || item.state),
      bbb_rating: defaultNA(item.BBB_rating || item.bbb_rating),
      business_phone: defaultNA(item.Business_phone || item.business_phone || item.company_phone)
    }));

    setLeads(normalizedWithoutIds)
    setGlobalLeads(normalizedWithoutIds);
    // Reset to first page when data changes
    setCurrentPage(1);
  }, [data]);

  // Auto-resize textareas
  useEffect(() => {
    const resizeTextareas = () => {
      textareaRefs.current.forEach(textarea => {
        if (textarea) {
          textarea.style.height = 'auto';
          textarea.style.height = textarea.scrollHeight + 'px';
        }
      });
    };

    resizeTextareas();

    // Reset references when leads change
    textareaRefs.current = textareaRefs.current.slice(0, leads.length * 3);
  }, [leads.length]);

  // Auto-resize all textareas when leads data changes
  useEffect(() => {
    if (leads.length > 0) {
      setTimeout(() => {
        textareaRefs.current.forEach(textarea => {
          if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
          }
        });
      }, 0);
    }
  }, [leads]);

  // Reset to first page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  useEffect(() => {
    try {
      const storedUser = sessionStorage.getItem("user");
      if (storedUser) {
        const parsed = JSON.parse(storedUser);
        setUserTier(parsed?.tier || null);
      }
    } catch (err) {
      console.error("Failed to parse user from session storage:", err);
    }
  }, []);

  const handleCellChange = (rowIdx: number, field: string, value: string) => {
    setLeads(prev =>
      prev.map((row, idx) =>
        idx === rowIdx ? { ...row, [field]: value } : row
      )
    );

    const leadId = leads[rowIdx].id;

    setUpdatedLeads((prev: { id: number }[]) => {
      const existing = prev.find((item: { id: number }) => item.id === leadId);

      if (existing) {
        return prev.map((item: { id: number }) =>
          item.id === leadId
            ? { ...item, [field]: value }
            : item
        );
      } else {
        return [...prev, { id: leadId, [field]: value }];
      }
    });

    // Resize the textarea after content change
    setTimeout(() => {
      const index = field === "company" ? rowIdx * 3 :
        field === "industry" ? rowIdx * 3 + 1 :
          field === "street" ? rowIdx * 3 + 2 : -1;

      if (index >= 0 && textareaRefs.current[index]) {
        const textarea = textareaRefs.current[index];
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
      }
    }, 0);
  };

  const handleNext = () => {
    if (Object.keys(revenueMap).length > 0) {
      sessionStorage.setItem("revenueMap", JSON.stringify(revenueMap));
    } else {
      sessionStorage.removeItem("revenueMap");
    }
    router.push(`/enhancement?industry=${encodeURIComponent(industry)}&location=${encodeURIComponent(location)}&country=${country}`)
  }

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedCompanies([])
    } else {
      setSelectedCompanies(currentItems.map((company) => company.id))
    }
    setSelectAll(!selectAll)
  }

  const handleSelectCompany = (index: number) => {
    if (selectedCompanies.includes(index)) {
      setSelectedCompanies(selectedCompanies.filter((idx) => idx !== index))
      setSelectAll(false)
    } else {
      const updated = [...selectedCompanies, index]
      setSelectedCompanies(updated)
      if (updated.length === leads.length) {
        setSelectAll(true)
      }
    }
  }


  const filteredResults = leads.filter((lead) => {
    const matchesSearch =
      lead.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.industry.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.city.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lead.state.toLowerCase().includes(searchTerm.toLowerCase());

    const revenueKey = lead.lead_id || lead.id.toString();
    const revenueString = revenueMap[revenueKey];

    if (revenueString && (confidenceFilter || minRevenue !== null || maxRevenue !== null)) {
      // Extract the numeric part from the revenue string
      const revenueMatch = revenueString.match(/([\d.,]+\s*[KMB])/i);
      const revenueValueStr = revenueMatch ? revenueMatch[1] : "";
      const [_, confidence] = revenueString.split(" - ");
      const revenueVal = parseRevenueStringToMillions(revenueValueStr);

      const confidenceMatches =
        !confidenceFilter || confidence.toLowerCase() === confidenceFilter.toLowerCase();

      const revenueMatches =
        (minRevenue === null || (revenueVal !== null && revenueVal >= minRevenue)) &&
        (maxRevenue === null || (revenueVal !== null && revenueVal <= maxRevenue));

      return matchesSearch && confidenceMatches && revenueMatches;
    }

    return matchesSearch;
  });

  const sortedResults = (() => {
    if (!sortConfig) return filteredResults;

    const { key, direction } = sortConfig;

    return [...filteredResults].sort((a, b) => {
      const getValue = (item: any) => {
        if (key === "revenue") {
          const revenueKey = item.lead_id || item.id.toString();
          const raw = revenueMap[revenueKey];
          if (!raw) return null;

          const rangePart = raw.split(" - ")[0];
          return parseRevenueStringToMillions(rangePart);
        }
        return item[key] || "";
      };

      const valA = getValue(a);
      const valB = getValue(b);

      // Push "N/A", null, "" to bottom
      if (valA == null && valB != null) return 1;
      if (valB == null && valA != null) return -1;
      if (valA == null && valB == null) return 0;

      if (valA < valB) return direction === "ascending" ? -1 : 1;
      if (valA > valB) return direction === "ascending" ? 1 : -1;
      return 0;
    });
  })();

  // Calculate pagination values
  const totalPages = Math.ceil(sortedResults.length / itemsPerPage);
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = sortedResults.slice(indexOfFirstItem, indexOfLastItem);

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

  const exportCSV = () => {
    const csvRows = [
      Object.keys(leads[0]).join(","),
      ...leads.map(row =>
        Object.values(row).map(val => `"${String(val).replace(/"/g, '""')}"`).join(",")
      )
    ]
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "leads.csv"
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(leads, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "leads.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportExcel = () => {
    const worksheet = XLSX.utils.json_to_sheet(leads)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, "Leads")
    const excelBuffer = XLSX.write(workbook, { bookType: "xlsx", type: "array" })
    const blob = new Blob([excelBuffer], { type: "application/octet-stream" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "leads.xlsx"
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExport = () => {
    if (exportFormat === "csv") exportCSV()
    else if (exportFormat === "excel") exportExcel()
    else if (exportFormat === "json") exportJSON()
  }

  // Function to clean URLs for display (remove http://, https://, www. and anything after the TLD)
  const cleanUrlForDisplay = (url: string): string => {
    if (!url || typeof url !== 'string' || url === "N/A" || url === "NA") return url;

    // First remove http://, https://, and www.
    let cleanUrl = url.replace(/^(https?:\/\/)?(www\.)?/i, "");

    // Then truncate everything after the domain (matches common TLDs)
    const domainMatch = cleanUrl.match(/^([^\/\?#]+\.(com|org|net|io|ai|co|gov|edu|app|dev|me|info|biz|us|uk|ca|au|de|fr|jp|ru|br|in|cn|nl|se)).*$/i);
    if (domainMatch) {
      return domainMatch[1];
    }

    // If no common TLD found, just truncate at the first slash, question mark or hash
    return cleanUrl.split(/[\/\?#]/)[0];
  }

  const normalizeDisplayValue = (value: any) => {
    if (value === null || value === undefined) return "";
    if (value === "NA") return "N/A";
    return value;
  }

  const [isDeleting, setIsDeleting] = useState(false)
  const DELETE_LEADS_API = `${process.env.NEXT_PUBLIC_DATABASE_URL}/leads/delete-multiple`

  const handleDelete = async () => {
    if (selectedCompanies.length === 0) {
      toast.error("Please select at least one lead to delete");
      return;
    }
    setIsDeleting(true);
    setLeads(prev => prev.filter((_, idx) => !selectedCompanies.includes(idx)));
    setGlobalLeads(prev => prev.filter((_, idx) => !selectedCompanies.includes(idx)));
    setSelectedCompanies([]);
    setSelectAll(false);
    setShowCheckboxes(false); // Hide checkboxes after deletion
    toast.success("Lead removed successfully.");
    setIsDeleting(false);
  };

  const handleToggleDeleteMode = () => {
    setShowCheckboxes(!showCheckboxes);
    if (showCheckboxes) {
      // If hiding checkboxes, clear selection
      setSelectedCompanies([]);
      setSelectAll(false);
    }
  };

  const handleEstimateRevenue = async () => {
    setIsEstimating(true);

    const BATCH_SIZE = 25;

    try {
      // Use all leads shown in the table after filter + sort
      const payload = sortedResults.filter(item => {
        const key = item.lead_id || item.id.toString();
        return !revenueMap[key]; // Only include if not yet estimated
      }).map(item => ({
        Company: item.company,
        Industry: item.industry,
        Address: [item.street, item.city, item.state],
        "BBB Rating": item.bbb_rating,
        Website: item.website,
        id: item.id,
        lead_id: item.lead_id || "",
      }));

      // Split into batches of 25
      const batches: typeof payload[] = [];
      for (let i = 0; i < payload.length; i += BATCH_SIZE) {
        batches.push(payload.slice(i, i + BATCH_SIZE));
      }

      // Make API calls in parallel
      const responses = await Promise.all(
        batches.map(batch =>
          axios
            .post(`${DATABASE_URL}/leads/estimate-revenue-batch`, batch, {
              withCredentials: true,
            })
            .then(res => ({ batch, results: res.data }))
        )
      );

      // Merge into revenue map
      const updatedMap = { ...revenueMap };

      responses.forEach(({ batch, results }) => {
        results.forEach((entry: { Company: string; revenue: string }) => {
          const match = batch.find(l => l.Company === entry.Company);
          if (match) {
            const key = match.lead_id || match.id.toString();
            updatedMap[key] = entry.revenue;
          }
        });
      });

      setRevenueMap(updatedMap);
      toast.success(`Estimated revenue for ${payload.length} companies.`);
    } catch (err) {
      // console.error("Error estimating revenue for all leads:", err);
      toast.error("Failed to estimate revenue. Please try again.");
    } finally {
      setIsEstimating(false);
    }
  };

  const numToEstimate = sortedResults.filter(item => {
    const key = item.lead_id || item.id.toString();
    return !revenueMap[key];
  }).length;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Company Search Results</CardTitle>
          <div className="flex items-center gap-4">
            {/* Search Bar */}
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="search"
                placeholder="Search results..."
                className="w-80 pl-8"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={handleToggleDeleteMode}
                className={showCheckboxes ? "bg-red-50 text-red-600 border-red-200 hover:bg-red-100" : ""}
                title={showCheckboxes ? "Cancel Delete Mode" : "Delete Items"}
              >
                <Trash2 className={`h-4 w-4 ${showCheckboxes ? "text-red-600" : ""}`} />
              </Button>
              {showCheckboxes && selectedCompanies.length > 0 && (
                <Button
                  variant="outline"
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="text-red-500 hover:text-red-700 hover:bg-red-50"
                >
                  {isDeleting ? "Deleting..." : `Delete (${selectedCompanies.length})`}
                </Button>
              )}
              {Object.keys(revenueMap).length > 0 && (
                <Button
                  variant="outline"
                  onClick={() => setShowRevenueFilter(prev => !prev)}
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Filter Revenue
                </Button>
              )}
              {currentItems.length > 0 && userTier !== "free" && (
                <div className="relative">
                  <Button
                    className="bg-indigo-500 hover:bg-indigo-600 text-white"
                    onClick={handleEstimateRevenue}
                    disabled={isEstimating || isScrapingActive}
                  >
                    {isEstimating ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Estimating...
                      </div>
                    ) : (
                      <>Estimate Revenue</>
                    )}
                  </Button>
                  {/* "New" badge/icon */}
                  <span className="absolute -top-2 -right-2 bg-pink-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-md select-none">
                    NEW
                  </span>
                </div>
              )}
              <Button
                className="bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600"
                onClick={handleNext}
              >
                <ArrowRight className="mr-2 h-4 w-4" />
                Next
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {showRevenueFilter && (
          <div className="flex justify-end mb-4 px-2">
            <div className="flex flex-wrap gap-4 items-center">
              {/* Confidence Filter */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Confidence:</label>
                <Select
                  value={confidenceFilter ?? "any"}
                  onValueChange={(val) => setConfidenceFilter(val === "any" ? null : val)}
                >
                  <SelectTrigger className="w-[120px]">
                    <SelectValue placeholder="Any" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Revenue Range Inputs */}
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Revenue:</label>
                <Input
                  type="text"
                  placeholder="Min (e.g. 1M)"
                  className="w-[110px]"
                  value={minRevenueInput}
                  onChange={(e) => {
                    const val = e.target.value;
                    setMinRevenueInput(val);
                    const parsed = parseRevenueStringToMillions(val);
                    setMinRevenue(isNaN(parsed ?? NaN) ? null : parsed);
                  }}
                />
                <span className="text-muted-foreground">to</span>
                <Input
                  type="text"
                  placeholder="Max (e.g. 50M)"
                  className="w-[130px]"
                  value={maxRevenueInput}
                  onChange={(e) => {
                    const val = e.target.value;
                    setMaxRevenueInput(val);
                    const parsed = parseRevenueStringToMillions(val);
                    setMaxRevenue(isNaN(parsed ?? NaN) ? null : parsed);
                  }}
                />
              </div>

              {/* Clear Button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setConfidenceFilter(null);
                  setMinRevenue(null);
                  setMaxRevenue(null);
                  setMinRevenueInput("");
                  setMaxRevenueInput("");
                }}
              >
                <X className="w-3 h-3" />
                Clear
              </Button>
            </div>
          </div>
        )}
        {isEstimating && (
          <div className="flex justify-end mb-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
              Estimating revenue for {numToEstimate} {numToEstimate === 1 ? "lead" : "leads"}...
            </div>
          </div>
        )}
        {/* Table container */}
        <div className="w-full overflow-x-auto relative border rounded-md">
          <Table className="w-full" fixedLayout={false}>
            <TableHeader>
              <TableRow>
                {showCheckboxes && (
                  <TableHead className="w-[50px] sticky top-0 left-0 z-40 bg-background border-r">
                    <Checkbox
                      checked={selectAll}
                      onCheckedChange={handleSelectAll}
                      aria-label="Select all"
                    />
                  </TableHead>
                )}
                <TableHead onClick={() => requestSort("company")} className={getHeaderClass("company")}>
                  <div className="flex items-center gap-1">
                    Company
                    {sortConfig?.key === "company" ? (
                      sortConfig.direction === "ascending" ? "↑" : "↓"
                    ) : (
                      <span className="text-muted-foreground text-xs">⇅</span>
                    )}
                  </div>
                </TableHead>
                <TableHead onClick={() => requestSort("industry")} className={getHeaderClass("industry")}>
                  <div className="flex items-center gap-1 max-w-[150px] whitespace-nowrap">
                    Industry
                    {sortConfig?.key === "industry" ? (
                      sortConfig.direction === "ascending" ? "↑" : "↓"
                    ) : (
                      <span className="text-muted-foreground text-xs">⇅</span>
                    )}
                  </div>
                </TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">
                  Address
                </TableHead>
                <TableHead onClick={() => requestSort("bbb_rating")} className={getHeaderClass("bbb_rating")}>
                  <div className="flex items-center gap-1 w-[80px]">
                    BBB Rating
                    {sortConfig?.key === "bbb_rating" ? (
                      sortConfig.direction === "ascending" ? "↑" : "↓"
                    ) : (
                      <span className="text-muted-foreground text-xs">⇅</span>
                    )}
                  </div>
                </TableHead>
                <TableHead onClick={() => requestSort("business_phone")} className={getHeaderClass("business_phone")}>
                  <div className="flex items-center gap-1">
                    Company Phone
                    {sortConfig?.key === "business_phone" ? (
                      sortConfig.direction === "ascending" ? "↑" : "↓"
                    ) : (
                      <span className="text-muted-foreground text-xs">⇅</span>
                    )}
                  </div>
                </TableHead>
                <TableHead onClick={() => requestSort("website")} className={getHeaderClass("website")}>
                  <div className="flex items-center gap-1">
                    Website
                    {sortConfig?.key === "website" ? (
                      sortConfig.direction === "ascending" ? "↑" : "↓"
                    ) : (
                      <span className="text-muted-foreground text-xs">⇅</span>
                    )}
                  </div>
                </TableHead>
                {Object.keys(revenueMap).length > 0 && (
                  <TableHead onClick={() => requestSort("revenue")} className={getHeaderClass("revenue")}>
                    <div className="flex items-center gap-1">
                      Estimated Revenue
                      {sortConfig?.key === "revenue" ? (
                        sortConfig.direction === "ascending" ? "↑" : "↓"
                      ) : (
                        <span className="text-muted-foreground text-xs">⇅</span>
                      )}
                    </div>
                  </TableHead>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {currentItems.length > 0 ? (
                currentItems.map((result, rowIdx) => {
                  // Calculate the actual index in the filtered results
                  const actualIndex = indexOfFirstItem + rowIdx;
                  return (
                    <TableRow key={result.lead_id || result.id}>
                      {showCheckboxes && (
                        <TableCell className="w-[50px] sticky left-0 z-20 bg-inherit border-r">
                          <Checkbox
                            checked={selectedCompanies.includes(actualIndex)}
                            onCheckedChange={() => handleSelectCompany(actualIndex)}
                            aria-label={`Select ${result.company}`}
                          />
                        </TableCell>
                      )}
                      <TableCell className={`sticky ${showCheckboxes ? 'left-[50px]' : 'left-0'} z-10 bg-inherit border-r px-6 py-2 max-w-[240px] align-top`}>
                        <textarea
                          className="font-medium border-b w-full bg-transparent break-words resize-none min-h-[24px] overflow-hidden"
                          value={normalizeDisplayValue(result.company ?? "")}
                          onChange={e => {
                            handleCellChange(actualIndex, "company", e.target.value);
                            const el = e.currentTarget;
                            el.style.height = "auto";
                            el.style.height = `${el.scrollHeight}px`;
                          }}
                          rows={1}
                          onBlur={e => {
                            if (e.target.value.trim() === "") {
                              handleCellChange(actualIndex, "company", "N/A")
                            }
                          }}
                          ref={(el) => {
                            textareaRefs.current[actualIndex * 3] = el;
                            if (el) {
                              el.style.height = "auto";
                              el.style.height = `${el.scrollHeight}px`;
                            }
                          }}
                        />
                      </TableCell>
                      <TableCell className="px-6 py-2 align-top max-w-[150px]">
                        <textarea
                          className="border-b w-full bg-transparent break-words resize-none min-h-[24px] overflow-hidden whitespace-pre-wrap"
                          value={normalizeDisplayValue(result.industry ?? "")}
                          onChange={e => {
                            handleCellChange(actualIndex, "industry", e.target.value);
                            const el = e.currentTarget;
                            el.style.height = "auto";
                            el.style.height = `${el.scrollHeight}px`;
                          }}
                          rows={1}
                          onBlur={e => {
                            if (e.target.value.trim() === "") {
                              handleCellChange(actualIndex, "industry", "N/A")
                            }
                          }}
                          ref={(el) => {
                            textareaRefs.current[actualIndex * 3 + 1] = el;
                            if (el) {
                              el.style.height = "auto";
                              el.style.height = `${el.scrollHeight}px`;
                            }
                          }}
                        />
                        {/*
                        <div className="font-medium">{result.naics_industry_name || result.industry}</div>
                        <div className="text-sm text-muted-foreground">{result.naics_parent_name}</div>
                        */}
                      </TableCell>
                      <TableCell className="px-6 py-2 max-w-[200px] align-top">
                        <textarea
                          className="border-b w-full bg-transparent break-words resize-none min-h-[24px] overflow-hidden"
                          value={normalizeDisplayValue(result.street)}
                          onChange={e => handleCellChange(actualIndex, "street", e.target.value)}
                          placeholder="Street"
                          rows={1}
                          onBlur={e => {
                            if (e.target.value.trim() === "") {
                              handleCellChange(actualIndex, "street", "N/A")
                            }
                          }}
                          ref={(el) => {
                            textareaRefs.current[actualIndex * 3 + 2] = el;
                          }}
                        />
                        <div className="flex gap-1 mt-1">
                          <input
                            className="border-b w-1/2 bg-transparent text-sm text-muted-foreground break-words"
                            value={normalizeDisplayValue(result.city)}
                            onChange={e => handleCellChange(actualIndex, "city", e.target.value)}
                            onBlur={e => {
                              if (e.target.value.trim() === "") {
                                handleCellChange(actualIndex, "city", "N/A")
                              }
                            }}
                            placeholder="City"
                          />
                          <input
                            className="border-b w-1/2 bg-transparent text-sm text-muted-foreground break-words"
                            value={normalizeDisplayValue(result.state)}
                            onChange={e => handleCellChange(actualIndex, "state", e.target.value)}
                            onBlur={e => {
                              if (e.target.value.trim() === "") {
                                handleCellChange(actualIndex, "state", "N/A")
                              }
                            }}
                            placeholder="State"
                          />
                        </div>
                      </TableCell>
                      <TableCell className="px-6 py-2 max-w-[100px] align-top">
                        <input
                          className="border-b w-full bg-transparent break-words"
                          value={normalizeDisplayValue(result.bbb_rating)}
                          onChange={e => handleCellChange(actualIndex, "bbb_rating", e.target.value)}
                          onBlur={e => {
                            if (e.target.value.trim() === "") {
                              handleCellChange(actualIndex, "bbb_rating", "N/A")
                            }
                          }}
                        />
                      </TableCell>
                      <TableCell className="px-6 py-2 max-w-[240px] align-top">
                        {normalizeDisplayValue(result.business_phone)
                          .split(",")
                          .map((phone: string, i: number) => (
                            <div key={`${result.id}-phone-${i}`} className="break-words">
                              {normalizeDisplayValue(phone.trim())}
                            </div>
                          ))}
                      </TableCell>
                      <TableCell className="px-6 py-2 max-w-[240px] align-top">
                        <div className="flex items-center gap-2">
                          <input
                            className="border-b w-full bg-transparent"
                            value={result.website ? cleanUrlForDisplay(normalizeDisplayValue(result.website)) : ""}
                            onChange={e => handleCellChange(actualIndex, "website", e.target.value)}
                            onBlur={e => {
                              if (e.target.value.trim() === "") {
                                handleCellChange(actualIndex, "website", "N/A")
                              }
                            }}
                            placeholder="Website (domain only)"
                          />
                          {result.website && normalizeDisplayValue(result.website) !== "N/A" && normalizeDisplayValue(result.website) !== "NA" && (
                            <a
                              href={result.website.toString().startsWith('http') ? result.website : `https://${result.website}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-500 hover:text-blue-700"
                              title="Open website in new tab"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          )}
                        </div>
                      </TableCell>
                      {Object.keys(revenueMap).length > 0 && (() => {
                        const key = result.lead_id || result.id.toString();
                        const raw = revenueMap[key];
                        if (!raw) return null;

                        const [rangeRaw, confidence] = raw.split(" - ");
                        const range = rangeRaw.split(": ")[1].replace(/m/i, "M");
                        const confidenceLabel = confidence?.charAt(0).toUpperCase() + confidence?.slice(1).toLowerCase();

                        return (
                          <TableCell className="px-6 py-2 max-w-[230px] align-top text-sm text-muted-foreground">
                            <span className="font-medium text-foreground flex items-center gap-2">
                              {range}
                              <TooltipProvider delayDuration={100}>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className="flex items-center gap-1 cursor-help">
                                      <span
                                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${confidence === "high"
                                          ? "bg-green-100 text-green-700"
                                          : confidence === "medium"
                                            ? "bg-blue-100 text-blue-700"
                                            : "bg-yellow-100 text-yellow-700"
                                          }`}
                                      >
                                        {confidenceLabel} confidence
                                      </span>
                                      <sup className="text-muted-foreground">*</sup>
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>This is an estimated value and may not reflect actual revenue.</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </span>
                          </TableCell>
                        );
                      })()}
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={7} className="h-24 text-center">
                    No results found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination at the bottom */}
        {filteredResults.length > 0 && (
          <div className="flex flex-col md:flex-row justify-between items-center mt-4 gap-4 px-4 py-2">
            <div className="text-sm text-muted-foreground">
              Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, filteredResults.length)} of {filteredResults.length} results
              {selectedCompanies.length > 0 && (
                <span className="ml-2 text-blue-600">
                  ({selectedCompanies.length} selected)
                </span>
              )}
            </div>

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
          </div>
        )}
      </CardContent>
    </Card>
  )
}
