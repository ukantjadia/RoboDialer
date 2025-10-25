"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ArrowRight, RefreshCw } from "lucide-react"

// Mock CSV headers
const csvHeaders = [
  "Company Name",
  "URL",
  "Industry",
  "Product",
  "Type",
  "Employees",
  "Revenue",
  "Founded",
  "City",
  "State",
  "LinkedIn",
  "Contact Name",
  "Contact Title",
  "Contact Email",
  "Contact Phone",
  "Contact LinkedIn",
]

// Standard fields
const standardFields = [
  {
    category: "Company Information",
    fields: [
      "Company",
      "Website",
      "Industry",
      "Product/Service Category",
      "Business Type",
      "Employees count",
      "Revenue",
      "Year Founded",
      "City",
      "State",
      "LinkedIn URL",
    ],
  },
  {
    category: "Primary Contact",
    fields: ["First Name", "Last Name", "Title", "Email", "Phone Number", "Owner's LinkedIn"],
  },
  { category: "Engagement Details", fields: ["Source", "Score"] },
]

export function ColumnMapping() {
  const [mappings, setMappings] = useState({
    "Company Name": "Company",
    URL: "Website",
    Industry: "Industry",
    Product: "Product/Service Category",
    Type: "Business Type",
    Employees: "Employees count",
    Revenue: "Revenue",
    Founded: "Year Founded",
    City: "City",
    State: "State",
    LinkedIn: "LinkedIn URL",
    "Contact Name": "First Name", // This would need to be split in a real app
    "Contact Title": "Title",
    "Contact Email": "Email",
    "Contact Phone": "Phone Number",
    "Contact LinkedIn": "Owner's LinkedIn",
  })

  const handleMappingChange = (csvHeader, standardField) => {
    setMappings({
      ...mappings,
      [csvHeader]: standardField,
    })
  }

  const handleAutoMap = () => {
    // In a real app, this would use an algorithm to match similar field names
    // For now, we'll just use our predefined mappings
    console.log("Auto-mapping fields...")
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Map CSV Columns to Standard Fields</h3>
        <Button variant="outline" onClick={handleAutoMap}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Auto-Map Fields
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-1/3">CSV Column</TableHead>
              <TableHead className="w-[100px]"></TableHead>
              <TableHead>Standard Field</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {csvHeaders.map((header) => (
              <TableRow key={header}>
                <TableCell>
                  <Badge variant="outline" className="font-mono">
                    {header}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex justify-center">
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </TableCell>
                <TableCell>
                  <Select value={mappings[header] || ""} onValueChange={(value) => handleMappingChange(header, value)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select field" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="do_not_import">Do not import</SelectItem>
                      {standardFields.map((group) => (
                        <div key={group.category}>
                          <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">{group.category}</div>
                          {group.fields.map((field) => (
                            <SelectItem key={field} value={field}>
                              {field}
                            </SelectItem>
                          ))}
                        </div>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="rounded-md bg-muted p-4">
        <div className="text-sm">
          <p className="font-medium">Mapping Tips:</p>
          <ul className="list-disc space-y-1 pl-5 mt-2 text-muted-foreground">
            <li>Map each CSV column to the appropriate standard field</li>
            <li>Fields like "Name" may need to be split into "First Name" and "Last Name" during processing</li>
            <li>Select "Do not import" for columns you want to exclude</li>
            <li>All required fields must be mapped before proceeding</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
