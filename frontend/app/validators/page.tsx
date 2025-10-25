"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Phone, Mail, CheckCircle, XCircle, AlertCircle, Download, Trash2, Upload, FileText, Database, Shield, RefreshCw } from "lucide-react"
import { toast } from "@/hooks/use-toast"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface ValidationResult {
  id: string
  input: string
  type: 'phone' | 'email'
  isValid: boolean
  details: any
  verificationDetails: any
  timestamp: string
  status: 'valid' | 'invalid' | 'unknown'
  verified: boolean
  dbId?: string // Added for existing history
  userId?: string // Added for existing history
  leadId?: string // Added for existing history
}

interface BulkValidationData {
  file: File
  content: string
  preview: string[]
  rowCount: number
  type: 'phone' | 'email'
}

export default function ValidatorsPage() {
  const [phoneInput, setPhoneInput] = useState("")
  const [emailInput, setEmailInput] = useState("")
  const [isValidatingPhone, setIsValidatingPhone] = useState(false)
  const [isValidatingEmail, setIsValidatingEmail] = useState(false)
  const [validationResults, setValidationResults] = useState<ValidationResult[]>([])
  const [activeTab, setActiveTab] = useState("phone")
  
  // Pagination and filtering states
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(10)
  const [filterType, setFilterType] = useState<'all' | 'phone' | 'email'>('all')
  
  // Bulk validation states
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [bulkData, setBulkData] = useState<BulkValidationData | null>(null)
  const [isBulkValidating, setIsBulkValidating] = useState(false)

  // Details popup state
  const [selectedResult, setSelectedResult] = useState<ValidationResult | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)

  // Get the API URLs from environment variables
  const DATABASE_API_URL = process.env.NEXT_PUBLIC_DATABASE_URL || 'https://sandbox-api.saasquatchleads.com/api'
  const VALIDATOR_API_URL = process.env.NEXT_PUBLIC_PHONEVALIDATOR_API_URL || 'http://localhost:5002'

  // Load verification history from database on component mount
  useEffect(() => {
    loadVerificationHistory()
  }, [])

  // Load verification history from database
  const loadVerificationHistory = async () => {
    try {
      const response = await fetch(`${DATABASE_API_URL}/contact_verification/standalone/history`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const data = await response.json()
        if (data.success && data.history) { // Changed from data.data to data.history
          // Convert DB data to ValidationResult format
          const dbResults: ValidationResult[] = data.history.map((item: any) => {
            // Extract details from verification_data.details for proper display
            const verificationDetails = item.verification_data?.details || {}
            const isPhone = item.contact_type === 'phone'
            
            // Map database structure to validation API structure for consistent display
            const mappedDetails = isPhone ? {
              country: verificationDetails.country_code || 'Unknown',
              'country-code': verificationDetails.country_code || 'Unknown',
              'international-number': `+${verificationDetails.international_calling_code || '1'}${item.contact_value}`,
              'local-number': item.contact_value,
              'is-mobile': verificationDetails.line_type === 'mobile',
              'prefix-network': verificationDetails.carrier || 'Unknown',
              type: verificationDetails.line_type || 'unknown',
              valid: verificationDetails.valid || verificationDetails.format_valid || false,
              location: verificationDetails.timezone || 'Unknown'
            } : {
              active: verificationDetails.valid || verificationDetails.format_valid || false,
              email: item.contact_value,
              is_personal: verificationDetails.is_personal || false,
              smtp_status: verificationDetails.smtp_status || 'unknown',
              valid: verificationDetails.valid || verificationDetails.format_valid || false
            }
            
            return {
              id: item.id.toString(),
              input: item.contact_value,
              type: item.contact_type === 'phone' ? 'phone' : 'email',
              isValid: item.verification_data?.status === 'valid',
              details: mappedDetails,
              verificationDetails: item.verification_data,
              timestamp: item.last_verified || item.updated_at,
              status: item.verification_data?.status === 'valid' ? 'valid' : 'invalid',
              verified: true,
              dbId: item.id,
              userId: item.user_id,
              leadId: item.lead_id
            }
          })
          setValidationResults(dbResults)
        }
      }
      } catch (error) {
      console.error('Error loading verification history:', error)
    }
  }

  // Step 1: Lookup contact in database
  const lookupContactInDB = async (contact: string, type: 'phone' | 'email') => {
    try {
      const contactType = type === 'phone' ? 'phone' : 'email'
      const response = await fetch(
        `${DATABASE_API_URL}/contact_verification/standalone/lookup?contact_type=${contactType}&contact_value=${encodeURIComponent(contact.trim())}`,
        {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )

      if (response.ok) {
        const data = await response.json()
        return { success: true, data: data.data, found: data.found }
      } else {
        return { success: false, error: 'Lookup failed', found: false }
      }
    } catch (error) {
      return { success: false, error: 'Network error during lookup', found: false }
    }
  }

  // Step 2: Validate phone number (external service)
  const validatePhoneNumber = async (phone: string) => {
    try {
      const response = await fetch(`${VALIDATOR_API_URL}/validate_phone`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ phone: phone.trim() }),
      })

      if (response.ok) {
        const data = await response.json()
        return { success: true, data: data.phone_result || data }
      } else {
        return { success: false, error: 'Phone validation failed' }
      }
    } catch (error) {
      return { success: false, error: 'Network error during validation' }
    }
  }

  // Step 2: Validate email address (external service)
  const validateEmailAddress = async (email: string) => {
    try {
      const response = await fetch(`${VALIDATOR_API_URL}/validate_email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email.trim() }),
      })

      if (response.ok) {
        const data = await response.json()
        return { success: true, data: data.email_result || data }
      } else {
        return { success: false, error: 'Email validation failed' }
      }
    } catch (error) {
      return { success: false, error: 'Network error during validation' }
    }
  }

  // Step 3: Store phone verification results in database
  const storePhoneVerificationInDB = async (phone: string, validationData: any) => {
    try {
      const response = await fetch(`${DATABASE_API_URL}/contact_verification/standalone/phone`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone: phone.trim(),
          verification_data: {
            status: validationData?.valid || validationData?.is_valid ? "valid" : "invalid",
            score: 0.9, // Default score, could be calculated based on validation results
            details: {
              format_valid: validationData?.valid || validationData?.is_valid || false,
              country_code: validationData?.country || "Unknown",
              carrier: validationData?.['prefix-network'] || "Unknown",
              line_type: validationData?.type || "unknown",
              timezone: validationData?.location || "Unknown",
              valid: validationData?.valid || validationData?.is_valid || false
            },
            timestamp: new Date().toISOString()
          }
        }),
      })

      if (response.ok) {
        return { success: true, data: await response.json() }
      } else {
        return { success: false, error: 'Failed to store phone verification in DB' }
      }
    } catch (error) {
      return { success: false, error: 'Network error during storage' }
    }
  }

  // Step 3: Store email verification results in database
  const storeEmailVerificationInDB = async (email: string, validationData: any) => {
    try {
      const response = await fetch(`${DATABASE_API_URL}/contact_verification/standalone/email`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          verification_data: {
            status: validationData?.active || validationData?.valid ? "valid" : "invalid",
            score: 0.9, // Default score, could be calculated based on validation results
            details: {
              format_valid: validationData?.valid || false,
              is_personal: validationData?.is_personal || false,
              smtp_status: validationData?.smtp_status || 'unknown'
            },
            timestamp: new Date().toISOString()
          }
        }),
      })

      if (response.ok) {
        return { success: true, data: await response.json() }
      } else {
        return { success: false, error: 'Failed to store email verification in DB' }
      }
    } catch (error) {
      return { success: false, error: 'Network error during storage' }
    }
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>, type: 'phone' | 'email') => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.name.endsWith('.csv')) {
      toast({
        title: "Invalid File Type",
        description: "Please upload a CSV file",
        variant: "destructive"
      })
      return
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "File Too Large",
        description: "Please upload a file smaller than 5MB",
        variant: "destructive"
      })
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      const lines = content.split('\n').filter(line => line.trim())
      const preview = lines.slice(0, 5) // Show first 5 rows
      
      setBulkData({
        file,
        content,
        preview,
        rowCount: lines.length,
        type
      })
      setShowUploadModal(true)
    }
    reader.readAsText(file)
  }

  const handlePhoneValidation = async () => {
    if (!phoneInput.trim()) {
      toast({
        title: "Error",
        description: "Please enter a phone number to validate",
        variant: "destructive"
      })
      return
    }

    setIsValidatingPhone(true)
    try {
      // Step 1: Lookup in database
      const lookupResult = await lookupContactInDB(phoneInput.trim(), 'phone')
      if (lookupResult.found) {
        toast({
          title: "Already in DB",
          description: `Phone number "${phoneInput.trim()}" already exists in your database.`,
          variant: "default"
        })
        setPhoneInput("")
        setIsValidatingPhone(false)
        return
      }

      // Step 2: Validate phone number (only if NOT found in DB)
      const validationResult = await validatePhoneNumber(phoneInput.trim())
      
      // Step 3: Store results in database
      const storageResult = await storePhoneVerificationInDB(
        phoneInput.trim(), 
        validationResult.success ? validationResult.data : null
      )
      
      // Combine results
      const phoneResult = validationResult.success ? validationResult.data : {}
        const isValid = phoneResult.valid || phoneResult.is_valid || false
        
        const result: ValidationResult = {
          id: Date.now().toString(),
          input: phoneInput.trim(),
          type: 'phone',
          isValid: isValid,
          details: phoneResult,
        verificationDetails: null, // No DB verification details since contact wasn't found
          timestamp: new Date().toISOString(),
        status: isValid ? 'valid' : 'invalid',
        verified: false, // Not verified in DB since it's a new contact
        dbId: undefined,
        userId: undefined,
        leadId: undefined
        }
        
        setValidationResults(prev => [result, ...prev])
        setPhoneInput("")
        
      const storageStatus = storageResult.success ? " (Stored in DB)" : " (Storage failed)"
        toast({
          title: "Phone Validation Complete",
        description: `${isValid ? "Phone number is valid" : "Phone number is invalid"}${storageStatus}`,
          variant: isValid ? "default" : "destructive"
        })
    } catch (error) {
      console.error('Phone validation error:', error)
      toast({
        title: "Error",
        description: "Failed to validate phone number. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsValidatingPhone(false)
    }
  }

  const handleEmailValidation = async () => {
    if (!emailInput.trim()) {
      toast({
        title: "Error",
        description: "Please enter an email address to validate",
        variant: "destructive"
      })
      return
    }

    setIsValidatingEmail(true)
    try {
      // Step 1: Lookup in database
      const lookupResult = await lookupContactInDB(emailInput.trim(), 'email')
      if (lookupResult.found) {
        toast({
          title: "Already in DB",
          description: `Email address "${emailInput.trim()}" already exists in your database.`,
          variant: "default"
        })
        setEmailInput("")
        setIsValidatingEmail(false)
        return
      }

      // Step 2: Validate email address (only if NOT found in DB)
      const validationResult = await validateEmailAddress(emailInput.trim())
      
      // Step 3: Store results in database
      const storageResult = await storeEmailVerificationInDB(
        emailInput.trim(), 
        validationResult.success ? validationResult.data : null
      )
      
      // Combine results
      const emailResult = validationResult.success ? validationResult.data : {}
        const isValid = emailResult.active || emailResult.valid || emailResult.is_valid || false
        
        const result: ValidationResult = {
          id: Date.now().toString(),
          input: emailInput.trim(),
          type: 'email',
          isValid: isValid,
          details: emailResult,
        verificationDetails: null, // No DB verification details since contact wasn't found
          timestamp: new Date().toISOString(),
        status: isValid ? 'valid' : 'invalid',
        verified: false, // Not verified in DB since it's a new contact
        dbId: undefined,
        userId: undefined,
        leadId: undefined
        }
        
        setValidationResults(prev => [result, ...prev])
        setEmailInput("")
        
      const storageStatus = storageResult.success ? " (Stored in DB)" : " (Storage failed)"
        toast({
          title: "Email Validation Complete",
        description: `${isValid ? "Email address is valid" : "Email address is invalid"}${storageStatus}`,
          variant: isValid ? "default" : "destructive"
        })
    } catch (error) {
      console.error('Email validation error:', error)
      toast({
        title: "Error",
        description: "Failed to validate email address. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsValidatingEmail(false)
    }
  }

  // Bulk verification and validation functions
  const verifyBulkInDatabase = async (data: string[], type: 'phone' | 'email') => {
    try {
      // For bulk operations, we'll need to make individual lookup calls for each item
      const lookupPromises = data.map(item => {
        return lookupContactInDB(item.trim(), type)
      })
      
      const lookupResults = await Promise.all(lookupPromises)
      const foundItems = lookupResults.filter(result => result.success && result.found)
      
      if (foundItems.length > 0) {
        return { 
          success: true, 
          data: { 
            bulk_phone_results: type === 'phone' ? foundItems.map(r => r.data) : [],
            bulk_email_results: type === 'email' ? foundItems.map(r => r.data) : []
          } 
        }
      } else {
        return { success: false, error: 'No items found in database for bulk validation' }
      }
    } catch (error) {
      return { success: false, error: 'Network error during bulk lookup' }
    }
  }

  const validateBulkData = async (data: string[], type: 'phone' | 'email') => {
    try {
      const endpoint = type === 'phone' ? '/validate_phone' : '/validate_email'
      const payload = type === 'phone' ? { phones: data } : { emails: data }
      
      const response = await fetch(`${VALIDATOR_API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (response.ok) {
        const responseData = await response.json()
        return { success: true, data: responseData }
      } else {
        return { success: false, error: 'Bulk validation failed' }
      }
    } catch (error) {
      return { success: false, error: 'Network error during bulk validation' }
    }
  }

  const handleBulkValidation = async () => {
    if (!bulkData) return

    setIsBulkValidating(true)
    try {
      // Parse CSV content to extract data
      const lines = bulkData.content.split('\n').filter(line => line.trim())
      const data = lines.map(line => line.trim())
      
      // Step 1: Lookup all data in database
      const lookupResult = await verifyBulkInDatabase(data, bulkData.type)
      
      if (!lookupResult.success) {
        toast({
          title: "Bulk Validation Failed",
          description: lookupResult.error || "No items found in database for bulk validation",
          variant: "destructive"
        })
        return
      }
      
      // Step 2: Validate all found data
      const validationResult = await validateBulkData(data, bulkData.type)
      
      if (validationResult.success) {
        const results = bulkData.type === 'phone' 
          ? validationResult.data.bulk_phone_results 
          : validationResult.data.bulk_email_results

        if (results && Array.isArray(results)) {
          // Convert bulk results to individual validation results
          const bulkResults: ValidationResult[] = results.map((result, index) => {
            const input = bulkData.type === 'phone' 
              ? result.phone || result.input || data[index] || `Row ${index + 1}`
              : result.email || result.input || data[index] || `Row ${index + 1}`
            
            const isValid = bulkData.type === 'phone'
              ? result.validation?.valid || result.valid || false
              : result.active || result.valid || false

            // Get lookup details for this specific item
            let verificationDetails = null
            if (lookupResult.success && lookupResult.data) {
              const lookupData = bulkData.type === 'phone' 
                ? lookupResult.data.bulk_phone_results 
                : lookupResult.data.bulk_email_results
              if (lookupData && lookupData[index]) {
                verificationDetails = lookupData[index]
              }
            }

            return {
              id: `${Date.now()}-${index}`,
              input,
              type: bulkData.type,
              isValid,
              details: result,
              verificationDetails,
              timestamp: new Date().toISOString(),
              status: isValid ? 'valid' : 'invalid',
              verified: true,
              dbId: verificationDetails?.id,
              userId: verificationDetails?.user_id,
              leadId: verificationDetails?.lead_id
            }
          })

          // Store all results in database in parallel
          const storagePromises = bulkResults.map(result => {
            if (result.type === 'phone') {
              return storePhoneVerificationInDB(
                result.input,
                result.details
              )
            } else {
              return storeEmailVerificationInDB(
                result.input,
                result.details
              )
            }
          })
          
          // Wait for all storage operations to complete
          await Promise.allSettled(storagePromises)

          setValidationResults(prev => [...bulkResults, ...prev])
          
          const verifiedCount = bulkResults.filter(r => r.verified).length
          toast({
            title: "Bulk Validation Complete",
            description: `Processed ${bulkResults.length} ${bulkData.type === 'phone' ? 'phone numbers' : 'email addresses'} (${verifiedCount} found in DB)`,
            variant: "default"
          })
        }
      } else {
        throw new Error('Bulk validation failed')
      }
    } catch (error) {
      console.error('Bulk validation error:', error)
      toast({
        title: "Error",
        description: "Failed to process bulk validation. Please try again.",
        variant: "destructive"
      })
    } finally {
      setIsBulkValidating(false)
      setShowUploadModal(false)
      setBulkData(null)
    }
  }

  const cancelBulkUpload = () => {
    setShowUploadModal(false)
    setBulkData(null)
    // Reset file input
    const fileInputs = document.querySelectorAll('input[type="file"]') as NodeListOf<HTMLInputElement>
    fileInputs.forEach(input => input.value = '')
  }

  const openDetailsModal = (result: ValidationResult) => {
    setSelectedResult(result)
    setShowDetailsModal(true)
  }

  const closeDetailsModal = () => {
    setSelectedResult(null)
    setShowDetailsModal(false)
  }

  const handleRevalidateFromDetails = async () => {
    if (!selectedResult) return

    if (selectedResult.type === 'phone') {
      // Re-validate phone number
      setIsValidatingPhone(true)
      try {
        const validationResult = await validatePhoneNumber(selectedResult.input)
        
        if (validationResult.success) {
          const phoneData = validationResult.data.phone_result || validationResult.data
          const isValid = phoneData.valid || phoneData.is_valid || false
          
          // Update the selected result with new data
          const updatedResult: ValidationResult = {
            ...selectedResult,
            isValid: isValid,
            details: phoneData,
            verificationDetails: {
              status: isValid ? 'valid' : 'invalid',
              score: 0.9,
              details: {
                format_valid: phoneData.valid || false,
                country_code: phoneData.country || 'Unknown',
                carrier: phoneData['prefix-network'] || 'Unknown',
                line_type: phoneData.type || 'unknown',
                timezone: phoneData.location || 'Unknown',
                valid: phoneData.valid || false
              },
              timestamp: new Date().toISOString()
            },
            timestamp: new Date().toISOString(),
            status: isValid ? 'valid' : 'invalid'
          }
          
          setSelectedResult(updatedResult)
          
          // Update the validation results list
          setValidationResults(prev => 
            prev.map(result => 
              result.id === selectedResult.id ? updatedResult : result
            )
          )
          
          // Store in database
          await storePhoneVerificationInDB(selectedResult.input, phoneData)
          
          toast({
            title: "Phone Re-validation Complete",
            description: `Phone number is ${isValid ? "valid" : "invalid"}`,
            variant: isValid ? "default" : "destructive"
          })
        }
      } catch (error) {
        console.error('Phone re-validation error:', error)
        toast({
          title: "Error",
          description: "Failed to re-validate phone number",
          variant: "destructive"
        })
      } finally {
        setIsValidatingPhone(false)
      }
    } else {
      // Re-validate email address
      setIsValidatingEmail(true)
      try {
        const validationResult = await validateEmailAddress(selectedResult.input)
        
        if (validationResult.success) {
          const emailData = validationResult.data.email_result || validationResult.data
          const isValid = emailData.active || emailData.valid || emailData.is_valid || false
          
          // Update the selected result with new data
          const updatedResult: ValidationResult = {
            ...selectedResult,
            isValid: isValid,
            details: emailData,
            verificationDetails: {
              status: isValid ? 'valid' : 'invalid',
              score: 0.9,
              details: {
                format_valid: emailData.valid || false,
                is_personal: emailData.is_personal || false,
                smtp_status: emailData.smtp_status || 'unknown'
              },
              timestamp: new Date().toISOString()
            },
            timestamp: new Date().toISOString(),
            status: isValid ? 'valid' : 'invalid'
          }
          
          setSelectedResult(updatedResult)
          
          // Update the validation results list
          setValidationResults(prev => 
            prev.map(result => 
              result.id === selectedResult.id ? updatedResult : result
            )
          )
          
          // Store in database
          await storeEmailVerificationInDB(selectedResult.input, emailData)
          
          toast({
            title: "Email Re-validation Complete",
            description: `Email address is ${isValid ? "valid" : "invalid"}`,
            variant: isValid ? "default" : "destructive"
          })
        }
      } catch (error) {
        console.error('Email re-validation error:', error)
        toast({
          title: "Error",
          description: "Failed to re-validate email address",
          variant: "destructive"
        })
      } finally {
        setIsValidatingEmail(false)
      }
    }
  }

  const clearHistory = () => {
    // Refresh from database instead of clearing local state
    loadVerificationHistory()
    setFilterType('all')
    setCurrentPage(1)
    toast({
      title: "History Refreshed",
      description: "Verification history has been refreshed from database",
      variant: "default"
    })
  }

  const exportResults = () => {
    const resultsToExport = filteredResults.length > 0 ? filteredResults : validationResults
    
    if (resultsToExport.length === 0) {
      toast({
        title: "No Data",
        description: "No validation results to export",
        variant: "destructive"
      })
      return
    }

    // Helper function to safely get nested values
    const getValue = (obj: any, path: string, defaultValue: any = 'N/A') => {
      return path.split('.').reduce((o, p) => o && o[p], obj) || defaultValue
    }

    // Helper function to format boolean values
    const formatBoolean = (value: any) => {
      if (value === true || value === 'true') return 'Yes'
      if (value === false || value === 'false') return 'No'
      return 'N/A'
    }

    // Helper function to format phone type
    const formatPhoneType = (details: any) => {
      const type = details?.type || details?.['phone_result']?.type || 'unknown'
      if (type === 'mobile') return 'Mobile'
      if (type === 'landline') return 'Landline'
      return type.charAt(0).toUpperCase() + type.slice(1)
    }

    const csvContent = [
      [
        'Index',
        'Type',
        'Input',
        'Status',
        'Valid',
        'Format Valid',
        'Verified in DB',
        'Last Verified',
        // Phone-specific columns
        'Country',
        'Phone Type',
        'Carrier',
        'Location',
        'International Number',
        'Local Number',
        'Is Mobile',
        'Calling Code',
        // Email-specific columns
        'Active',
        'Is Personal',
        'SMTP Status',
        'Domain'
      ],
      ...resultsToExport.map((result, index) => {
        const details = result.details || {}
        const isPhone = result.type === 'phone'
        
        return [
          // Basic info
          index + 1,
          result.type,
          result.input,
          result.status,
          formatBoolean(result.isValid),
          formatBoolean(details.valid || details.format_valid),
          formatBoolean(result.verified),
          new Date(result.timestamp).toLocaleString(),
          
          // Phone-specific data
          isPhone ? (details.country || 'N/A') : 'N/A',
          isPhone ? formatPhoneType(details) : 'N/A',
          isPhone ? (details['prefix-network'] || details.carrier || 'N/A') : 'N/A',
          isPhone ? (details.location || 'N/A') : 'N/A',
          isPhone ? (details['international-number'] || 'N/A') : 'N/A',
          isPhone ? (details['local-number'] || 'N/A') : 'N/A',
          isPhone ? formatBoolean(details['is-mobile']) : 'N/A',
          isPhone ? (details['international-calling-code'] ? `+${details['international-calling-code']}` : 'N/A') : 'N/A',
          
          // Email-specific data
          !isPhone ? formatBoolean(details.active) : 'N/A',
          !isPhone ? formatBoolean(details.is_personal) : 'N/A',
          !isPhone ? (details.smtp_status || 'N/A') : 'N/A',
          !isPhone ? (details.domain || details.email?.split('@')[1] || 'N/A') : 'N/A'
        ]
      })
    ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `verification-results-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)

    toast({
      title: "Export Complete",
      description: "Verification results exported successfully",
      variant: "default"
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'valid':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'invalid':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'valid':
        return <Badge variant="default" className="bg-green-600">Valid</Badge>
      case 'invalid':
        return <Badge variant="destructive">Invalid</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  // Filter and pagination logic
  const filteredResults = validationResults.filter(result => {
    if (filterType === 'all') return true
    return result.type === filterType
  })

  const totalPages = Math.ceil(filteredResults.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const paginatedResults = filteredResults.slice(startIndex, endIndex)

  const handleFilterChange = (type: 'all' | 'phone' | 'email') => {
    setFilterType(type)
    setCurrentPage(1) // Reset to first page when filtering
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-white">Validators</h1>
        <p className="text-gray-400">Validate phone numbers and email addresses</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="phone" className="flex items-center gap-2">
            <Phone className="h-4 w-4" />
            Phone Validation
          </TabsTrigger>
          <TabsTrigger value="email" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Email Validation
          </TabsTrigger>
        </TabsList>

        <TabsContent value="phone" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Phone className="h-5 w-5" />
                Phone Number Validation
              </CardTitle>
              <CardDescription>
                Enter a phone number to validate its format and existence
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter phone number (e.g., +1-555-123-4567)"
                  value={phoneInput}
                  onChange={(e) => setPhoneInput(e.target.value)}
                  className="flex-1"
                />
                <Button 
                  onClick={handlePhoneValidation}
                  disabled={isValidatingPhone || !phoneInput.trim()}
                >
                  {isValidatingPhone ? "Verifying & Validating..." : "Verify & Validate"}
                </Button>
                <div className="relative">
                  <Input
                    type="file"
                    accept=".csv"
                    onChange={(e) => handleFileUpload(e, 'phone')}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                    id="phone-file-upload"
                  />
                  <Button variant="outline" className="cursor-pointer" asChild>
                    <label htmlFor="phone-file-upload">
                      <Upload className="h-4 w-4 mr-2" />
                      Upload
                    </label>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="email" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5" />
                Email Address Validation
              </CardTitle>
              <CardDescription>
                Enter an email address to validate its format and existence
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter email address (e.g., user@example.com)"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className="flex-1"
                />
                <Button 
                  onClick={handleEmailValidation}
                  disabled={isValidatingEmail || !emailInput.trim()}
                >
                  {isValidatingEmail ? "Verifying & Validating..." : "Verify & Validate"}
                </Button>
                <div className="relative">
                  <Input
                    type="file"
                    accept=".csv"
                    onChange={(e) => handleFileUpload(e, 'email')}
                    className="absolute inset-0 opacity-0 cursor-pointer"
                    id="email-file-upload"
                  />
                  <Button variant="outline" className="cursor-pointer" asChild>
                    <label htmlFor="email-file-upload">
                      <Upload className="h-4 w-4 mr-2" />
                      Upload
                    </label>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Upload Confirmation Modal */}
      <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Confirm Bulk Validation</DialogTitle>
            <DialogDescription>
              Review the file details before starting bulk validation
            </DialogDescription>
          </DialogHeader>
          
          {bulkData && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-500" />
                <span className="font-medium">{bulkData.file.name}</span>
                <Badge variant="outline">{bulkData.rowCount} rows</Badge>
              </div>
              
              <div>
                <span className="text-sm font-medium text-gray-400">Preview (first 5 rows):</span>
                <div className="mt-2 p-3 bg-gray-800 rounded-md max-h-32 overflow-y-auto">
                  {bulkData.preview.map((line, index) => (
                    <div key={index} className="text-sm text-gray-300 font-mono">
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={cancelBulkUpload} disabled={isBulkValidating}>
              Cancel
            </Button>
            <Button 
              onClick={handleBulkValidation}
              disabled={isBulkValidating}
            >
              {isBulkValidating ? "Verifying & Validating..." : "Start Verification & Validation"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Details Modal */}
      <Dialog open={showDetailsModal} onOpenChange={setShowDetailsModal}>
        <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto [&>button]:hidden">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedResult?.type === 'phone' ? (
                <Phone className="h-5 w-5 text-blue-400" />
              ) : (
                <Mail className="h-5 w-5 text-green-400" />
              )}
              {selectedResult?.type === 'phone' ? 'Phone' : 'Email'} Validation Details
            </DialogTitle>
            <DialogDescription>
              Comprehensive information about the validation and verification results
            </DialogDescription>
          </DialogHeader>
          
          {selectedResult && (
            <div className="space-y-6 relative">
              {/* Loading Overlay */}
              {(isValidatingPhone || isValidatingEmail) && (
                <div className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-50 rounded-lg">
                  <div className="text-center space-y-4">
                    <div className={`animate-spin rounded-full h-16 w-16 border-b-2 mx-auto ${selectedResult.type === 'phone' ? 'border-blue-600' : 'border-green-600'}`}></div>
                    <div className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                      Re-validating {selectedResult.type === 'phone' ? 'Phone Number' : 'Email Address'}...
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Please wait while we verify the contact
                    </div>
                  </div>
                </div>
              )}

              {/* Validation Details */}
              <div className="p-4 bg-gray-800/50 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  {/* {selectedResult.type === 'phone' ? (
                    <Phone className="h-4 w-4 text-blue-400" />
                  ) : (
                    <Mail className="h-4 w-4 text-green-400" />
                  )} */}
                  {/* <span className="text-sm font-medium text-gray-300">Validation Details</span> */}
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {/* Basic Information */}
                  <div className="flex justify-between">
                    <span className="text-gray-400">Input:</span>
                    <span className="text-white font-mono">{selectedResult.input}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Type:</span>
                    <Badge variant="outline">
                      {selectedResult.type === 'phone' 
                        ? (selectedResult.details?.type || selectedResult.details?.['phone_result']?.type || 'phone')
                        : selectedResult.type
                      }
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Status:</span>
                    {getStatusBadge(selectedResult.status)}
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Verified in DB:</span>
                    <span className={selectedResult.verified ? 'text-green-400' : 'text-red-400'}>
                      {selectedResult.verified ? 'Yes' : 'No'}
                    </span>
                  </div>

                  {/* Phone-specific details - ordered logically */}
                  {selectedResult.type === 'phone' && selectedResult.details && (
                    <>
                      {selectedResult.details['international-number'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">International Number:</span>
                          <span className="text-white font-mono">{selectedResult.details['international-number']}</span>
                        </div>
                      )}
                      {selectedResult.details['local-number'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Local Number:</span>
                          <span className="text-white font-mono">{selectedResult.details['local-number']}</span>
                        </div>
                      )}
                      {selectedResult.details.country && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Country:</span>
                          <span className="text-white">{selectedResult.details.country}</span>
                        </div>
                      )}
                      {selectedResult.details['country-code'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Country Code:</span>
                          <span className="text-white">{selectedResult.details['country-code']}</span>
                        </div>
                      )}
                      {selectedResult.details['is-mobile'] !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Is Mobile:</span>
                          <span className={selectedResult.details['is-mobile'] ? 'text-green-400' : 'text-red-400'}>
                            {selectedResult.details['is-mobile'] ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                      {selectedResult.details['prefix-network'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Carrier:</span>
                          <span className="text-white">{selectedResult.details['prefix-network']}</span>
                        </div>
                      )}
                    </>
                  )}

                  {/* Email-specific details - ordered logically */}
                  {selectedResult.type === 'email' && selectedResult.details && (
                    <>
                      {selectedResult.details.active !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Active:</span>
                          <span className={selectedResult.details.active ? 'text-green-400' : 'text-red-400'}>
                            {selectedResult.details.active ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                      {selectedResult.details.is_personal !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Is Personal:</span>
                          <span className={selectedResult.details.is_personal ? 'text-green-400' : 'text-red-400'}>
                            {selectedResult.details.is_personal ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                      {selectedResult.details.smtp_status && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">SMTP Status:</span>
                          <span className="text-white">{selectedResult.details.smtp_status}</span>
                        </div>
                      )}
                      {selectedResult.details.email && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Email:</span>
                          <span className="text-white font-mono">{selectedResult.details.email}</span>
                        </div>
                      )}
                    </>
                  )}

                  {/* Timestamp at the end */}
                  <div className="flex justify-between col-span-2">
                    <span className="text-gray-400">Last Verified:</span>
                    <span className="text-white">
                      {new Date(selectedResult.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>

            </div>
          )}
          
          <DialogFooter>
            <Button 
              variant="outline"
              onClick={handleRevalidateFromDetails}
              disabled={isValidatingPhone || isValidatingEmail}
            >
              {(isValidatingPhone || isValidatingEmail) ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Re-validating...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Re-validate
                </>
              )}
            </Button>
            <Button variant="outline" onClick={closeDetailsModal}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Validation History */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Validation History</CardTitle>
              <CardDescription>
                Recent validation results with database verification status
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={exportResults} disabled={validationResults.length === 0}>
                <Download className="h-4 w-4 mr-2" />
                Export {filterType !== 'all' ? filterType : ''} Results
              </Button>
              <Button variant="outline" onClick={clearHistory} disabled={validationResults.length === 0}>
                <Trash2 className="h-4 w-4 mr-2" />
                Clear
              </Button>
            </div>
          </div>
          
          {/* Filter Buttons */}
          <div className="flex gap-2 mt-4">
            <Button
              variant={filterType === 'all' ? 'default' : 'outline'}
              onClick={() => handleFilterChange('all')}
              size="sm"
            >
              All ({validationResults.length})
            </Button>
            <Button
              variant={filterType === 'phone' ? 'default' : 'outline'}
              onClick={() => handleFilterChange('phone')}
              size="sm"
            >
              <Phone className="h-4 w-4 mr-2" />
              Phone ({validationResults.filter(r => r.type === 'phone').length})
            </Button>
            <Button
              variant={filterType === 'email' ? 'default' : 'outline'}
              onClick={() => handleFilterChange('email')}
              size="sm"
            >
              <Mail className="h-4 w-4 mr-2" />
              Email ({validationResults.filter(r => r.type === 'email').length})
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {validationResults.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No validation results yet. Start by validating a phone number or email address.
            </div>
          ) : filteredResults.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No {filterType === 'all' ? '' : filterType} validation results found.
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {paginatedResults.map((result) => (
                  <div 
                    key={result.id} 
                    className="border rounded-lg p-4 bg-gray-800/50 hover:bg-gray-700/50 cursor-pointer transition-colors"
                    onClick={() => openDetailsModal(result)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {result.type === 'phone' ? (
                          <Phone className="h-5 w-5 text-blue-400" />
                        ) : (
                          <Mail className="h-5 w-5 text-green-400" />
                        )}
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-white">{result.input}</span>
                            {getStatusBadge(result.status)}
                            <Badge variant="outline">
                              {result.type === 'phone' 
                                ? (result.details?.type || result.details?.['phone_result']?.type || 'phone')
                                : result.type
                              }
                            </Badge>
                          </div>
                          <div className="text-sm text-gray-400">
                            {new Date(result.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </div>
                      <div className="text-sm text-gray-400">
                        Click to view details
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-6">
                  <div className="text-sm text-gray-400">
                    Showing {startIndex + 1} to {Math.min(endIndex, filteredResults.length)} of {filteredResults.length} results
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </Button>
                    <div className="flex gap-1">
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                        <Button
                          key={page}
                          variant={currentPage === page ? "default" : "outline"}
                          size="sm"
                          onClick={() => handlePageChange(page)}
                          className="w-8 h-8 p-0"
                        >
                          {page}
                        </Button>
                      ))}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

