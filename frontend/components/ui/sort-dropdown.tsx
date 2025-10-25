"use client"

import { useState } from "react"
import { Button } from "./button"
import { Checkbox } from "./checkbox"
import { Popover, PopoverContent, PopoverTrigger } from "./popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select"
import { SlidersHorizontal } from "lucide-react" // add at the top if not yet imported

type SortOption = "filled" | "company" | "revenue" | "employees" | "owner" | "recent"

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
    const [selectedOption, setSelectedOption] = useState<SortOption>(defaultOption)
    const [direction, setDirection] = useState<"most" | "least">(defaultDirection)

    const handleDirectionToggle = (dir: "most" | "least") => {
        setDirection(dir)
    }

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button variant="outline" size="icon" title="Sort">
                    <SlidersHorizontal className="h-4 w-4" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[250px] space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium">Sort By</label>
                    <Select value={selectedOption} onValueChange={(val) => setSelectedOption(val as SortOption)}>
                        <SelectTrigger>
                            <SelectValue placeholder="Choose criteria" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="filled">Data Completeness</SelectItem>
                            <SelectItem value="company">Company Name</SelectItem>
                            <SelectItem value="revenue">Revenue</SelectItem>
                            <SelectItem value="employees">Employee Count</SelectItem>
                            <SelectItem value="owner">Has Contact Info</SelectItem>
                            <SelectItem value="recent">Recently Enriched</SelectItem>
                        </SelectContent>
                    </Select>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="most"
                            checked={direction === "most"}
                            onCheckedChange={() => handleDirectionToggle("most")}
                        />
                        <label htmlFor="most" className="text-sm">Most</label>
                    </div>
                    <div className="flex items-center gap-2">
                        <Checkbox
                            id="least"
                            checked={direction === "least"}
                            onCheckedChange={() => handleDirectionToggle("least")}
                        />
                        <label htmlFor="least" className="text-sm">Least</label>
                    </div>
                </div>

                <Button
                    size="sm"
                    onClick={() => {
                        onApply(selectedOption, direction)
                        setOpen(false)
                    }}
                    className="w-full"
                >
                    Apply
                </Button>
            </PopoverContent>
        </Popover>
    )
}
