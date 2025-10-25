"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Search,
  Download,
  ArrowLeft,
  FileText,
  FileSpreadsheet,
  FileJson,
  ChevronDown,
  BarChart3,
  Users,
  Building,
  Star,
  Mail,
  Phone,
  Linkedin,
  MapPin,
  ExternalLink,
  X,
} from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { EnrichmentResults } from "@/components/enrichment-results"

interface PeopleEnrichmentResultsProps {
  onBack: () => void
  selectedCompanies: string[]
  dataSource?: "growjo" | "apollo" | "both"
  people?: any[]
}

export function PeopleEnrichmentResults({
  onBack,
  selectedCompanies,
  dataSource = "apollo",
  people = [],
}: PeopleEnrichmentResultsProps) {
  const [selectedResults, setSelectedResults] = useState<string[]>([])
  const [selectAll, setSelectAll] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [exportDropdownOpen, setExportDropdownOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [companyFilter, setCompanyFilter] = useState<string>("all-companies")
  const [titleFilter, setTitleFilter] = useState<string>("all-titles")
  const [filteredPeople, setFilteredPeople] = useState<any[]>([])

  const enrichedPeople = people.length > 0 ? people : [
    {
      id: "1",
      name: "John Smith",
      title: "Chief Technology Officer",
      company: "Acme Inc",
      companyWebsite: "acme.com",
      email: "john.smith@acme.com",
      phone: "+1 (555) 123-4567",
      linkedin: "linkedin.com/in/johnsmith",
      location: "San Francisco, CA",
      department: "Technology",
      seniority: "C-Level",
      experience: "15+ years",
      confidenceScore: 95,
      dataSource: dataSource,
      lastUpdated: "2023-11-15",
      avatar: "/placeholder.svg?height=40&width=40",
      companySize: "120 employees",
      companyRevenue: "$25.0M",
    },
    {
      id: "2",
      name: "Sarah Johnson",
      title: "Chief Executive Officer",
      company: "TechCorp",
      companyWebsite: "techcorp.io",
      email: "sarah.johnson@techcorp.io",
      phone: "+1 (555) 987-6543",
      linkedin: "linkedin.com/in/sarahjohnson",
      location: "Austin, TX",
      department: "Executive",
      seniority: "C-Level",
      experience: "12+ years",
      confidenceScore: 92,
      dataSource: dataSource,
      lastUpdated: "2023-12-01",
      avatar: "/placeholder.svg?height=40&width=40",
      companySize: "45 employees",
      companyRevenue: "$5.0M",
    },
    {
      id: "3",
      name: "Michael Chen",
      title: "Chief Information Officer",
      company: "DataSystems",
      companyWebsite: "datasystems.co",
      email: "michael.chen@datasystems.co",
      phone: "+1 (555) 456-7890",
      linkedin: "linkedin.com/in/michaelchen",
      location: "New York, NY",
      department: "Technology",
      seniority: "C-Level",
      experience: "18+ years",
      confidenceScore: 98,
      dataSource: dataSource,
      lastUpdated: "2023-11-28",
      avatar: "/placeholder.svg?height=40&width=40",
      companySize: "320 employees",
      companyRevenue: "$75.0M",
    },
    {
      id: "4",
      name: "Emily Davis",
      title: "VP of Sales",
      company: "CloudWorks",
      companyWebsite: "cloudworks.net",
      email: "emily.davis@cloudworks.net",
      phone: "+1 (555) 234-5678",
      linkedin: "linkedin.com/in/emilydavis",
      location: "Seattle, WA",
      department: "Sales",
      seniority: "VP",
      experience: "10+ years",
      confidenceScore: 88,
      dataSource: dataSource,
      lastUpdated: "2023-11-20",
      avatar: "/placeholder.svg?height=40&width=40",
      companySize: "150 employees",
      companyRevenue: "$30.0M",
    },
    {
      id: "5",
      name: "David Wilson",
      title: "Founder & CEO",
      company: "AI Solutions",
      companyWebsite: "aisolutions.ai",
      email: "david.wilson@aisolutions.ai",
      phone: "+1 (555) 876-5432",
      linkedin: "linkedin.com/in/davidwilson",
      location: "Boston, MA",
      department: "Executive",
      seniority: "Founder",
      experience: "20+ years",
      confidenceScore: 94,
      dataSource: dataSource,
      lastUpdated: "2023-12-05",
      avatar: "/placeholder.svg?height=40&width=40",
      companySize: "35 employees",
      companyRevenue: "$3.0M",
    },
    {
      id: "6",
      name: "Lisa Rodriguez",
      title: "VP of Marketing",
      company: "Acme Inc",
      companyWebsite: "acme.com",
      email: "lisa.rodriguez@acme.com",
      phone: "+1 (555) 321-7654",
      linkedin: "linkedin.com/in/lisarodriguez",
      location: "San Francisco, CA",
      department: "Marketing",
      seniority: "VP",
      experience: "8+ years",
      confidenceScore: 85,
      dataSource: dataSource,
      lastUpdated: "2023-11-16",
      avatar: "/placeholder.svg?height=40&width=40",
      companySize: "120 employees",
      companyRevenue: "$25.0M",
    },
    {
      id: "7",
      name: "Robert Kim",
      title: "Head of Product",
      company: "TechCorp",
      companyWebsite: "techcorp.io",
      email: "robert.kim@techcorp.io",
      phone: "+1 (555) 654-3210",
      linkedin: "linkedin.com/in/robertkim",
      location: "Austin, TX",
      department: "Product",
      seniority: "Director",
      experience: "12+ years",
      confidenceScore: 90,
      dataSource: dataSource,
      lastUpdated: "2023-12-02",
      avatar: "/placeholder.svg?height=40&width=40",
      companySize: "45 employees",
      companyRevenue: "$5.0M",
    },
    {
      id: "8",
      name: "Amanda Foster",
      title: "CFO",
      company: "DataSystems",
      companyWebsite: "datasystems.co",
      email: "amanda.foster@datasystems.co",
      phone: "+1 (555) 789-0123",
      linkedin: "linkedin.com/in/amandafoster",
      location: "New York, NY",
      department: "Finance",
      seniority: "C-Level",
      experience: "14+ years",
      confidenceScore: 93,
      dataSource: dataSource,
      lastUpdated: "2023-11-29",
      avatar: "/placeholder.svg?height=40&width=40",
      companySize: "320 employees",
      companyRevenue: "$75.0M",
    },
  ]

  // Get unique companies and titles for filter dropdowns
  const uniqueCompanies = [...new Set(enrichedPeople.map((person) => person.company))].sort()
  const uniqueTitles = [...new Set(enrichedPeople.map((person) => person.title))].sort()

  // Apply filters
  useEffect(() => {
    let filtered = [...enrichedPeople]

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(
        (person) =>
          person.name.toLowerCase().includes(term) ||
          person.title.toLowerCase().includes(term) ||
          person.company.toLowerCase().includes(term) ||
          person.email.toLowerCase().includes(term) ||
          person.department.toLowerCase().includes(term),
      )
    }

    // Apply company filter
    if (companyFilter && companyFilter !== "all-companies") {
      filtered = filtered.filter((person) => person.company === companyFilter)
    }

    // Apply title filter
    if (titleFilter && titleFilter !== "all-titles") {
      filtered = filtered.filter((person) => person.title === titleFilter)
    }

    setFilteredPeople(filtered)
  }, [searchTerm, companyFilter, titleFilter])

  // Initialize filtered people
  useEffect(() => {
    setFilteredPeople(enrichedPeople)
  }, [])

  useEffect(() => {
    // Auto-select all results initially
    setSelectedResults(filteredPeople.map((person) => person.id))
    setSelectAll(true)
  }, [filteredPeople])

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedResults([])
    } else {
      setSelectedResults(filteredPeople.map((person) => person.id))
    }
    setSelectAll(!selectAll)
  }

  const handleSelectPerson = (id: string) => {
    if (selectedResults.includes(id)) {
      setSelectedResults(selectedResults.filter((personId) => personId !== id))
      setSelectAll(false)
    } else {
      setSelectedResults([...selectedResults, id])
      if (selectedResults.length + 1 === filteredPeople.length) {
        setSelectAll(true)
      }
    }
  }

  const handleExport = (format: string) => {
    setIsLoading(true)
    setExportDropdownOpen(false)
    setTimeout(() => {
      setIsLoading(false)
      console.log(`Exporting ${selectedResults.length} contacts in ${format} format`)
      // Here you would implement actual export functionality
    }, 2000)
  }

  const clearFilters = () => {
    setCompanyFilter("all-companies")
    setTitleFilter("all-titles")
    setSearchTerm("")
  }

  const hasActiveFilters =
    (companyFilter && companyFilter !== "all-companies") || (titleFilter && titleFilter !== "all-titles") || searchTerm

  // Calculate statistics based on filtered results
  const cLevelCount = filteredPeople.filter(
    (person) => person.seniority === "C-Level" || person.seniority === "Founder",
  ).length
  const averageConfidence = Math.round(
    filteredPeople.reduce((sum, person) => sum + person.confidenceScore, 0) / (filteredPeople.length || 1),
  )
  const uniqueCompaniesCount = new Set(filteredPeople.map((person) => person.company)).size

  return (
    <div className="space-y-6 bg-[#121826] text-gray-100 min-h-screen p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">People Enrichment Results</h1>
          <p className="text-gray-400">
            Key contacts and decision makers from {dataSource === "apollo" ? "Apollo" : dataSource === "growjo" ? "Growjo" : "Both"}
            {hasActiveFilters && " • Filters applied"}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={onBack}
          className="gap-2 bg-[#1E2639] border-[#2E3A59] text-gray-300 hover:bg-[#2A3349] hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Selection
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-[#1E2639] to-[#171F2F] border-[#2E3A59] shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Contacts Found</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-2xl font-bold text-white">{filteredPeople.length}</div>
              <Users className="h-5 w-5 text-teal-400" />
            </div>
            <p className="text-xs text-gray-400 mt-1">{selectedResults.length} selected for export</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-[#1E2639] to-[#171F2F] border-[#2E3A59] shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">C-Level Contacts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-2xl font-bold text-white">{cLevelCount}</div>
              <Star className="h-5 w-5 text-yellow-400" />
            </div>
            <p className="text-xs text-gray-400 mt-1">senior decision makers</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-[#1E2639] to-[#171F2F] border-[#2E3A59] shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Companies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-2xl font-bold text-white">{uniqueCompaniesCount}</div>
              <Building className="h-5 w-5 text-blue-400" />
            </div>
            <p className="text-xs text-gray-400 mt-1">unique organizations</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-[#1E2639] to-[#171F2F] border-[#2E3A59] shadow-lg">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Data Quality</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-2xl font-bold text-white">{averageConfidence}%</div>
              <BarChart3 className="h-5 w-5 text-purple-400" />
            </div>
            <div className="mt-2">
              <Progress
                value={averageConfidence}
                className="h-1 bg-[#2E3A59]"
                indicatorClassName="bg-gradient-to-r from-teal-500 to-blue-500"
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">average confidence score</p>
          </CardContent>
        </Card>
      </div>

      {/* Results Table */}
      <Card className="bg-[#1A2133] border-[#2E3A59] shadow-lg">
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <CardTitle className="text-white">Contact Results</CardTitle>
              <CardDescription className="text-gray-400">
                {filteredPeople.length} key contacts identified and enriched
                {dataSource && (
                  <Badge variant="outline" className="ml-2 text-xs border-gray-500 text-gray-400">
                    {dataSource === "apollo" ? "Apollo" : dataSource === "growjo" ? "Growjo" : "Both"}
                  </Badge>
                )}
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  type="search"
                  placeholder="Search contacts, companies, titles..."
                  className="pl-8 w-64 bg-[#2A3349] border-[#3A4562] text-gray-200 placeholder:text-gray-500 focus-visible:ring-teal-500"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>

              {/* Export Dropdown */}
              <div className="relative">
                <Button
                  onClick={() => setExportDropdownOpen(!exportDropdownOpen)}
                  disabled={selectedResults.length === 0 || isLoading}
                  className="gap-2 bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600 text-white border-0 disabled:opacity-50"
                >
                  <Download className="h-4 w-4" />
                  {isLoading ? "Exporting..." : "Export"}
                  <ChevronDown className={`h-4 w-4 transition-transform ${exportDropdownOpen ? "rotate-180" : ""}`} />
                </Button>

                {exportDropdownOpen && (
                  <div className="absolute right-0 top-full mt-2 w-48 bg-[#1A2133] border border-[#2E3A59] rounded-md shadow-lg z-50">
                    <div className="py-1">
                      <button
                        onClick={() => handleExport("csv")}
                        className="w-full px-4 py-2 text-left hover:bg-[#2A3349] text-gray-300 hover:text-white transition-colors flex items-center gap-2"
                      >
                        <FileText className="h-4 w-4 text-teal-400" />
                        Export as CSV
                      </button>
                      <button
                        onClick={() => handleExport("excel")}
                        className="w-full px-4 py-2 text-left hover:bg-[#2A3349] text-gray-300 hover:text-white transition-colors flex items-center gap-2"
                      >
                        <FileSpreadsheet className="h-4 w-4 text-green-400" />
                        Export as Excel
                      </button>
                      <button
                        onClick={() => handleExport("json")}
                        className="w-full px-4 py-2 text-left hover:bg-[#2A3349] text-gray-300 hover:text-white transition-colors flex items-center gap-2"
                      >
                        <FileJson className="h-4 w-4 text-blue-400" />
                        Export as JSON
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Filter Controls */}
          <div className="flex flex-wrap items-center gap-2 mt-4">
            <Select value={companyFilter} onValueChange={setCompanyFilter}>
              <SelectTrigger className="w-48 bg-[#2A3349] border-[#3A4562] text-gray-200">
                <div className="flex items-center gap-2">
                  <Building className="h-4 w-4 text-gray-400" />
                  <SelectValue placeholder="Filter by company" />
                </div>
              </SelectTrigger>
              <SelectContent className="bg-[#1E2639] border-[#2E3A59] text-gray-200">
                <SelectItem value="all-companies" className="hover:bg-[#2A3349] focus:bg-[#2A3349]">
                  All Companies
                </SelectItem>
                {uniqueCompanies.map((company) => (
                  <SelectItem key={company} value={company} className="hover:bg-[#2A3349] focus:bg-[#2A3349]">
                    {company}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={titleFilter} onValueChange={setTitleFilter}>
              <SelectTrigger className="w-48 bg-[#2A3349] border-[#3A4562] text-gray-200">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-gray-400" />
                  <SelectValue placeholder="Filter by title" />
                </div>
              </SelectTrigger>
              <SelectContent className="bg-[#1E2639] border-[#2E3A59] text-gray-200">
                <SelectItem value="all-titles" className="hover:bg-[#2A3349] focus:bg-[#2A3349]">
                  All Titles
                </SelectItem>
                {uniqueTitles.map((title) => (
                  <SelectItem key={title} value={title} className="hover:bg-[#2A3349] focus:bg-[#2A3349]">
                    {title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {hasActiveFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={clearFilters}
                className="gap-1 bg-[#2A3349] border-[#3A4562] text-gray-300 hover:bg-[#3A4562] hover:text-white"
              >
                <X className="h-4 w-4" />
                Clear Filters
              </Button>
            )}

            {hasActiveFilters && (
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <div className="w-2 h-2 bg-teal-500 rounded-full"></div>
                <span>Filters active</span>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-[#2E3A59]">
            <Table>
              <TableHeader>
                <TableRow className="bg-[#1E2639] hover:bg-[#1E2639] border-b-[#2E3A59]">
                  <TableHead className="w-[50px] text-gray-400">
                    <Checkbox
                      checked={selectAll && filteredPeople.length > 0}
                      onCheckedChange={handleSelectAll}
                      className="border-[#3A4562] data-[state=checked]:bg-teal-500 data-[state=checked]:border-teal-500"
                    />
                  </TableHead>
                  <TableHead className="text-gray-400">Contact</TableHead>
                  <TableHead className="text-gray-400">Title</TableHead>
                  <TableHead className="text-gray-400">Company</TableHead>
                  <TableHead className="text-gray-400">Contact Info</TableHead>
                  <TableHead className="text-gray-400">Location</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPeople.length > 0 ? (
                  filteredPeople.map((person, index) => (
                    <TableRow
                      key={person.id}
                      className={`${index % 2 === 0 ? "bg-[#1A2133]" : "bg-[#1E2639]"} hover:bg-[#2A3349] border-b-[#2E3A59]`}
                    >
                      <TableCell>
                        <Checkbox
                          checked={selectedResults.includes(person.id)}
                          onCheckedChange={() => handleSelectPerson(person.id)}
                          className="border-[#3A4562] data-[state=checked]:bg-teal-500 data-[state=checked]:border-teal-500"
                        />
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-white">{person.name}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-gray-200">{person.title}</div>
                        <Badge
                          variant="outline"
                          className={`text-xs mt-1 ${
                            person.seniority === "C-Level" || person.seniority === "Founder"
                              ? "border-yellow-500 text-yellow-400"
                              : person.seniority === "VP"
                                ? "border-blue-500 text-blue-400"
                                : "border-gray-500 text-gray-400"
                          }`}
                        >
                          {person.seniority}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="text-white font-medium">{person.company}</div>
                          <div className="text-xs text-blue-400 flex items-center gap-1">
                            {person.companyWebsite}
                            <ExternalLink className="h-3 w-3" />
                          </div>
                          <div className="text-xs text-gray-400 mt-1">
                            {person.companySize} • {person.companyRevenue}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <div className="flex items-center gap-1 text-blue-400">
                            <Mail className="h-3 w-3" />
                            <span className="text-sm">{person.email}</span>
                          </div>
                          <div className="flex items-center gap-1 text-gray-200">
                            <Phone className="h-3 w-3" />
                            <span className="text-sm">{person.phone}</span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-gray-200">
                          <MapPin className="h-3 w-3" />
                          <span className="text-sm">{person.location}</span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow className="hover:bg-[#1A2133] border-b-[#2E3A59]">
                    <TableCell colSpan={7} className="h-24 text-center">
                      <div className="flex flex-col items-center justify-center py-8">
                        <Search className="h-8 w-8 text-gray-500 mb-4" />
                        <p className="text-lg font-medium text-gray-300">No results found</p>
                        <p className="text-sm text-gray-500">Try adjusting your search or filter criteria</p>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          <div className="flex justify-between items-center mt-4 pt-4 border-t border-[#2E3A59]">
            <p className="text-sm text-gray-400">
              {selectedResults.length} of {filteredPeople.length} contacts selected
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedResults([])}
                disabled={selectedResults.length === 0}
                className="bg-[#2A3349] border-[#3A4562] text-gray-300 hover:bg-[#3A4562] hover:text-white"
              >
                Clear Selection
              </Button>
              <Button
                size="sm"
                onClick={() => setSelectedResults(filteredPeople.map((p) => p.id))}
                disabled={selectedResults.length === filteredPeople.length}
                className="bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600 text-white border-0"
              >
                Select All
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Click outside to close export dropdown */}
      {exportDropdownOpen && <div className="fixed inset-0 z-40" onClick={() => setExportDropdownOpen(false)} />}
    </div>
  )
} 