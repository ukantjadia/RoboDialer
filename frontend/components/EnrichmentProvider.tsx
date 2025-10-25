"use client"
import React, { createContext, useContext, useState } from "react"
import type { EnrichedCompany } from "@/components/enrichment-results"

export type EnrichmentContextType = {
    enrichedCompanies: EnrichedCompany[]
    setEnrichedCompanies: React.Dispatch<React.SetStateAction<EnrichedCompany[]>>
    loading: boolean
    setLoading: React.Dispatch<React.SetStateAction<boolean>>
}

const EnrichmentContext = createContext<EnrichmentContextType | undefined>(undefined)

export const EnrichmentProvider = ({ children }: { children: React.ReactNode }) => {
    const [enrichedCompanies, setEnrichedCompanies] = useState<EnrichedCompany[]>([])
    const [loading, setLoading] = useState<boolean>(false)

    return (
        <EnrichmentContext.Provider value={{ enrichedCompanies, setEnrichedCompanies, loading, setLoading }}>
            {children}
        </EnrichmentContext.Provider>
    )
}

export const useEnrichment = () => {
    const context = useContext(EnrichmentContext)
    if (!context) throw new Error("useEnrichment must be used within EnrichmentProvider")
    return context
}
