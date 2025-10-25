"use client"

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Download, Filter, X, ExternalLink } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import PopupBig from "@/components/ui/popup-big";
import FeedbackPopup from "@/components/FeedbackPopup";
import axios from "axios";
import { SortDropdown } from "@/components/ui/sort-dropdown";
import Notif from "@/components/ui/notif";
import ForwardDropdown from "@/components/ui/ForwardDropdown";
import { Eye, Globe, Linkedin, MapPin, Edit, Pencil, Mail, StickyNote, Star, Newspaper, RefreshCw, Save, BookOpen, MoreHorizontal, ChevronDown, Copy, Trash2, Shield, Info } from "lucide-react";
import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Search } from "lucide-react";
import { NotesPopup } from "@/components/NotesPopup";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Building2 } from "lucide-react";
import EnrichCompanies from "./EnrichCompanies";
import { NewTag } from "@/components/ui/new-tag";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;
const DATABASE_URL_NOAPI = DATABASE_URL?.replace(/\/api\/?$/, "");
const AI_NEWS_API_URL = process.env.NEXT_PUBLIC_AI_NEWS_API_URL;

// Helper to render *text* as italic in insights
function renderInsightWithItalics(insight) {
  const parts = insight.split(/(\*[^*]+\*)/g);
  return parts.map((part, idx) =>
    part.startsWith('*') && part.endsWith('*') ? (
      <em key={idx}>{part.slice(1, -1)}</em>
    ) : (
      <span key={idx}>{part}</span>
    )
  );
}

/**
 * Checks if a LinkedIn value indicates missing information and should be replaced with "N/A"
 * @param {string} linkedinValue - The LinkedIn URL or value to check
 * @returns {boolean} true if the value indicates missing information, false otherwise
 */
const isLinkedInMissing = (linkedinValue) => {
  if (!linkedinValue || linkedinValue.trim() === '') return true;
  
  const missingPatterns = [
    /linkedin\s*information\s*is\s*missing/i,
    /not\s*found/i,
    /not\s*provided/i,
    /n\/a/i,
    /none/i,
    /unknown/i,
    /missing/i,
    /unavailable/i,
    /no\s*linkedin/i,
    /linkedin\s*not\s*available/i,
    /linkedin\s*not\s*found/i,
    /linkedin\s*not\s*provided/i,
    /linkedin\s*missing/i,
    /linkedin\s*unavailable/i,
    /linkedin\s*information\s*not\s*found/i,
    /linkedin\s*information\s*not\s*provided/i,
    /linkedin\s*information\s*unavailable/i,
    /linkedin\s*information\s*missing/i,
    /linkedin\s*profile\s*not\s*found/i,
    /linkedin\s*profile\s*not\s*provided/i,
    /linkedin\s*profile\s*unavailable/i,
    /linkedin\s*profile\s*missing/i,
    /linkedin\s*profile\s*information\s*is\s*missing/i,
    /linkedin\s*profile\s*information\s*not\s*found/i,
    /linkedin\s*profile\s*information\s*not\s*provided/i,
    /linkedin\s*profile\s*information\s*unavailable/i,
    /linkedin\s*profile\s*not\s*available\./i,
    /couldn't\s*find\s*a\s*linkedin\s*link\./i,
    /couldn't\s*find\s*a\s*linkedin\s*link/i,
    /couldn't\s*find\s*linkedin\s*link/i,
    /couldn't\s*find\s*linkedin/i,
    /no\s*linkedin\s*link\s*found/i,
    /no\s*linkedin\s*link/i,
    /linkedin\s*link\s*not\s*found/i,
    /linkedin\s*link\s*not\s*available/i
  ];
  
  return missingPatterns.some(pattern => pattern.test(linkedinValue.trim()));
};

/**
 * Checks if a website value indicates missing information and should be replaced with "N/A"
 * @param {string} websiteValue - The website URL or value to check
 * @returns {boolean} true if the value indicates missing information, false otherwise
 */
const isWebsiteMissing = (websiteValue) => {
  if (!websiteValue || websiteValue.trim() === '') return true;
  
  const missingPatterns = [
    /not\s*found/i,
    /not\s*provided/i,
    /n\/a/i,
    /none/i,
    /unknown/i,
    /missing/i,
    /unavailable/i,
    /no\s*website/i,
    /website\s*not\s*available/i,
    /website\s*not\s*found/i,
    /website\s*not\s*provided/i,
    /website\s*missing/i,
    /website\s*unavailable/i,
    /website\s*information\s*not\s*found/i,
    /website\s*information\s*not\s*provided/i,
    /website\s*information\s*unavailable/i,
    /website\s*information\s*missing/i,
    /http:\/\/localhost:\d+\/lead\/N\/A/i,
    /localhost:\d+\/lead\/N\/A/i
  ];
  
  return missingPatterns.some(pattern => pattern.test(websiteValue.trim()));
};

/**
 * Checks if an email value indicates missing information and should be replaced with "N/A"
 * @param {string} emailValue - The email address or value to check
 * @returns {boolean} true if the value indicates missing information, false otherwise
 */
const isEmailMissing = (emailValue) => {
  if (!emailValue || emailValue.trim() === '') return true;
  
  const missingPatterns = [
    /not\s*found/i,
    /not\s*provided/i,
    /n\/a/i,
    /none/i,
    /unknown/i,
    /missing/i,
    /unavailable/i,
    /no\s*email/i,
    /email\s*not\s*available/i,
    /email\s*not\s*found/i,
    /email\s*not\s*provided/i,
    /email\s*missing/i,
    /email\s*unavailable/i,
    /email\s*information\s*not\s*found/i,
    /email\s*information\s*not\s*provided/i,
    /email\s*information\s*unavailable/i,
    /email\s*information\s*missing/i,
    /email\s*is\s*currently\s*unavailable/i,
    /email\s*is\s*not\s*listed/i,
    /email\s*is\s*not\s*available/i,
    /mailto:N\/A/i,
    /mailto:n\/a/i,
    /email:\s*$/i,
    /email:\s*-$/i,
    /email:\s*not\s*listed$/i,
    /email:\s*not\s*available$/i,
    /email:\s*unavailable$/i,
    /email:\s*missing$/i,
    /email:\s*n\/a$/i,
    /email:\s*none$/i,
    /^email:\s*$/i,
    /^email:\s*-$/i,
    /^email:\s*not\s*listed$/i,
    /^email:\s*not\s*available$/i,
    /^email:\s*unavailable$/i,
    /^email:\s*missing$/i,
    /^email:\s*n\/a$/i,
    /^email:\s*none$/i
  ];
  
  return missingPatterns.some(pattern => pattern.test(emailValue.trim()));
};

/**
 * Normalizes LinkedIn values by replacing missing information indicators with "N/A"
 * @param {string} linkedinValue - The LinkedIn URL or value to normalize
 * @returns {string} "N/A" if the value indicates missing information, otherwise the original value
 */
const normalizeLinkedInValue = (linkedinValue) => {
  return isLinkedInMissing(linkedinValue) ? 'N/A' : linkedinValue;
};

/**
 * Normalizes website values by replacing missing information indicators with "N/A"
 * @param {string} websiteValue - The website URL or value to normalize
 * @returns {string} "N/A" if the value indicates missing information, otherwise the original value
 */
const normalizeWebsiteValue = (websiteValue) => {
  return isWebsiteMissing(websiteValue) ? 'N/A' : websiteValue;
};

/**
 * Normalizes email values by replacing missing information indicators with "N/A"
 * @param {string} emailValue - The email address or value to normalize
 * @returns {string} "N/A" if the value indicates missing information, otherwise the original value
 */
const normalizeEmailValue = (emailValue) => {
  return isEmailMissing(emailValue) ? 'N/A' : emailValue;
};

const dummyData = [
{
    id: "1",
    lead_id: "1",
    draft_id: "draft_1",
    company: "Acme Corporation",
    website: "https://acme.com",
    industry: "Manufacturing",
    productCategory: "Industrial Supplies",
    businessType: "B2B",
    employees: "250",
    revenue: "$50M",
    yearFounded: "1985",
    bbbRating: "A+",
    street: "123 Industrial Way",
    city: "Springfield",
    state: "IL",
    companyPhone: "(555) 123-4567",
    companyLinkedin: "https://linkedin.com/company/acme-corp",
    ownerFirstName: "John",
    ownerLastName: "Doe",
    ownerTitle: "CEO",
    ownerLinkedin: "https://linkedin.com/in/johndoe",
    ownerPhoneNumber: "(555) 987-6543",
    ownerEmail: "john.doe@acme.com",
    source: "Manual Entry",
    created: "2023-05-15T10:30:00Z",
    updated: "2023-06-20T14:45:00Z",
    sourceType: "database"
},
{
    id: "2",
    lead_id: "2",
    draft_id: "draft_2",
    company: "TechSolutions Inc.",
    website: "https://techsolutions.com",
    industry: "Information Technology",
    productCategory: "Software Development",
    businessType: "B2B",
    employees: "120",
    revenue: "$25M",
    yearFounded: "2010",
    bbbRating: "A",
    street: "456 Tech Boulevard",
    city: "San Francisco",
    state: "CA",
    companyPhone: "(415) 555-7890",
    companyLinkedin: "https://linkedin.com/company/techsolutions",
    ownerFirstName: "Sarah",
    ownerLastName: "Johnson",
    ownerTitle: "CTO",
    ownerLinkedin: "https://linkedin.com/in/sarahjohnson",
    ownerPhoneNumber: "(415) 555-1234",
    ownerEmail: "sarah.johnson@techsolutions.com",
    source: "Web Scraper",
    created: "2023-04-10T09:15:00Z",
    updated: "2023-05-18T11:20:00Z",
    sourceType: "database"
},
{
    id: "3",
    lead_id: "3",
    draft_id: "draft_3",
    company: "GreenEarth Organics",
    website: "https://greenearth.com",
    industry: "Agriculture",
    productCategory: "Organic Produce",
    businessType: "B2C",
    employees: "75",
    revenue: "$12M",
    yearFounded: "2005",
    bbbRating: "A+",
    street: "789 Farm Road",
    city: "Portland",
    state: "OR",
    companyPhone: "(503) 555-4567",
    companyLinkedin: "https://linkedin.com/company/greenearth",
    ownerFirstName: "Michael",
    ownerLastName: "Brown",
    ownerTitle: "Founder",
    ownerLinkedin: "https://linkedin.com/in/michaelbrown",
    ownerPhoneNumber: "(503) 555-8901",
    ownerEmail: "michael.brown@greenearth.com",
    source: "Trade Show",
    created: "2023-03-22T14:00:00Z",
    updated: "2023-04-30T16:30:00Z",
    sourceType: "database"
},
{
    id: "4",
    lead_id: "4",
    draft_id: "draft_4",
    company: "UrbanStyle Apparel",
    website: "https://urbanstyle.com",
    industry: "Fashion",
    productCategory: "Clothing",
    businessType: "B2C",
    employees: "200",
    revenue: "$40M",
    yearFounded: "2015",
    bbbRating: "A-",
    street: "321 Fashion Avenue",
    city: "New York",
    state: "NY",
    companyPhone: "(212) 555-6789",
    companyLinkedin: "https://linkedin.com/company/urbanstyle",
    ownerFirstName: "Jessica",
    ownerLastName: "Williams",
    ownerTitle: "Creative Director",
    ownerLinkedin: "https://linkedin.com/in/jessicawilliams",
    ownerPhoneNumber: "(212) 555-2345",
    ownerEmail: "jessica.williams@urbanstyle.com",
    source: "Social Media",
    created: "2023-02-18T11:45:00Z",
    updated: "2023-03-25T13:15:00Z",
    sourceType: "database"
},
{
    id: "5",
    lead_id: "5",
    draft_id: "draft_5",
    company: "BlueOcean Consulting",
    website: "https://blueocean.com",
    industry: "Professional Services",
    productCategory: "Business Consulting",
    businessType: "B2B",
    employees: "50",
    revenue: "$15M",
    yearFounded: "2018",
    bbbRating: "A",
    street: "654 Corporate Lane",
    city: "Boston",
    state: "MA",
    companyPhone: "(617) 555-3456",
    companyLinkedin: "https://linkedin.com/company/blueocean",
    ownerFirstName: "David",
    ownerLastName: "Miller",
    ownerTitle: "Managing Partner",
    ownerLinkedin: "https://linkedin.com/in/davidmiller",
    ownerPhoneNumber: "(617) 555-7890",
    ownerEmail: "david.miller@blueocean.com",
    source: "Referral",
    created: "2023-01-05T08:30:00Z",
    updated: "2023-02-12T10:45:00Z",
    sourceType: "database"
}
];

