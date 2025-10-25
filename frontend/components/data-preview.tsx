"use client"
import React from "react"
import { useState, useEffect } from "react"
import { Button } from "../components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table"
import { Checkbox } from "../components/ui/checkbox"
import { Input } from "../components/ui/input"
import { Search, Filter, ExternalLink } from "lucide-react"
import { useLeads } from "./LeadsProvider"
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

// Mock data for demonstration - this would come from the scraper results in a real app
const mockData = [
  {
    id: 1,
    company: "Acme Inc",
    website: "acme.com",
    industry: "Software & Technology",
    street: "123 Tech Blvd",
    city: "San Francisco",
    state: "CA",
    bbb_rating: "A+",
    business_phone: "+1 (555) 123-4567",
  },
  {
    id: 2,
    company: "TechCorp",
    website: "techcorp.io",
    industry: "Software & Technology",
    street: "456 Innovation Way",
    city: "Austin",
    state: "TX",
    bbb_rating: "A",
    business_phone: "+1 (555) 987-6543",
  },
  {
    id: 3,
    company: "DataSystems",
    website: "datasystems.co",
    industry: "Software & Technology",
    street: "789 Data Drive",
    city: "New York",
    state: "NY",
    bbb_rating: "A+",
    business_phone: "+1 (555) 456-7890",
  },
  {
    id: 4,
    company: "CloudWorks",
    website: "cloudworks.net",
    industry: "Software & Technology",
    street: "321 Cloud Ave",
    city: "Seattle",
    state: "WA",
    bbb_rating: "B+",
    business_phone: "+1 (555) 234-5678",
  },
  {
    id: 5,
    company: "AI Solutions",
    website: "aisolutions.ai",
    industry: "Software & Technology",
    street: "555 AI Parkway",
    city: "Boston",
    state: "MA",
    bbb_rating: "A-",
    business_phone: "+1 (555) 876-5432",
  },
]

export function DataPreview() {
  const { leads } = useLeads()
  const [selectedRows, setSelectedRows] = useState<number[]>(leads.map((row) => row.id))
  const [searchTerm, setSearchTerm] = useState("")
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(25)

  // Reset to first page when search term changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  // Function to normalize display values
  const normalizeDisplayValue = (value: any) => {
    if (value === null || value === undefined || value === "") return "N/A";
    if (value === "NA") return "N/A";
    return value;
  }

  // Function to clean URLs for display (remove http://, https://, www. and anything after the TLD)
  const cleanUrlForDisplay = (url: string): string => {
    if (!url || url === "N/A" || url === "NA") return url;
    
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

  const toggleSelectAll = () => {
    if (selectedRows.length === leads.length) {
      setSelectedRows([])
    } else {
      setSelectedRows(leads.map((row) => row.id))
    }
  }

  const toggleSelectRow = (id: number) => {
    if (selectedRows.includes(id)) {
      setSelectedRows(selectedRows.filter((rowId) => rowId !== id))
    } else {
      setSelectedRows([...selectedRows, id])
    }
  }

  const filteredData = leads.filter(
    (row) =>
      row.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      row.industry.toLowerCase().includes(searchTerm.toLowerCase()) ||
      row.city.toLowerCase().includes(searchTerm.toLowerCase()) ||
      row.state.toLowerCase().includes(searchTerm.toLowerCase()),
  )
  
  // Calculate pagination values
  const totalPages = Math.ceil(filteredData.length / itemsPerPage)
  const indexOfLastItem = currentPage * itemsPerPage
  const indexOfFirstItem = indexOfLastItem - itemsPerPage
  const currentItems = filteredData.slice(indexOfFirstItem, indexOfLastItem)

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Preview and Select Companies</h3>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search companies..."
              className="w-64 pl-8"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Button variant="outline" size="icon">
            <Filter className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Pagination controls */}
      {filteredData.length > 0 && (
        <div className="mb-4 flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, filteredData.length)} of {filteredData.length} results
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

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={selectedRows.length === leads.length && leads.length > 0}
                  onCheckedChange={toggleSelectAll}
                />
              </TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Industry</TableHead>
              <TableHead>Address</TableHead>
              <TableHead>BBB Rating</TableHead>
              <TableHead>Phone</TableHead>
              <TableHead>Website</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {currentItems.map((row) => (
              <TableRow key={row.id}>
                <TableCell>
                  <Checkbox checked={selectedRows.includes(row.id)} onCheckedChange={() => toggleSelectRow(row.id)} />
                </TableCell>
                <TableCell>
                  <div className="font-medium">{normalizeDisplayValue(row.company)}</div>
                </TableCell>
                <TableCell>{normalizeDisplayValue(row.industry)}</TableCell>
                <TableCell>
                  <div>{normalizeDisplayValue(row.street)}</div>
                  <div className="text-sm text-muted-foreground">
                    {normalizeDisplayValue(row.city)}, {normalizeDisplayValue(row.state)}
                  </div>
                </TableCell>
                <TableCell>{normalizeDisplayValue(row.bbb_rating)}</TableCell>
                <TableCell>{normalizeDisplayValue(row.business_phone)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {row.website ? normalizeDisplayValue(cleanUrlForDisplay(row.website)) : "N/A"}
                    {row.website && row.website !== "N/A" && row.website !== "NA" && (
                      <a
                        href={row.website.startsWith('http') ? row.website : `https://${row.website}`}
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
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {selectedRows.length} of {leads.length} companies selected for enrichment
        </div>
        <Button
          variant="outline"
          onClick={() => setSelectedRows(leads.map((row) => row.id))}
          disabled={selectedRows.length === leads.length}
        >
          Select All
        </Button>
      </div>
    </div>
  )
}
