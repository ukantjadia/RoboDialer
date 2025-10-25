"use client"

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogOverlay } from "@/components/ui/dialog";
import dynamic from "next/dynamic";
import { 
  Building2, 
  Globe, 
  MapPin, 
  Phone, 
  Linkedin, 
  Users, 
  Calendar, 
  TrendingUp,
  User,
  Mail,
  Briefcase,
  ArrowLeft,
  Lightbulb,
  Target,
  AlertTriangle,
  Search,
  BarChart3,
  Star,
  TrendingDown,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Activity,
  Network,
  Globe2,
  Hash,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Map,
  UserPlus,
  X
} from "lucide-react";

// Dynamic import for Leaflet map to avoid SSR issues
const MapComponent = dynamic(() => import('./MapComponent'), {
  ssr: false,
  loading: () => <div className="h-96 bg-gray-100 rounded-lg flex items-center justify-center">Loading map...</div>
});

interface CompanyData {
  id: string;
  lead_id: string;
  company: string;
  website: string;
  industry: string;
  productCategory: string;
  businessType: string;
  employees: string;
  revenue: string;
  yearFounded: string;
  bbbRating: string;
  street: string;
  city: string;
  state: string;
  companyPhone: string;
  companyLinkedin: string;
  contacts: Array<{
    name: string;
    title: string;
    email: string;
    phone: string;
    linkedin: string;
  }>;
}

interface Insight {
  id: string;
  type: 'market' | 'competitor' | 'opportunity' | 'risk' | 'trend';
  title: string;
  description: string;
  confidence: number;
  impact: "high" | "medium" | "low";
  category: string;
  createdAt: string;
}

interface Competitor {
  id: string;
  name: string;
  city: string;
  employees: number;
  revenue: string;
  similarityScore: number;
  threatLevel: "high" | "medium" | "low";
  lastUpdated: string;
}

interface GrowthTrend {
  id: string;
  metric: string;
  currentValue: string;
  previousValue: string;
  change: number;
  trend: "up" | "down" | "stable";
  period: string;
  description: string;
}

interface ConnectedPerson {
  id: string;
  name: string;
  title: string;
  company: string;
  connection: "direct" | "indirect" | "potential";
  mutualConnections: number;
  lastInteraction: string;
  linkedinUrl: string;
  notes: string;
}

interface Review {
  id: string;
  source: string;
  rating: number;
  reviewText: string;
  reviewer: string;
  date: string;
  sentiment: "positive" | "negative" | "neutral";
  verified: boolean;
}

interface SocialMediaPulse {
  id: string;
  platform: string;
  metric: string;
  value: string;
  change: number;
  trend: "up" | "down" | "stable";
  period: string;
  description: string;
}

interface MapLocation {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  phone?: string;
  website?: string;
  rating?: number;
  businessType?: string;
  mapsUrl?: string;
}