const revenueOptions = [
  "$100K", "$500K", "$1M", "$5M", "$10M", "$25M", "$50M", "$100M", "$500M", "$1B",
];

export default function CompaniesPage() {
    const [user, setUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    // Copy ALL state from the original scraping history component
    const [searchTerm, setSearchTerm] = useState("");
    const [employeesFilter, setEmployeesFilter] = useState("");
    const [employeesOperator, setEmployeesOperator] = useState("is-greater");
    const [employeesValue1, setEmployeesValue1] = useState("");
    const [employeesValue2, setEmployeesValue2] = useState("");
    const [revenueOperator, setRevenueOperator] = useState("is-greater");
    const [revenueValue1, setRevenueValue1] = useState("");
    const [revenueValue2, setRevenueValue2] = useState("");
    const [yearOperator, setYearOperator] = useState("is-greater");
    const [yearValue1, setYearValue1] = useState("");
    const [yearValue2, setYearValue2] = useState("");
    const [businessTypeFilter, setBusinessTypeFilter] = useState("");
    const [productFilter, setProductFilter] = useState("");
    const [yearFoundedFilter, setYearFoundedFilter] = useState("");
    const [bbbRatingFilter, setBbbRatingFilter] = useState("");
    const [streetFilter, setStreetFilter] = useState("");
    const [industryFilter, setIndustryFilter] = useState("");
    const [cityFilter, setCityFilter] = useState("");
    const [stateFilter, setStateFilter] = useState("");
    const [sourceFilter, setSourceFilter] = useState("");
    const [showFilters, setShowFilters] = useState(false);
    const [selectAll, setSelectAll] = useState(false);
    const [scrapingHistory, setScrapingHistory] = useState([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(25);
    const [selectedCompanies, setSelectedCompanies] = useState([]);
    const [notif, setNotif] = useState({
        show: false,
        message: "",
        type: "success",
    });
    const [popupData, setPopupData] = useState(null); // null means no popup open
    const [popupTab, setPopupTab] = useState('overview');
    const [isEditing, setIsEditing] = useState(false);
    const [favoriteLeads, setFavoriteLeads] = useState(new Set()); // Track favorite status
    const [notesPopupOpen, setNotesPopupOpen] = useState(false);
    const [notesLeadId, setNotesLeadId] = useState(null);
    const [notesName, setNotesName] = useState("");
    const [leadsWithNotes, setLeadsWithNotes] = useState(new Set());

    // Action preview popup states
    const [actionPreviewPopup, setActionPreviewPopup] = useState({
        show: false,
        type: 'email',
        company: null
    });

    // News modal state and logic
    const [newsModalOpen, setNewsModalOpen] = useState(false);
    const [newsCompany, setNewsCompany] = useState(null);
    const [newsTab, setNewsTab] = useState("latest");
    const [newsLoading, setNewsLoading] = useState(false);
    const [newsList, setNewsList] = useState([]);
    const [savedInsights, setSavedInsights] = useState([]);
    const [newsError, setNewsError] = useState("");
    // Add state for news time range
    const [newsRange, setNewsRange] = useState("day"); // 'day', 'week', 'year', '5years'
    
    // Progress tracking states
    const [newsProgress, setNewsProgress] = useState({
      status: '',
      message: '',
      processed: 0,
      total: 0,
      articles: []
    });
    const newsRangeLabel = {
      day: "This Day",
      week: "This Week",
      year: "This Year",
      "5years": "Last 5 Years"
    };

    // Map frontend newsRange to backend time_option
    const newsRangeToTimeOption = {
      day: "today",
      week: "this_week",
      year: "this_year",
      "5years": "5_years"
    };

    // Ref to store cancel function for news fetch
    const newsCancelRef = useRef(null);
    
    // Add refs for tracking abort controller and reader for stop functionality
    const newsAbortControllerRef = useRef(null);
    const newsReaderRef = useRef(null);



    // Get current user ID function
    const getCurrentUserId = () => {
        const userData = sessionStorage.getItem('user');
        if (userData) {
            try {
                const parsedUser = JSON.parse(userData);
                return parsedUser.user_id || 'default-user-id';
            } catch (error) {
                console.error('Error parsing user data from session storage:', error);
                return 'default-user-id';
            }
        }
        return 'default-user-id';
    };

















    const fetchCompanyNews = async (company, append = false, range = newsRange) => {
      setNewsLoading(true);
      setNewsError("");
      // Cancel previous request if any
      if (newsCancelRef.current) {
        newsCancelRef.current();
        newsCancelRef.current = null;
      }

      // Use SSE for real-time progress updates with single connection
      fetchCompanyNewsSSE(company, append, range);
    };

    const fetchCompanyNewsSSE = async (company, append = false, range = newsRange) => {
      // SSE approach - single connection with real-time progress updates
      try {
        // Create abort controller for cancellation
        const abortController = new AbortController();
        newsAbortControllerRef.current = abortController;

        // Create a POST request to the SSE endpoint
        const response = await fetch(`${AI_NEWS_API_URL}/news/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            company: company.company,
            time_option: newsRangeToTimeOption[range] || "this_week",
            max_items: 10
          }),
          signal: abortController.signal
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Create a reader for the response stream
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body reader available');
        }

        // Store reader reference for cancellation
        newsReaderRef.current = reader;

        const decoder = new TextDecoder();

        // Helper function to cleanup resources
        const cleanup = () => {
          newsAbortControllerRef.current = null;
          newsReaderRef.current = null;
        };

        // Read the stream
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            cleanup();
            break;
          }

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6)); // Remove 'data: ' prefix
                
                if (data.event === 'progress') {
                  const progressData = JSON.parse(data.data);
                  setNewsProgress({
                    status: progressData.status,
                    message: progressData.message,
                    processed: progressData.processed || 0,
                    total: progressData.total || 0,
                    articles: progressData.articles || []
                  });
                } else if (data.event === 'complete') {
                  const completeData = JSON.parse(data.data);
                  if (completeData.status === 'complete' && completeData.result) {
                    let newsData = completeData.result.news || [];
                    newsData = newsData.slice().sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
                    setNewsList((prev) => append ? [...prev, ...newsData] : newsData);
                  }
                  
                  setNewsProgress({
                    status: '',
                    message: '',
                    processed: 0,
                    total: 0,
                    articles: []
                  });
                  setNewsLoading(false);
                  cleanup();
                  return;
                } else if (data.event === 'article_complete') {
                  // Handle individual article completion
                  const articleData = JSON.parse(data.data);
                  if (articleData.article) {
                    setNewsList(prevList => {
                      // Add the new article to the list
                      const newList = append ? [...prevList, articleData.article] : [...prevList, articleData.article];
                      // Sort by match score
                      return newList.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
                    });
                  }
                } else if (data.event === 'error') {
                  const errorData = JSON.parse(data.data);
                  setNewsError(errorData.message || "An error occurred while fetching news.");
                  setNewsProgress({
                    status: '',
                    message: '',
                    processed: 0,
                    total: 0,
                    articles: []
                  });
                  setNewsLoading(false);
                  cleanup();
                  return;
                }
              } catch (err) {
                console.error('SSE data parsing failed:', err);
              }
            }
          }
        }

      } catch (e) {
        console.error('SSE connection failed:', e);
        
        // Don't fall back to polling if this was an intentional abort
        if (e.name === 'AbortError' || e.message?.includes('aborted') || e.message?.includes('BodyStreamBuffer was aborted')) {
          console.log('SSE connection was intentionally aborted');
          // Clear refs on intentional abort
          newsAbortControllerRef.current = null;
          newsReaderRef.current = null;
          return;
        }
        
        // Clear refs on error
        newsAbortControllerRef.current = null;
        newsReaderRef.current = null;
        
        // Fallback to polling if SSE fails for other reasons
        console.log('SSE failed, falling back to polling...');
        fetchCompanyNewsPolling(company, append, range);
      }
    };

    const fetchCompanyNewsPolling = async (company, append = false, range = newsRange) => {
      // Fallback to original polling method
      try {
        const response = await axios.post(
          `${AI_NEWS_API_URL}/news`,
          {
            company: company.company,
            time_option: newsRangeToTimeOption[range] || "this_week",
            max_items: 10
          }
        );

        const { session_id } = response.data;
        
        // Check if session_id exists before proceeding
        if (!session_id) {
          console.error('No session_id received from API');
          setNewsError("Failed to start news search. Please try again.");
          setNewsLoading(false);
          return;
        }
        
        const startTime = Date.now();
        const POLLING_TIMEOUT_MS = 60000; // 60 seconds

        const interval = setInterval(async () => {
          try {
            // Timeout check
            if (Date.now() - startTime > POLLING_TIMEOUT_MS) {
              clearInterval(interval);
              setNewsLoading(false);
              setNewsError("Request timed out. Please try again later.");
              return;
            }

            const progressResponse = await axios.get(`${AI_NEWS_API_URL}/progress/${session_id}`);
            const progressData = progressResponse.data;

            if (progressData.complete) {
              clearInterval(interval);

              if (progressData.status === 'complete' && progressData.result) {
                let newsData = progressData.result.news || [];
                newsData = newsData.slice().sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
                setNewsList((prev) => append ? [...prev, ...newsData] : newsData);
              } else if (progressData.status === 'error') {
                setNewsError(progressData.message || "An error occurred while fetching news.");
              }

              setNewsLoading(false);
              // Clear refs
              newsAbortControllerRef.current = null;
              newsReaderRef.current = null;
            }
          } catch (err) {
            console.error('Progress check failed:', err);
            clearInterval(interval);
            setNewsError("Failed to check progress.");
            setNewsLoading(false);
            // Clear refs
            newsAbortControllerRef.current = null;
            newsReaderRef.current = null;
          }
        }, 1000);

      } catch (e) {
        if (e.response && e.response.status === 429) {
          setNewsError("Too many requests right now, please try again later.");
          showNotification("Too many requests right now, please try again later.", "error");
        } else {
          setNewsError("Failed to fetch news.");
        }
        setNewsLoading(false);
      }
    };

    const handleOpenNews = (company) => {
      setNewsCompany(company);
      setNewsTab("latest");
      setNewsList([]);
      setNewsModalOpen(true);
      // Do not fetch news immediately
    };

    const handleFetchNews = (range) => {
      setNewsRange(range);
      if (newsCompany) fetchCompanyNews(newsCompany, false, range);
    };

    const handleAddMoreNews = (range) => {
      setNewsRange(range);
      if (newsCompany) fetchCompanyNews(newsCompany, true, range);
    };

    const handleStopNews = () => {
      // Clear the progress interval if it exists
      if (newsCancelRef.current) {
        newsCancelRef.current();
        newsCancelRef.current = null;
      }

      // Cancel the reader if it exists (do this before aborting the controller)
      if (newsReaderRef.current) {
        try {
          newsReaderRef.current.cancel();
        } catch (error) {
          console.log('News reader already cancelled or disposed');
        }
        newsReaderRef.current = null;
      }

      // Cancel the abort controller if it exists
      if (newsAbortControllerRef.current) {
        try {
          newsAbortControllerRef.current.abort();
        } catch (error) {
          console.log('News abort controller already aborted or disposed');
        }
        newsAbortControllerRef.current = null;
      }

      // Reset loading state but keep current results
      setNewsLoading(false);
      setNewsProgress({
        status: 'Stopped',
        message: 'Search stopped by user',
        processed: 0,
        total: 0,
        articles: []
      });
    };

    const handleSaveInsight = async (newsItem) => {
      try {
        const payload = {
          lead_id: newsCompany.lead_id || newsCompany.id,
          company_name: newsCompany.company,
          headline: newsItem.title,
          insights: newsItem.ai_insights?.insights || [],
          source: newsItem.link,
          tags: newsItem.tags,
          published_at: newsItem.published,
        };
        const response = await axios.post(`${DATABASE_URL}/news_insights/`, payload, { withCredentials: true });
        setSavedInsights((prev) => [response.data, ...prev]);
      } catch (err) {
        // Optionally show error notification
      }
    };

    const handleRemoveInsight = (newsItem) => {
      setSavedInsights((prev) => prev.filter((n) => n.id !== newsItem.id));
    };

    const handleDeleteInsight = async (news) => {
      try {
        await axios.delete(`${DATABASE_URL}/news_insights/${news.id}`, { withCredentials: true });
        setSavedInsights((prev) => prev.filter((n) => n.id !== news.id));
      } catch (err) {
        // Optionally show error notification
      }
    };

    const router = useRouter();

    const saveLeadToAPI = async (lead) => {
        const toSnake = (str) => str.replace(/([A-Z])/g, "_$1").toLowerCase();
        const normalizeKeys = (obj) => {
            const result = {};
            for (const [k, v] of Object.entries(obj)) {
                result[toSnake(k)] = v;
            }
            return result;
        };

        const normalizedLead = normalizeKeys(lead);
        normalizedLead.user_id = user.id;

        try {
            // First POST
            const postResponse = await axios.post(
                `${DATABASE_URL_NOAPI}/leads/${lead.id}/edit`,
                normalizedLead,
                { withCredentials: true }
            );

            // Then PUT
            const payload = {
                draft_data: normalizedLead,
                change_summary: "Updated from popup",
                phase: "draft",
                status: "pending",
            };
            const actualDraftId = postResponse.data?.draft?.draft_id || lead.draft_id;

            await axios.put(`${DATABASE_URL}/leads/drafts/${actualDraftId}`, payload, {
                withCredentials: true,
            });

            return { success: true, updatedLead: { ...lead, ...normalizedLead } };
        } catch (err) {
            console.error("❌ Error saving lead:", err);
            return { success: false, error: err };
        }
    };

    const handlePopupSave = async () => {
        if (!popupData) return;

        const result = await saveLeadToAPI(popupData);

        if (result.success) {
            const updatedList = scrapingHistory.map((item) =>
                item.id === popupData.id ? popupData : item
            );
            setScrapingHistory(updatedList);
            setIsEditing(false);
            showNotification("Changes saved.", "success");
        } else {
            showNotification("Failed to save changes.", "error");
        }
    };

    const showNotification = (message, type = "success") => {
        setNotif({ show: true, message, type });

        // Automatically hide after X seconds
        setTimeout(() => {
        setNotif((prev) => ({ ...prev, show: false }));
        }, 3500);
    };

    const clearAllFilters = () => {
        setEmployeesFilter("");
        setEmployeesOperator("is-greater");
        setEmployeesValue1("");
        setEmployeesValue2("");
        setRevenueOperator("is-greater");
        setRevenueValue1("");
        setRevenueValue2("");
        setYearOperator("is-greater");
        setYearValue1("");
        setYearValue2("");
        setBusinessTypeFilter("");
        setProductFilter("");
        setYearFoundedFilter("");
        setBbbRatingFilter("");
        setStreetFilter("");
        setCityFilter("");
        setStateFilter("");
        setSourceFilter("");
    };

    const parseRevenue = (revenueInput) => {
        if (typeof revenueInput === "number") return revenueInput;
        if (typeof revenueInput !== "string") return null;

        let revenueStr = revenueInput.toLowerCase().trim().replace(/[$,]/g, "");
        let multiplier = 1;

        if (revenueStr.endsWith("k")) {
        multiplier = 1_000;
        revenueStr = revenueStr.slice(0, -1);
        } else if (revenueStr.endsWith("m")) {
        multiplier = 1_000_000;
        revenueStr = revenueStr.slice(0, -1);
        } else if (revenueStr.endsWith("b")) {
        multiplier = 1_000_000_000;
        revenueStr = revenueStr.slice(0, -1);
        }

        const value = parseFloat(revenueStr);
        return isNaN(value) ? null : value * multiplier;
    };

    const parseFilter = (filterStr, isRevenue = false) => {
        const result = {
        operation: "exact",
        value: null | null,
        upper: null | null,
        };
        filterStr = filterStr.toLowerCase().trim();
        const rangeMatch = filterStr.match(
        /^(\d+(?:[kmb]?)?)\s*-\s*(\d+(?:[kmb]?)?)$/
        );
        if (rangeMatch) {
        const val1 = isRevenue
            ? parseRevenue(rangeMatch[1])
            : parseInt(rangeMatch[1]);
        const val2 = isRevenue
            ? parseRevenue(rangeMatch[2])
            : parseInt(rangeMatch[2]);
        return { operation: "between", value: val1, upper: val2 };
        }
        if (filterStr.startsWith(">="))
        (result.operation = "greater than or equal"),
            (filterStr = filterStr.slice(2));
        else if (filterStr.startsWith(">"))
        (result.operation = "greater than"), (filterStr = filterStr.slice(1));
        else if (filterStr.startsWith("<="))
        (result.operation = "less than or equal"),
            (filterStr = filterStr.slice(2));
        else if (filterStr.startsWith("<"))
        (result.operation = "less than"), (filterStr = filterStr.slice(1));
        result.value = isRevenue ? parseRevenue(filterStr) : parseInt(filterStr);
        return result;
    };

    // Helper function to parse employee ranges
    const parseEmployeeRange = (employeeValue) => {
        if (!employeeValue) return null;
        
        const value = employeeValue.toString().trim();
        
        // Handle single numbers (including with + suffix)
        const singleNumberMatch = value.match(/^(\d+)\+?$/);
        if (singleNumberMatch) {
            return parseInt(singleNumberMatch[1], 10);
        }

        // Handle ranges like "50-100", "25-50 people", "10-20 employees"
        const rangeMatch = value.match(/^(\d+)\s*-\s*(\d+)(?:\s+\w+)?$/);
        if (rangeMatch) {
            const min = parseInt(rangeMatch[1], 10);
            const max = parseInt(rangeMatch[2], 10);
            
            if (min <= max) {
                return { min, max, isRange: true };
            }
        }

        return null;
    };

    // Helper function to check if a filter value matches an employee range
    const matchesEmployeeRange = (companyEmployees, filterValue) => {
        const parsed = parseEmployeeRange(companyEmployees);
        
        if (!parsed) return false;
        
        // If it's a single number
        if (typeof parsed === 'number') {
            return parsed === filterValue;
        }
        
        // If it's a range, check if filter value falls within the range
        if (parsed.isRange) {
            return filterValue >= parsed.min && filterValue <= parsed.max;
        }
        
        return false;
    };

    // Helper function to parse year founded ranges
    const parseYearRange = (yearValue) => {
        if (!yearValue) return null;
        
        const value = yearValue.toString().trim();
        
        // Handle single years (including with + suffix)
        const singleYearMatch = value.match(/^(\d{4})\+?$/);
        if (singleYearMatch) {
            return parseInt(singleYearMatch[1], 10);
        }

        // Handle ranges like "2020-2023", "2015-2020 founded", "2018-2022 years"
        const rangeMatch = value.match(/^(\d{4})\s*-\s*(\d{4})(?:\s+\w+)?$/);
        if (rangeMatch) {
            const min = parseInt(rangeMatch[1], 10);
            const max = parseInt(rangeMatch[2], 10);
            
            if (min <= max) {
                return { min, max, isRange: true };
            }
        }

        return null;
    };

    // Helper function to check if a filter value matches a year range
    const matchesYearRange = (companyYear, filterValue) => {
        const parsed = parseYearRange(companyYear);
        
        if (!parsed) return false;
        
        // If it's a single year
        if (typeof parsed === 'number') {
            return parsed === filterValue;
        }
        
        // If it's a range, check if filter value falls within the range
        if (parsed.isRange) {
            return filterValue >= parsed.min && filterValue <= parsed.max;
        }
        
        return false;
    };

    const toCamelCase = (str) =>
        str.replace(/([-_][a-z])/gi, (group) =>
        group.toUpperCase().replace("-", "").replace("_", "")
        );

    const toCamelCaseKeys = (obj) => {
        const newObj = {};
        for (const key in obj) {
        const camelKey = toCamelCase(key);
        newObj[camelKey] = obj[key];
        }
        return newObj;
    };

    const ExpandableCell = ({ text, onClick }) => {
        const [expanded, setExpanded] = useState(false);
        
        // Ensure text is always a string and handle null/undefined cases
        const safeText = text != null ? String(text) : "";
        const isLong = safeText.length > 100;
        
        if (!isLong) return <span onClick={onClick}>{safeText}</span>;
        return (
            <div className="whitespace-pre-wrap">
                <span onClick={onClick}>
                    {expanded ? safeText : safeText.slice(0, 30) + "... "}
                </span>
                <button
                    className="text-blue-500 hover:underline text-xs ml-1"
                    onClick={() => setExpanded(!expanded)}
                >
                    {expanded ? "Show less" : "Show more"}
                </button>
            </div>
        );
    };

    const handleExportCSV = (items, filename) => {
        const headers = [
        "Company",
        "Website",
        "Industry",
        "Product Category",
        "Business Type",
        "Employees",
        "Revenue",
        "Year Founded",
        "BBB Rating",
        "Street",
        "City",
        "State",
        "Company Phone",
        "Company LinkedIn",
        "Owner First Name",
        "Owner Last Name",
        "Owner Title",
        "Owner LinkedIn",
        "Owner Phone Number",
        "Owner Email",
        "Source",
        "Created At",
        "Updated At",
        ];

        // Create a mapping from header names to actual field names
        const headerToFieldMap = {
            "Company": "company",
            "Website": "website",
            "Industry": "industry",
            "Product Category": "productCategory",
            "Business Type": "businessType",
            "Employees": "employees",
            "Revenue": "revenue",
            "Year Founded": "yearFounded",
            "BBB Rating": "bbbRating",
            "Street": "street",
            "City": "city",
            "State": "state",
            "Company Phone": "companyPhone",
            "Company LinkedIn": "companyLinkedin",
            "Owner First Name": "ownerFirstName",
            "Owner Last Name": "ownerLastName",
            "Owner Title": "ownerTitle",
            "Owner LinkedIn": "ownerLinkedin",
            "Owner Phone Number": "ownerPhoneNumber",
            "Owner Email": "ownerEmail",
            "Source": "source",
            "Created At": "created",
            "Updated At": "updated",
        };

        const csvContent = [
        headers.join(","), // Header row
        ...items.map((row) =>
            headers
            .map((h) => {
                const fieldName = headerToFieldMap[h];
                const value = row[fieldName];
                return `"${value || ""}"`;
            })
            .join(",")
        ),
        ].join("\n");

        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleExportCSVWithCredits = async () => {
        if (selectedCompanies.length === 0) {
            showNotification("Please select at least one row to export.", "info");
            return;
        }
        try {
            const { data: subscriptionInfo } = await axios.get(
                `${DATABASE_URL}/user/subscription_info`,
                { withCredentials: true }
            );
            const planName = subscriptionInfo?.subscription?.plan_name?.toLowerCase() ?? "free";
            const availableCredits = subscriptionInfo?.subscription?.credits_remaining ?? 0;
            const requiredCredits = selectedCompanies.length;
            const user = typeof window !== "undefined" ? JSON.parse(sessionStorage.getItem("user") || "{}") : {};
            const userRole = user?.role || "user";
            const isDeveloper = userRole === "developer";
            const hasNonFreeTier = planName !== "free";
            if (!isDeveloper && !hasNonFreeTier) {
                showNotification(
                    "Exporting requires either a paid subscription or developer role. Please upgrade your plan or contact support.",
                    "info"
                );
                return;
            }
            if (isDeveloper) {
                const selectedItems = scrapingHistory.filter(item => selectedCompanies.includes(item.id));
                handleExportCSV(selectedItems, "scraping_history.csv");
                showNotification(`Successfully exported ${selectedItems.length} selected items.`, "success");
                return;
            }
            if (availableCredits < requiredCredits) {
                showNotification(
                    "Insufficient credits to export all selected leads. Please upgrade or reduce selection.",
                    "error"
                );
                return;
            }
            const selectedItems = scrapingHistory.filter(item => selectedCompanies.includes(item.id));
            handleExportCSV(selectedItems, "scraping_history.csv");
            showNotification(`Successfully exported ${selectedItems.length} selected items.`, "success");
        } catch (err) {
            console.error("❌ Failed to verify subscription:", err);
            showNotification(
                "Failed to verify your subscription. Please try again later.",
                "error"
            );
        }
    };

    const handleToggleFiltersWithCheck = async () => {
        try {
        const { data: subscriptionInfo } = await axios.get(
            `${DATABASE_URL}/user/subscription_info`,
            { withCredentials: true }
        );
        const planName =
            subscriptionInfo?.subscription?.plan_name?.toLowerCase() ?? "free";
        
        // Get user role from session storage
        const userRole = user?.role || "user";
        const isDeveloper = userRole === "developer";
        const hasNonFreeTier = planName !== "free";
        
        // Allow filters if user is developer OR has non-free tier
        if (!isDeveloper && !hasNonFreeTier) {
            showNotification(
            "Advanced filters are disabled on the Free tier. Please upgrade your plan or contact support for developer access.",
            "info"
            );
            return;
        }
        setShowFilters((prev) => !prev);
        } catch (err) {
        console.error("❌ Failed to verify subscription:", err);
        showNotification(
            "Failed to verify your subscription. Please try again later.",
            "error"
        );
        }
    };

    const filteredScrapingHistory = scrapingHistory.filter((entry) => {
        // Search term filter (case-insensitive, matches any main field)
        const search = searchTerm.toLowerCase();
        const matchesSearch =
          !search ||
          [
            entry.company,
            entry.website,
            entry.industry,
            entry.productCategory,
            entry.businessType,
            entry.city,
            entry.state,
            entry.bbbRating,
            entry.ownerFirstName,
            entry.ownerLastName,
            entry.ownerTitle,
            entry.ownerEmail,
            entry.ownerLinkedin,
            entry.companyPhone
          ]
            .map((v) => (v || "").toLowerCase())
            .some((v) => v.includes(search));

        const matchIndustry = entry.industry
        ?.toLowerCase()
        .includes(industryFilter.toLowerCase());
        const matchCity = entry.city
        ?.toLowerCase()
        .includes(cityFilter.toLowerCase());
        const matchState = entry.state
        ?.toLowerCase()
        .includes(stateFilter.toLowerCase());
        const matchBBB = entry.bbbRating
        ?.toLowerCase()
        .includes(bbbRatingFilter.toLowerCase());
        const matchProduct = entry.productCategory
        ?.toLowerCase()
        .includes(productFilter.toLowerCase());
        const matchBusinessType = entry.businessType
        ?.toLowerCase()
        .includes(businessTypeFilter.toLowerCase());
        const matchSource = entry.source
        ?.toLowerCase()
        .includes(sourceFilter.toLowerCase());

        const companyRev = parseRevenue(entry.revenue);
        const val1 = parseRevenue(revenueValue1);
        const val2 = parseRevenue(revenueValue2);

        const matchRevenue = (() => {
          if (!revenueValue1 || val1 === null) return true; // Don't filter if first input is empty
          if (companyRev === null) return false; // Company has no valid revenue data

          switch (revenueOperator) {
            case 'is-greater':
              return companyRev > val1;
            case 'is-less':
              return companyRev < val1;
            case 'is-between':
              if (val2 !== null) {
                return companyRev >= val1 && companyRev <= val2;
              }
              return companyRev >= val1; // If max isn't set, act as "greater than"
            default:
              return true;
          }
        })();

        // Use new operator-based logic for employees
        const matchEmployees = (() => {
            if (!employeesValue1) return true; // No filter applied
            
            const filterVal = parseInt(employeesValue1);
            const filterVal2 = parseInt(employeesValue2);
            
            if (isNaN(filterVal)) return true;
            
            // Parse the company's employee value
            const parsed = parseEmployeeRange(entry.employees);
            if (!parsed) return false; // Can't parse company employees
            
            // If company has a single number
            if (typeof parsed === 'number') {
                switch (employeesOperator) {
                    case "is-less": return parsed < filterVal;
                    case "is-greater": return parsed > filterVal;
                    case "is-between": 
                        if (isNaN(filterVal2)) return parsed >= filterVal;
                        return parsed >= filterVal && parsed <= filterVal2;
                    default: return parsed === filterVal;
                }
            }
            
            // If company has a range, use the mean for comparison
            if (parsed.isRange) {
                const mean = (parsed.min + parsed.max) / 2;
                switch (employeesOperator) {
                    case "is-less": return mean < filterVal;
                    case "is-greater": return mean > filterVal;
                    case "is-between": 
                        if (isNaN(filterVal2)) return mean >= filterVal;
                        return mean >= filterVal && mean <= filterVal2;
                    default: return mean === filterVal;
                }
            }
            
            return false;
        })();

        // Use new operator-based logic for year founded
        const matchYearFounded = (() => {
            if (!yearValue1) return true; // No filter applied
            
            const filterVal = parseInt(yearValue1);
            const filterVal2 = parseInt(yearValue2);
            
            if (isNaN(filterVal)) return true;
            
            // Parse the company's year value
            const parsed = parseYearRange(entry.yearFounded);
            if (!parsed) return false; // Can't parse company year
            
            // If company has a single year
            if (typeof parsed === 'number') {
                switch (yearOperator) {
                    case "is-less": return parsed < filterVal;
                    case "is-greater": return parsed > filterVal;
                    case "is-between": 
                        if (isNaN(filterVal2)) return parsed >= filterVal;
                        return parsed >= filterVal && parsed <= filterVal2;
                    default: return parsed === filterVal;
                }
            }
            
            // If company has a range, use the mean for comparison
            if (parsed.isRange) {
                const mean = (parsed.min + parsed.max) / 2;
                switch (yearOperator) {
                    case "is-less": return mean < filterVal;
                    case "is-greater": return mean > filterVal;
                    case "is-between": 
                        if (isNaN(filterVal2)) return mean >= filterVal;
                        return mean >= filterVal && mean <= filterVal2;
                    default: return mean === filterVal;
                }
            }
            
            return false;
        })();

        return (
        matchesSearch &&
        matchIndustry &&
        matchCity &&
        matchState &&
        matchBBB &&
        matchProduct &&
        matchBusinessType &&
        matchRevenue &&
        matchSource &&
        matchEmployees &&
        matchYearFounded
        );
    });

    const totalPages = Math.ceil(filteredScrapingHistory.length / itemsPerPage);
    const indexOfFirstItem = (currentPage - 1) * itemsPerPage;
    const indexOfLastItem = currentPage * itemsPerPage;
    const currentItems = filteredScrapingHistory.slice(
    indexOfFirstItem,
    indexOfLastItem
    );

    const handleSelectAll = () => {
        const visibleIds = scrapingHistory
        .slice(indexOfFirstItem, indexOfLastItem)
        .map((entry) => entry.id);

        if (selectAll) {
        setSelectedCompanies([]);
        } else {
        setSelectedCompanies(visibleIds);
        }

        setSelectAll(!selectAll);
    };

    const handleSelectCompany = (id) => {
        if (selectedCompanies.includes(id)) {
        setSelectedCompanies(selectedCompanies.filter(companyId => companyId !== id));
        } else {
        setSelectedCompanies([...selectedCompanies, id]);
        }
    };

    const handleSortBy = (sortBy, direction) => {
        // Count how many non‐empty fields each row has:
        const getFilledCount = (row) =>
        Object.entries(row).filter(([key, value]) => {
            if (
            ["id", "lead_id", "draft_id", "sourceType"].includes(key) ||
            value === null ||
            value === undefined ||
            value === "" ||
            value === "N/A"
            ) {
            return false;
            }
            return true;
        }).length;

        // Determine the base array to sort:
        const base = [...scrapingHistory];

        // Sort by completeness only if sortBy === "filled", otherwise you can
        // extend this switch for revenue, employees, etc.:
        const sorted = base.sort((a, b) => {
        if (sortBy === "filled") {
            const aCount = getFilledCount(a);
            const bCount = getFilledCount(b);
            return direction === "most" ? bCount - aCount : aCount - bCount;
        }
        // Example: alphabetical company
        if (sortBy === "company") {
            return direction === "most"
            ? b.company.localeCompare(a.company)
            : a.company.localeCompare(b.company);
        }
        // ...add more sortBy cases here...
        return 0;
        });

        // Push the new order into state:
        setScrapingHistory(sorted);
        setCurrentPage(1); // reset pagination to page 1
    };

    // Function to toggle favorite status
    const handleToggleFavorite = async (leadId) => {
        try {
            const response = await axios.post(
                `${DATABASE_URL_NOAPI}/drafts/${leadId}/favorite`,
                {},
                { withCredentials: true }
            );

            if (response.status === 200) {
                const isFavorite = response.data.is_favorite;
                
                // Update local state
                setFavoriteLeads(prev => {
                    const newSet = new Set(prev);
                    if (isFavorite) {
                        newSet.add(leadId);
                    } else {
                        newSet.delete(leadId);
                    }
                    return newSet;
                });

                // Update the company in scrapingHistory array with favorite status
                setScrapingHistory(prev => 
                    prev.map(company => 
                        (company.lead_id || company.id) === leadId 
                            ? { ...company, is_favorite: isFavorite }
                            : company
                    )
                );

                showNotification(
                    isFavorite ? "Added to favorites!" : "Removed from favorites!", 
                    "success"
                );
            }
        } catch (error) {
            console.error("Error toggling favorite:", error);
            if (axios.isAxiosError(error) && error.response?.status === 404) {
                showNotification("Lead not found. Please interact with the lead first.", "error");
            } else {
                showNotification("Failed to update favorite status.", "error");
            }
        }
    };

    const handleActionPreview = (company, type) => {
        setActionPreviewPopup({
            show: true,
            type,
            company
        });
    };

    const handleActionConfirm = (type) => {
        if (!actionPreviewPopup.company) return;
        
        const company = actionPreviewPopup.company;
        
        if (type === 'email' && company.ownerEmail && normalizeEmailValue(company.ownerEmail) !== 'N/A') {
            window.open(`mailto:${company.ownerEmail}`, '_blank');
        } else if (type === 'linkedin' && company.companyLinkedin && normalizeLinkedInValue(company.companyLinkedin) !== 'N/A') {
            window.open(company.companyLinkedin, '_blank');
        } else if (type === 'website' && company.website && normalizeWebsiteValue(company.website) !== 'N/A') {
            window.open(company.website, '_blank');
        }
        
        setActionPreviewPopup({ show: false, type: 'email', company: null });
    };

    const handleActionClose = () => {
        setActionPreviewPopup({ show: false, type: 'email', company: null });
    };

    const handleGenerateInsights = (company) => {
        const leadId = company.lead_id || company.id;
        if (leadId) {
            router.push(`/lead/companies/${leadId}/company-insights`);
        } else {
            showNotification("Unable to generate insights: Lead ID not found", "error");
        }
    };

    // Fetch data on component mount
    useEffect(() => {
  const storedUser = typeof window !== "undefined" 
    ? JSON.parse(sessionStorage.getItem("user") || "{}")
    : {};
  setUser(storedUser);

  const fetchDrafts = async () => {
    try {
      const draftsRes = await fetch(`${DATABASE_URL}/leads/drafts`, {
        method: "GET",
        credentials: "include",
      });

      if (!draftsRes.ok) {
        throw new Error("API request failed");
      }

      const data = await draftsRes.json();
      const parsed = data.map((entry) => {
        const draftData = entry.draft_data || {};
        return {
          id: entry.lead_id || entry.id || "",
          lead_id: entry.lead_id || entry.id || "",
          draft_id: entry.draft_id || "",
          company: draftData.company || "N/A",
          website: normalizeWebsiteValue(draftData.website || ""),
          industry: draftData.industry || "",
          productCategory: draftData.product_category || "",
          businessType: draftData.business_type || "",
          employees: (() => {
            const emp = draftData.employees;
            if (!emp) return "";
            if (typeof emp === "string") return emp;
            if (typeof emp === "number") return emp.toString();
            if (typeof emp === "object" && emp.isRange) {
              return `${emp.min}-${emp.max}`;
            }
            return emp.toString();
          })(),
          revenue: draftData.revenue || "",
          yearFounded: draftData.year_founded?.toString() || "",
          bbbRating: draftData.bbb_rating || "",
          street: draftData.street || "",
          city: draftData.city || "",
          state: draftData.state || "",
          companyPhone: draftData.company_phone || "",
          companyLinkedin: normalizeLinkedInValue(draftData.company_linkedin || ""),
          ownerFirstName: draftData.owner_first_name || "",
          ownerLastName: draftData.owner_last_name || "",
          ownerTitle: draftData.owner_title || "",
          ownerLinkedin: normalizeLinkedInValue(draftData.owner_linkedin || ""),
          ownerPhoneNumber: draftData.owner_phone_number || "",
          ownerEmail: normalizeEmailValue(draftData.owner_email || ""),
          source: draftData.source || "",
          created: entry.created_at
            ? new Date(entry.created_at).toLocaleString()
            : "N/A",
          updated: entry.updated_at
            ? new Date(entry.updated_at).toLocaleString()
            : "N/A",
          sourceType: "database",
          is_favorite: entry.is_favorite || false,
          contacts: Array.isArray(draftData.contacts) ? draftData.contacts : [],
        };
      });

      setScrapingHistory(parsed);

      // Build favoriteLeads set from the drafts response
      const favoriteIds = new Set();
      const notesIds = new Set();
      data.forEach(entry => {
        const leadId = entry.lead_id || entry.id;
        if (entry.is_favorite && leadId) {
          favoriteIds.add(leadId);
        }
        // Highlight notes if notes.content exists and is not empty
        if (entry.notes && entry.notes.content && entry.notes.content.trim() !== "" && leadId) {
          notesIds.add(leadId);
        }
      });
      setFavoriteLeads(favoriteIds);
      setLeadsWithNotes(notesIds);

    } catch (error) {
      console.error("Error fetching drafts, using dummy data:", error);
      setScrapingHistory(dummyData.map(item => ({
        ...item,
        created: new Date(item.created).toLocaleString(),
        updated: new Date(item.updated).toLocaleString(),
        is_favorite: false
      })));
      showNotification("Using sample data while API is unavailable", "info");
      setLeadsWithNotes(new Set());
    } finally {
      setIsLoading(false);
    }
  };

  fetchDrafts();
}, []);

    // Fetch all saved insights on mount
    useEffect(() => {
      const fetchSavedInsights = async () => {
        try {
          // Fetch from both endpoints
          const [regularResponse, standaloneResponse] = await Promise.allSettled([
            axios.get(`${DATABASE_URL}/news_insights/`, { withCredentials: true }),
          ]);

          const allInsights = [];

          // Add regular insights
          if (regularResponse.status === 'fulfilled' && regularResponse.value.data && Array.isArray(regularResponse.value.data)) {
            allInsights.push(...regularResponse.value.data);
          }

          // Add standalone insights
          if (standaloneResponse.status === 'fulfilled' && standaloneResponse.value.data && Array.isArray(standaloneResponse.value.data)) {
            allInsights.push(...standaloneResponse.value.data);
          }

          setSavedInsights(allInsights);
        } catch (err) {
          setSavedInsights([]);
        }
      };
      fetchSavedInsights();
    }, []);

    const handleNewsModalOpenChange = (open) => {
      if (!open) {
        // Clear any ongoing requests when modal closes
        setNewsLoading(false);
        setNewsError("");
        setNewsList([]);
        setNewsProgress({
          status: '',
          message: '',
          processed: 0,
          total: 0,
          articles: []
        });
      }
      setNewsModalOpen(open);
    };

    // Cleanup effect to clear refs and intervals on unmount
    useEffect(() => {
      return () => {
        // Clear interval first
        if (newsCancelRef.current) {
          newsCancelRef.current();
        }
        
        // Cancel reader before aborting controller
        if (newsReaderRef.current) {
          try {
            newsReaderRef.current.cancel();
          } catch (error) {
            console.log('News reader already cancelled or disposed');
          }
        }
        
        // Clear abort controller last
        if (newsAbortControllerRef.current) {
          try {
            newsAbortControllerRef.current.abort();
          } catch (error) {
            console.log('News abort controller already aborted or disposed');
          }
        }
      };
    }, []);

    if (isLoading) {
      return (
        <div className="flex flex-col h-screen">
          <div className="flex flex-1 overflow-hidden">
            <main className="flex-1 p-6 overflow-auto">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Companies</CardTitle>
                    <div className="flex items-center gap-4">
                      {/* Search Bar */}
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                          type="search"
                          placeholder="Search companies..."
                          className="w-80 pl-8"
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </div>
                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        <SortDropdown onApply={handleSortBy} />
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={handleToggleFiltersWithCheck}
                          title={showFilters ? "Hide Filters" : "Show Filters"}
                        >
                          <Filter className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={handleExportCSVWithCredits}
                          title={selectedCompanies.length > 0 ? `Export ${selectedCompanies.length} selected items` : "Select items to export"}
                          disabled={selectedCompanies.length === 0}
                          className={`relative ${selectedCompanies.length === 0 ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                          <Download className="h-4 w-4" />
                          {selectedCompanies.length > 0 && (
                            <span className="absolute -top-2 -right-2 text-xs bg-blue-500 text-white rounded-full px-1.5 py-0.5 min-w-[1.2rem] flex items-center justify-center">
                              {selectedCompanies.length}
                            </span>
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                  {/* Filter Section (hidden during loading) */}
                </CardHeader>
                <CardContent>
                  <div className="p-8 text-center">
                    <div className="text-lg text-gray-700 dark:text-gray-200">Loading companies data...</div>
                  </div>
                </CardContent>
              </Card>
            </main>
          </div>
        </div>
      );
    }

    const overviewFields = [
        { key: "company", label: "Company" },
        { key: "website", label: "Website" },
        { key: "companyLinkedin", label: "Company LinkedIn" },
        { key: "industry", label: "Industry" },
        { key: "productCategory", label: "Product/Service Category" },
        { key: "businessType", label: "Business Type" },
        { key: "employees", label: "Employees Count" },
        { key: "revenue", label: "Revenue" },
        { key: "yearFounded", label: "Year Founded" },
        { key: "bbbRating", label: "BBB Rating" },
        { key: "street", label: "Street" },
        { key: "city", label: "City" },
        { key: "state", label: "State" },
        { key: "companyPhone", label: "Company Phone" },
        { key: "source", label: "Source" },
    ];



    return (
    <div className="flex flex-col h-screen">
        <FeedbackPopup />
        <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 p-6 overflow-auto">
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Companies</CardTitle>
                        <div className="flex items-center gap-4">
                            {/* Search Bar */}
                            <div className="relative">
                                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                                <Input
                                    type="search"
                                    placeholder="Search companies..."
                                    className="w-80 pl-8"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>
                            
                            {/* Actions */}
                            <div className="flex items-center gap-2">
                                <SortDropdown onApply={handleSortBy} />
                                
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={handleToggleFiltersWithCheck}
                                    title={showFilters ? "Hide Filters" : "Show Filters"}
                                >
                                    <Filter className="h-4 w-4" />
                                </Button>
                                <ForwardDropdown
                                    selectedCompanies={selectedCompanies}
                                    onForwardComplete={() => {
                                        // Optional: Add any cleanup or refresh logic here
                                    }}
                                    onNotification={showNotification}
                                    scrapingHistory={scrapingHistory}
                                />
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={handleExportCSVWithCredits}
                                    title={selectedCompanies.length > 0 ? `Export ${selectedCompanies.length} selected items` : "Select items to export"}
                                    disabled={selectedCompanies.length === 0}
                                    className={`relative ${selectedCompanies.length === 0 ? "opacity-50 cursor-not-allowed" : ""}`}
                                >
                                    <Download className="h-4 w-4" />
                                    {selectedCompanies.length > 0 && (
                                        <span className="absolute -top-2 -right-2 text-xs bg-blue-500 text-white rounded-full px-1.5 py-0.5 min-w-[1.2rem] flex items-center justify-center">
                                            {selectedCompanies.length}
                                        </span>
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>

                    {/* Filter Section */}
                    {showFilters && (
                        <div className="space-y-4 my-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                <div className="space-y-1">
                                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Industry</label>
                                    <Input
                                        placeholder="Enter industry..."
                                        value={industryFilter}
                                        onChange={(e) => setIndustryFilter(e.target.value)}
                                        className="w-full"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Product/Service Category</label>
                                    <Input
                                        placeholder="Enter category..."
                                        value={productFilter}
                                        onChange={(e) => setProductFilter(e.target.value)}
                                        className="w-full"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Business Type</label>
                                    <Input
                                        placeholder="B2B, B2C, etc."
                                        value={businessTypeFilter}
                                        onChange={(e) => setBusinessTypeFilter(e.target.value)}
                                        className="w-full"
                                    />
                                </div>
                                {/* Numeric Filters Row */}
                                <div className="col-span-full grid grid-cols-1 lg:grid-cols-3 gap-4">
                                    {/* Employees Count */}
                                    <div className="space-y-1">
                                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Employees Count</label>
                                        <div className="space-y-2">
                                            {/* Operator Selection */}
                                            <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
                                                <button
                                                    onClick={() => setEmployeesOperator('is-greater')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        employeesOperator === 'is-greater'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    Greater than (&gt;)
                                                </button>
                                                <button
                                                    onClick={() => setEmployeesOperator('is-less')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        employeesOperator === 'is-less'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    Less than (&lt;)
                                                </button>
                                                <button
                                                    onClick={() => setEmployeesOperator('is-between')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        employeesOperator === 'is-between'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    Between
                                                </button>
                                            </div>
                                            
                                            {/* Value Inputs */}
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm text-gray-600 dark:text-gray-400 min-w-[60px]">
                                                        {employeesOperator === 'is-greater' ? 'Greater than:' : 
                                                         employeesOperator === 'is-less' ? 'Less than:' : 'From:'}
                                                    </span>
                                                    <Input
                                                        placeholder="e.g., 50, 100"
                                                        value={employeesValue1}
                                                        onChange={(e) => setEmployeesValue1(e.target.value)}
                                                        className="flex-1"
                                                    />
                                                </div>
                                                {employeesOperator === 'is-between' && (
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-sm text-gray-600 dark:text-gray-400 min-w-[60px]">To:</span>
                                                        <Input
                                                            placeholder="e.g., 500, 1000"
                                                            value={employeesValue2}
                                                            onChange={(e) => setEmployeesValue2(e.target.value)}
                                                            className="flex-1"
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Revenue Filter */}
                                    <div className="space-y-1">
                                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Revenue Filter</label>
                                        <div className="space-y-2">
                                            {/* Operator Selection */}
                                            <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
                                                <button
                                                    onClick={() => setRevenueOperator('is-greater')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        revenueOperator === 'is-greater'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    Greater than (&gt;)
                                                </button>
                                                <button
                                                    onClick={() => setRevenueOperator('is-less')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        revenueOperator === 'is-less'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    Less than (&lt;)
                                                </button>
                                                <button
                                                    onClick={() => setRevenueOperator('is-between')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        revenueOperator === 'is-between'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    Between
                                                </button>
                                            </div>
                                            
                                            {/* Value Inputs */}
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm text-gray-600 dark:text-gray-400 min-w-[60px]">
                                                        {revenueOperator === 'is-greater' ? 'Greater than:' : 
                                                         revenueOperator === 'is-less' ? 'Less than:' : 'From:'}
                                                    </span>
                                                    <Input
                                                        placeholder="e.g., 5M, 100K, 1B"
                                                        value={revenueValue1}
                                                        onChange={(e) => setRevenueValue1(e.target.value)}
                                                        className="flex-1"
                                                    />
                                                </div>
                                                {revenueOperator === 'is-between' && (
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-sm text-gray-600 dark:text-gray-400 min-w-[60px]">To:</span>
                                                        <Input
                                                            placeholder="e.g., 10M, 500K, 2B"
                                                            value={revenueValue2}
                                                            onChange={(e) => setRevenueValue2(e.target.value)}
                                                            className="flex-1"
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Year Founded */}
                                    <div className="space-y-1">
                                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Year Founded</label>
                                        <div className="space-y-2">
                                            {/* Operator Selection */}
                                            <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
                                                <button
                                                    onClick={() => setYearOperator('is-greater')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        yearOperator === 'is-greater'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    After (&gt;)
                                                </button>
                                                <button
                                                    onClick={() => setYearOperator('is-less')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        yearOperator === 'is-less'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    Before (&lt;)
                                                </button>
                                                <button
                                                    onClick={() => setYearOperator('is-between')}
                                                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                                                        yearOperator === 'is-between'
                                                            ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                                                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                                    }`}
                                                >
                                                    Between
                                                </button>
                                            </div>
                                            
                                            {/* Value Inputs */}
                                            <div className="space-y-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm text-gray-600 dark:text-gray-400 min-w-[60px]">
                                                        {yearOperator === 'is-greater' ? 'After:' : 
                                                         yearOperator === 'is-less' ? 'Before:' : 'From:'}
                                                    </span>
                                                    <Input
                                                        placeholder="e.g., 2015, 2020"
                                                        value={yearValue1}
                                                        onChange={(e) => setYearValue1(e.target.value)}
                                                        className="flex-1"
                                                    />
                                                </div>
                                                {yearOperator === 'is-between' && (
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-sm text-gray-600 dark:text-gray-400 min-w-[60px]">To:</span>
                                                        <Input
                                                            placeholder="e.g., 2023, 2025"
                                                            value={yearValue2}
                                                            onChange={(e) => setYearValue2(e.target.value)}
                                                            className="flex-1"
                                                        />
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">BBB Rating</label>
                                    <Input
                                        placeholder="A+, A, B+, etc."
                                        value={bbbRatingFilter}
                                        onChange={(e) => setBbbRatingFilter(e.target.value)}
                                        className="w-full"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">City</label>
                                    <Input
                                        placeholder="Enter city..."
                                        value={cityFilter}
                                        onChange={(e) => setCityFilter(e.target.value)}
                                        className="w-full"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">State</label>
                                    <Input
                                        placeholder="Enter state..."
                                        value={stateFilter}
                                        onChange={(e) => setStateFilter(e.target.value)}
                                        className="w-full"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Source</label>
                                    <Input
                                        placeholder="Enter source..."
                                        value={sourceFilter}
                                        onChange={(e) => setSourceFilter(e.target.value)}
                                        className="w-full"
                                    />
                                </div>
                            </div>
                            <div className="flex justify-end">
                                <Button variant="ghost" size="sm" onClick={clearAllFilters}>
                                    <X className="h-4 w-4 mr-1" />
                                    Clear All Filters
                                </Button>
                            </div>
                        </div>
                    )}
                </CardHeader>
                <CardContent>
                    {/* Scrollable container */}
                    <div className="w-full overflow-x-auto relative border rounded-md">
                    <Table className="min-w-full text-sm ">
                        <TableHeader>
                        <TableRow>
                            {/* Sticky Checkbox Column */}
                            <TableHead className="sticky top-0 left-0 z-40 bg-background px-6 py-3 w-12 text-base font-bold text-white">
                            <Checkbox
                                checked={selectAll}
                                onCheckedChange={handleSelectAll}
                            />
                            </TableHead>
        
                            {/* Sticky Company Column */}
                            <TableHead className="sticky top-0 left-12 z-30 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap min-w-[200px] border-r">
                            Company
                            </TableHead>

                            <TableHead className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">
                            Actions
                            </TableHead>
        
                            {/* Remaining Headers */}
                            {[
                            "Industry",
                            "Links",
                            "Product/Service Category",
                            "Business Type (B2B, B2B2C)",
                            "Employees Count",
                            "Revenue",
                            "Year Founded",
                            "BBB Rating",
                            "Street",
                            "City",
                            "State",
                            "Company Phone",
                            "Source",
                            "Created Date",
                            "Updated",
                            ].map((label, i) => (
                            <TableHead
                                key={i}
                                className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap"
                            >
                                {label}
                            </TableHead>
                            ))}
                        </TableRow>
                        </TableHeader>
        
                        <tbody>
                        {currentItems.map((row, i) => (
                            <TableRow key={i} className="border-t">
                            {/* Sticky Checkbox Column */}
                            <TableCell className="sticky left-0 z-20 bg-inherit px-6 py-2 w-12">
                                <Checkbox
                                checked={selectedCompanies.includes(row.id)}
                                onCheckedChange={() => handleSelectCompany(row.id)}
                                />
                            </TableCell>
        
                            {/* Sticky Company Column */}
                            <TableCell className="sticky left-12 z-10 bg-inherit px-6 py-2 max-w-[240px] align-top border-r">
                                <ExpandableCell text={typeof row.company === 'object' ? JSON.stringify(row.company) : (row.company || "N/A")} />
                            </TableCell>

                            {/* Action Column */}
                            <TableCell className="px-6 py-2">
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <button className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-zinc-800 focus:outline-none">
                                            <MoreHorizontal className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                                        </button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="start">
                                        <DropdownMenuItem onClick={() => { setPopupData(row); setIsEditing(false); setPopupTab('overview'); }}>
                                            <Eye className="w-4 h-4 mr-2 text-blue-500" /> View Details
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => { setPopupData(row); setIsEditing(true); setPopupTab('overview'); }}>
                                            <Pencil className="w-4 h-4 mr-2 text-blue-600" /> Edit
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => { setNotesLeadId(row.lead_id || row.id); setNotesName(row.company); setNotesPopupOpen(true); }}>
                                            <StickyNote className={`w-4 h-4 mr-2 ${leadsWithNotes.has(String(row.lead_id || row.id || "")) ? "fill-current text-yellow-400" : "text-yellow-500"}`} /> Notes
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => handleOpenNews(row)}>
                                            <Newspaper className="w-4 h-4 mr-2 text-indigo-600" /> News
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => handleGenerateInsights(row)}>
                                            <BookOpen className="w-4 h-4 mr-2 text-green-600" /> Insights
                                        </DropdownMenuItem>
                                        <DropdownMenuItem onClick={() => router.push('/validators')}>
                                            <Shield className="w-4 h-4 mr-2 text-purple-600" /> Validators
                                            <NewTag text="NEW" />
                                        </DropdownMenuItem>
                                        <DropdownMenuSeparator />
                                        <DropdownMenuItem onClick={(e) => { e.preventDefault(); handleToggleFavorite(row.id); }}>
                                            <Star className={`w-4 h-4 mr-2 ${favoriteLeads.has(row.id) ? "text-yellow-500 fill-current" : "text-yellow-500"}`} />
                                            {favoriteLeads.has(row.id) ? "Unfavorite" : "Favorite"}
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </TableCell>
        
                            {/* Remaining Cells */}
                            {[
                                "industry",
                                "productCategory",
                                "businessType",
                                "employees",
                                "revenue",
                                "yearFounded",
                                "bbbRating",
                                "street",
                                "city",
                                "state",
                                "companyPhone",
                                "source",
                                "created",
                                "updated",
                            ].map((field, fieldIndex) => {
                                const rawValue = row[field];
                                const displayValue =
                                rawValue === null ||
                                rawValue === undefined ||
                                rawValue === ""
                                    ? "N/A"
                                    : typeof rawValue === 'object' 
                                        ? JSON.stringify(rawValue) 
                                        : String(rawValue);
        
                                const isUrl =
                                typeof rawValue === "string" &&
                                (rawValue.startsWith("http://") ||
                                    rawValue.startsWith("https://"));
        
                                const shortened =
                                isUrl && rawValue.length > 0
                                    ? rawValue
                                        .replace(/^https?:\/\//, "")
                                        .replace(/^www\./, "")
                                        .split("/")[0]
                                    : displayValue;
        
                                return (
                                <React.Fragment key={field}>
                                    <TableCell className="px-6 py-2 max-w-[240px] align-top">
                                        {isUrl ? (
                                        <a
                                            href={rawValue}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-blue-600 underline hover:text-blue-800 block truncate"
                                            title={rawValue}
                                        >
                                            {shortened}
                                        </a>
                                        ) : (
                                        <ExpandableCell text={displayValue} />
                                        )}
                                    </TableCell>

                                    {/* Inject Actions Cell after "industry" */}
                                    {field === "industry" && (
                                        <TableCell className="px-6 py-2 max-w-[240px] align-top space-x-2 whitespace-nowrap">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleActionPreview(row, 'website')}
                                                disabled={!row.website || normalizeWebsiteValue(row.website) === 'N/A'}
                                                className={normalizeWebsiteValue(row.website) === 'N/A' ? 'opacity-50 cursor-not-allowed' : ''}
                                                title="Website"
                                            >
                                                <Globe className="h-4 w-4 text-blue-600" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleActionPreview(row, 'linkedin')}
                                                disabled={!row.companyLinkedin || normalizeLinkedInValue(row.companyLinkedin) === 'N/A'}
                                                className={normalizeLinkedInValue(row.companyLinkedin) === 'N/A' ? 'opacity-50 cursor-not-allowed' : ''}
                                                title="LinkedIn"
                                            >
                                                <Linkedin className="h-4 w-4 text-blue-700" />
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => handleActionPreview(row, 'email')}
                                                disabled={!row.ownerEmail || normalizeEmailValue(row.ownerEmail) === 'N/A'}
                                                className={normalizeEmailValue(row.ownerEmail) === 'N/A' ? 'opacity-50 cursor-not-allowed' : ''}
                                                title="Send Email"
                                            >
                                                <Mail className="h-4 w-4 text-green-600" />
                                            </Button>
                                            {(row.street || row.city || row.state) && (
                                            <a
                                                href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${row.street || ""}, ${row.city || ""}, ${row.state || ""}`)}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-block p-1 rounded hover:bg-gray-200"
                                                title="Map Location"
                                            >
                                                <MapPin className="h-4 w-4 text-red-600" />
                                            </a>
                                            )}
                                        </TableCell>
                                    )}
                                </React.Fragment>
                                );
                            })}

                            </TableRow>
                        ))}
                        </tbody>
                    </Table>
                    </div>
                    <div className="flex flex-col md:flex-row justify-between items-center mt-4 gap-4 px-4 py-2">
                    <div className="text-sm text-muted-foreground">
                        Showing {indexOfFirstItem + 1}–
                        {Math.min(indexOfLastItem, scrapingHistory.length)} of{" "}
                        {scrapingHistory.length} results
                    </div>
        
                    <div className="flex items-center gap-3 px-3 py-2">
                        <Select
                        value={itemsPerPage.toString()}
                        onValueChange={(value) => {
                            setItemsPerPage(Number(value));
                            setCurrentPage(1);
                        }}
                        >
                        <SelectTrigger className="w-[120px]  text-black font-medium rounded-md hover:bg-[#6bb293]">
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
                                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                                aria-disabled={currentPage === 1}
                                className={
                                currentPage === 1
                                    ? "pointer-events-none opacity-50"
                                    : ""
                                }
                            />
                            </PaginationItem>
        
                            {Array.from({ length: totalPages }, (_, i) => i + 1)
                            .filter((page) => {
                                // show all if totalPages <= 7
                                if (totalPages <= 7) return true;
        
                                // show first, last, current, and neighbors
                                return (
                                page === 1 ||
                                page === totalPages ||
                                Math.abs(page - currentPage) <= 1
                                );
                            })
                            .reduce((acc, page, i, arr) => {
                                if (i > 0 && page - arr[i - 1] > 1) {
                                acc.push("ellipsis");
                                }
                                acc.push(page);
                                return acc;
                            }, [])
                            .map((page, idx) => (
                                <PaginationItem key={idx}>
                                {page === "ellipsis" ? (
                                    <PaginationEllipsis />
                                ) : (
                                    <PaginationLink
                                    isActive={page === currentPage}
                                    onClick={() => setCurrentPage(page)}
                                    className={`px-3 py-1 rounded-md text-sm font-medium ${
                                        page === currentPage
                                        ? " text-black" // active teal background
                                        : "text-black hover:bg-muted"
                                    }`}
                                    >
                                    {page}
                                    </PaginationLink>
                                )}
                                </PaginationItem>
                            ))}
        
                            <PaginationItem>
                            <PaginationNext
                                onClick={() =>
                                setCurrentPage((p) => Math.min(p + 1, totalPages))
                                }
                                aria-disabled={currentPage === totalPages}
                                className={
                                currentPage === totalPages
                                    ? "pointer-events-none opacity-50"
                                    : ""
                                }
                            />
                            </PaginationItem>
                        </PaginationContent>
                        </Pagination>
                    </div>
                    </div>
                </CardContent>
            </Card>

                        {/* Enrich Companies Section - Now using the modularized component */}
            <EnrichCompanies
              showNotification={showNotification}
              onCompanyEnriched={(enrichedData) => {
                // Handle enriched company data
                console.log("Company enriched:", enrichedData);
                // You can add additional logic here if needed
              }}
            />

            <PopupBig show={!!popupData} onClose={() => {
            setPopupData(null);
            setIsEditing(false);
            setPopupTab('overview');
            }}>
            {popupData && (
                <div className="space-y-8">
                    {/* Title and Tabs */}
                    <div className="border-b pb-4">
                        <h2 className="text-3xl font-semibold tracking-tight text-gray-900 dark:text-white">
                            Company Overview
                        </h2>
                    </div>
                    {/* Overview Content (only tab) */}
                    {isEditing ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Editable fields */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Company Name</label>
                                <Input value={popupData.company || ''} onChange={e => setPopupData({ ...popupData, company: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Website</label>
                                <Input value={popupData.website || ''} onChange={e => setPopupData({ ...popupData, website: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Industry</label>
                                <Input value={popupData.industry || ''} onChange={e => setPopupData({ ...popupData, industry: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Product/Service Category</label>
                                <Input value={popupData.productCategory || ''} onChange={e => setPopupData({ ...popupData, productCategory: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Business Type</label>
                                <Input value={popupData.businessType || ''} onChange={e => setPopupData({ ...popupData, businessType: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Employees</label>
                                <Input type="number" value={popupData.employees || ''} onChange={e => setPopupData({ ...popupData, employees: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Revenue</label>
                                <Input value={popupData.revenue || ''} onChange={e => setPopupData({ ...popupData, revenue: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Year Founded</label>
                                <Input value={popupData.yearFounded || ''} onChange={e => setPopupData({ ...popupData, yearFounded: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">BBB Rating</label>
                                <Input value={popupData.bbbRating || ''} onChange={e => setPopupData({ ...popupData, bbbRating: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Street</label>
                                <Input value={popupData.street || ''} onChange={e => setPopupData({ ...popupData, street: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">City</label>
                                <Input value={popupData.city || ''} onChange={e => setPopupData({ ...popupData, city: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">State</label>
                                <Input value={popupData.state || ''} onChange={e => setPopupData({ ...popupData, state: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Company Phone</label>
                                <Input value={popupData.companyPhone || ''} onChange={e => setPopupData({ ...popupData, companyPhone: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Source</label>
                                <Input value={popupData.source || ''} onChange={e => setPopupData({ ...popupData, source: e.target.value })} />
                            </div>
                        </div>
                    ) : (
                        // Prettified summary (existing code)
                        <>
                            <div className="mb-6">
                                <h2 className="text-2xl font-bold text-white mb-1">{popupData.company}</h2>
                                {popupData.industry && (
                                    <div className="text-base text-blue-200 mb-2">{popupData.industry}</div>
                                )}
                                {popupData.website && popupData.website !== 'N/A' && (
                                    <div className="mb-1">
                                        <span className="font-semibold text-gray-300">Website:</span> <a href={popupData.website.startsWith('http') ? popupData.website : `https://${popupData.website}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{popupData.website}</a>
                                    </div>
                                )}
                                <div className="mb-1">
                                    <span className="font-semibold text-gray-300">Location:</span> <span className="text-white">{[popupData.city, popupData.state].filter(Boolean).join(', ')}</span>
                                </div>
                                <div>
                                    <span className="font-semibold text-gray-300">Revenue:</span> <span className="text-yellow-400 font-bold">{popupData.revenue || 'N/A'}</span>
                                    <span className="ml-4 font-semibold text-gray-300">Employees:</span> <span className="text-yellow-300 font-bold">{popupData.employees || 'N/A'}</span>
                                </div>
                            </div>
                            {/* Contacts Table (if any) */}
                            {popupData.contacts && popupData.contacts.length > 0 && (
                                <div className="mt-8">
                                    <h3 className="text-xl font-semibold mb-2 text-gray-900 dark:text-white">Contacts</h3>
                                    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
                                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                            <thead className="bg-gray-100 dark:bg-zinc-800">
                                                <tr>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Name</th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Title</th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Email</th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">LinkedIn</th>
                                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Phone</th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white dark:bg-zinc-900 divide-y divide-gray-200 dark:divide-gray-700">
                                                {popupData.contacts.map((contact, idx) => (
                                                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-zinc-800">
                                                        <td className="px-4 py-2 whitespace-nowrap font-medium text-gray-900 dark:text-white">{`${contact.owner_first_name || ''} ${contact.owner_last_name || ''}`.trim() || 'N/A'}</td>
                                                        <td className="px-4 py-2 whitespace-nowrap text-gray-700 dark:text-gray-300">{contact.owner_title || 'N/A'}</td>
                                                        <td className="px-4 py-2 whitespace-nowrap text-blue-700 dark:text-blue-300">
                                                            {contact.owner_email && contact.owner_email !== 'N/A' ? (
                                                                <a href={`mailto:${contact.owner_email}`} className="hover:underline">{contact.owner_email}</a>
                                                            ) : 'N/A'}
                                                        </td>
                                                        <td className="px-4 py-2 whitespace-nowrap">
                                                            {contact.owner_linkedin && contact.owner_linkedin !== 'N/A' ? (
                                                                <a href={contact.owner_linkedin} target="_blank" rel="noopener noreferrer" className="text-blue-600 dark:text-blue-400 hover:underline">LinkedIn</a>
                                                            ) : 'N/A'}
                                                        </td>
                                                        <td className="px-4 py-2 whitespace-nowrap text-gray-700 dark:text-gray-300">{contact.owner_phone_number || 'N/A'}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                    {/* Action Buttons */}
                    <div className="flex justify-end gap-4 pt-4 border-t">
                        {isEditing ? (
                            <Button size="sm" onClick={handlePopupSave}>
                                Save Changes
                            </Button>
                        ) : null}
                    </div>
                </div>
            )}
            </PopupBig>

            {/* Notification */}
            <div className="flex justify-end mt-3 gap-3">
            <Notif
                show={notif.show}
                message={notif.message}
                type={notif.type}
                onClose={() => setNotif((prev) => ({ ...prev, show: false }))}
            />
            </div>

            <NotesPopup
                leadId={notesLeadId || ""}
                type="company"
                name={notesName}
                open={notesPopupOpen}
                onClose={() => setNotesPopupOpen(false)}
                baseUrl={DATABASE_URL_NOAPI || ""}
                onNoteStatusChange={(hasNote) => {
                    setLeadsWithNotes(prev => {
                        const newSet = new Set(prev);
                        const id = String(notesLeadId ?? "");
                        if (id) {
                            if (hasNote) newSet.add(id);
                            else newSet.delete(id);
                        }
                        return newSet;
                    });
                }}
            />

            {/* Action Preview Popup */}
            {actionPreviewPopup.show && (
                <Dialog open={actionPreviewPopup.show} onOpenChange={handleActionClose}>
                    <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                        <DialogHeader>
                            <DialogTitle className="text-2xl text-center">
                                {actionPreviewPopup.type === 'email' ? 'Email Address' : 
                                actionPreviewPopup.type === 'linkedin' ? 'LinkedIn Profile' : 'Website'}
                            </DialogTitle>
                        </DialogHeader>
                        <div className="py-4">
                            <div className="mb-4">
                                <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                                    {actionPreviewPopup.company?.company}
                                </p>
                                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                                    <p className="font-mono text-sm break-all">
                                        {actionPreviewPopup.type === 'email' && actionPreviewPopup.company?.ownerEmail}
                                        {actionPreviewPopup.type === 'linkedin' && actionPreviewPopup.company?.companyLinkedin}
                                        {actionPreviewPopup.type === 'website' && actionPreviewPopup.company?.website}
                                    </p>
                                </div>
                            </div>
                            <p className="text-gray-600 dark:text-gray-300 text-sm">
                                {actionPreviewPopup.type === 'email' ? 'This will open your default email client to compose a new message.' :
                                actionPreviewPopup.type === 'linkedin' ? 'This will open the LinkedIn profile in a new tab.' :
                                'This will open the website in a new tab.'}
                            </p>
                        </div>
                        <div className="flex justify-end gap-3 pt-4">
                            <Button variant="outline" onClick={handleActionClose}>
                                Cancel
                            </Button>
                            <Button onClick={() => handleActionConfirm(actionPreviewPopup.type)}>
                                {actionPreviewPopup.type === 'email' ? 'Send Email' :
                                actionPreviewPopup.type === 'linkedin' ? 'Open LinkedIn' :
                                'Open Website'}
                            </Button>
                        </div>
                    </DialogContent>
                </Dialog>
            )}

            {newsModalOpen && newsCompany && (
  <Dialog open={newsModalOpen} onOpenChange={handleNewsModalOpenChange}>
    <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle className="text-2xl font-bold">{newsCompany.company} News & Insights</DialogTitle>
        <div className="flex space-x-4 mt-4 border-b border-gray-700">
          <button
            onClick={() => setNewsTab("latest")}
            className={`px-4 py-2 font-medium ${newsTab === 'latest' ? 'border-b-2 border-indigo-500 text-indigo-400' : 'text-gray-400 hover:text-gray-300'}`}
          >
            Latest News
          </button>
          <button
            onClick={() => setNewsTab("saved")}
            className={`px-4 py-2 font-medium ${newsTab === 'saved' ? 'border-b-2 border-indigo-500 text-indigo-400' : 'text-gray-400 hover:text-gray-300'}`}
          >
            Saved Insights
          </button>
        </div>
      </DialogHeader>
      <div className="py-4">
        {newsTab === "latest" && (
          <>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">AI-powered news for <b>{newsCompany.company}</b></span>
              <div className="flex flex-col items-end space-y-2">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" disabled={newsLoading}>
                      <RefreshCw className={`h-4 w-4 mr-1 ${newsLoading ? 'animate-spin' : ''}`} />
                      Fetch News
                      <ChevronDown className="h-4 w-4 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => handleFetchNews('day')}>Today</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFetchNews('week')}>This Week</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFetchNews('month')}>This Month</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFetchNews('year')}>This Year</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFetchNews('5years')}>Last 5 Years</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                
                {/* Stop Button - appears when loading */}
                {newsLoading && (
                  <Button
                    onClick={handleStopNews}
                    variant="destructive"
                    size="sm"
                    className="w-full"
                  >
                    Stop
                  </Button>
                )}
              </div>
            </div>
            {newsLoading && (
              <div className="text-gray-100 text-center py-8 space-y-4">
                {/* Progress Message */}
                <div className="text-lg font-medium">{newsProgress.message || 'Loading...'}</div>
                
                {/* Progress Bar */}
                {newsProgress.total > 0 && (
                  <div className="max-w-md mx-auto px-4">
                    <div className="flex justify-between text-sm text-gray-400 mb-2">
                      <span>Processing articles</span>
                      <span>{newsProgress.processed} / {newsProgress.total}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-green-400 to-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${(newsProgress.processed / newsProgress.total) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                
                {/* Status */}
                <div className="text-sm text-gray-400">
                  Status: <span className="text-gray-200 capitalize">{newsProgress.status}</span>
                </div>
                
                {/* Live Article Preview */}
                {newsProgress.articles.length > 0 && (
                  <div className="mt-4">
                    <div className="text-sm text-gray-400 mb-2">Recently processed:</div>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {newsProgress.articles.slice(-3).map((article, idx) => (
                        <div key={idx} className="text-xs text-gray-300 px-4 truncate">
                          • {article.title}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            {newsError && <div className="text-red-500 py-2">{newsError}</div>}
            <div className="space-y-4">
              {newsList.length === 0 && !newsLoading && <div className="text-gray-400">No news found.</div>}
              {newsList.map((news) => (
                <div key={news.link + news.title} className="border rounded-lg p-4 bg-gray-50 dark:bg-zinc-900">
                  {/* Title */}
                  <div className="font-bold text-lg text-indigo-700 dark:text-indigo-300 mb-1">
                    {news.title}
                  </div>
                  {/* Published Date */}
                  {news.published && (
                    <div className="text-xs text-gray-500 mb-2">
                      {new Date(news.published).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                    </div>
                  )}
                  {/* Source Link */}
                  {news.link && (
                    <a href={news.link} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 underline mb-2 inline-block">
                      View Source
                    </a>
                  )}
                  {news.ai_insights && news.ai_insights.error === 'No content fetched' ? (
                    <div className="mt-2">
                      <div className="text-gray-400 italic">Our AI cannot access this source.</div>
                    </div>
                  ) : (
                    <>
                      {/* Summary (if present) */}
                      {news.summary && (
                        <div className="text-gray-700 dark:text-gray-200 mt-2">{news.summary}</div>
                      )}
                      {news.tags && typeof news.tags === 'object' && news.tags !== null &&
                        (news.tags.event_type || news.tags.relevancy || news.tags.topic) && (
                          <div className="flex flex-wrap gap-2 mt-2">
                            {news.tags.event_type && (
                              <span className="bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded text-xs font-semibold">
                                Event Type: {news.tags.event_type}
                              </span>
                            )}
                            {news.tags.relevancy && (
                              <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-semibold">
                                Relevancy: {news.tags.relevancy}
                              </span>
                            )}
                            {news.tags.topic && (
                              Array.isArray(news.tags.topic)
                                ? news.tags.topic.map((topic, i) => (
                                    <span key={i} className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold">
                                      Topic: {topic}
                                    </span>
                                  ))
                                : <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold">
                                    Topic: {news.tags.topic}
                                  </span>
                            )}
                          </div>
                      )}
                      {/* AI Insights Section - only show key insights as bullet points in the box */}
                      {news.ai_insights && (
                        <div className="mt-3 p-3 rounded bg-indigo-50 dark:bg-zinc-800 border border-indigo-200 dark:border-indigo-700">
                          {news.ai_insights.error ? (
                            <div className="text-red-500 text-xs">
                              AI Insights unavailable: {news.ai_insights.error}
                            </div>
                          ) : (
                            (() => {
                              try {
                                // Handle different formats of ai_insights
                                let insightsArray;
                                if (typeof news.ai_insights === 'string') {
                                  // Parse JSON string if it's a string
                                  const insightsData = JSON.parse(news.ai_insights);
                                  insightsArray = insightsData.insights || [];
                                } else if (Array.isArray(news.ai_insights)) {
                                  insightsArray = news.ai_insights;
                                } else if (typeof news.ai_insights === 'object' && news.ai_insights.insights) {
                                  // Handle case where insights might be wrapped in markdown code blocks
                                  const insights = news.ai_insights.insights;
                                  if (Array.isArray(insights)) {
                                    insightsArray = [];
                                    insights.forEach(insight => {
                                      if (typeof insight === 'string' && insight.includes('```json')) {
                                        // Extract JSON from markdown code block
                                        const jsonMatch = insight.match(/```json\s*(\{[\s\S]*?\})\s*```/);
                                        if (jsonMatch) {
                                          try {
                                            const parsed = JSON.parse(jsonMatch[1]);
                                            if (parsed.insights && Array.isArray(parsed.insights)) {
                                              // Add all insights from the parsed JSON
                                              insightsArray.push(...parsed.insights);
                                            } else {
                                              insightsArray.push(insight);
                                            }
                                          } catch (e) {
                                            insightsArray.push(insight);
                                          }
                                        } else {
                                          insightsArray.push(insight);
                                        }
                                      } else {
                                        insightsArray.push(insight);
                                      }
                                    });
                                  } else {
                                    insightsArray = [];
                                  }
                                } else if (typeof news.ai_insights === 'object' && news.ai_insights.error) {
                                  return <div className="text-red-500 text-sm">AI Insights unavailable: {news.ai_insights.error}</div>;
                                } else {
                                  return <div className="text-gray-500 text-sm">No insights available</div>;
                                }

                                if (insightsArray.length === 0) {
                                  return <div className="text-gray-500 text-sm">No insights available</div>;
                                }

                                return (
                                  <ul className="list-disc ml-6 text-gray-800 dark:text-gray-200">
                                    {insightsArray.map((insight, idx) => (
                                      <li key={idx}>{renderInsightWithItalics(insight)}</li>
                                    ))}
                                  </ul>
                                );
                              } catch (error) {
                                console.error('Error parsing insights:', error);
                                // If parsing fails, try to display the raw string as a fallback
                                return (
                                  <div className="text-gray-800 dark:text-gray-200 text-sm">
                                    {typeof news.ai_insights === 'string' ? news.ai_insights : 'Error parsing insights'}
                                  </div>
                                );
                              }
                            })()
                          )}
                        </div>
                      )}
                    </>
                  )}
                  <div className="flex justify-end mt-2">
                    <Button variant="outline" size="sm" onClick={() => handleSaveInsight(news)}>
                      <Save className="h-4 w-4 mr-1" /> Save as Insight
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
        {newsTab === "saved" && (
          <div className="space-y-4">
            {savedInsights.filter(insight => insight.lead_id === newsCompany.lead_id || insight.lead_id === newsCompany.id).length === 0 && <div className="text-gray-400">No saved insights yet.</div>}
            {savedInsights
              .filter(insight => insight.lead_id === newsCompany.lead_id || insight.lead_id === newsCompany.id)
              .map((news) => (
                <div key={news.id} className="border rounded-lg p-4 bg-gray-50 dark:bg-zinc-900 relative">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-bold text-lg text-indigo-700 dark:text-indigo-300">{news.headline}</div>
                      {news.source && (
                        <div className="mt-1">
                          <a href={news.source} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 underline">Source</a>
                        </div>
                      )}
                    </div>
                    {/* Actions dropdown at top right */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button className="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-zinc-800 focus:outline-none">
                          <MoreHorizontal className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => {
                          const text = (news.insights || []).map((i) => `• ${i}`).join('\n');
                          navigator.clipboard.writeText(text);
                        }}>
                          <Copy className="w-4 h-4 mr-2" /> Copy Insights
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDeleteInsight(news)} className="text-red-600">
                          <Trash2 className="w-4 h-4 mr-2" /> Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  {/* Date */}
                  {news.published_at && (
                    <div className="text-xs text-gray-500 mt-1">
                      {new Date(news.published_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                    </div>
                  )}
                  {/* Insights */}
                  {news.insights && news.insights.length > 0 && (
                    <div className="mt-2 bg-indigo-50 dark:bg-zinc-800 rounded p-3">
                      <div className="font-semibold text-sm text-gray-800 dark:text-gray-100 mb-2">Insights</div>
                      {(() => {
                        // For saved insights, insights is already an array
                        if (Array.isArray(news.insights) && news.insights.length > 0) {
                          // Handle case where insights might be wrapped in markdown code blocks
                          const processedInsights = [];
                          news.insights.forEach(insight => {
                            if (typeof insight === 'string' && insight.includes('```json')) {
                              // Extract JSON from markdown code block
                              const jsonMatch = insight.match(/```json\s*(\{[\s\S]*?\})\s*```/);
                              if (jsonMatch) {
                                try {
                                  const parsed = JSON.parse(jsonMatch[1]);
                                  if (parsed.insights && Array.isArray(parsed.insights)) {
                                    // Add all insights from the parsed JSON
                                    processedInsights.push(...parsed.insights);
                                  } else {
                                    processedInsights.push(insight);
                                  }
                                } catch (e) {
                                  processedInsights.push(insight);
                                }
                              } else {
                                processedInsights.push(insight);
                              }
                            } else {
                              processedInsights.push(insight);
                            }
                          });

                          return (
                            <ul className="list-disc pl-6 text-gray-800 dark:text-gray-200 text-sm">
                              {processedInsights.map((insight, idx) => (
                                <li key={idx}>{renderInsightWithItalics(insight)}</li>
                              ))}
                            </ul>
                          );
                        } else {
                          return <div className="text-gray-500 text-sm">No insights available</div>;
                        }
                      })()}
                    </div>
                  )}
                  {/* Tags */}
                  {news.tags && typeof news.tags === 'object' && news.tags !== null &&
                    (news.tags.event_type || news.tags.relevancy || news.tags.topic) && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {news.tags.event_type && (
                          <span className="bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded text-xs font-semibold">
                            Event Type: {news.tags.event_type}
                          </span>
                        )}
                        {news.tags.relevancy && (
                          <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-semibold">
                            Relevancy: {news.tags.relevancy}
                          </span>
                        )}
                        {news.tags.topic && (
                          Array.isArray(news.tags.topic)
                            ? news.tags.topic.map((topic, i) => (
                                <span key={i} className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold">
                                  Topic: {topic}
                                </span>
                              ))
                            : <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold">
                                Topic: {news.tags.topic}
                              </span>
                        )}
                      </div>
                  )}
                </div>
              ))}
          </div>
        )}
      </div>
    </DialogContent>
  </Dialog>
)}

        </main>
      </div>
    </div>
  );
}