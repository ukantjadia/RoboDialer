"use client"
import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import type { EnrichedCompany } from '../types/enrichment'

interface EnrichmentContextType {
  // State
  enrichedCompanies: EnrichedCompany[]
  dbEnrichedCompanies: EnrichedCompany[]
  scrapedEnrichedCompanies: EnrichedCompany[]
  hasFirstEnrichment: boolean
  firstEnrichmentType: "company" | "people" | "both" | null
  showResults: boolean
  
  // Actions
  setEnrichedCompanies: (companies: EnrichedCompany[] | ((prev: EnrichedCompany[]) => EnrichedCompany[])) => void
  setDbEnrichedCompanies: (companies: EnrichedCompany[] | ((prev: EnrichedCompany[]) => EnrichedCompany[])) => void
  setScrapedEnrichedCompanies: (companies: EnrichedCompany[] | ((prev: EnrichedCompany[]) => EnrichedCompany[])) => void
  addEnrichedCompany: (company: EnrichedCompany) => void
  addEnrichedCompanies: (companies: EnrichedCompany[]) => void
  removeEnrichedCompany: (companyId: string) => void
  clearEnrichedCompanies: () => void
  setHasFirstEnrichment: (has: boolean) => void
  setFirstEnrichmentType: (type: "company" | "people" | "both" | null) => void
  setShowResults: (show: boolean) => void
  
  // Utility methods
  hasCompany: (companyName: string) => boolean
  getCompanyById: (id: string) => EnrichedCompany | undefined
  getCompanyByName: (name: string) => EnrichedCompany | undefined
}

const EnrichmentContext = createContext<EnrichmentContextType | undefined>(undefined)

export const useEnrichment = () => {
  const context = useContext(EnrichmentContext)
  if (context === undefined) {
    throw new Error('useEnrichment must be used within an EnrichmentProvider')
  }
  return context
}

interface EnrichmentProviderProps {
  children: ReactNode
}

export const EnrichmentProvider: React.FC<EnrichmentProviderProps> = ({ children }) => {
  // State
  const [enrichedCompanies, setEnrichedCompanies] = useState<EnrichedCompany[]>([])
  const [dbEnrichedCompanies, setDbEnrichedCompanies] = useState<EnrichedCompany[]>([])
  const [scrapedEnrichedCompanies, setScrapedEnrichedCompanies] = useState<EnrichedCompany[]>([])
  const [hasFirstEnrichment, setHasFirstEnrichment] = useState<boolean>(false)
  const [firstEnrichmentType, setFirstEnrichmentType] = useState<"company" | "people" | "both" | null>(null)
  const [showResults, setShowResults] = useState<boolean>(false)

  // Actions
  const addEnrichedCompany = useCallback((company: EnrichedCompany) => {
    setEnrichedCompanies(prev => {
      // Check if company already exists (by company name)
      const exists = prev.some(c => c.company === company.company)
      if (exists) {
        // Update existing company
        return prev.map(c => c.company === company.company ? company : c)
      }
      // Add new company
      return [...prev, company]
    })
  }, [])

  const addEnrichedCompanies = useCallback((companies: EnrichedCompany[]) => {
    setEnrichedCompanies(prev => {
      const existingCompanies = new Set(prev.map(c => c.company))
      const uniqueNewCompanies = companies.filter(c => !existingCompanies.has(c.company))
      return [...prev, ...uniqueNewCompanies]
    })
  }, [])

  const removeEnrichedCompany = useCallback((companyId: string) => {
    setEnrichedCompanies(prev => prev.filter(c => c.id !== companyId))
  }, [])

  const clearEnrichedCompanies = useCallback(() => {
    setEnrichedCompanies([])
    setDbEnrichedCompanies([])
    setScrapedEnrichedCompanies([])
    setHasFirstEnrichment(false)
    setFirstEnrichmentType(null)
    setShowResults(false)
  }, [])

  // Utility methods
  const hasCompany = useCallback((companyName: string) => {
    return enrichedCompanies.some(c => c.company === companyName)
  }, [enrichedCompanies])

  const getCompanyById = useCallback((id: string) => {
    return enrichedCompanies.find(c => c.id === id)
  }, [enrichedCompanies])

  const getCompanyByName = useCallback((name: string) => {
    return enrichedCompanies.find(c => c.company === name)
  }, [enrichedCompanies])

  // Sync enrichedCompanies with dbEnrichedCompanies and scrapedEnrichedCompanies
  React.useEffect(() => {
    const combined = [...dbEnrichedCompanies, ...scrapedEnrichedCompanies]
    setEnrichedCompanies(combined)
  }, [dbEnrichedCompanies, scrapedEnrichedCompanies])

  // Helper functions to handle both direct values and function callbacks
  const handleSetEnrichedCompanies = useCallback((companies: EnrichedCompany[] | ((prev: EnrichedCompany[]) => EnrichedCompany[])) => {
    if (typeof companies === 'function') {
      setEnrichedCompanies(companies)
    } else {
      setEnrichedCompanies(companies)
    }
  }, [])

  const handleSetDbEnrichedCompanies = useCallback((companies: EnrichedCompany[] | ((prev: EnrichedCompany[]) => EnrichedCompany[])) => {
    if (typeof companies === 'function') {
      setDbEnrichedCompanies(companies)
    } else {
      setDbEnrichedCompanies(companies)
    }
  }, [])

  const handleSetScrapedEnrichedCompanies = useCallback((companies: EnrichedCompany[] | ((prev: EnrichedCompany[]) => EnrichedCompany[])) => {
    if (typeof companies === 'function') {
      setScrapedEnrichedCompanies(companies)
    } else {
      setScrapedEnrichedCompanies(companies)
    }
  }, [])

  const value: EnrichmentContextType = {
    // State
    enrichedCompanies,
    dbEnrichedCompanies,
    scrapedEnrichedCompanies,
    hasFirstEnrichment,
    firstEnrichmentType,
    showResults,
    
    // Actions
    setEnrichedCompanies: handleSetEnrichedCompanies,
    setDbEnrichedCompanies: handleSetDbEnrichedCompanies,
    setScrapedEnrichedCompanies: handleSetScrapedEnrichedCompanies,
    addEnrichedCompany,
    addEnrichedCompanies,
    removeEnrichedCompany,
    clearEnrichedCompanies,
    setHasFirstEnrichment,
    setFirstEnrichmentType,
    setShowResults,
    
    // Utility methods
    hasCompany,
    getCompanyById,
    getCompanyByName,
  }

  return (
    <EnrichmentContext.Provider value={value}>
      {children}
    </EnrichmentContext.Provider>
  )
}