export default function CompanyInsightsPage() {
  const params = useParams();
  const router = useRouter();
  const leadId = params.leadId as string;
  
  const [company, setCompany] = useState<CompanyData | null>(null);
  const [growjoCompany, setGrowjoCompany] = useState<any>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [growthTrends, setGrowthTrends] = useState<GrowthTrend[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [socialMediaPulse, setSocialMediaPulse] = useState<SocialMediaPulse[]>([]);
  const [mapLocations, setMapLocations] = useState<MapLocation[]>([]);
  const [isMapLoading, setIsMapLoading] = useState(false);
  const [isGeneratingInsights, setIsGeneratingInsights] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingCompetitors, setIsLoadingCompetitors] = useState(false);
  const [competitorError, setCompetitorError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("insights");
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Clear errors when switching tabs
  useEffect(() => {
    setInsightError(null);
    setGrowthError(null);
    setCompetitorError(null);
    setNoReviewsFound(false);
    setNoReviewsMessage('');
  }, [activeTab]);
  const [connectedPeople, setConnectedPeople] = useState<ConnectedPerson[]>([]);
  const [isLoadingConnectedPeople, setIsLoadingConnectedPeople] = useState(false);
  const [isGeneratingGrowthTrends, setIsGeneratingGrowthTrends] = useState(false);
  const [isGeneratingReviews, setIsGeneratingReviews] = useState(false);
  const [insightError, setInsightError] = useState<string | null>(null);
  const [growthError, setGrowthError] = useState<string | null>(null);


  const [reviewStatus, setReviewStatus] = useState<string>('idle');
  const [noReviewsFound, setNoReviewsFound] = useState(false);
  const [noReviewsMessage, setNoReviewsMessage] = useState<string>('');
  const [isGeneratingConnectedPeople, setIsGeneratingConnectedPeople] = useState(false);
  const [showReviewsModal, setShowReviewsModal] = useState(false);
  const [reviewsSummary, setReviewsSummary] = useState<string>('');
  const [reviewsRating, setReviewsRating] = useState<number | null>(null);
  const [reviewsSource, setReviewsSource] = useState<string>('');
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isLoadingExistingInsights, setIsLoadingExistingInsights] = useState(false);
  const [competitorMetadata, setCompetitorMetadata] = useState<any>(null);
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [aiAnalysisData, setAiAnalysisData] = useState<any>(null);
  const [selectedGrowthTrend, setSelectedGrowthTrend] = useState<GrowthTrend | null>(null);
  const [isGrowthDialogOpen, setIsGrowthDialogOpen] = useState(false);
  const [growthTrendsData, setGrowthTrendsData] = useState<any>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const { toast } = useToast();

  // Handle insight card click
  const handleInsightClick = (insight: Insight) => {
    setSelectedInsight(insight);
    setIsDialogOpen(true);
  };

  // Handle growth trend card click
  const handleGrowthTrendClick = (trend: GrowthTrend) => {
    setSelectedGrowthTrend(trend);
    setIsGrowthDialogOpen(true);
  };

  // Unified function to transform AI analysis data into insights
  const transformAiAnalysisToInsights = (aiAnalysis: any, createdAt: string = new Date().toISOString()): Insight[] => {
    const insights: Insight[] = [];

    // Create a single comprehensive AI analysis insight
    if (aiAnalysis) {
      const overallScore = aiAnalysis.overall_score || aiAnalysis.total_score || 50;
      const investmentRec = aiAnalysis.investment_recommendation || 'Moderate';
      
      // Create sneak peek description
      let sneakPeek = `Overall Score: ${overallScore}/100 | Investment: ${investmentRec}`;
      
      // Add a snippet from the most relevant analysis
      const riskReason = aiAnalysis.risk_reason || aiAnalysis.risk?.explanation?.join('. ');
      const growthReason = aiAnalysis.growth_reason || aiAnalysis.growth_potential?.explanation?.join('. ');
      
      if (riskReason) {
        sneakPeek += `\n${riskReason.substring(0, 120)}...`;
      } else if (growthReason) {
        sneakPeek += `\n${growthReason.substring(0, 120)}...`;
      }

      insights.push({
        id: 'ai-overall',
        type: 'trend',
        title: 'AI Company Analysis',
        description: sneakPeek,
        confidence: overallScore / 100,
        impact: overallScore > 70 ? 'high' : overallScore > 40 ? 'medium' : 'low',
        category: 'AI Analysis',
        createdAt: createdAt
      });
    }

    return insights;
  };

  // Helper function to show notifications
  const showNotification = (message: string, type: "success" | "error" | "info" = "success") => {
    toast({
      title: message,
      variant: type === "error" ? "destructive" : type === "info" ? "default" : "default",
    });
  };

  // Fetch company data from Growjo API first to get company_id
  const fetchGrowjoCompanyData = async () => {
    try {
      console.log('Fetching Growjo company data for company:', company?.company || leadId);

      const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL || 'http://localhost:5000';
      const searchResponse = await fetch(`${DATABASE_URL}/growjo/companies`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_names: [company?.company || leadId]
        })
      });

      if (searchResponse.ok) {
        const searchData = await searchResponse.json();
        console.log('Growjo search response:', searchData);

        if (searchData.company_batch_results && searchData.company_batch_results.length > 0) {
          const batchResult = searchData.company_batch_results[0];
          if (batchResult.items && batchResult.items.length > 0) {
            const foundCompany = batchResult.items[0];
            const companyId = foundCompany.company_id;
            console.log('Extracted company_id:', companyId, 'from company:', foundCompany.company_name);

            if (companyId) {
              // Update the growjoCompany state and return the data
              const growjoData = { company_id: companyId };
              setGrowjoCompany(growjoData);
              return growjoData;
            }
          }
        }
      }

      console.log('No Growjo company data found');
      return null;
    } catch (error) {
      console.error('Error fetching Growjo company data:', error);
      return null;
    }
  };

  // Fetch company data with retry mechanism
  const fetchCompanyData = async (retryCount = 0) => {
    try {
      console.log(`Fetching company data for leadId: ${leadId} (attempt ${retryCount + 1})`);
      
      // Wait a bit for sessionStorage to be available (helps with navigation timing)
      if (retryCount === 0) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // First try to get data from draft data (most recent)
      const currentDraftData = sessionStorage.getItem("currentDraftData");
      console.log('🔍 Checking currentDraftData in sessionStorage:', currentDraftData ? 'Found' : 'Not found');
      if (currentDraftData) {
        const draftData = JSON.parse(currentDraftData);
        console.log('✅ Found company in currentDraftData:', draftData);
        console.log('Raw currentDraftData:', JSON.stringify(draftData, null, 2));
        
        // Transform the draft data to match our CompanyData interface
        const companyData: CompanyData = {
          id: draftData.lead_id || draftData.id || leadId,
          lead_id: draftData.lead_id || draftData.id || leadId,
          company: draftData.company || draftData.company_name || draftData.name || 'Unknown Company',
          website: draftData.website || draftData.website_url || draftData.domain,
          industry: draftData.industry || draftData.sector,
          productCategory: draftData.productCategory || draftData.product_category || draftData.category,
          businessType: draftData.businessType || draftData.business_type || draftData.type,
          employees: draftData.employees || draftData.employee_count || draftData.employees_count,
          revenue: draftData.revenue || draftData.revenue_range,
          yearFounded: draftData.year_founded || draftData.founded || draftData.established || draftData.founded_year?.toString() || draftData.founded?.toString(),
          bbbRating: draftData.bbbRating || draftData.bbb_rating || draftData.rating,
          street: draftData.street || draftData.address || draftData.location,
          city: draftData.city || draftData.city_name,
          state: draftData.state || draftData.state_name || draftData.region,
          companyPhone: draftData.phone || draftData.phone_number || draftData.contact_phone || draftData.company_phone,
          companyLinkedin: draftData.linkedin || draftData.linkedin_url || draftData.social_linkedin || draftData.company_linkedin,
          contacts: (() => {
            // Handle draft_data structure with contacts array
            if (draftData.contacts && Array.isArray(draftData.contacts)) {
              return draftData.contacts.map((contact: {
                owner_first_name?: string;
                owner_last_name?: string;
                owner_title?: string;
                owner_email?: string;
                owner_phone_number?: string;
                owner_linkedin?: string;
              }) => ({
                name: `${contact.owner_first_name || ''} ${contact.owner_last_name || ''}`.trim(),
                title: contact.owner_title,
                email: contact.owner_email,
                phone: contact.owner_phone_number,
                linkedin: contact.owner_linkedin
              })).filter((contact: { name: string }) => contact.name && contact.name.trim() !== '');
            }
            
            // Handle draft_data structure with owner_ fields (for backward compatibility)
            if (draftData.owner_first_name || draftData.owner_last_name || draftData.owner_email || draftData.owner_phone_number || draftData.owner_linkedin || draftData.owner_title) {
              return [{
                name: `${draftData.owner_first_name || ''} ${draftData.owner_last_name || ''}`.trim(),
                title: draftData.owner_title,
                email: draftData.owner_email,
                phone: draftData.owner_phone_number,
                linkedin: draftData.owner_linkedin
              }];
            }
            
            // Fallback to other contact fields
            return draftData.people || draftData.employees_list || [];
          })()
        };
        
        console.log('Transformed draft data to company data:', companyData);
        setCompany(companyData);
        
        // After setting company data, fetch Growjo data to get company_id
        const growjoData = await fetchGrowjoCompanyData();
        if (growjoData && growjoData.company_id) {
          setGrowjoCompany(growjoData);
        }
        
        return;
      }

      // Then try to get data from currentCompanyData (most recent)
      const currentCompanyData = sessionStorage.getItem("currentCompanyData");
      if (currentCompanyData) {
        const company = JSON.parse(currentCompanyData);
        console.log('Found currentCompanyData:', company);
        console.log('Raw company data structure:', JSON.stringify(company, null, 2));
        if (company.lead_id === leadId || company.id === leadId) {
          // Extract data from nested draft_data structure if it exists
          const draftData = company.draft_data || company;
          console.log('🔍 Using draftData for transformation:', draftData);
          console.log('🔍 Draft data keys:', Object.keys(draftData));
          console.log('🔍 Draft data revenue:', draftData.revenue);
          console.log('🔍 Draft data employees:', draftData.employees);
          
          // Transform the data to match our CompanyData interface
          const companyData: CompanyData = {
            id: company.id || company.lead_id || leadId,
            lead_id: company.lead_id || company.id || leadId,
            company: draftData.company || draftData.company_name || draftData.name || 'Unknown Company',
            website: draftData.website || draftData.website_url || draftData.domain,
            industry: draftData.industry || draftData.sector,
            productCategory: draftData.productCategory || draftData.product_category || draftData.category,
            businessType: draftData.businessType || draftData.business_type || draftData.type,
            employees: draftData.employees || draftData.employee_count || draftData.employees_count,
            revenue: draftData.revenue || draftData.revenue_range,
            yearFounded: draftData.yearFounded || draftData.year_founded || draftData.founded || draftData.established || draftData.founded_year?.toString() || draftData.founded?.toString(),
            bbbRating: draftData.bbbRating || draftData.bbb_rating || draftData.rating,
            street: draftData.street || draftData.address || draftData.location,
            city: draftData.city || draftData.city_name,
            state: draftData.state || draftData.state_name || draftData.region,
            companyPhone: draftData.companyPhone || draftData.phone || draftData.phone_number || draftData.contact_phone || draftData.company_phone,
            companyLinkedin: draftData.companyLinkedin || draftData.linkedin || draftData.linkedin_url || draftData.social_linkedin || draftData.company_linkedin,
            contacts: (() => {
              // Handle draft_data structure with contacts array
              if (draftData.contacts && Array.isArray(draftData.contacts)) {
                return draftData.contacts.map((contact: {
                  owner_first_name?: string;
                  owner_last_name?: string;
                  owner_title?: string;
                  owner_email?: string;
                  owner_phone_number?: string;
                  owner_linkedin?: string;
                }) => ({
                  name: `${contact.owner_first_name || ''} ${contact.owner_last_name || ''}`.trim(),
                  title: contact.owner_title,
                  email: contact.owner_email,
                  phone: contact.owner_phone_number,
                  linkedin: contact.owner_linkedin
                })).filter((contact: { name: string }) => contact.name && contact.name.trim() !== '');
              }
              
              // Handle draft_data structure with owner_ fields (for backward compatibility)
              if (draftData.owner_first_name || draftData.owner_last_name || draftData.owner_email || draftData.owner_phone_number || draftData.owner_linkedin || draftData.owner_title) {
                return [{
                  name: `${draftData.owner_first_name || ''} ${draftData.owner_last_name || ''}`.trim(),
                  title: draftData.owner_title,
                  email: draftData.owner_email,
                  phone: draftData.owner_phone_number,
                  linkedin: draftData.owner_linkedin
                }];
              }
              
              // Fallback to other contact fields
              return draftData.people || draftData.employees_list || [];
            })()
          };
          console.log('Transformed company data:', companyData);
          setCompany(companyData);
          return;
        }
      }

      // First try to get data from session storage (scraping history)
      const storedData = sessionStorage.getItem("scrapingHistory");
      if (storedData) {
        const companies = JSON.parse(storedData);
        const foundCompany = companies.find((c: any) => c.lead_id === leadId || c.id === leadId);
        if (foundCompany) {
          console.log('Found company in scrapingHistory:', foundCompany);
          console.log('Raw scrapingHistory company data:', JSON.stringify(foundCompany, null, 2));
          setCompany(foundCompany);
          return;
        }
      }

      // Try to get data from leads data
      const leadsData = sessionStorage.getItem("leadsData");
      if (leadsData) {
        const leads = JSON.parse(leadsData);
        const foundLead = leads.find((lead: any) => lead.id === leadId || lead.lead_id === leadId);
        if (foundLead) {
          console.log('Found company in leadsData:', foundLead);
          console.log('Raw leadsData company data:', JSON.stringify(foundLead, null, 2));
          // Transform lead data to company data format
          const companyData: CompanyData = {
            id: foundLead.id || foundLead.lead_id || leadId,
            lead_id: foundLead.lead_id || foundLead.id || leadId,
            company: foundLead.company || foundLead.company_name || foundLead.name || 'Unknown Company',
            website: foundLead.website || foundLead.website_url || foundLead.domain,
            industry: foundLead.industry || foundLead.sector,
            productCategory: foundLead.productCategory || foundLead.product_category || foundLead.category,
            businessType: foundLead.businessType || foundLead.business_type || foundLead.type,
            employees: foundLead.employees || foundLead.employee_count || foundLead.employees_count,
            revenue: foundLead.revenue || foundLead.revenue_range,
            yearFounded: foundLead.year_founded || foundLead.founded || foundLead.established || foundLead.founded_year?.toString() || foundLead.founded?.toString(),
            bbbRating: foundLead.bbbRating || foundLead.bbb_rating || foundLead.rating,
            street: foundLead.street || foundLead.address || foundLead.location,
            city: foundLead.city || foundLead.city_name,
            state: foundLead.state || foundLead.state_name || foundLead.region,
            companyPhone: foundLead.phone || foundLead.phone_number || foundLead.contact_phone || foundLead.company_phone,
            companyLinkedin: foundLead.linkedin || foundLead.linkedin_url || foundLead.social_linkedin || foundLead.company_linkedin,
            contacts: (() => {
              // Handle draft_data structure with contacts array
              if (foundLead.contacts && Array.isArray(foundLead.contacts)) {
                return foundLead.contacts.map((contact: {
                  owner_first_name?: string;
                  owner_last_name?: string;
                  owner_title?: string;
                  owner_email?: string;
                  owner_phone_number?: string;
                  owner_linkedin?: string;
                }) => ({
                  name: `${contact.owner_first_name || ''} ${contact.owner_last_name || ''}`.trim(),
                  title: contact.owner_title,
                  email: contact.owner_email,
                  phone: contact.owner_phone_number,
                  linkedin: contact.owner_linkedin
                })).filter((contact: { name: string }) => contact.name && contact.name.trim() !== '');
              }
              
              // Handle draft_data structure with owner_ fields (for backward compatibility)
              if (foundLead.owner_first_name || foundLead.owner_last_name || foundLead.owner_email || foundLead.owner_phone_number || foundLead.owner_linkedin || foundLead.owner_title) {
                return [{
                  name: `${foundLead.owner_first_name || ''} ${foundLead.owner_last_name || ''}`.trim(),
                  title: foundLead.owner_title,
                  email: foundLead.owner_email,
                  phone: foundLead.owner_phone_number,
                  linkedin: foundLead.owner_linkedin
                }];
              }
              
              // Fallback to other contact fields
              return foundLead.people || foundLead.employees_list || [];
            })()
          };
          setCompany(companyData);
          return;
        }
      }

      // Try to get data from enriched companies
      const enrichedData = sessionStorage.getItem("enrichedCompanies");
      if (enrichedData) {
        const enriched = JSON.parse(enrichedData);
        const foundEnriched = enriched.find((c: any) => c.id === leadId || c.lead_id === leadId);
        if (foundEnriched) {
          console.log('Found company in enrichedCompanies:', foundEnriched);
          console.log('Raw enrichedCompanies data:', JSON.stringify(foundEnriched, null, 2));
          const companyData: CompanyData = {
            id: foundEnriched.id || foundEnriched.lead_id || leadId,
            lead_id: foundEnriched.lead_id || foundEnriched.id || leadId,
            company: foundEnriched.company || foundEnriched.company_name || foundEnriched.name || 'Unknown Company',
            website: foundEnriched.website || foundEnriched.website_url || foundEnriched.domain,
            industry: foundEnriched.industry || foundEnriched.sector,
            productCategory: foundEnriched.productCategory || foundEnriched.product_category || foundEnriched.category,
            businessType: foundEnriched.businessType || foundEnriched.business_type || foundEnriched.type,
            employees: foundEnriched.employees || foundEnriched.employee_count || foundEnriched.employees_count,
            revenue: foundEnriched.revenue || foundEnriched.revenue_range,
            yearFounded: foundEnriched.year_founded || foundEnriched.founded || foundEnriched.established || foundEnriched.founded_year?.toString() || foundEnriched.founded?.toString(),
            bbbRating: foundEnriched.bbbRating || foundEnriched.bbb_rating || foundEnriched.rating,
            street: foundEnriched.street || foundEnriched.address || foundEnriched.location,
            city: foundEnriched.city || foundEnriched.city_name,
            state: foundEnriched.state || foundEnriched.state_name || foundEnriched.region,
            companyPhone: foundEnriched.phone || foundEnriched.phone_number || foundEnriched.contact_phone || foundEnriched.company_phone,
            companyLinkedin: foundEnriched.linkedin || foundEnriched.linkedin_url || foundEnriched.social_linkedin || foundEnriched.company_linkedin,
            contacts: (() => {
              // Handle draft_data structure with contacts array
              if (foundEnriched.contacts && Array.isArray(foundEnriched.contacts)) {
                return foundEnriched.contacts.map((contact: {
                  owner_first_name?: string;
                  owner_last_name?: string;
                  owner_title?: string;
                  owner_email?: string;
                  owner_phone_number?: string;
                  owner_linkedin?: string;
                }) => ({
                  name: `${contact.owner_first_name || ''} ${contact.owner_last_name || ''}`.trim(),
                  title: contact.owner_title,
                  email: contact.owner_email,
                  phone: contact.owner_phone_number,
                  linkedin: contact.owner_linkedin
                })).filter((contact: { name: string }) => contact.name && contact.name.trim() !== '');
              }
              
              // Handle draft_data structure with owner_ fields (for backward compatibility)
              if (foundEnriched.owner_first_name || foundEnriched.owner_last_name || foundEnriched.owner_email || foundEnriched.owner_phone_number || foundEnriched.owner_linkedin || foundEnriched.owner_title) {
                return [{
                  name: `${foundEnriched.owner_first_name || ''} ${foundEnriched.owner_last_name || ''}`.trim(),
                  title: foundEnriched.owner_title,
                  email: foundEnriched.owner_email,
                  phone: foundEnriched.owner_phone_number,
                  linkedin: foundEnriched.owner_linkedin
                }];
              }
              
              // Fallback to other contact fields
              return foundEnriched.contacts || foundEnriched.people || foundEnriched.employees_list || [];
            })()
          };
          setCompany(companyData);
          return;
        }
      }

      // If no data found, show error state
      console.warn('No company data found for leadId:', leadId);
      console.log('Available session storage keys:', Object.keys(sessionStorage));
      
      // Debug: Show all session storage data
      Object.keys(sessionStorage).forEach(key => {
        try {
          const data = sessionStorage.getItem(key);
          if (data && (key.includes('company') || key.includes('lead') || key.includes('scraping') || key.includes('enriched'))) {
            console.log(`Session storage key "${key}":`, data);
          }
        } catch (e) {
          console.log(`Could not parse session storage key "${key}"`);
        }
      });
      
      // If we reach here and no company was found, retry if we haven't exceeded retry limit
      if (retryCount < 3) {
        console.log(`No company data found, retrying in 200ms (attempt ${retryCount + 1})`);
        setTimeout(() => {
          fetchCompanyData(retryCount + 1);
        }, 200);
        return;
      }
      
      setCompany(null);
      
    } catch (error) {
      console.error("Error fetching company data:", error);
      
      // Retry logic: if no company data found and we haven't retried too many times
      if (retryCount < 3 && !company) {
        console.log(`Retrying fetchCompanyData in 200ms (attempt ${retryCount + 1})`);
        setTimeout(() => {
          fetchCompanyData(retryCount + 1);
        }, 200);
        return;
      }
      
      setCompany(null);
    } finally {
      setIsLoading(false);
    }
  };

  // Generate AI insights using the AI scoring API
  const generateAIInsights = async () => {
    if (!company) return;
    
    setIsGeneratingInsights(true);
    setInsightError(null); // Clear any previous errors
    
    try {
      // Enhanced parsing functions for revenue and employees
      const parseRevenue = (revenueInput: string | number | null): number => {
        if (!revenueInput) return 5000000; // Default $5M
        
        try {
          // If it's already a number, return it (assuming it's in thousands)
          if (typeof revenueInput === 'number') {
            return revenueInput * 1000; // Convert to actual dollars
          }
          
          // Convert to string for regex matching
          const revenueStr = String(revenueInput);
          
          // Handle various revenue formats
          const match = revenueStr.match(/\$?(\d+(?:\.\d+)?)M/);
          if (match) {
            return parseFloat(match[1]) * 1000000;
          }
          
          // Handle K format
          const kMatch = revenueStr.match(/\$?(\d+(?:\.\d+)?)K/);
          if (kMatch) {
            return parseFloat(kMatch[1]) * 1000;
          }
          
          // Handle plain numbers
          const numMatch = revenueStr.match(/(\d+(?:,\d+)*)/);
          if (numMatch) {
            return parseInt(numMatch[1].replace(/,/g, ''));
          }
          
          return 5000000; // Default fallback
        } catch (error) {
          console.warn('Error parsing revenue:', revenueInput, error);
          return 5000000; // Default fallback on error
        }
      };

      const parseEmployees = (employeeInput: string | number | null): number => {
        if (!employeeInput) return 75; // Default 75
        
        try {
          // If it's already a number, return it
          if (typeof employeeInput === 'number') {
            return employeeInput;
          }
          
          // Convert to string for regex matching
          const employeeStr = String(employeeInput);
          
          // Handle ranges like "50-100"
          const rangeMatch = employeeStr.match(/(\d+)-(\d+)/);
          if (rangeMatch) {
            const min = parseInt(rangeMatch[1]);
            const max = parseInt(rangeMatch[2]);
            return Math.round((min + max) / 2);
          }
          
          // Handle single numbers
          const singleMatch = employeeStr.match(/(\d+)/);
          if (singleMatch) {
            return parseInt(singleMatch[1]);
          }
          
          return 75; // Default fallback
        } catch (error) {
          console.warn('Error parsing employees:', employeeInput, error);
          return 75; // Default fallback on error
        }
      };

      // Debug: Log all available company fields that might contain revenue/employee data
      console.log('🔍 Debugging company data for metrics:');
      console.log('  - company.revenue:', company.revenue);
      console.log('  - company.revenue_range:', (company as any).revenue_range);
      console.log('  - company.annual_revenue:', (company as any).annual_revenue);
      console.log('  - company.organization_revenue:', (company as any).organization_revenue);
      console.log('  - company.employees:', company.employees);
      console.log('  - company.employee_count:', (company as any).employee_count);
      console.log('  - company.employees_count:', (company as any).employees_count);
      console.log('  - company.organization_size:', (company as any).organization_size);
      console.log('  - company.staff_count:', (company as any).staff_count);
      console.log('  - Full company object keys:', Object.keys(company));

      // Get company metrics with enhanced parsing - try multiple field sources
      const revenue = parseRevenue(company.revenue) || 
                     parseRevenue((company as any).revenue_range) || 
                     parseRevenue((company as any).annual_revenue) || 
                     parseRevenue((company as any).organization_revenue);
      
      const employees = parseEmployees(company.employees) || 
                       parseEmployees((company as any).employee_count) || 
                       parseEmployees((company as any).employees_count) || 
                       parseEmployees((company as any).organization_size) || 
                       parseEmployees((company as any).staff_count);
      
      // Log raw data for debugging
      console.log('Raw company data for metrics:', {
        revenue: company.revenue,
        employees: company.employees,
        industry: company.industry,
        productCategory: company.productCategory,
        businessType: company.businessType
      });

      console.log('Calculated metrics:', { revenue, employees });
      
      // Additional debugging for parsing
      console.log('🔍 Parsing details:');
      console.log('  - Original revenue:', company.revenue, 'Type:', typeof company.revenue);
      console.log('  - Parsed revenue:', revenue);
      console.log('  - Original employees:', company.employees, 'Type:', typeof company.employees);
      console.log('  - Parsed employees:', employees);

      // Extract keywords from company description and product category
      const extractKeywords = (): string => {
        const keywords = [];
        if (company.productCategory) keywords.push(company.productCategory);
        if (company.industry) keywords.push(company.industry);
        if (company.businessType) keywords.push(company.businessType);
        return keywords.join(', ');
      };

      // Build API payload with actual company data
      const payload = {
        preferences: {
          industry: company.industry || "Home Healthcare Services",
          target_revenue: company.revenue || (company as any).revenue_range || (company as any).annual_revenue || (company as any).organization_revenue || "Unknown",
          target_employees: company.employees || (company as any).employee_count || (company as any).employees_count || (company as any).organization_size || (company as any).staff_count || "Unknown",
          keywords: extractKeywords()
        },
        companies: [{
          name: company.company,
          website: company.website,
          revenue: company.revenue || (company as any).revenue_range || (company as any).annual_revenue || (company as any).organization_revenue || "Unknown",
          employees: company.employees || (company as any).employee_count || (company as any).employees_count || (company as any).organization_size || (company as any).staff_count || "Unknown"
        }]
      };

      console.log('AI Insights API payload:', payload);

      // Check if API URL is configured
      const apiUrl = process.env.NEXT_PUBLIC_AI_SCORE_API_URL;
      if (!apiUrl) {
        throw new Error('AI scoring API URL not configured. Please add NEXT_PUBLIC_AI_SCORE_API_URL to your environment variables.');
      }

      // Call AI scoring API
      const response = await fetch(`${apiUrl}/score_leads`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`AI scoring API failed: ${response.status} - ${errorText}`);
      }

      const aiResponse = await response.json();
      console.log('AI Insights API response:', aiResponse);

      // Transform AI response to insights using unified function
      if (aiResponse.results && aiResponse.results[0]) {
        const aiAnalysis = aiResponse.results[0].analysis;
        
        // Use unified function to transform AI analysis to insights
        const newInsights = transformAiAnalysisToInsights(aiAnalysis);
        
        setInsights(newInsights);
        setAiAnalysisData(aiAnalysis);
        
          // Store AI insights data
          try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/ai-insights`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              credentials: 'include',
              body: JSON.stringify({
                lead_id: leadId,
                data: {
                  lead_id: leadId,
                  project_id: null,
                  website_text: {
                    content: `${company.company} is a company in the ${company.industry} industry.`,
                    title: `${company.company} - ${company.industry}`,
                    description: `${company.company} provides ${company.productCategory || 'N/A'} services.`,
                    keywords: [company.company, company.industry, company.productCategory || 'N/A'],
                    meta_data: {
                      author: company.company,
                      language: "en",
                      robots: "index, follow"
                    },
                    scraped_at: new Date().toISOString()
                  },
                  ai_analysis: {
                    risk_reason: aiAnalysis.risk?.explanation?.join('. ') || "Analysis not available",
                    growth_reason: aiAnalysis.growth_potential?.explanation?.join('. ') || "Analysis not available",
                    key_strengths: aiAnalysis.strengths || [],
                    key_concerns: aiAnalysis.concerns || [],
                    risk_score: aiAnalysis.risk?.score || 50,
                    growth_potential_score: aiAnalysis.growth_potential?.score || 50,
                    keyword_score: aiAnalysis.keywords?.score || 0,
                    keyword_reason: aiAnalysis.keywords?.explanation?.join('. ') || "Analysis not available",
                    investment_recommendation: aiAnalysis.investment_recommendation || "Moderate",
                    overall_score: aiAnalysis.total_score || 50
                  }
                }
              })
            });

            if (!response.ok) {
              console.warn('Failed to store AI insights:', response.statusText);
            } else {
              console.log('AI insights stored successfully');
            }
          } catch (error) {
            console.warn('Error storing AI insights:', error);
          }
        
        // Save AI analysis to database using the same API as AdminTaskView
        try {
          // Try the full API URL first
          const apiUrl = `${process.env.NEXT_PUBLIC_DATABASE_URL}/recommend`;
          console.log('Attempting to save AI analysis to:', apiUrl);
          
          const saveResponse = await fetch(apiUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              lead_id: company.lead_id,
              project_id: null, // No project context in company insights
              website_text: {
                content: `${company.company} is a company in the ${company.industry} industry.`,
                title: `${company.company} - ${company.industry}`,
                description: `${company.company} provides ${company.productCategory} services.`,
                keywords: [company.company, company.industry, company.productCategory],
                meta_data: {
                  author: company.company,
                  language: "en",
                  robots: "index, follow"
                },
                scraped_at: new Date().toISOString()
              },
              ai_analysis: {
                risk_reason: aiAnalysis.risk?.explanation?.join('. ') || "Analysis not available",
                growth_reason: aiAnalysis.growth_potential?.explanation?.join('. ') || "Analysis not available",
                key_strengths: aiAnalysis.strengths || [],
                key_concerns: aiAnalysis.concerns || [],
                risk_score: aiAnalysis.risk?.score || 50,
                growth_potential_score: aiAnalysis.growth_potential?.score || 50,
                keyword_score: aiAnalysis.keywords?.score || 0,
                keyword_reason: aiAnalysis.keywords?.explanation?.join('. ') || "Analysis not available",
                investment_recommendation: aiAnalysis.investment_recommendation || "Moderate",
                overall_score: aiAnalysis.total_score || 50
              }
            })
          });

          console.log('Save response status:', saveResponse.status);
          console.log('Save response headers:', saveResponse.headers);

          if (saveResponse.ok) {
            console.log('Successfully saved AI analysis to database');
            showNotification('AI insights generated and saved successfully!', 'success');
          } else if (saveResponse.status === 302) {
            console.warn('API returned 302 redirect - checking response headers');
            const location = saveResponse.headers.get('location');
            console.log('Redirect location:', location);
            
            // Try the original endpoint as fallback
            console.log('Trying fallback endpoint...');
            const fallbackResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/recommend`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
              },
              credentials: 'include',
              body: JSON.stringify({
                lead_id: company.lead_id,
                project_id: null,
                website_text: {
                  content: `${company.company} is a company in the ${company.industry} industry.`,
                  title: `${company.company} - ${company.industry}`,
                  description: `${company.company} provides ${company.productCategory} services.`,
                  keywords: [company.company, company.industry, company.productCategory],
                  meta_data: {
                    author: company.company,
                    language: "en",
                    robots: "index, follow"
                  },
                  scraped_at: new Date().toISOString()
                },
                ai_analysis: {
                  risk_reason: aiAnalysis.risk?.explanation?.join('. ') || "Analysis not available",
                  growth_reason: aiAnalysis.growth_potential?.explanation?.join('. ') || "Analysis not available",
                  key_strengths: aiAnalysis.strengths || [],
                  key_concerns: aiAnalysis.concerns || [],
                  risk_score: aiAnalysis.risk?.score || 50,
                  growth_potential_score: aiAnalysis.growth_potential?.score || 50,
                  keyword_score: aiAnalysis.keywords?.score || 0,
                  keyword_reason: aiAnalysis.keywords?.explanation?.join('. ') || "Analysis not available",
                  investment_recommendation: aiAnalysis.investment_recommendation || "Moderate",
                  overall_score: aiAnalysis.total_score || 50
                }
              })
            });
            
            if (fallbackResponse.ok) {
              console.log('Successfully saved AI analysis using fallback endpoint');
              showNotification('AI insights generated and saved successfully!', 'success');
            } else {
              console.warn('Fallback endpoint also failed:', fallbackResponse.status);
              showNotification('AI insights generated but failed to save to database', 'info');
            }
          } else {
            console.warn('Failed to save AI analysis to database:', saveResponse.status);
            const errorText = await saveResponse.text();
            console.log('Error response body:', errorText);
            showNotification(`AI insights generated but failed to save to database (${saveResponse.status})`, 'info');
          }
        } catch (saveError) {
          console.error('Error saving AI analysis to database:', saveError);
          showNotification('AI insights generated but failed to save to database', 'info');
        }
      } else {
        throw new Error('No AI analysis results received');
      }
    } catch (error) {
      console.error('Error generating AI insights:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
                        setInsightError(`Failed to generate AI insights: ${errorMessage}`);
      showNotification(`Failed to generate AI insights: ${errorMessage}`, 'error');
    } finally {
      setIsGeneratingInsights(false);
    }
  };

  // Fetch competitors data
  const fetchCompetitors = async () => {
    if (!company) {
      console.log('Company data not ready yet, skipping competitors fetch');
      return;
    }
    
    setIsLoadingCompetitors(true);
    try {
      // First, get the company_id from Growjo data
      let companyId = null;
      if (growjoCompany && growjoCompany.company_id) {
        companyId = growjoCompany.company_id;
      } else {
        // If we don't have Growjo data, try to fetch it first
        const growjoData = await fetchGrowjoCompanyData();
        if (growjoData && growjoData.company_id) {
          companyId = growjoData.company_id;
        }
      }
      
      if (!companyId) {
        console.log('No company_id found, skipping competitors fetch');
        setIsLoadingCompetitors(false);
        return;
      }
      
      // Call the Flask backend API for competitors with company_id
      console.log('Calling competitors API with company_id:', companyId);
      const response = await fetch(`${process.env.NEXT_PUBLIC_COMPANYINSIGHTS_API_URL}/get-competitors`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_company_id: companyId,
          range: 10,
          top_n: 10
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Competitors API response:', data);
      
      // Transform the API response to match our Competitor interface
      if (data.competitors && Array.isArray(data.competitors)) {
        const transformedCompetitors: Competitor[] = data.competitors.map((comp: any, index: number) => ({
          id: comp.id || comp.company_id || `competitor-${index}`,
          name: comp.company_name || 'Unknown Company',
          city: comp.city || 'Unknown',
          employees: comp.number_of_employees || 0,
          revenue: comp.revenue || 'Unknown',
          similarityScore: comp.similarity_score || 0,
          threatLevel: comp.similarity_score > 0.7 ? "high" : 
                      comp.similarity_score > 0.5 ? "medium" : "low",
          lastUpdated: data.generated_at || new Date().toISOString()
        }));
        
        setCompetitors(transformedCompetitors);
        // Store metadata if available
        if (data.metadata) {
          setCompetitorMetadata(data.metadata);
        }
        showNotification(`Found ${transformedCompetitors.length} competitors!`, 'success');
      } else {
        // Fallback to dummy data if API response format is unexpected
        console.warn('Unexpected API response format, using fallback data');
        const dummyCompetitors: Competitor[] = [
          {
            id: "1",
            name: "TechFlow Systems",
            city: "San Francisco",
            employees: 500,
            revenue: "$50M",
            similarityScore: 0.75,
            threatLevel: "high",
            lastUpdated: "2023-10-27T09:00:00Z"
          },
          {
            id: "2",
            name: "InnovateCorp",
            city: "Austin",
            employees: 250,
            revenue: "$25M",
            similarityScore: 0.65,
            threatLevel: "medium",
            lastUpdated: "2023-10-27T08:30:00Z"
          },
          {
            id: "3",
            name: "DataSphere Solutions",
            city: "Seattle",
            employees: 400,
            revenue: "$40M",
            similarityScore: 0.60,
            threatLevel: "medium",
            lastUpdated: "2023-10-27T08:00:00Z"
          }
        ];
        setCompetitors(dummyCompetitors);
        showNotification('Using fallback competitor data', 'info');
      }
    } catch (error) {
      console.error('Error fetching competitors:', error);
      
      // Check if it's a 404 error (no companies found)
      if (error instanceof Error && error.message.includes('404')) {
        setCompetitorError('No companies found in this location with the specified industry code. This could be due to limited data availability in the area.');
      } else {
        setCompetitorError('Failed to fetch competitors. Please try again or check your connection.');
      }
      
      // Clear competitors and show error instead of fallback data
      setCompetitors([]);
    } finally {
      setIsLoadingCompetitors(false);
    }
  };

  // Fetch growth trends data
  const fetchGrowthTrends = async () => {
    // Growth trends will be generated by AI when user clicks the generate button
    setGrowthTrends([]);
  };

  // Fetch connected people data from leads/draft API
  const fetchConnectedPeople = async () => {
    if (!company) {
      showNotification('Company data not available', 'error');
      return;
    }
    
    if (!company.company || company.company.trim() === '') {
      showNotification('Company name is required to find connected people', 'error');
      return;
    }
    
    setIsLoadingConnectedPeople(true);
    try {
      // Get the DATABASE_URL from environment or use a default
      const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL || 'http://localhost:5000';
      
      console.log('Searching for connected people for company:', company.company);
      console.log('Using DATABASE_URL:', DATABASE_URL);
      
      // First try to get company_id from the current company data
      const companyId = parseInt(company.lead_id) || parseInt(company.id);
      
      if (companyId && !isNaN(companyId)) {
        // Call the backend API for connected people
        const apiUrl = `${process.env.NEXT_PUBLIC_COMPANYINSIGHTS_API_URL}/get-connected-people`;
        console.log('Calling connected people API:', apiUrl);
        
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            company_id: companyId,
            domain: company.website,
            limit: 50
          })
        });
        
        if (response.ok) {
          const data = await response.json();
          console.log('Connected people API response:', data);
          
          if (data.data && Array.isArray(data.data)) {
            // Transform the API response to match our ConnectedPerson interface
            const transformedPeople: ConnectedPerson[] = data.data.map((person: any, index: number) => {
              // Combine first_name and last_name for the full name
              const fullName = `${person.first_name || ''} ${person.last_name || ''}`.trim() || 'Unknown Person';
              
              // Build notes from available data
              const notes = [
                person.email && `Email: ${person.email}`,
                person.city && `City: ${person.city}`,
                person.state && `State: ${person.state}`,
                person.phone_numbers && person.phone_numbers.length > 0 && 
                  `Phone: ${person.phone_numbers.map((p: any) => `${p.number} (${p.type})`).join(', ')}`,
                person.social_media?.linkedin_url && `LinkedIn: ${person.social_media.linkedin_url}`
              ].filter(Boolean).join(' | ') || 'No additional information';
              
              return {
                id: person.id || `connected-${index}`,
                name: fullName,
                title: person.title || 'Unknown Title',
                company: company.company,
                connection: "direct",
                mutualConnections: 0,
                lastInteraction: 'Recently',
                linkedinUrl: person.social_media?.linkedin_url || '#',
                notes: notes
              };
            });
            
            console.log('Transformed people:', transformedPeople);
            setConnectedPeople(transformedPeople);
            showNotification(`Found ${transformedPeople.length} connected people!`, 'success');
            return;
          }
        } else {
          console.warn('Connected people API failed, falling back to draft data');
        }
      }
      
      // Fallback to fetching from draft data if API fails or no company_id
      const response = await fetch(`${DATABASE_URL}/leads/drafts`, {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Fetched draft data:', data);
      console.log('Looking for company:', company.company);
      console.log('Total drafts found:', data.length);
      
      // Filter leads by company name (case-insensitive) and collect all people
      const allConnectedPeople: ConnectedPerson[] = [];
      
      data.forEach((entry: any) => {
        const draftData = entry.draft_data || {};
        const leadCompany = draftData.company || draftData.company_name || draftData.name || '';
        const currentCompany = company.company || '';
        
        console.log('Checking entry:', { 
          entry_lead_id: entry.lead_id, 
          entry_change_summary: entry.change_summary,
          leadCompany, 
          currentCompany, 
          isMatch: leadCompany.toLowerCase() === currentCompany.toLowerCase() 
        });
        
        const isMatch = leadCompany.toLowerCase() === currentCompany.toLowerCase();
        if (isMatch) {
          console.log('Found matching lead:', { leadCompany, currentCompany, draftData });
          
          // Handle multiple contacts from the same company
          if (draftData.contacts && Array.isArray(draftData.contacts)) {
            console.log('Found contacts array with', draftData.contacts.length, 'contacts');
            // Process each contact in the contacts array
            draftData.contacts.forEach((contact: any, contactIndex: number) => {
              const contactFirstName = contact.owner_first_name || '';
              const contactLastName = contact.owner_last_name || '';
              const contactName = `${contactFirstName} ${contactLastName}`.trim() || 'Unknown Person';
              
              console.log('Processing contact:', { contactIndex, contactName, contact });
              
              if (contactName !== 'Unknown Person') {
                allConnectedPeople.push({
                  id: `${entry.lead_id || entry.id}-contact-${contactIndex}`,
                  name: contactName,
                  title: contact.owner_title || 'Unknown Title',
                  company: draftData.company || draftData.company_name || draftData.name || 'Unknown Company',
                  connection: "direct",
                  mutualConnections: 1,
                  lastInteraction: entry.created_at ? new Date(entry.created_at).toLocaleDateString() : 'Unknown',
                  linkedinUrl: contact.owner_linkedin || '#',
                  notes: `Lead ID: ${entry.lead_id || entry.id}${contact.owner_email ? ` | Email: ${contact.email}` : ''}${contact.owner_phone_number ? ` | Phone: ${contact.owner_phone_number}` : ''}`
                });
                console.log('Added contact to allConnectedPeople');
              }
            });
          } else {
            console.log('No contacts array found in draftData');
          }
          
          // Also check for direct owner fields (for backward compatibility)
          if (draftData.owner_first_name || draftData.owner_last_name) {
            const ownerFirstName = draftData.owner_first_name || '';
            const ownerLastName = draftData.owner_last_name || '';
            const ownerName = `${ownerFirstName} ${ownerLastName}`.trim();
            
            if (ownerName) {
              // Check if this person is already added from contacts array
              const isAlreadyAdded = allConnectedPeople.some(person => 
                person.name === ownerName && person.company === draftData.company
              );
              
              if (!isAlreadyAdded) {
                allConnectedPeople.push({
                  id: `${entry.lead_id || entry.id}-owner`,
                  name: ownerName,
                  title: draftData.owner_title || 'Unknown Title',
                  company: draftData.company || draftData.company_name || draftData.name || 'Unknown Company',
                  connection: "direct",
                  mutualConnections: 1,
                  lastInteraction: entry.created_at ? new Date(entry.created_at).toLocaleDateString() : 'Unknown',
                  linkedinUrl: draftData.owner_linkedin || '#',
                  notes: `Lead ID: ${entry.lead_id || entry.id}${draftData.owner_email ? ` | Email: ${draftData.owner_email}` : ''}${draftData.owner_phone_number ? ` | Phone: ${draftData.owner_phone_number}` : ''}`
                });
              }
            }
          }
        }
      });

      console.log('Found connected people for company:', company.company, allConnectedPeople);
      console.log('Total people found before deduplication:', allConnectedPeople.length);

      // Remove duplicates based on name and company
      const uniqueConnectedPeople = allConnectedPeople.filter((person, index, self) => 
        index === self.findIndex(p => p.name === person.name && p.company === person.company)
      );

      console.log('Total people after deduplication:', uniqueConnectedPeople.length);
      console.log('Final unique people:', uniqueConnectedPeople);

      setConnectedPeople(uniqueConnectedPeople);
      
      if (uniqueConnectedPeople.length > 0) {
        showNotification(`Found ${uniqueConnectedPeople.length} connected people!`, 'success');
      } else {
        showNotification('No connected people found for this company', 'info');
      }
      
    } catch (error) {
      console.error('Error fetching connected people:', error);
      showNotification('Failed to fetch connected people. Using fallback data.', 'error');
      
      // Fallback to dummy data on error
      const dummyConnectedPeople: ConnectedPerson[] = [
        {
          id: "1",
          name: "Alex Thompson",
          title: "VP of Engineering",
          company: "TechFlow Systems",
          connection: "direct",
          mutualConnections: 12,
          lastInteraction: "2023-10-20",
          linkedinUrl: "https://linkedin.com/in/alexthompson",
          notes: "Former colleague, interested in collaboration opportunities"
        },
        {
          id: "2",
          name: "Maria Rodriguez",
          title: "CTO",
          company: "InnovateCorp",
          connection: "indirect",
          mutualConnections: 8,
          lastInteraction: "2023-10-15",
          linkedinUrl: "https://linkedin.com/in/mariarodriguez",
          notes: "Met at conference, potential partnership discussion"
        },
        {
          id: "3",
          name: "David Kim",
          title: "Head of Product",
          company: "DataSphere Solutions",
          connection: "potential",
          mutualConnections: 5,
          lastInteraction: "2023-10-10",
          linkedinUrl: "https://linkedin.com/in/davidkim",
          notes: "Reached out for product feedback, awaiting response"
        }
      ];
      
      setConnectedPeople(dummyConnectedPeople);
    } finally {
      setIsLoadingConnectedPeople(false);
    }
  };

  // Handle adding new connected people
  const handleAddConnectedPeople = async () => {
    if (!company) {
      showNotification('Company data not available', 'error');
      return;
    }
    
    setIsGeneratingConnectedPeople(true);
    try {
      // Use the specific URL for connected people API
      const CONNECTED_PEOPLE_URL = process.env.NEXT_PUBLIC_COMPANYINSIGHTS_API_URL;
      
      // First, we need to get the company_id from Growjo data
      let companyId = null;
      if (growjoCompany && growjoCompany.company_id) {
        companyId = growjoCompany.company_id;
      } else {
        // If we don't have Growjo data, try to fetch it first
        const growjoData = await fetchGrowjoCompanyData();
        if (growjoData && growjoData.company_id) {
          companyId = growjoData.company_id;
        }
      }
      
      if (!companyId) {
        showNotification('Company ID not found. Please ensure company data is loaded.', 'error');
        return;
      }
      
      // Call the get-connected-people API
      const response = await fetch(`${CONNECTED_PEOPLE_URL}/get-connected-people`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_id: companyId,
          domain: company.website || undefined,
          limit: 10
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error?.message || `HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Connected people API response:', data);
      
                     if (data.data && Array.isArray(data.data)) {
                       // Transform connected people data to contacts format
                       const contacts = data.data.map((person: any) => ({
                         owner_first_name: person.first_name || "",
                         owner_last_name: person.last_name || "",
                         owner_title: person.title || "",
                         owner_email: person.email || "",
                         owner_phone_number: person.phone_numbers?.[0]?.number || "",
                         owner_linkedin: person.social_media?.linkedin_url || ""
                       }));

                       // Get user_id from sessionStorage
                       const user = JSON.parse(sessionStorage.getItem("user") || "{}");
                       const user_id = user.user_id || "";

                       // Get the DATABASE_URL from environment or use a default
                       const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL || 'http://localhost:5000';

                       // Build company payload for upload
                       const companyPayload = {
                         id: 0, // Add this field
                         user_id: user_id,
                         lead_id: company.lead_id || "",
                         company: company.company,
                         website: company.website.startsWith('http') ? company.website : `https://${company.website}`, // Ensure protocol
                         industry: company.industry,
                         product_category: company.productCategory || "",
                         business_type: company.businessType || "",
                         employees: company.employees ? parseInt(company.employees) || 0 : 0, // Convert to number, default to 0
                         revenue: company.revenue ? parseInt(company.revenue) || 0 : 0, // Convert to number, default to 0
                         year_founded: company.yearFounded || "",
                         bbb_rating: company.bbbRating || "",
                         street: company.street || "",
                         city: company.city || "",
                         state: company.state || "",
                         country: "USA", // Add default country
                         company_phone: company.companyPhone || "",
                         company_linkedin: company.companyLinkedin || "",
                         source: "Connected People API",
                         contacts: contacts,
                         owner_linkedin: contacts[0]?.owner_linkedin || ""
                       };

                                                // Call /upload_leads API
                         try {
                           const uploadRes = await fetch(`${DATABASE_URL}/upload_leads`, {
                             method: 'POST',
                             headers: { 'Content-Type': 'application/json' },
                             credentials: 'include', // Include cookies for authentication
                             body: JSON.stringify([companyPayload])
                           });

                         if (!uploadRes.ok) {
                           throw new Error(`Upload failed: ${uploadRes.status} ${uploadRes.statusText}`);
                         }

                         const uploadData = await uploadRes.json();
                         console.log('Upload response:', uploadData);

                         // Extract lead_id from upload response if not already available
                         let lead_id = company.lead_id;
                         if (!lead_id && uploadData.stats?.detailed_results?.[0]?.lead_id) {
                           lead_id = uploadData.stats.detailed_results[0].lead_id;
                         }

                         // Call /leads/drafts API
                         if (lead_id) {
                           try {
                             const draftRes = await fetch(`${DATABASE_URL}/leads/drafts`, {
                               method: 'POST',
                               headers: { 'Content-Type': 'application/json' },
                               credentials: 'include', // Include cookies for authentication
                               body: JSON.stringify({
                                 lead_id: lead_id,
                                 draft_data: companyPayload,
                                 change_summary: "Added connected people via API"
                               })
                             });

                             if (!draftRes.ok) {
                               console.error('Draft creation failed:', draftRes.status, draftRes.statusText);
                             } else {
                               console.log('Draft created successfully');
                             }
                           } catch (draftErr) {
                             console.error('Error creating draft:', draftErr);
                           }
                         }

                         // Create ConnectedPerson objects for UI display
                         const newConnectedPeople: ConnectedPerson[] = data.data.map((person: any, index: number) => {
                           // Build notes with available information
                           let notes = [];
                           if (person.email) notes.push(`Email: ${person.email}`);
                           if (person.phone_numbers && person.phone_numbers.length > 0) {
                             const phoneInfo = person.phone_numbers.map((p: any) => `${p.type}: ${p.number}`).join(', ');
                             notes.push(`Phone: ${phoneInfo}`);
                           }
                           if (person.city && person.state) notes.push(`Location: ${person.city}, ${person.state}`);

                           return {
                             id: `api-${Date.now()}-${index}`,
                             name: `${person.first_name || ''} ${person.last_name || ''}`.trim() || 'Unknown Name',
                             title: person.title || 'Unknown Title',
                             company: company.company,
                             connection: "potential",
                             mutualConnections: Math.floor(Math.random() * 10) + 1,
                             lastInteraction: new Date().toLocaleDateString(),
                             linkedinUrl: person.social_media?.linkedin_url || '#',
                             notes: notes.length > 0 ? notes.join(' | ') : 'No additional info available'
                           };
                         });

                         setConnectedPeople(prev => [...prev, ...newConnectedPeople]);
                         showNotification(`Added ${newConnectedPeople.length} new connected people and saved to database!`, 'success');
                       } catch (uploadErr) {
                         console.error('Error uploading connected people:', uploadErr);
                         showNotification(`Failed to upload connected people: ${uploadErr instanceof Error ? uploadErr.message : 'Unknown error'}`, 'error');
                       }
                     } else {
                       showNotification('No connected people data received from API', 'info');
                     }
    } catch (error) {
      console.error('Error adding connected people:', error);
      showNotification(`Failed to add connected people: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    } finally {
      setIsGeneratingConnectedPeople(false);
    }
  };

  // Handle generating company reviews with API call
  const handleGenerateReviews = async () => {
    if (!company) {
      showNotification('Company data not available', 'error');
      return;
    }
    
    setIsGeneratingReviews(true);
    setReviewStatus('starting');
    setNoReviewsFound(false);
    setNoReviewsMessage('');
    
    try {
      const REVIEWS_API_URL = process.env.NEXT_PUBLIC_COMPANYINSIGHTS_API_URL;
      
      // Prepare the payload with enhanced location data
      const payload = {
        company_name: company.company,
        location: company.street ? `${company.street}, ${company.city}, ${company.state}` : (company.city && company.state ? `${company.city}, ${company.state}` : ''),
        website: company.website
      };
      
      console.log('🔍 Company Reviews API Payload:', payload);
      console.log('🔍 Company data for address:', {
        street: company.street,
        city: company.city,
        state: company.state,
        location: payload.location
      });
      
      // Call the company reviews API
      const response = await fetch(`${REVIEWS_API_URL}/get-company-reviews/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        setNoReviewsFound(false);
        setNoReviewsMessage('');
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Company reviews API response:', data);
      
      setReviewStatus('completed');
      
      // Store summary and rating information
      if (data.summary && data.summary.text) {
        setReviewsSummary(data.summary.text);
      }
      if (data.rating_info && data.rating_info.overall_rating) {
        setReviewsRating(data.rating_info.overall_rating);
        setReviewsSource(data.rating_info.source || 'Unknown');
      }
      
      // Transform the API response into Review objects
      if (data.reviews && Array.isArray(data.reviews.list) && data.reviews.list.length > 0) {
        const newReviews: Review[] = data.reviews.list.map((review: any, index: number) => ({
          id: `api-${Date.now()}-${index}`,
          source: data.reviews.source || 'API Review',
          rating: review.rating || review.stars || 4.0,
          reviewText: review.text || review.review_text || 'Review content not available',
          reviewer: review.reviewer || review.author || 'Anonymous',
          date: review.date || new Date().toISOString().split('T')[0],
          sentiment: review.sentiment || 'neutral',
          verified: review.verified || false
        }));
        
        setReviews(newReviews);
        setNoReviewsFound(false);
        setNoReviewsMessage('');
                  // Store reviews data
          try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/reviews`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              credentials: 'include',
              body: JSON.stringify({
                lead_id: leadId,
                data: {
                  notes: "Company reviews analysis completed",
                  rating_info: {
                    overall_rating: 4.0,
                    source: "Multiple sources"
                  },
                  request_info: {
                    company_name: company.company,
                    location: `${company.city}, ${company.state}`,
                    website: company.website
                  },
                  reviews: newReviews.map(review => ({
                    rating: review.rating || 4.0,
                    text: review.reviewText || "Review text not available",
                    source: review.source || "Unknown source"
                  })),
                  summary: {
                    review_count: newReviews.length,
                    text: `Generated ${newReviews.length} company reviews for analysis`
                  }
                }
              })
            });

            if (!response.ok) {
              console.warn('Failed to store reviews data:', response.statusText);
            } else {
              console.log('Reviews data stored successfully');
            }
          } catch (error) {
            console.warn('Error storing reviews data:', error);
          }
          
        showNotification(`Generated ${newReviews.length} company reviews!`, 'success');
      } else if (data.notes && data.notes.includes('Could not determine')) {
        // Handle case where ALL sources failed to find reviews
        showNotification('No reviews found from any source', 'info');
        setReviews([]); // Clear any existing reviews
        setNoReviewsFound(true);
        setNoReviewsMessage('all_sources_failed');
      } else if (data.notes) {
        // Handle other cases where no reviews were found
        showNotification(data.notes, 'info');
        setReviews([]);
        setNoReviewsFound(true);
        setNoReviewsMessage(data.notes);
      } else {
        showNotification('Review generation completed but no review data received', 'info');
        setReviews([]);
        setNoReviewsFound(true);
        setNoReviewsMessage('Review generation completed but no review data received');
      }
      
    } catch (error) {
      console.error('Error generating company reviews:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      showNotification(`Failed to generate company reviews: ${errorMessage}`, 'error');
      setReviewStatus('error');
      setNoReviewsFound(true);
      setNoReviewsMessage('generation_failed');
      setReviews([]);
    } finally {
      setIsGeneratingReviews(false);
    }
  };

  // Fetch reviews data - now empty since we're using real API
  const fetchReviews = async () => {
    // Reviews are now fetched through the real-time API
    setReviews([]);
  };

  // Fetch social media pulse data - now empty since we're using real data
  const fetchSocialMediaPulse = async () => {
    // Social media data will be fetched from real APIs in the future
    setSocialMediaPulse([]);
  };

  // Fetch map locations from Flask backend
  const fetchMapLocations = async () => {
    if (!company) return;
    
    setIsMapLoading(true);
    try {
      // Call your Flask backend API
              const response = await fetch(`${process.env.NEXT_PUBLIC_COMPANYINSIGHTS_API_URL}/get-map-links`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company_name: company.company,
          location: company.street ? `${company.street}, ${company.city}, ${company.state}` : `${company.city}, ${company.state}`
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Transform the response to map locations
      // Extract coordinates from Google Maps URL
      const locations: MapLocation[] = data.data.map((item: any, index: number) => {
        // Extract coordinates from Google Maps URL
        let latitude = 37.7749; // Default to SF
        let longitude = -122.4194;
        
        if (item.maps_url) {
          // Extract coordinates from Google Maps URL
          // Format: ...!3d37.7463078!4d-122.3922697!...
          const latMatch = item.maps_url.match(/!3d([\d.-]+)/);
          const lngMatch = item.maps_url.match(/!4d([\d.-]+)/);
          
          if (latMatch && lngMatch) {
            latitude = parseFloat(latMatch[1]);
            longitude = parseFloat(lngMatch[1]);
          }
        }
        
        return {
          id: item.id || `location-${index}`,
          name: item.name || 'Unknown Business',
          address: `${company.city}, ${company.state}`, // Use company location as fallback
          latitude: latitude,
          longitude: longitude,
          phone: company.companyPhone,
          website: company.website,
          rating: 4.5,
          businessType: company.industry,
          mapsUrl: item.maps_url // Store the maps URL
        };
      });

      setMapLocations(locations);
        
        // Store map locations data
        try {
          const response = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/maps`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              lead_id: leadId,
              data: {
                maps_url: locations.length > 0 ? locations[0].mapsUrl || `https://maps.google.com/maps/place/${encodeURIComponent(company.company)}` : `https://maps.google.com/maps/place/${encodeURIComponent(company.company)}`,
                name: company.company
              }
            })
          });

          if (!response.ok) {
            console.warn('Failed to store map locations data:', response.statusText);
          } else {
            console.log('Map locations data stored successfully');
          }
        } catch (error) {
          console.warn('Error storing map locations data:', error);
        }
        
    } catch (error) {
      console.error('Error fetching map locations:', error);
      // No fallback data - let the UI handle empty state
      setMapLocations([]);
    } finally {
      setIsMapLoading(false);
    }
  };

  // Generate insights
  const generateInsights = async () => {
    await generateAIInsights();
  };

  // Scroll navigation functions
  const scrollLeft = () => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current;
      const itemWidth = 320 + 16; // item width + gap
      container.scrollBy({ left: -itemWidth, behavior: 'smooth' });
    }
  };

  const scrollRight = () => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current;
      const itemWidth = 320 + 16; // item width + gap
      container.scrollBy({ left: itemWidth, behavior: 'smooth' });
    }
  };

  const checkScrollPosition = () => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current;
      setCanScrollLeft(container.scrollLeft > 0);
      setCanScrollRight(
        container.scrollLeft < container.scrollWidth - container.clientWidth - 1
      );
    }
  };

  // Helper function to get insight icon
  const getInsightIcon = (type: string) => {
    switch (type) {
      case "market": return <BarChart3 className="w-5 h-5" />;
      case "competitor": return <Target className="w-5 h-5" />;
      case "risk": return <AlertTriangle className="w-5 h-5" />;
      case "opportunity": return <Search className="w-5 h-5" />;
      case "trend": return <Lightbulb className="w-5 h-5" />;
      default: return <Lightbulb className="w-5 h-5" />;
    }
  };

  // Helper function to get impact color
  const getImpactColor = (impact: string) => {
    switch (impact) {
      case "high": return "bg-red-100 text-red-800 border-red-200";
      case "medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "low": return "bg-green-100 text-green-800 border-green-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  // Helper function to get threat level color
  const getThreatLevelColor = (level: string) => {
    switch (level) {
      case "high": return "bg-red-100 text-red-800 border-red-200";
      case "medium": return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "low": return "bg-green-100 text-green-800 border-green-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  // Helper function to get trend icon and color
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case "up": return <TrendingUp className="w-4 h-4 text-green-600" />;
      case "down": return <TrendingDown className="w-4 h-4 text-red-600" />;
      case "stable": return <Activity className="w-4 h-4 text-blue-600" />;
      default: return <Activity className="w-4 h-4 text-gray-600" />;
    }
  };

  // Helper function to get connection type color
  const getConnectionColor = (type: string) => {
    switch (type) {
      case "direct": return "bg-green-100 text-green-800 border-green-200";
      case "indirect": return "bg-blue-100 text-blue-800 border-blue-200";
      case "potential": return "bg-purple-100 text-purple-800 border-purple-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  // Helper function to get sentiment color
  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive": return "bg-green-100 text-green-800 border-green-200";
      case "negative": return "bg-red-100 text-red-800 border-red-200";
      case "neutral": return "bg-gray-100 text-gray-800 border-gray-200";
      default: return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  useEffect(() => {
    const initializeData = async () => {
      // Clear any previous errors when loading new company data
      setInsightError(null);
      setGrowthError(null);
      setCompetitorError(null);
      setNoReviewsFound(false);
      setNoReviewsMessage('');
      
      try {
        // First, fetch draft/leads data to populate sessionStorage
        const fetchDraftLeads = async () => {
          try {
            const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL || 'http://localhost:5000';
            const response = await fetch(`${DATABASE_URL}/leads/drafts`, {
              method: "GET",
              credentials: "include",
            });
            
            if (response.ok) {
              const data = await response.json();
              console.log('Fetched draft/leads data:', data);
              
              // Store the draft data in session storage so it can be accessed by company data transformation
              if (data && data.length > 0) {
                // Find the draft data for the current lead
                const currentDraft = data.find((draft: any) => 
                  draft.draft_data && 
                  (draft.draft_data.lead_id === leadId || draft.draft_data.id === leadId)
                );
                
                if (currentDraft && currentDraft.draft_data) {
                  console.log('Found matching draft data for current lead:', currentDraft.draft_data);
                  // Store in session storage so it can be accessed by fetchCompanyData
                  sessionStorage.setItem('currentDraftData', JSON.stringify(currentDraft.draft_data));
                  console.log('✅ Stored currentDraftData in sessionStorage');
                }
              }
            }
          } catch (error) {
            console.error('Error fetching draft/leads:', error);
          }
        };
        
        // Wait for draft data to be fetched and stored first
        await fetchDraftLeads();
        
        // Small delay to ensure sessionStorage is fully updated
        await new Promise(resolve => setTimeout(resolve, 50));
        
        // Fetch all existing company insights data IMMEDIATELY after draft data
        setIsLoadingExistingInsights(true);
        try {
          const insightsResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/all/${leadId}`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
          });
          
          if (insightsResponse.ok) {
            const insightsData = await insightsResponse.json();
            console.log('Fetched existing company insights:', insightsData);
            
            if (insightsData.success && insightsData.data) {
              const data = insightsData.data;
              
              // Load AI insights if available
              if (data.ai_insights && data.ai_insights.ai_analysis) {
                console.log('Loading existing AI insights from stored data:', data.ai_insights.ai_analysis);
                const aiAnalysis = data.ai_insights.ai_analysis;
                setAiAnalysisData(aiAnalysis);
                
                // Use unified function to transform AI analysis to insights
                const newInsights = transformAiAnalysisToInsights(aiAnalysis, data.created_at || new Date().toISOString());
                setInsights(newInsights);
              }
              
              // Load competitors if available
              if (data.competitors && data.competitors.competitors) {
                console.log('Loading existing competitors from stored data:', data.competitors.competitors);
                const transformedCompetitors: Competitor[] = data.competitors.competitors.map((comp: any, index: number) => ({
                  id: comp.id || `competitor-${index}`,
                  name: comp.company_name,
                  city: comp.city,
                  employees: comp.number_of_employees,
                  revenue: comp.revenue,
                  similarityScore: comp.similarity_score,
                  threatLevel: comp.similarity_score > 0.7 ? 'high' : comp.similarity_score > 0.4 ? 'medium' : 'low',
                  lastUpdated: data.updated_at || new Date().toISOString()
                }));
                setCompetitors(transformedCompetitors);
                if (data.competitors.metadata) {
                  setCompetitorMetadata(data.competitors.metadata);
                }
              }
              
              // Load growth trends if available
              if (data.growth_trends) {
                console.log('Loading existing growth trends from stored data:', data.growth_trends);
                // Store the detailed growth trends data for popup
                setGrowthTrendsData(data.growth_trends);
                const newGrowthTrends: GrowthTrend[] = [
                  {
                    id: 'growth-trend',
                    metric: 'Growth Trend Analysis',
                    currentValue: data.growth_trends.growth_trend || 'Stable',
                    previousValue: 'N/A',
                    change: data.growth_trends.growth_trend_score || 0,
                    trend: data.growth_trends.growth_trend === 'Accelerating' ? 'up' : 
                           data.growth_trends.growth_trend === 'Declining' ? 'down' : 'stable',
                    period: 'Recent',
                    description: `${data.growth_trends.company_name || 'Unknown Company'} • ${data.growth_trends.current_growth_stage || 'Unknown'} Stage • ${data.growth_trends.recommendation || 'Moderate'} Potential`
                  }
                ];
                setGrowthTrends(newGrowthTrends);
              }
              
              // Load reviews if available
              if (data.reviews && data.reviews.reviews) {
                console.log('Loading existing reviews from stored data:', data.reviews.reviews);
                const newReviews: Review[] = data.reviews.reviews.map((review: any, index: number) => ({
                  id: review.id || `review-${index}`,
                  source: review.source || 'Unknown',
                  rating: review.rating || 4.0,
                  reviewText: review.review_text || 'Review text not available',
                  reviewer: 'Anonymous',
                  date: data.updated_at || new Date().toISOString(),
                  sentiment: review.rating > 4 ? 'positive' : review.rating < 3 ? 'negative' : 'neutral',
                  verified: false
                }));
                setReviews(newReviews);
              }
              
              // Load map locations if available
              if (data.maps && data.maps.maps_url) {
                console.log('Loading existing map data from insights:', data.maps);
                
                // Extract coordinates from Google Maps URL
                let latitude = 37.7749; // Default to SF
                let longitude = -122.4194;
                
                if (data.maps.maps_url) {
                  console.log('Attempting to extract coordinates from URL:', data.maps.maps_url);
                  // Extract coordinates from Google Maps URL
                  // Format: ...!3d37.7463078!4d-122.3922697!...
                  const latMatch = data.maps.maps_url.match(/!3d([\d.-]+)/);
                  const lngMatch = data.maps.maps_url.match(/!4d([\d.-]+)/);
                  
                  console.log('Coordinate matches:', { latMatch, lngMatch });
                  
                  if (latMatch && lngMatch) {
                    latitude = parseFloat(latMatch[1]);
                    longitude = parseFloat(lngMatch[1]);
                    console.log('Extracted coordinates:', { latitude, longitude });
                  } else {
                    console.log('Failed to extract coordinates, using defaults:', { latitude, longitude });
                  }
                }
                
                const newMapLocations: MapLocation[] = [
                  {
                    id: 'map-location',
                    name: data.maps.name || 'Company Location',
                    address: 'Address not available',
                    latitude: latitude,
                    longitude: longitude,
                    mapsUrl: data.maps.maps_url
                  }
                ];
                
                console.log('Created map locations:', newMapLocations);
                setMapLocations(newMapLocations);
              }
              
              console.log('Successfully loaded existing company insights data');
            }
          } else if (insightsResponse.status === 404) {
            console.log('No existing company insights data found for this lead');
          } else {
            console.warn('Failed to fetch company insights:', insightsResponse.status);
          }
        } catch (error) {
          console.warn('Error fetching existing company insights:', error);
        } finally {
          setIsLoadingExistingInsights(false);
        }
        
        // Now fetch company data (which will use the draft data we just stored)
        await fetchCompanyData();
        
        // Fetch Growjo data to get company_id (this will also update growjoCompany state)
                await fetchGrowjoCompanyData();
        
        try {
          const insightsResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/all/${leadId}`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
          });
          
          if (insightsResponse.ok) {
            const insightsData = await insightsResponse.json();
            console.log('Fetched existing company insights:', insightsData);
            
            if (insightsData.success && insightsData.data) {
              const data = insightsData.data;
              
              // Load AI insights if available
              if (data.ai_insights && data.ai_insights.ai_analysis) {
                console.log('Loading existing AI insights from stored data:', data.ai_insights.ai_analysis);
                const aiAnalysis = data.ai_insights.ai_analysis;
                setAiAnalysisData(aiAnalysis);
                
                // Use unified function to transform AI analysis to insights
                const newInsights = transformAiAnalysisToInsights(aiAnalysis, data.created_at || new Date().toISOString());
                setInsights(newInsights);
              }
              
              // Load competitors if available
              if (data.competitors && data.competitors.competitors) {
                console.log('Loading existing competitors from stored data:', data.competitors.competitors);
                const transformedCompetitors: Competitor[] = data.competitors.competitors.map((comp: any, index: number) => ({
                  id: comp.id || `competitor-${index}`,
                  name: comp.company_name,
                  city: comp.city,
                  employees: comp.number_of_employees,
                  revenue: comp.revenue,
                  similarityScore: comp.similarity_score,
                  threatLevel: comp.similarity_score > 0.7 ? 'high' : comp.similarity_score > 0.4 ? 'medium' : 'low',
                  lastUpdated: data.updated_at || new Date().toISOString()
                }));
                setCompetitors(transformedCompetitors);
                if (data.competitors.metadata) {
                  setCompetitorMetadata(data.competitors.metadata);
                }
              }
              
              // Load growth trends if available
              if (data.growth_trends) {
                console.log('Loading existing growth trends from stored data:', data.growth_trends);
                // Store the detailed growth trends data for popup
                setGrowthTrendsData(data.growth_trends);
                const newGrowthTrends: GrowthTrend[] = [
                  {
                    id: 'growth-trend',
                    metric: 'Growth Trend Analysis',
                    currentValue: data.growth_trends.growth_trend || 'Stable',
                    previousValue: 'N/A',
                    change: data.growth_trends.growth_trend_score || 0,
                    trend: data.growth_trends.growth_trend === 'Accelerating' ? 'up' : 
                           data.growth_trends.growth_trend === 'Declining' ? 'down' : 'stable',
                    period: 'Recent',
                    description: `${data.growth_trends.company_name || 'Unknown Company'} • ${data.growth_trends.current_growth_stage || 'Unknown'} Stage • ${data.growth_trends.recommendation || 'Moderate'} Potential`
                  }
                ];
                setGrowthTrends(newGrowthTrends);
              }
              
              // Load reviews if available
              if (data.reviews && data.reviews.reviews) {
                console.log('Loading existing reviews from stored data:', data.reviews.reviews);
                const newReviews: Review[] = data.reviews.reviews.map((review: any, index: number) => ({
                  id: review.id || `review-${index}`,
                  source: review.source || 'Unknown',
                  rating: review.rating || 4.0,
                  reviewText: review.text || 'Review text not available',
                  reviewer: 'Anonymous',
                  date: data.updated_at || new Date().toISOString(),
                  sentiment: review.rating > 4 ? 'positive' : review.rating < 3 ? 'negative' : 'neutral',
                  verified: false
                }));
                setReviews(newReviews);
              }
              
              // Load map locations if available
              if (data.maps && data.maps.maps_url && company) {
                console.log('Loading existing map data from insights:', data.maps);
                console.log('Company data for map:', {
                  company: company.company,
                  street: company.street,
                  city: company.city,
                  state: company.state
                });
                
                // Extract coordinates from Google Maps URL
                let latitude = 37.7749; // Default to SF
                let longitude = -122.4194;
                
                if (data.maps.maps_url) {
                  console.log('Attempting to extract coordinates from URL:', data.maps.maps_url);
                  // Extract coordinates from Google Maps URL
                  // Format: ...!3d37.7463078!4d-122.3922697!...
                  const latMatch = data.maps.maps_url.match(/!3d([\d.-]+)/);
                  const lngMatch = data.maps.maps_url.match(/!4d([\d.-]+)/);
                  
                  console.log('Coordinate matches:', { latMatch, lngMatch });
                  
                  if (latMatch && lngMatch) {
                    latitude = parseFloat(latMatch[1]);
                    longitude = parseFloat(lngMatch[1]);
                    console.log('Extracted coordinates:', { latitude, longitude });
                  } else {
                    console.log('Failed to extract coordinates, using defaults:', { latitude, longitude });
                  }
                }
                
                const newMapLocations: MapLocation[] = [
                  {
                    id: 'map-location',
                    name: data.maps.name || company.company || 'Company Location',
                    address: company.street && company.city && company.state ? 
                      `${company.street}, ${company.city}, ${company.state}` : 
                      `${company.city}, ${company.state}`,
                    latitude: latitude,
                    longitude: longitude,
                    phone: company.companyPhone,
                    website: company.website,
                    rating: 4.5,
                    businessType: company.industry,
                    mapsUrl: data.maps.maps_url
                  }
                ];
                
                console.log('Created map locations:', newMapLocations);
                console.log('Setting mapLocations state to:', newMapLocations);
                setMapLocations(newMapLocations);
                console.log('Map locations state should now be updated');
              }
              
              console.log('Successfully loaded existing company insights data');
              
              // Now fetch competitors with the company_id from Growjo data (only if we don't have existing data)
              if (!data.competitors || !data.competitors.competitors) {
                console.log('No existing competitors found, fetching fresh data...');
        try {
          await fetchCompetitors();
        } catch (error) {
          console.warn('Failed to fetch competitors during initialization:', error);
          // Don't fail the entire initialization if competitors fail
                }
              } else {
                console.log('Competitors already available from existing insights, skipping fetch');
        }
        
              // Fetch other data (only if we don't have existing data)
              if (!data.growth_trends) {
                console.log('No existing growth trends found, fetching fresh data...');
        fetchGrowthTrends();
              } else {
                console.log('Growth trends already available from existing insights, skipping fetch');
              }
              if (!data.reviews || !data.reviews.reviews) {
                console.log('No existing reviews found, fetching fresh data...');
        fetchReviews();
              } else {
                console.log('Reviews already available from existing insights, skipping fetch');
              }
              if (!data.maps || !data.maps.maps_url) {
                console.log('No existing map data found, fetching fresh map data...');
                fetchMapLocations();
                              } else {
                  console.log('Map data already available from existing insights, processing existing data...');
                  // Process existing map data instead of skipping
                  if (company) {
                    console.log('Processing existing map data:', data.maps);
                    
                    // Extract coordinates from Google Maps URL
                    let latitude = 37.7749; // Default to SF
                    let longitude = -122.4194;
                    
                    if (data.maps.maps_url) {
                      console.log('Attempting to extract coordinates from existing URL:', data.maps.maps_url);
                      // Extract coordinates from Google Maps URL
                      // Format: ...!3d29.7043056!4d-95.8387638!...
                      const latMatch = data.maps.maps_url.match(/!3d([\d.-]+)/);
                      const lngMatch = data.maps.maps_url.match(/!4d([\d.-]+)/);
                      
                      console.log('Coordinate matches from existing data:', { latMatch, lngMatch });
                      
                      if (latMatch && lngMatch) {
                        latitude = parseFloat(latMatch[1]);
                        longitude = parseFloat(lngMatch[1]);
                        console.log('Extracted coordinates from existing data:', { latitude, longitude });
                      } else {
                        console.log('Failed to extract coordinates from existing data, using defaults:', { latitude, longitude });
                      }
                    }
                    
                    const newMapLocations: MapLocation[] = [
                      {
                        id: 'map-location-existing',
                        name: data.maps.name || company.company || 'Company Location',
                        address: company.street && company.city && company.state ? 
                          `${company.street}, ${company.city}, ${company.state}` : 
                          `${company.city}, ${company.state}`,
                        latitude: latitude,
                        longitude: longitude,
                        phone: company.companyPhone,
                        website: company.website,
                        rating: 4.5,
                        businessType: company.industry,
                        mapsUrl: data.maps.maps_url
                      }
                    ];
                    
                    console.log('Created map locations from existing data:', newMapLocations);
                    setMapLocations(newMapLocations);
                  }
                }
              if (!data.social_media_pulse) {
                console.log('No existing social media pulse found, fetching fresh data...');
        fetchSocialMediaPulse();
              } else {
                console.log('Social media pulse already available from existing insights, skipping fetch');
              }
            }
          } else if (insightsResponse.status === 404) {
            console.log('No existing company insights data found for this lead');
            
            // If no existing insights, fetch all data fresh
            console.log('Fetching all data fresh since no existing insights found...');
            try {
              await fetchCompetitors();
            } catch (error) {
              console.warn('Failed to fetch competitors during initialization:', error);
            }
            fetchGrowthTrends();
            fetchReviews();
            fetchMapLocations();
            fetchSocialMediaPulse();
          } else {
            console.warn('Failed to fetch company insights:', insightsResponse.status);
            
            // If insights fetch failed, fetch all data fresh as fallback
            console.log('Fetching all data fresh as fallback...');
            try {
              await fetchCompetitors();
            } catch (error) {
              console.warn('Failed to fetch competitors during initialization:', error);
            }
            fetchGrowthTrends();
            fetchReviews();
            fetchMapLocations();
            fetchSocialMediaPulse();
          }
        } catch (error) {
          console.warn('Error fetching existing company insights:', error);
          
          // If insights fetch had an error, fetch all data fresh as fallback
          console.log('Fetching all data fresh as fallback due to error...');
          try {
            await fetchCompetitors();
          } catch (error) {
            console.warn('Failed to fetch competitors during initialization:', error);
          }
          fetchGrowthTrends();
          fetchReviews();
          fetchMapLocations();
          fetchSocialMediaPulse();
        } finally {
          setIsLoadingExistingInsights(false);
        }
      } catch (error) {
        console.error('Error in initializeData:', error);
      } finally {
        // Set page loading to false after all main API calls are complete
        setIsPageLoading(false);
      }
    };
    
    initializeData();
  }, [leadId]);

  // Cleanup effect to remove currentCompanyData when component unmounts
  useEffect(() => {
    return () => {
      // Clean up the currentCompanyData to prevent it from persisting between different companies
      sessionStorage.removeItem("currentCompanyData");
    };
  }, []);

  // Retry effect: if company data is still not available after initial load, retry fetching
  useEffect(() => {
    if (!isPageLoading && !company && !isLoading) {
      console.log('Company data not available after initial load, retrying...');
      // Wait a bit more for sessionStorage to be fully available
      const timer = setTimeout(() => {
        fetchCompanyData(0);
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, [isPageLoading, company, isLoading]);

  // Separate useEffect for map data to avoid dependency issues
  // Removed since map data is now handled in the main initialization logic

  // Clear errors when company changes
  useEffect(() => {
    if (company) {
      setInsightError(null);
      setGrowthError(null);
      setCompetitorError(null);
      setNoReviewsFound(false);
      setNoReviewsMessage('');
    }
  }, [company]);

  // Debug map locations state changes
  useEffect(() => {
    console.log('Map locations state changed:', mapLocations);
    console.log('Map locations length:', mapLocations.length);
    console.log('Map locations content:', mapLocations);
  }, [mapLocations]);

  // Trigger competitors fetch when growjoCompany is available
  useEffect(() => {
    if (growjoCompany && growjoCompany.company_id && company && !competitors.length) {
      console.log('Growjo company data available, fetching competitors');
      fetchCompetitors();
    }
  }, [growjoCompany, company, competitors.length]);

  useEffect(() => {
    checkScrollPosition();
    if (scrollContainerRef.current) {
      scrollContainerRef.current.addEventListener('scroll', checkScrollPosition);
      return () => {
        if (scrollContainerRef.current) {
          scrollContainerRef.current.removeEventListener('scroll', checkScrollPosition);
        }
      };
    }
  }, [company]);



  // Show unified loading screen until all main API calls are complete
  if (isPageLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm z-50 flex items-center justify-center pointer-events-none">
        <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-yellow-400"></div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-8"></div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
          <div className="h-96 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (!company) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Company Not Found</h1>
          <p className="text-gray-600 mb-6">The requested company could not be found.</p>
          <Button onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Button 
          onClick={() => router.back()}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Companies
        </Button>
        <h1 className="text-3xl font-bold text-white">
          {company.company} Insights Board
        </h1>

      </div>

      {/* Company Description and People Cards */}
      <div className="space-y-6 mb-8">
        {/* Company Description Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-blue-600" />
              Company Description
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Left Column - All Company Information */}
              <div className="space-y-8 pt-4">
                {/* Company Details and Metrics in Double Column */}
                <div className="grid grid-cols-2 gap-8">
                  {/* Company Details */}
                  <div className="space-y-10">
                    <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Company Details</h4>
                    <div className="space-y-10">
                      <div className="flex items-center gap-3">
                        <Globe className="w-5 h-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-600">Website</span>
                          <div>
                            {company.website ? (
                              <a 
                                href={company.website} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:underline font-medium"
                              >
                                {company.website.replace(/^https?:\/\//, '')}
                              </a>
                            ) : (
                              <span className="text-gray-400 font-medium italic">N/A</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Building2 className="w-5 h-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-600">Industry</span>
                          <div className="text-gray-400 font-medium">
                            {company.industry || <span className="italic">N/A</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Target className="w-5 h-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-600">Product Category</span>
                          <div className="text-gray-400 font-medium">
                            {company.productCategory || <span className="italic">N/A</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Briefcase className="w-5 h-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-600">Business Type</span>
                          <div className="text-gray-400 font-medium">
                            {company.businessType || <span className="italic">N/A</span>}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Company Metrics */}
                  <div className="space-y-10">
                    <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Company Metrics</h4>
                    <div className="space-y-10">
                      <div className="flex items-center gap-3">
                        <Users className="w-5 h-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-600">Employees</span>
                          <div className="text-gray-400 font-medium">
                            {company.employees || <span className="italic">N/A</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <TrendingUp className="w-5 h-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-600">Revenue</span>
                          <div className="text-gray-400 font-medium">
                            {company.revenue && typeof company.revenue === 'number' ? `$${(company.revenue / 1000000).toFixed(1)}M` : <span className="italic">N/A</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Calendar className="w-5 h-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-600">Founded</span>
                          <div className="text-gray-400 font-medium">
                            {company.yearFounded || <span className="italic">N/A</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Star className="w-5 h-5 text-gray-500" />
                        <div>
                          <span className="text-sm font-medium text-gray-600">BBB Rating</span>
                          <div>
                            <Badge variant="secondary" className="text-sm px-3 py-1">
                              {company.bbbRating || <span className="italic">N/A</span>}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>


              </div>
              
              {/* Right Column - Map Component */}
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <MapPin className="w-5 h-5 text-gray-500" />
                  <div>
                    <span className="text-sm font-medium text-gray-600">Location</span>
                    <div className="text-white font-medium">
                      {company.city}, {company.state}
                    </div>
                  </div>
                </div>
                
                {/* Map Component */}
                <div className="h-80 rounded-lg overflow-hidden border">
                  {isMapLoading ? (
                    <div className="h-full bg-gray-100 rounded-lg flex items-center justify-center">
                      <div className="text-center">
                        <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-blue-600" />
                        <p className="text-gray-600 text-sm">Loading map...</p>
                      </div>
                    </div>
                  ) : mapLocations.length > 0 ? (
                    <div className="space-y-4">
                    <MapComponent locations={mapLocations} />
                      
                      {/* Map Link Section */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <MapPin className="w-4 h-4 text-gray-500" />
                          <span className="text-sm font-medium text-gray-600">Map Link:</span>
                          {mapLocations[0]?.mapsUrl ? (
                            <a 
                              href={mapLocations[0].mapsUrl} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline font-medium text-sm"
                            >
                              Open in Google Maps
                            </a>
                          ) : (
                            <span className="text-gray-400 font-medium text-sm italic">No map URL available</span>
                          )}
                        </div>
                        
                        {/* Reload Button */}
                        <Button 
                          onClick={fetchMapLocations}
                          disabled={isMapLoading}
                          size="sm"
                          variant="outline"
                          className="ml-auto"
                        >
                          <RefreshCw className={`w-3 h-3 mr-1 ${isMapLoading ? 'animate-spin' : ''}`} />
                          {isMapLoading ? 'Loading...' : 'Reload'}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="h-full bg-gray-100 rounded-lg flex items-center justify-center">
                      <div className="text-center">
                        <Map className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                        <p className="text-gray-600 text-sm">No map data</p>
                        <Button 
                          onClick={fetchMapLocations}
                          disabled={isMapLoading}
                          size="sm"
                          className="mt-2"
                        >
                          <RefreshCw className={`w-3 h-3 mr-1 ${isMapLoading ? 'animate-spin' : ''}`} />
                          {isMapLoading ? 'Loading...' : 'Load Map'}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Contact Information - Full Width Below Both Sections */}
            <Separator />
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Contact Information</h4>
              <div className="grid grid-cols-3 gap-6">
                <div className="flex items-center gap-3">
                  <Phone className="w-5 h-5 text-gray-500" />
                  <div>
                    <span className="text-sm font-medium text-gray-600">Phone</span>
                    <div className="text-gray-400 font-medium">
                      {company.companyPhone || <span className="italic">N/A</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Linkedin className="w-5 h-5 text-gray-500" />
                  <div>
                    <span className="text-sm font-medium text-gray-600">LinkedIn</span>
                    <div>
                      {company.companyLinkedin ? (
                        <a 
                          href={company.companyLinkedin} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline font-medium"
                        >
                          Company Profile
                        </a>
                      ) : (
                        <span className="text-gray-400 font-medium italic">N/A</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <MapPin className="w-5 h-5 text-gray-500" />
                  <div>
                    <span className="text-sm font-medium text-gray-600">Address</span>
                    <div className="text-gray-400 font-medium">
                      {company.street && company.city && company.state ? 
                        `${company.street}, ${company.city}, ${company.state}` : 
                        <span className="italic">N/A</span>
                      }
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </CardContent>
        </Card>

                {/* People Card */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5 text-green-600" />
                Connected People
              </CardTitle>
              <Button
                onClick={handleAddConnectedPeople}
                disabled={isGeneratingConnectedPeople}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isGeneratingConnectedPeople ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Adding...
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4 mr-2" />
                    Add Connected People
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="relative">
            {/* Scrollable Container */}
            <div 
              ref={scrollContainerRef}
              className="flex overflow-x-auto gap-4 pb-4 scroll-smooth hover:scrollbar-thin hover:scrollbar-track-gray-100 hover:scrollbar-thumb-purple-500"
              style={{ 
                scrollbarWidth: 'thin', 
                msOverflowStyle: 'auto',
                scrollbarColor: '#8B5CF6 #F3F4F6'
              }}
            >
                              {/* Render original company contacts (draft people) */}
                              {company.contacts.map((contact, index) => (
                  <div key={`contact-${index}`} className={`relative rounded-lg p-4 hover:shadow-md transition-shadow bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 p-[1px] ${
                    (company.contacts.length + connectedPeople.length) < 4 
                      ? 'flex-1 min-w-0' 
                      : 'flex-shrink-0 min-w-[320px] w-[320px]'
                  }`}>
                                      <div className="relative bg-white dark:bg-gray-900 rounded-lg p-4 w-full h-full">
                    <div className="flex items-start gap-3 mb-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                        <User className="w-6 h-6 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-gray-900 dark:text-white text-base mb-1">{contact.name || 'N/A'}</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">{contact.title || 'N/A'}</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 text-sm">
                        <Mail className="w-4 h-4 text-white flex-shrink-0" />
                        {contact.email ? (
                          <a 
                            href={`mailto:${contact.email}`}
                            className="text-blue-600 hover:underline truncate block"
                            title={contact.email}
                          >
                            {contact.email}
                          </a>
                        ) : (
                          <span className="text-white">N/A</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Phone className="w-4 h-4 text-white flex-shrink-0" />
                        <span className="text-white truncate">{contact.phone || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Linkedin className="w-4 h-4 text-white flex-shrink-0" />
                        {contact.linkedin && contact.linkedin !== '#' ? (
                          <a 
                            href={contact.linkedin} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            LinkedIn Profile
                          </a>
                        ) : (
                          <span className="text-white">N/A</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                              ))}
                              
                              {/* Render new connected people from API */}
                              {connectedPeople.map((person, index) => (
                  <div key={`connected-${person.id}`} className={`relative rounded-lg p-4 hover:shadow-md transition-shadow bg-gradient-to-r from-green-500 via-blue-500 to-purple-500 p-[1px] ${
                    (company.contacts.length + connectedPeople.length) < 4 
                      ? 'flex-1 min-w-0' 
                      : 'flex-shrink-0 min-w-[320px] w-[320px]'
                  }`}>
                                      <div className="relative bg-white dark:bg-gray-900 rounded-lg p-4 w-full h-full">
                    <div className="flex items-start gap-3 mb-4">
                      <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                        <UserPlus className="w-6 h-6 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-gray-900 dark:text-white text-base mb-1">{person.name || 'N/A'}</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-300">{person.title || 'N/A'}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{person.company || 'N/A'}</p>
                      </div>
                    </div>
                    <div className="space-y-3">
                      {person.notes && (
                        <div className="flex items-start gap-2 text-sm">
                          <Briefcase className="w-4 h-4 text-gray-500 flex-shrink-0 mt-0.5" />
                          <span className="text-gray-600 dark:text-gray-300 text-xs leading-relaxed">{person.notes}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-2 text-sm">
                        <Network className="w-4 h-4 text-gray-500 flex-shrink-0" />
                        <span className="text-gray-600 dark:text-gray-300 text-xs">
                          {person.connection || 'N/A'} • {person.mutualConnections || 0} mutual connections
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Calendar className="w-4 h-4 text-gray-500 flex-shrink-0" />
                        <span className="text-gray-600 dark:text-gray-300 text-xs">
                          Last interaction: {person.lastInteraction || 'N/A'}
                        </span>
                      </div>
                      {person.linkedinUrl && person.linkedinUrl !== '#' && (
                        <div className="flex items-center gap-2 text-sm">
                          <Linkedin className="w-4 h-4 text-gray-500 flex-shrink-0" />
                          <a 
                            href={person.linkedinUrl} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline text-xs"
                          >
                            LinkedIn Profile
                          </a>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI-Generated Insights Tabs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-purple-600" />
              AI-Powered Insights Dashboard
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                                                   <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="insights" className="flex items-center gap-2">
                  AI Scorer
                </TabsTrigger>
                <TabsTrigger value="competitors" className="flex items-center gap-2">
                  Competitors
                </TabsTrigger>
                <TabsTrigger value="growth" className="flex items-center gap-2">
                  Growth Trends
                </TabsTrigger>
                <TabsTrigger value="reviews" className="flex items-center gap-2">
                  Reviews
                </TabsTrigger>

              </TabsList>

                         {/* AI Insights Tab */}
             <TabsContent value="insights" className="mt-6">
               <div className="space-y-6">
                 {/* Generate Button */}
                 <div className="flex items-center justify-between">
                   <div>
                     <h3 className="text-lg font-semibold text-white mb-2">AI-Powered Company Insights</h3>
                     <p className="text-sm text-gray-400">
                       Generate intelligent insights about this company using AI analysis
                     </p>
                   </div>
                   <Button
                     onClick={generateAIInsights}
                     disabled={isGeneratingInsights || !company}
                     className="bg-blue-600 hover:bg-blue-700"
                   >
                     {isGeneratingInsights ? (
                       <>
                         <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                         Generating...
                       </>
                     ) : (
                       <>
                         <Lightbulb className="w-4 h-4 mr-2" />
                         Generate AI Insights
                       </>
                     )}
                   </Button>
                 </div>

                 {/* Insights Display */}
                 {insightError ? (
                   <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6 mb-6 text-center">
                     <div className="flex items-center justify-center gap-3 mb-3">
                       <AlertTriangle className="w-6 h-6 text-red-400" />
                       <h3 className="text-lg font-semibold text-red-400">AI Insights Generation Failed</h3>
                     </div>
                     <p className="text-red-300 mb-4">Sorry, we are not able to generate the AI insights as the company data is not found in our sources</p>
                     <div className="flex justify-center">
                       <Button
                         variant="outline"
                         onClick={() => setInsightError(null)}
                         className="border-red-500 text-red-400 hover:bg-red-500/10"
                       >
                         Dismiss
                       </Button>
                     </div>
                   </div>
                 ) : insights.length === 0 ? (
                   <div className="text-center py-12">
                     <Lightbulb className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                     <h3 className="text-lg font-medium text-gray-300 mb-2">No Insights Generated Yet</h3>
                     <p className="text-gray-500">
                       Click the "Generate AI Insights" button to get started with AI-powered company analysis.
                     </p>
                   </div>
                 ) : (
                   <div className="space-y-6">
                     {insights.map((insight) => (
                       <Card 
                         key={insight.id} 
                         className={`hover:shadow-lg transition-shadow cursor-pointer hover:scale-105 transform transition-transform ${
                           insight.id === 'ai-overall' ? 'w-full' : 'w-full'
                         }`}
                         onClick={() => handleInsightClick(insight)}
                       >
                         <CardHeader className="pb-3">
                           <div className="flex items-center justify-between">
                             <div className="flex items-center gap-2">
                               <div className="text-blue-600">
                                 {getInsightIcon(insight.type)}
                               </div>
                               <Badge variant="outline" className={getImpactColor(insight.impact)}>
                                 {insight.impact} impact
                               </Badge>
                             </div>
                             <div className="flex items-center gap-1">
                               <Star className="w-4 h-4 text-yellow-500 fill-current" />
                               <span className="text-sm font-medium">{Math.round(insight.confidence * 100)}%</span>
                             </div>
                           </div>
                           <CardTitle className="text-lg">{insight.title}</CardTitle>
                         </CardHeader>
                         <CardContent>
                           <div className="text-white text-sm leading-relaxed mb-4">
                             {insight.description?.split('\n').map((line, index) => (
                               <div key={index} className={line.startsWith('•') ? 'ml-2' : ''}>
                                 {line}
                               </div>
                             ))}
                           </div>
                           <div className="flex items-center justify-between text-xs text-gray-500">
                             <span className="capitalize">{insight.category}</span>
                             <span>{new Date(insight.createdAt).toLocaleDateString()}</span>
                           </div>
                           <div className="mt-3 text-xs text-blue-400 text-center">
                             Click to view full details
                           </div>
                         </CardContent>
                       </Card>
                     ))}
                   </div>
                 )}
               </div>
             </TabsContent>

            {/* Competitors Tab */}
            <TabsContent value="competitors" className="mt-6">
              <div className="space-y-6">
                {/* Generate Button */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Competitor Analysis</h3>
                    <p className="text-sm text-gray-400">
                      Generate competitor insights using AI-powered analysis
                    </p>
                  </div>
                  <Button
                    onClick={async () => {
                      if (!company) {
                        showNotification('Company data not available', 'error');
                        return;
                      }
                      
                      setIsLoadingCompetitors(true);
                      setCompetitorError(null); // Clear any previous errors
                      try {
                        // First, get the company_id from Growjo data
                        let companyId = null;
                        if (growjoCompany && growjoCompany.company_id) {
                          companyId = growjoCompany.company_id;
                        } else {
                          // If we don't have Growjo data, try to fetch it first
                          const growjoData = await fetchGrowjoCompanyData();
                          if (growjoData && growjoData.company_id) {
                            companyId = growjoData.company_id;
                          }
                        }
                        
                        if (!companyId) {
                          setCompetitorError('Company ID not found. Please ensure company data is loaded.');
                          setCompetitors([]);
                          return;
                        }
                        
                        // Prepare the payload for the competitors API with company_id
                        const payload = {
                          target_company_id: companyId,
                          range: 10,
                          top_n: 10
                        };
                        
                        console.log('Calling competitors API with payload:', payload);
                        
                        const response = await fetch(`${process.env.NEXT_PUBLIC_COMPANYINSIGHTS_API_URL}/get-competitors`, {
                          method: 'POST',
                          headers: {
                            'Content-Type': 'application/json',
                          },
                          body: JSON.stringify(payload)
                        });
                        
                        if (response.ok) {
                          const data = await response.json();
                          console.log('Competitors API response:', data);
                          
                          if (data.competitors && Array.isArray(data.competitors)) {
                            // Transform the API response to match our Competitor interface
                            const transformedCompetitors = data.competitors.map((competitor: any) => ({
                              id: competitor.id || competitor.company_id || Math.random().toString(),
                              name: competitor.company_name || 'Unknown Company',
                              city: competitor.city || 'Unknown',
                              employees: competitor.number_of_employees || 0,
                              revenue: competitor.revenue || 'Unknown',
                              similarityScore: competitor.similarity_score || 0,
                              threatLevel: competitor.similarity_score > 0.7 ? "high" : 
                                          competitor.similarity_score > 0.5 ? "medium" : "low",
                              lastUpdated: data.generated_at || new Date().toISOString()
                            }));
                            
                            setCompetitors(transformedCompetitors);
                            // Store metadata if available
                            if (data.metadata) {
                              setCompetitorMetadata(data.metadata);
                            }
                            // Store competitors data
          try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/competitors`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              credentials: 'include',
              body: JSON.stringify({
                lead_id: leadId,
                data: {
                  competitors: transformedCompetitors.map((comp: Competitor) => ({
                    city: comp.city,
                    company_name: comp.name,
                    number_of_employees: comp.employees,
                    revenue: comp.revenue,
                    similarity_score: comp.similarityScore
                  })),
                  generated_at: new Date().toISOString(),
                  metadata: competitorMetadata || {
                    processing_time: new Date().toISOString(),
                    search_range: 10,
                    total_companies_analyzed: transformedCompetitors.length
                  },
                  target_company: {
                    city: company.city,
                    name: company.company
                  }
                }
              })
            });

            if (!response.ok) {
              console.warn('Failed to store competitors data:', response.statusText);
            } else {
              console.log('Competitors data stored successfully');
            }
          } catch (error) {
            console.warn('Error storing competitors data:', error);
          }
          
                            showNotification(`Found ${transformedCompetitors.length} competitors!`, 'success');
                          } else {
                            console.log('No competitors data in API response');
                            setCompetitors([]);
                            setCompetitorError('No competitors found for this company in the current location.');
                          }
                        } else if (response.status === 404) {
                          const errorData = await response.json();
                          console.error('API 404 Error:', errorData);
                          setCompetitorError(errorData.error || 'No companies found in this location with the specified industry code.');
                          setCompetitors([]);
                        } else {
                          const errorText = await response.text();
                          console.error('API Error response:', errorText);
                          setCompetitorError(`API Error: ${response.status} - ${errorText}`);
                          setCompetitors([]);
                        }
                      } catch (error) {
                        console.error('Error fetching competitors:', error);
                        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
                        setCompetitorError(`Failed to fetch competitors: ${errorMessage}`);
                        setCompetitors([]);
                      } finally {
                        setIsLoadingCompetitors(false);
                      }
                    }}
                    disabled={isLoadingCompetitors || !company}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    {isLoadingCompetitors ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Generating...
                      </>
                    ) : (
                      <>
                        <Target className="w-4 h-4 mr-2" />
                        Generate Competitors
                      </>
                    )}
                  </Button>
                </div>

                {/* Competitors Display */}
                {isLoadingCompetitors ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
                    <h3 className="text-lg font-medium text-gray-300 mb-2">Analyzing Competitors...</h3>
                    <p className="text-gray-500">
                      Please wait while we analyze the competitive landscape using AI.
                    </p>
                  </div>
                ) : competitorError ? (
                   <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6 mb-6 text-center">
                     <div className="flex items-center justify-center gap-3 mb-3">
                      <AlertTriangle className="w-6 h-6 text-red-400" />
                       <h3 className="text-lg font-semibold text-red-400">Competitor Analysis Failed</h3>
                    </div>
                      <p className="text-red-300 mb-4">Sorry, we are not able to generate the competitors as they are not found in our sources</p>
                      <div className="flex justify-center">
                      <Button
                        variant="outline"
                        onClick={() => setCompetitorError(null)}
                        className="border-red-500 text-red-400 hover:bg-red-500/10"
                      >
                        Dismiss
                      </Button>
                    </div>
                  </div>
                ) : competitors.length === 0 ? (
                                    <div className="text-center py-12">
                    <Target className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-300 mb-2">No Competitors Generated Yet</h3>
                    <p className="text-gray-500">
                      Click the "Generate Competitors" button to analyze the competitive landscape.
                    </p>
                  </div>
                ) : (
                  <>
                    {/* Analysis Metadata */}
                    <div className="bg-gray-900/20 border border-gray-500/30 rounded-lg p-4 mb-6">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <BarChart3 className="w-5 h-5 text-blue-400" />
                          <h4 className="text-sm font-semibold text-blue-400">Analysis Summary</h4>
                        </div>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setCompetitors([]);
                            setCompetitorMetadata(null);
                            setCompetitorError(null);
                          }}
                          className="border-gray-500 text-gray-400 hover:bg-gray-500/10"
                        >
                          Clear
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-gray-400">Companies Analyzed:</span>
                          <div className="text-white font-medium">
                            {competitorMetadata?.total_companies_analyzed || competitors.length}
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-400">SIC Code:</span>
                          <div className="text-white font-medium">
                            {competitorMetadata?.SIC_Code || company.industry || 'N/A'}
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-400">Search Range:</span>
                          <div className="text-white font-medium">
                            {competitorMetadata?.search_range || 10} miles
                          </div>
                        </div>
                        <div>
                          <span className="text-gray-400">Analysis Date:</span>
                          <div className="text-white font-medium">
                            {new Date().toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Competitors Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {competitors.map((competitor) => (
                      <Card key={competitor.id} className="hover:shadow-lg transition-shadow">
                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <Target className="w-5 h-5 text-red-600" />
                              <Badge variant="outline" className={getThreatLevelColor(competitor.threatLevel)}>
                                {competitor.threatLevel} threat
                              </Badge>
                            </div>
                            <span className="text-sm text-gray-500">
                              {Math.round(competitor.similarityScore * 100)}% similar
                            </span>
                          </div>
                          <CardTitle className="text-lg">{competitor.name}</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <div className="flex items-center gap-2 text-sm">
                            <MapPin className="w-4 h-4 text-gray-500" />
                            <span className="text-gray-600 dark:text-gray-300">
                              {competitor.city}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <span className="text-xs text-gray-500">Employees</span>
                              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                {competitor.employees.toLocaleString()}
                              </div>
                            </div>
                            <div>
                              <span className="text-xs text-gray-500">Revenue</span>
                              <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                {competitor.revenue}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-gray-500" />
                            <span className="text-sm text-gray-600 dark:text-gray-300">
                              Similarity Score: {Math.round(competitor.similarityScore * 100)}%
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            Updated: {new Date(competitor.lastUpdated).toLocaleDateString()}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </>)}
              </div>
            </TabsContent>

            {/* Growth Trends Tab */}
            <TabsContent value="growth" className="mt-6">
              <div className="space-y-6">
                {/* Generate Button */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Growth Trends Analysis</h3>
                    <p className="text-sm text-gray-400">
                      Generate growth trends and performance metrics using AI-powered analysis
                    </p>
                  </div>
                  <Button
                    onClick={async () => {
                      if (!company) {
                        showNotification('Company data not available', 'error');
                        return;
                      }
                      
                      setIsGeneratingGrowthTrends(true);
                      setGrowthError(null); // Clear any previous errors
                      try {
                        // First, try to get company_id from Growjo if not already available
                        let companyId = growjoCompany?.company_id;
                        if (!companyId) {
                          console.log('No company_id available, fetching from Growjo...');
                          const growjoData = await fetchGrowjoCompanyData();
                          companyId = growjoData?.company_id || null;
                          console.log('Retrieved company_id from Growjo:', companyId);
                        }

                        // Call the growth trends API
                        const response = await fetch(`${process.env.NEXT_PUBLIC_COMPANYINSIGHTS_API_URL}/get-growth-trends`, {
                          method: 'POST',
                          headers: {
                            'Content-Type': 'application/json',
                          },
                          body: JSON.stringify({
                            results: [{
                              company: company.company,
                              company_id: companyId,
                              industry: company.industry,
                              employees: company.employees,
                              revenue: company.revenue,
                              year_founded: company.yearFounded,
                              website: company.website,
                              city: company.city,
                              state: company.state
                            }]
                          })
                        });

                        if (!response.ok) {
                          const errorData = await response.json().catch(() => ({}));
                          throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
                        }

                        const data = await response.json();
                        console.log('Growth trends API response:', data);

                        // Store the detailed growth trends data for popup
                        setGrowthTrendsData(data);

                        // Handle single growth trend object response
                        if (data.growth_trend || data.company_name) {
                          // Transform the single growth trend response to match our GrowthTrend interface
                          const newGrowthTrends: GrowthTrend[] = [{
                            id: 'growth-trend',
                            metric: 'Growth Trend Analysis',
                            currentValue: data.growth_trend || 'Stable',
                            previousValue: 'N/A',
                            change: data.growth_trend_score || 0,
                            trend: data.growth_trend === 'Accelerating' ? 'up' : 
                                   data.growth_trend === 'Declining' ? 'down' : 'stable',
                            period: 'Recent',
                            description: `${data.company_name || 'Unknown Company'} • ${data.current_growth_stage || 'Unknown'} Stage • ${data.recommendation || 'Moderate'} Potential`
                          }];
                          
                          setGrowthTrends(newGrowthTrends);
                          
                          // Store growth trends data
                          console.log('Attempting to store growth trends data...');
                          console.log('Storage URL:', `${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/growth-trends`);
                          try {
                            const response = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/growth-trends`, {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json',
                              },
                              credentials: 'include',
                              body: JSON.stringify({
                                lead_id: leadId,
                                data: {
                                  company_name: company.company,
                                  current_growth_stage: "Growth",
                                  data_confidence: {
                                    level: "Moderate",
                                    missing: ["Exact revenue growth trends", "Customer acquisition metrics"]
                                  },
                                  growth_drivers: ["AI-powered analysis", "Industry trend analysis"],
                                  growth_inhibitors: ["Limited historical data", "Market volatility"],
                                  growth_trend: "Stable",
                                  growth_trend_score: 60,
                                  maturity_index: 50,
                                  recommendation: "Moderate Growth Potential",
                                  scalability_assessment: {
                                    level: "Medium",
                                    reasons: ["Industry analysis", "Market positioning"]
                                  },
                                  timeline_outlook: {
                                    medium_term: "Stable",
                                    short_term: "Gradual improvement"
                                  },
                                  trend_insights: newGrowthTrends.map(trend => trend.description)
                                }
                              })
                            });

                            if (!response.ok) {
                              console.warn('Failed to store growth trends data:', response.statusText);
                            } else {
                              console.log('Growth trends data stored successfully');
                            }
                          } catch (error) {
                            console.warn('Error storing growth trends data:', error);
                          }
                          
                          showNotification(`Generated ${newGrowthTrends.length} growth trends!`, 'success');
                        } else if (data.insights && Array.isArray(data.insights)) {
                          // Alternative response format
                          const newGrowthTrends: GrowthTrend[] = data.insights.map((insight: any, index: number) => ({
                            id: insight.id || `insight-${index}`,
                            metric: insight.metric || insight.name || 'Growth Metric',
                            currentValue: insight.current_value || insight.current || 'N/A',
                            previousValue: insight.previous_value || insight.previous || 'N/A',
                            change: insight.change_percentage || insight.change || 0,
                            trend: insight.direction === 'up' ? 'up' : 
                                   insight.direction === 'down' ? 'down' : 'stable',
                            period: insight.period || insight.timeframe || 'Recent',
                            description: insight.description || insight.insight || 'Growth trend analysis'
                          }));
                          
                          setGrowthTrends(newGrowthTrends);
                          
                          // Store growth trends data (alternative format)
                          console.log('Attempting to store growth trends data (alternative format)...');
                          try {
                            const response = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/growth-trends`, {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json',
                              },
                              credentials: 'include',
                              body: JSON.stringify({
                                lead_id: leadId,
                                data: {
                                  company_name: company.company,
                                  current_growth_stage: "Growth",
                                  data_confidence: {
                                    level: "Moderate",
                                    missing: ["Exact revenue growth trends", "Customer acquisition metrics"]
                                  },
                                  growth_drivers: ["AI-powered analysis", "Industry trend analysis"],
                                  growth_inhibitors: ["Limited historical data", "Market volatility"],
                                  growth_trend: "Stable",
                                  growth_trend_score: 60,
                                  maturity_index: 50,
                                  recommendation: "Moderate Growth Potential",
                                  scalability_assessment: {
                                    level: "Medium",
                                    reasons: ["Industry analysis", "Market positioning"]
                                  },
                                  timeline_outlook: {
                                    medium_term: "Stable",
                                    short_term: "Gradual improvement"
                                  },
                                  trend_insights: newGrowthTrends.map(trend => trend.description)
                                }
                              })
                            });

                            if (!response.ok) {
                              console.warn('Failed to store growth trends data:', response.statusText);
                            } else {
                              console.log('Growth trends data stored successfully');
                            }
                          } catch (error) {
                            console.warn('Error storing growth trends data:', error);
                          }
                          
                          showNotification(`Generated ${newGrowthTrends.length} growth trends!`, 'success');
                        } else {
                          // Fallback to mock data if API response format is unexpected
                          console.warn('Unexpected API response format, using fallback data');
                          const fallbackTrends: GrowthTrend[] = [
                            {
                              id: "1",
                              metric: "Revenue Growth",
                              currentValue: company.revenue || "$8.2M",
                              previousValue: company.revenue ? `$${Math.round(parseFloat(company.revenue.replace(/[^0-9.]/g, '')) * 0.85)}M` : "$6.8M",
                              change: 20.6,
                              trend: "up",
                              period: "Q3 2023",
                              description: "Strong performance in enterprise software sales and market expansion"
                            },
                            {
                              id: "2",
                              metric: "Employee Growth",
                              currentValue: company.employees || "78",
                              previousValue: company.employees ? Math.round(parseInt(company.employees) * 0.83).toString() : "65",
                              change: 20.0,
                              trend: "up",
                              period: "Q3 2023",
                              description: "Strategic hiring in engineering, sales, and customer success teams"
                            }
                          ];
                          
                          setGrowthTrends(fallbackTrends);
                          
                          // Store fallback growth trends data
                          console.log('Attempting to store fallback growth trends data...');
                          try {
                            const response = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/company-insights/growth-trends`, {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json',
                              },
                              credentials: 'include',
                              body: JSON.stringify({
                                lead_id: leadId,
                                data: {
                                  company_name: company.company,
                                  current_growth_stage: "Growth",
                                  data_confidence: {
                                    level: "Low",
                                    missing: ["Exact revenue growth trends", "Customer acquisition metrics", "Historical performance data"]
                                  },
                                  growth_drivers: ["Industry analysis", "Market positioning"],
                                  growth_inhibitors: ["Limited historical data", "Market volatility"],
                                  growth_trend: "Stable",
                                  growth_trend_score: 50,
                                  maturity_index: 40,
                                  recommendation: "Moderate Growth Potential",
                                  scalability_assessment: {
                                    level: "Medium",
                                    reasons: ["Industry analysis", "Market positioning"]
                                  },
                                  timeline_outlook: {
                                    medium_term: "Stable",
                                    short_term: "Gradual improvement"
                                  },
                                  trend_insights: fallbackTrends.map(trend => trend.description)
                                }
                              })
                            });

                            if (!response.ok) {
                              console.warn('Failed to store fallback growth trends data:', response.statusText);
                            } else {
                              console.log('Fallback growth trends data stored successfully');
                            }
                          } catch (error) {
                            console.warn('Error storing fallback growth trends data:', error);
                          }
                          
                          showNotification('Using fallback growth trends data', 'info');
                        }
                      } catch (error) {
                        console.error('Error generating growth trends:', error);
                        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
                        setGrowthError(`Failed to generate growth trends: ${errorMessage}`);
                        showNotification(`Failed to generate growth trends: ${errorMessage}`, 'error');
                        
                        // Set empty trends on error
                        setGrowthTrends([]);
                      } finally {
                        setIsGeneratingGrowthTrends(false);
                      }
                    }}
                    disabled={isGeneratingGrowthTrends || !company}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    {isGeneratingGrowthTrends ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Generating...
                      </>
                    ) : (
                      <>
                        <TrendingUp className="w-4 h-4 mr-2" />
                        Generate Growth Trends
                      </>
                    )}
                  </Button>
                </div>

                {/* Growth Trends Display */}
                {growthError ? (
                  <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6 mb-6 text-center">
                    <div className="flex items-center justify-center gap-3 mb-3">
                      <AlertTriangle className="w-6 h-6 text-red-400" />
                      <h3 className="text-lg font-semibold text-red-400">Growth Trends Generation Failed</h3>
                    </div>
                    <p className="text-red-300 mb-4">Sorry, we are not able to generate the growth trends as the company data is not found in our sources</p>
                    <div className="flex justify-center">
                      <Button
                        variant="outline"
                        onClick={() => setGrowthError(null)}
                        className="border-red-500 text-red-400 hover:bg-red-500/10"
                      >
                        Dismiss
                      </Button>
                    </div>
                  </div>
                ) : isGeneratingGrowthTrends ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto mb-4"></div>
                    <h3 className="text-lg font-medium text-gray-300 mb-2">Analyzing Growth Trends...</h3>
                    <p className="text-gray-500">
                      Please wait while we analyze the company's growth patterns and performance metrics.
                    </p>
                  </div>
                ) : growthTrends.length === 0 ? (
                  <div className="text-center py-12">
                    <TrendingUp className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-300 mb-2">No Growth Trends Generated Yet</h3>
                    <p className="text-gray-500">
                      Click the "Generate Growth Trends" button to analyze the company's performance metrics.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {growthTrends.map((trend) => (
                      <Card key={trend.id} className="hover:shadow-lg transition-shadow cursor-pointer hover:scale-105 transform transition-transform w-full" onClick={() => handleGrowthTrendClick(trend)}>
                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {getTrendIcon(trend.trend)}
                              <span className="text-sm text-gray-500">{trend.period}</span>
                            </div>
                            <Badge variant="outline" className={
                              trend.trend === "up" ? "bg-green-100 text-green-800 border-green-200" :
                              trend.trend === "down" ? "bg-red-100 text-red-800 border-red-200" :
                              "bg-blue-100 text-blue-800 border-blue-200"
                            }>
                              {trend.currentValue}
                            </Badge>
                          </div>
                          <CardTitle className="text-lg">{trend.metric}</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          <p className="text-sm text-white leading-relaxed">{trend.description}...</p>
                          <div className="mt-3 text-xs text-blue-400 text-center">
                            Click to view full details
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>



            {/* Reviews Tab */}
            <TabsContent value="reviews" className="mt-6">
              <div className="space-y-6">
                {/* Generate Button */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Customer Reviews Analysis</h3>
                    <p className="text-sm text-gray-400">
                      Generate customer reviews and sentiment analysis using AI-powered insights
                    </p>
                  </div>
                  <Button
                    onClick={handleGenerateReviews}
                    disabled={isGeneratingReviews || !company}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {isGeneratingReviews ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        {reviewStatus === 'starting' ? 'Starting...' : 
                         reviewStatus === 'processing' ? 'Processing...' : 'Generating...'}
                      </>
                    ) : (
                      <>
                        <MessageSquare className="w-4 h-4 mr-2" />
                        Generate Reviews
                      </>
                    )}
                  </Button>
                </div>

                                {/* Reviews Display */}
                {isGeneratingReviews || reviewStatus === 'processing' ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
                    <h3 className="text-lg font-medium text-gray-300 mb-2">
                      {reviewStatus === 'starting' ? 'Starting Review Generation...' : 
                       typeof reviewStatus === 'string' && reviewStatus.includes('Step') ? reviewStatus :
                       'Analyzing Customer Reviews...'}
                    </h3>
                    <p className="text-gray-500">
                      {reviewStatus === 'starting' ? 'Initializing the review analysis process...' :
                       typeof reviewStatus === 'string' && reviewStatus.includes('Step') ? 'Searching multiple sources for company reviews...' :
                       'Please wait while we analyze customer sentiment and generate review insights.'}
                    </p>
                    <div className="mt-4 p-3 bg-gray-800 rounded-lg">
                      <p className="text-xs text-gray-500">This process may take a few minutes...</p>
                    </div>
                  </div>
                                            ) : noReviewsFound ? (
              <>
                {/* Banner notice when no reviews are found */}
                {(noReviewsMessage === 'all_sources_failed' || noReviewsMessage === 'generation_failed') ? (
                  <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6 mb-6 text-center">
                    <div className="flex items-center justify-center gap-3 mb-3">
                       <AlertTriangle className="w-6 h-6 text-red-400" />
                      <h3 className="text-lg font-semibold text-red-400">Reviews Generation Failed</h3>
                     </div>
                    <p className="text-red-300 mb-4">Sorry, we are not able to generate the reviews as the company data is not found in our sources</p>
                    <div className="flex justify-center">
                       <Button
                         variant="outline"
                         onClick={() => setNoReviewsMessage('')}
                         className="border-red-500 text-red-400 hover:bg-red-500/10"
                       >
                         Dismiss
                       </Button>
                     </div>
                   </div>
                ) : (
                  <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6 mb-6 text-center">
                    <div className="flex items-center justify-center gap-3 mb-3">
                      <AlertTriangle className="w-6 h-6 text-red-400" />
                      <h3 className="text-lg font-semibold text-red-400">Reviews Generation Failed</h3>
                    </div>
                    <p className="text-red-300 mb-4">Sorry, we are not able to generate the reviews as the company data is not found in our sources</p>
                    <div className="flex justify-center">
                         <Button
                           variant="outline"
                           onClick={() => setNoReviewsMessage('')}
                           className="border-red-500 text-red-400 hover:bg-red-500/10"
                         >
                           Dismiss
                         </Button>
                       </div>
                  </div>
                )}
                    
                                       </>
                 ) : reviews.length === 0 && !noReviewsFound ? (
                   <div className="text-center py-12">
                     <MessageSquare className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                     <h3 className="text-lg font-medium text-gray-300 mb-2">No Reviews Generated Yet</h3>
                     <p className="text-gray-500">
                       Click the "Generate Reviews" button to analyze customer sentiment and reviews.
                     </p>
                   </div>
                ) : (
                  <>
                    {/* Reviews Summary Section */}
                    {reviewsSummary && (
                      <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 border border-purple-500/30 rounded-lg p-6 mb-6">
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <MessageSquare className="w-6 h-6 text-purple-400" />
                            <h4 className="text-lg font-semibold text-purple-400">AI-Generated Summary</h4>
                          </div>
                          {reviewsRating && (
                            <div className="flex items-center gap-2">
                              <Star className="w-5 h-5 text-yellow-500 fill-current" />
                              <span className="text-lg font-bold text-white">{reviewsRating}</span>
                              <span className="text-sm text-gray-400">/ 5.0</span>
                            </div>
                          )}
                        </div>
                        
                        <div className="mb-4">
                          <p className="text-white text-sm leading-relaxed">
                            {reviewsSummary}
                          </p>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 text-sm text-gray-400">
                            <span>Source: {reviewsSource}</span>
                            <span>•</span>
                            <span>{reviews.length} reviews analyzed</span>
                          </div>
                          
                          <Button
                            onClick={() => setShowReviewsModal(true)}
                            variant="outline"
                            className="border-purple-500 text-purple-400 hover:bg-purple-500/10"
                          >
                            <MessageSquare className="w-4 h-4 mr-2" />
                            Fetched Reviews
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </TabsContent>


               
          </Tabs>
        </CardContent>
      </Card>
      
      {/* Reviews Modal */}
      {showReviewsModal && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowReviewsModal(false)}
        >
          <div 
            className="bg-gray-900 border border-gray-700 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-6 border-b border-gray-700">
              <div className="flex items-center gap-3">
                <MessageSquare className="w-6 h-6 text-purple-400" />
                <h3 className="text-xl font-semibold text-white">Fetched Reviews</h3>
                {reviewsRating && (
                  <div className="flex items-center gap-2 ml-4">
                    <Star className="w-5 h-5 text-yellow-500 fill-current" />
                    <span className="text-lg font-bold text-white">{reviewsRating}</span>
                    <span className="text-sm text-gray-400">/ 5.0</span>
                  </div>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowReviewsModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {reviews.map((review) => (
                  <Card key={review.id} className="hover:shadow-lg transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="w-5 h-4 text-gray-600" />
                          <Badge variant="outline" className={getSentimentColor(review.sentiment)}>
                            {review.sentiment}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 text-yellow-500 fill-current" />
                          <span className="font-medium">{review.rating}</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">{review.source}</CardTitle>
                        {review.verified && (
                          <Badge variant="secondary" className="text-xs">
                            Verified
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-gray-600 text-sm leading-relaxed">
                        "{review.reviewText}"
                      </p>
                      <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>- {review.reviewer}</span>
                        <span>{review.date}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Insight Detail Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogOverlay className="z-[9998]" style={{ zIndex: 9998 }} />
        <DialogContent 
          className="max-w-2xl max-h-[80vh] overflow-y-auto z-[9999]" 
          style={{ zIndex: 9999 }}
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <div className="text-blue-600">
                {selectedInsight && getInsightIcon(selectedInsight.type)}
              </div>
              {selectedInsight?.title}
            </DialogTitle>
            <DialogDescription className="flex items-center gap-4 mt-2">
              <Badge variant="outline" className={selectedInsight ? getImpactColor(selectedInsight.impact) : ''}>
                {selectedInsight?.impact} impact
              </Badge>
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 text-yellow-500 fill-current" />
                <span className="text-sm font-medium">{selectedInsight ? Math.round(selectedInsight.confidence * 100) : 0}%</span>
              </div>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            {/* Show comprehensive AI analysis for ai-overall card */}
            {selectedInsight?.id === 'ai-overall' && aiAnalysisData ? (
              <div className="space-y-6">
                {/* Overall Assessment */}
                <div>
                  <h4 className="font-semibold text-white mb-3">Overall Assessment</h4>
                  <div className="bg-gray-800 p-4 rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Overall Score:</span>
                      <span className="text-lg font-bold text-white">{aiAnalysisData.overall_score || aiAnalysisData.total_score || 50}/100</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Investment Recommendation:</span>
                      <Badge variant={aiAnalysisData.investment_recommendation === 'Strong' ? 'default' : 
                                    aiAnalysisData.investment_recommendation === 'Moderate' ? 'secondary' : 'destructive'}>
                        {aiAnalysisData.investment_recommendation || 'Moderate'}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Risk Analysis */}
                {(aiAnalysisData.risk_reason || aiAnalysisData.risk?.explanation) && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Risk Analysis</h4>
                    <div className="bg-gray-800 p-4 rounded-lg space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Risk Score:</span>
                        <span className="text-sm font-medium text-white">{aiAnalysisData.risk_score || aiAnalysisData.risk?.score || 50}/100</span>
                      </div>
                      <p className="text-gray-300 text-sm leading-relaxed">
                        {aiAnalysisData.risk_reason || aiAnalysisData.risk?.explanation?.join('. ')}
                      </p>
                    </div>
                  </div>
                )}

                {/* Growth Potential */}
                {(aiAnalysisData.growth_reason || aiAnalysisData.growth_potential?.explanation) && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Growth Potential</h4>
                    <div className="bg-gray-800 p-4 rounded-lg space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Growth Score:</span>
                        <span className="text-sm font-medium text-white">{aiAnalysisData.growth_potential_score || aiAnalysisData.growth_potential?.score || 50}/100</span>
                      </div>
                      <p className="text-gray-300 text-sm leading-relaxed">
                        {aiAnalysisData.growth_reason || aiAnalysisData.growth_potential?.explanation?.join('. ')}
                      </p>
                    </div>
                  </div>
                )}

                {/* Keyword Analysis */}
                {(aiAnalysisData.keyword_reason || aiAnalysisData.keywords?.explanation) && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Keyword Analysis</h4>
                    <div className="bg-gray-800 p-4 rounded-lg space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Keyword Score:</span>
                        <span className="text-sm font-medium text-white">{aiAnalysisData.keyword_score || aiAnalysisData.keywords?.score || 0}/100</span>
                      </div>
                      <p className="text-gray-300 text-sm leading-relaxed">
                        {aiAnalysisData.keyword_reason || aiAnalysisData.keywords?.explanation?.join('. ')}
                      </p>
                    </div>
                  </div>
                )}

                {/* Key Strengths */}
                {aiAnalysisData.key_strengths && aiAnalysisData.key_strengths.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Key Strengths</h4>
                    <div className="bg-gray-800 p-4 rounded-lg">
                      <div className="space-y-2">
                        {aiAnalysisData.key_strengths.map((strength: string, index: number) => (
                          <div key={index} className="flex items-start gap-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                            <p className="text-gray-300 text-sm">{strength}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Key Concerns */}
                {aiAnalysisData.key_concerns && aiAnalysisData.key_concerns.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Key Concerns</h4>
                    <div className="bg-gray-800 p-4 rounded-lg">
                      <div className="space-y-2">
                        {aiAnalysisData.key_concerns.map((concern: string, index: number) => (
                          <div key={index} className="flex items-start gap-2">
                            <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                            <p className="text-gray-300 text-sm">{concern}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Default description for other insights */
              <div>
                <h4 className="font-semibold text-white mb-2">Description</h4>
                <div className="text-gray-300 text-sm leading-relaxed">
                  {selectedInsight?.description?.split('\n').map((line, index) => (
                    <div key={index} className={line.startsWith('•') ? 'ml-2' : ''}>
                      {line}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between text-sm text-gray-400 pt-4 border-t border-gray-600">
              <span className="capitalize">{selectedInsight?.category}</span>
              <span>{selectedInsight ? new Date(selectedInsight.createdAt).toLocaleDateString() : ''}</span>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Growth Trends Detail Dialog */}
      <Dialog open={isGrowthDialogOpen} onOpenChange={setIsGrowthDialogOpen}>
        <DialogOverlay className="z-[9998]" style={{ zIndex: 9998 }} />
        <DialogContent
          className="max-w-2xl max-h-[80vh] overflow-y-auto z-[9999]"
          style={{ zIndex: 9999 }}
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <div className="text-green-600">
                {selectedGrowthTrend && getTrendIcon(selectedGrowthTrend.trend)}
              </div>
              {selectedGrowthTrend?.metric}
            </DialogTitle>
            <DialogDescription className="flex items-center gap-4 mt-2">
              <Badge variant="outline" className={
                selectedGrowthTrend?.trend === "up" ? "bg-green-100 text-green-800 border-green-200" :
                selectedGrowthTrend?.trend === "down" ? "bg-red-100 text-red-800 border-red-200" :
                "bg-blue-100 text-blue-800 border-blue-200"
              }>
                {selectedGrowthTrend?.change && selectedGrowthTrend.change > 0 ? "+" : ""}{selectedGrowthTrend?.change?.toFixed(1)}%
              </Badge>
              <span className="text-sm text-gray-500">{selectedGrowthTrend?.period}</span>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            {/* Show comprehensive growth trends data */}
            {selectedGrowthTrend && growthTrendsData ? (
              <div className="space-y-6">
                {/* Company Overview */}
                <div>
                  <h4 className="font-semibold text-white mb-3">Company Overview</h4>
                  <div className="bg-gray-800 p-4 rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Company Name:</span>
                      <span className="text-sm font-medium text-white">{growthTrendsData.company_name || 'N/A'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Current Growth Stage:</span>
                      <Badge variant="outline" className="text-white border-gray-400">
                        {growthTrendsData.current_growth_stage || 'Unknown'}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Growth Trend:</span>
                      <Badge variant={growthTrendsData.growth_trend === 'Accelerating' ? 'default' :
                                    growthTrendsData.growth_trend === 'Declining' ? 'destructive' : 'secondary'}>
                        {growthTrendsData.growth_trend || 'Stable'}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Growth Trend Score:</span>
                      <span className="text-sm font-medium text-white">{growthTrendsData.growth_trend_score || 0}/100</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Maturity Index:</span>
                      <span className="text-sm font-medium text-white">{growthTrendsData.maturity_index || 0}/100</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-300">Recommendation:</span>
                      <Badge variant={growthTrendsData.recommendation === 'Strong Growth Potential' ? 'default' :
                                    growthTrendsData.recommendation === 'Limited Growth Potential' ? 'destructive' : 'secondary'}>
                        {growthTrendsData.recommendation || 'Moderate'}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Data Confidence */}
                {growthTrendsData.data_confidence && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Data Confidence</h4>
                    <div className="bg-gray-800 p-4 rounded-lg space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Confidence Level:</span>
                        <Badge variant={growthTrendsData.data_confidence.level === 'High' ? 'default' :
                                      growthTrendsData.data_confidence.level === 'Low' ? 'destructive' : 'secondary'}>
                          {growthTrendsData.data_confidence.level || 'Unknown'}
                        </Badge>
                      </div>
                      {growthTrendsData.data_confidence.missing && growthTrendsData.data_confidence.missing.length > 0 && (
                        <div>
                          <span className="text-sm text-gray-300 block mb-2">Missing Data:</span>
                          <div className="space-y-1">
                            {growthTrendsData.data_confidence.missing.map((item: string, index: number) => (
                              <div key={index} className="flex items-start gap-2">
                                <div className="w-2 h-2 bg-yellow-500 rounded-full mt-2 flex-shrink-0"></div>
                                <p className="text-gray-300 text-sm">{item}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Growth Drivers */}
                {growthTrendsData.growth_drivers && growthTrendsData.growth_drivers.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Growth Drivers</h4>
                    <div className="bg-gray-800 p-4 rounded-lg">
                      <div className="space-y-2">
                        {growthTrendsData.growth_drivers.map((driver: string, index: number) => (
                          <div key={index} className="flex items-start gap-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                            <p className="text-gray-300 text-sm">{driver}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Growth Inhibitors */}
                {growthTrendsData.growth_inhibitors && growthTrendsData.growth_inhibitors.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Growth Inhibitors</h4>
                    <div className="bg-gray-800 p-4 rounded-lg">
                      <div className="space-y-2">
                        {growthTrendsData.growth_inhibitors.map((inhibitor: string, index: number) => (
                          <div key={index} className="flex items-start gap-2">
                            <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                            <p className="text-gray-300 text-sm">{inhibitor}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Scalability Assessment */}
                {growthTrendsData.scalability_assessment && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Scalability Assessment</h4>
                    <div className="bg-gray-800 p-4 rounded-lg space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Scalability Level:</span>
                        <Badge variant={growthTrendsData.scalability_assessment.level === 'High' ? 'default' :
                                      growthTrendsData.scalability_assessment.level === 'Low' ? 'destructive' : 'secondary'}>
                          {growthTrendsData.scalability_assessment.level || 'Unknown'}
                        </Badge>
                      </div>
                      {growthTrendsData.scalability_assessment.reasons && growthTrendsData.scalability_assessment.reasons.length > 0 && (
                        <div>
                          <span className="text-sm text-gray-300 block mb-2">Reasons:</span>
                          <div className="space-y-1">
                            {growthTrendsData.scalability_assessment.reasons.map((reason: string, index: number) => (
                              <div key={index} className="flex items-start gap-2">
                                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                                <p className="text-gray-300 text-sm">{reason}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Timeline Outlook */}
                {growthTrendsData.timeline_outlook && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Timeline Outlook</h4>
                    <div className="bg-gray-800 p-4 rounded-lg space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Short Term:</span>
                        <Badge variant="outline" className="text-white border-gray-400">
                          {growthTrendsData.timeline_outlook.short_term || 'Unknown'}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Medium Term:</span>
                        <Badge variant="outline" className="text-white border-gray-400">
                          {growthTrendsData.timeline_outlook.medium_term || 'Unknown'}
                        </Badge>
                      </div>
                    </div>
                  </div>
                )}

                {/* Trend Insights */}
                {growthTrendsData.trend_insights && growthTrendsData.trend_insights.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-white mb-3">Trend Insights</h4>
                    <div className="bg-gray-800 p-4 rounded-lg">
                      <div className="space-y-2">
                        {growthTrendsData.trend_insights.map((insight: string, index: number) => (
                          <div key={index} className="flex items-start gap-2">
                            <div className="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></div>
                            <p className="text-gray-300 text-sm">{insight}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Default description for growth trends without detailed data */
              <div>
                <h4 className="font-semibold text-white mb-2">Description</h4>
                <div className="text-gray-300 text-sm leading-relaxed">
                  {selectedGrowthTrend?.description}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between text-sm text-gray-400 pt-4 border-t border-gray-600">
              <span>Growth Analysis</span>
              <span>{new Date().toLocaleDateString()}</span>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
