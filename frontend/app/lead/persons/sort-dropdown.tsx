"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { SlidersHorizontal } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"

type SortOption = "filled" | "company" | "employees" | "owner" | "recent"

interface SortDropdownProps {
    onApply: (option: SortOption, direction: "most" | "least") => void
    defaultOption?: SortOption
    defaultDirection?: "most" | "least"
}

export function SortDropdown({
    onApply,
    defaultOption = "filled",
    defaultDirection = "most",
}: SortDropdownProps) {
    const [open, setOpen] = useState(false)
    const [selectedOption, setSelectedOption] = useState(defaultOption)
    const [direction, setDirection] = useState<"most" | "least">(defaultDirection)

    const handleDirectionToggle = (dir: "most" | "least") => {
        setDirection(dir)
    }

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                    <SlidersHorizontal className="h-4 w-4" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
                <div className="space-y-4">
                    <div>
                        <label className="text-sm font-medium mb-2 block">Sort By</label>
                        <Select value={selectedOption} onValueChange={(val) => setSelectedOption(val as SortOption)}>
                            <SelectTrigger>
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="filled">Data Completeness</SelectItem>
                                <SelectItem value="company">Company Name</SelectItem>
                                <SelectItem value="employees">Employee Count</SelectItem>
                                <SelectItem value="owner">Has Contact Info</SelectItem>
                                <SelectItem value="recent">Recently Enriched</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div>
                        <label className="text-sm font-medium mb-2 block">Direction</label>
                        <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                                <Checkbox
                                    checked={direction === "most"}
                                    onCheckedChange={() => handleDirectionToggle("most")}
                                />
                                <span className="text-sm">Most</span>
                            </div>
                            <div className="flex items-center space-x-2">
                                <Checkbox
                                    checked={direction === "least"}
                                    onCheckedChange={() => handleDirectionToggle("least")}
                                />
                                <span className="text-sm">Least</span>
                            </div>
                        </div>
                    </div>

                    <Button
                        onClick={() => {
                            onApply(selectedOption, direction)
                            setOpen(false)
                        }}
                        className="w-full"
                    >
                        Apply
                    </Button>
                </div>
            </DropdownMenuContent>
        </DropdownMenu>
    )
}