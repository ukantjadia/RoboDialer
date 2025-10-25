"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { ScraperResults } from "@/components/scraper-results"
import axios from "axios"
import { AlertCircle, DatabaseIcon } from "lucide-react"
import { useRouter } from "next/navigation";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select"
import USFlag from '@/public/images/flags/us.svg';
import CAFlag from '@/public/images/flags/ca.svg';
import GBFlag from '@/public/images/flags/gb.svg';
import FRFlag from '@/public/images/flags/fr.svg';

const SCRAPER_API = `${process.env.NEXT_PUBLIC_BACKEND_URL_P1}/scrape-stream`;
const FETCH_INDUSTRIES_API = `${process.env.NEXT_PUBLIC_DATABASE_URL}/industries`;
const FETCH_DB_API = `${process.env.NEXT_PUBLIC_DATABASE_URL}/lead_scrape`;

type StateCities = {
  [countryCode: string]: {
    [stateCode: string]: string[];
  };
};
// Define interfaces for type safety
interface LeadData {
  lead_id?: string; // from backend
  Company?: string;
  company?: string;
  Website?: string;
  website?: string;
  Industry?: string;
  industry?: string;
  Street?: string;
  street?: string;
  City?: string;
  city?: string;
  State?: string;
  state?: string;
  BBB_rating?: string;
  bbb_rating?: string;
  Business_phone?: string;
  business_phone?: string;
  id?: number;
  company_phone?: string;
  [key: string]: any; // For any other properties we might not know about
}

interface FormattedLead {
  id: number;             // local index
  lead_id: string;        // unique identifier from DB
  company: string;
  website: string;
  industry: string;
  street: string;
  city: string;
  state: string;
  bbb_rating: string;
  business_phone: string;
}

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

export function Scraper() {
  const [isScrapingActive, setIsScrapingActive] = useState(false)
  const [progress, setProgress] = useState(0)
  const [showResults, setShowResults] = useState(false)
  const [needMoreLeads, setNeedMoreLeads] = useState(false)
  const [scrapingSource, setScrapingSource] = useState<'database' | 'scraper'>('database')
  
  // Industry dropdown states
  const [industries, setIndustries] = useState<string[]>([]); // Full list from API
  const [filteredIndustries, setFilteredIndustries] = useState<string[]>([]); // Filtered list
  const [showDropdown, setShowDropdown] = useState(false);

  // Search criteria state
  const [industry, setIndustry] = useState("")
  const [country, setCountry] = useState("")
  const [state, setState] = useState("")
  const [city, setCity] = useState("")
  const [scrapedResults, setScrapedResults] = useState<FormattedLead[]>([])
  const controllerRef = useRef<{ abort: () => void } | null>(null)

  // Location states
  const [rawCities, setRawCities] = useState<StateCities>({});
  const [locationInput, setLocationInput] = useState('');
  const [locationSuggestions, setLocationSuggestions] = useState<string[]>([]);
  const [showLocationDropdown, setShowLocationDropdown] = useState(false);
  const [countryCode, setCountryCode] = useState<'USA' | 'CAN' | 'UK' | 'FRA'>('USA');
  const [isLoadingLocations, setIsLoadingLocations] = useState(false);
  const debouncedLocationInput = useDebounce(locationInput, 300);

  const router = useRouter();
  const countryOptions = [
    { code: 'USA', label: 'United States', flag: USFlag },
    { code: 'CAN', label: 'Canada', flag: CAFlag },
    { code: 'UK', label: 'United Kingdom', flag: GBFlag },
    { code: 'FRA', label: 'France', flag: FRFlag }
  ] as const;

  // Track companies we've already seen to prevent duplicates
  const seenCompaniesRef = useRef<Set<string>>(new Set());

  // Clear revenueMap on component mount to avoid stale data
  // useEffect(() => {
  //   sessionStorage.removeItem("revenueMap");
  // }, []);

    useEffect(() => {
    const searchLocations = async () => {
      console.log("Debounced search triggered:", debouncedLocationInput, "Country:", countryCode);
      
      if (debouncedLocationInput.length < 3) {
        setLocationSuggestions([]);
        setShowLocationDropdown(false);
        return;
      }

      setIsLoadingLocations(true);
      try {
        const url = `${process.env.NEXT_PUBLIC_DATABASE_URL}/states_cities?q=${encodeURIComponent(debouncedLocationInput)}&country=${countryCode}&limit=10`;
        console.log("Fetching from URL:", url);
        
        const response = await fetch(url, {
          credentials: 'include'
        });
        
        console.log("Response status:", response.status);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log("API Response:", data);
        console.log("Type of data:", typeof data);
        console.log("Is Array:", Array.isArray(data));
        
        const suggestions: string[] = Array.isArray(data) ? data : [];
        console.log("Final suggestions:", suggestions);
        
        setLocationSuggestions(suggestions);
        setShowLocationDropdown(suggestions.length > 0);
      } catch (error) {
        console.error("Error fetching location suggestions:", error);
        setLocationSuggestions([]);
        setShowLocationDropdown(false);
      } finally {
        setIsLoadingLocations(false);
      }
    };

    searchLocations();
  }, [debouncedLocationInput, countryCode]);

  useEffect(() => {
    const fetchIndustries = async () => {
      try {
        const response = await fetch(FETCH_INDUSTRIES_API, {
          credentials: 'include',
        });
        const data = await response.json();
        if (data && Array.isArray(data.industries)) {
          setIndustries(data.industries);
        } else {
          console.error("Invalid API response format:", data);
        }
      } catch (error) {
        console.error("Error fetching industries:", error);
      }
    };

    fetchIndustries();
  }, []);

  const handleIndustryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setIndustry(value);

    if (value.length >= 3) {
      const filtered = industries.filter((ind) =>
        ind.toLowerCase().startsWith(value.toLowerCase())
      );
      setFilteredIndustries(filtered);
      setShowDropdown(true);
    } else {
      setShowDropdown(false);
    }
  };

  // Format data consistently across all sources
  const formatLeadData = (item: LeadData, index: number): FormattedLead => ({
    id: index, // internal use for React keys or pagination
    lead_id: item.lead_id || "", // real DB identifier, passed to /leads/multiple
    company: item.Company || item.company || "",
    website: item.Website || item.website || "",
    industry: item.Industry || item.industry || "",
    street: item.Street || item.street || "",
    city: item.City || item.city || "",
    state: item.State || item.state || "",
    bbb_rating: item.BBB_rating || item.bbb_rating || "",
    business_phone: item.Business_phone || item.business_phone || item.company_phone || "",
  });

  // Add new leads while avoiding duplicates
  const addNewLeads = (existingLeads: FormattedLead[], newLeads: FormattedLead[]): FormattedLead[] => {
    const combinedResults = [...existingLeads];

    // Use our ref to track seen companies instead of recreating the set each time
    newLeads.forEach((item: FormattedLead) => {
      const companyLower = item.company.toLowerCase().trim();
      if (companyLower && !seenCompaniesRef.current.has(companyLower)) {
        seenCompaniesRef.current.add(companyLower);
        combinedResults.push(item);
      }
    });

    return combinedResults;
  };

  const handleStartScraping = async () => {
    setIsScrapingActive(true);
    setProgress(5);
    setScrapingSource('scraper');

    // Don't hide results if we're appending to existing results
    if (scrapedResults.length === 0) {
      setShowResults(true);
      // Reset our seen companies set if we're starting fresh
      seenCompaniesRef.current = new Set();
    } else {
      // Initialize our seen companies set with existing companies if we're appending
      scrapedResults.forEach(item => {
        seenCompaniesRef.current.add(item.company.toLowerCase().trim());
      });
    }

    interface Batch {
      batch: number;
      new_items: LeadItem[];
      total_scraped: number;
      elapsed_time: number;
      processed_count: number;
    }

    interface LeadItem {
      [key: string]: any; // For any properties with unknown structure
    }

    // Set up debugging variables to track data
    let totalProcessedItems = 0;
    let allBatches: Batch[] = [];
    let receivedBatchIds = new Set<number>(); // Track received batch IDs to prevent duplicates

    // Create query parameters with separate location fields
    const queryParams = new URLSearchParams({
      industry,
      location: buildLocation()
    });

    // Create EventSource connection with explicit parameters
    const url = `${SCRAPER_API}?${queryParams.toString()}`;
    // console.log("Connecting to stream URL:", url);

    const eventSource = new EventSource(url);

    controllerRef.current = {
      abort: () => {
        console.log("Manually closing EventSource connection");
        eventSource.close();
      }
    };

    // Track connection state
    eventSource.onopen = () => {
      // console.log("EventSource connection opened successfully");
    };

    eventSource.addEventListener("init", (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Init event received:", data);
        setProgress(10);
      } catch (err) {
        console.error("Failed to parse init event:", event.data, err);
      }
    });

    eventSource.addEventListener("batch", (event) => {
      try {
        const parsed = JSON.parse(event.data);

        // Check if we've already processed this batch
        if (parsed.batch && receivedBatchIds.has(parsed.batch)) {
          // console.log(`Skipping duplicate batch ${parsed.batch}`);
          return;
        }

        // Add batch ID to tracking set
        if (parsed.batch) {
          receivedBatchIds.add(parsed.batch);
        }

        allBatches.push(parsed); // Store all batches for debugging

        const newItems = parsed.new_items || [];
        totalProcessedItems += newItems.length;

        // console.log(`Batch ${parsed.batch} received: ${newItems.length} new items, total batched: ${totalProcessedItems}`);
        // console.log("Sample item:", newItems.length > 0 ? newItems[0] : "No items");

        if (!Array.isArray(newItems)) {
          console.warn("Expected new_items to be an array, got:", typeof newItems);
          return;
        }

        if (newItems.length === 0) {
          console.log("Received empty batch, skipping processing");
          return;
        }

        // Format the new items with proper IDs
        const formattedItems = newItems.map((item: LeadItem, index: number) =>
          formatLeadData(item, Date.now() + index)
        );

        // Add new items to results, avoiding duplicates
        setScrapedResults((prev) => {
          const updatedResults = addNewLeads(prev, formattedItems);
          // console.log(`Current lead count: ${updatedResults.length}`);

          // NEW: Check if we've reached the limit
          if (updatedResults.length >= 500) {
            console.log("Reached 500 leads limit, stopping scraper");
            eventSource.close();
            setIsScrapingActive(false);
            setProgress(100);
            return updatedResults.slice(0, 500); // Ensure exactly 500
          }

          return updatedResults;
        });

        // Update progress based on actual data received
        // Calculate progress as a percentage of expected total (100 leads)
        setProgress((prev) => {
          // Calculate a dynamic progress that increases with each batch
          // but slows down as we approach 95% to avoid jumping too quickly
          const baseProgress = Math.min(10 + (totalProcessedItems / 10), 95);
          return Math.max(prev, baseProgress); // Never decrease progress
        });
      } catch (err) {
        console.error("Failed to parse batch event:", err);
        console.error("Raw event data:", event.data);
      }
    });

    // Add handler for the 'complete' event that backend sends
    eventSource.addEventListener("complete", (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Complete event received:", data);
      } catch (err) {
        console.error("Failed to parse complete event:", err);
      }
    });

    eventSource.addEventListener("ping", (event) => {
      console.log("Heartbeat:", JSON.parse(event.data));
    });

    eventSource.addEventListener("done", (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("Done event received:", data);
        console.log("Total items received across all batches:", totalProcessedItems);
        console.log("All batches summary:", allBatches.map((b: Batch) => b.new_items?.length || 0));

        setProgress(100);
        setIsScrapingActive(false);
        setScrapedResults((currentResults) => {
          console.log(`Final lead count: ${currentResults.length}`);
          return currentResults;
        });
      } catch (err) {
        console.error("Failed to parse done event:", err);
      } finally {
        console.log("Closing EventSource connection");
        eventSource.close();
      }
    });

    // Error handler 
    eventSource.onerror = (err) => {
      console.error("EventSource error:", err);
      setIsScrapingActive(false);
      setProgress(100);
      console.log("Closing EventSource connection due to error");
      eventSource.close();
    };
  };

  const handleCollectData = async () => {
    setIsScrapingActive(true)
    setProgress(0)
    setShowResults(false)
    setScrapingSource('database')

    // Reset our seen companies set
    seenCompaniesRef.current = new Set();

    const controller = new AbortController()
    controllerRef.current = {
      abort: () => controller.abort()
    };

    try {
      const response = await axios.post(
        FETCH_DB_API,
        {
          industry,
          location: buildLocation()
        },
        {
          signal: controller.signal,
          withCredentials: true
        }
      )

      const data = response.data
      const formattedData = data.map((item: LeadData, index: number) => formatLeadData(item, index));

      // Initialize our seen companies with these results
      formattedData.forEach((item: FormattedLead) => {
        if (item.company.trim()) {
          seenCompaniesRef.current.add(item.company.toLowerCase().trim());
        }
      });

      setScrapedResults(formattedData)
      setShowResults(true)
      setNeedMoreLeads(formattedData.length < 100)
    } catch (error: any) {
      if (axios.isCancel(error)) {
        console.warn("Database fetch canceled")
      } else {
        console.error("Database fetch failed:", error)
      }
    } finally {
      setIsScrapingActive(false)
      setProgress(100)
      controllerRef.current = null
    }
  }

  const handleClearSearch = () => {
    setIndustry('');
    setLocationInput('');
    setShowResults(false);
    setScrapedResults([]);
    setNeedMoreLeads(false);
    seenCompaniesRef.current = new Set();
  };

  const handleCancelScraping = () => {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    setIsScrapingActive(false);
    setProgress(0);
  };

    const handleLocationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocationInput(value);
    console.log("Location input changed to:", value);
  };

  const buildLocation = () => {
    const suggestions = Array.isArray(locationSuggestions) ? locationSuggestions : [];
    const trimmedInput = locationInput.trim();

    if (suggestions.includes(trimmedInput) || /^.+,\s*[A-Z]{2,3}$/.test(trimmedInput)) {
      return `${trimmedInput}, ${countryCode}`;
    }
    return '';
  };

  // Add this useEffect after your other useEffects
  useEffect(() => {
    const deduped = new Set(scrapedResults.map(l => l.company.toLowerCase().trim()));
    setNeedMoreLeads(deduped.size < 100);
  }, [scrapedResults]);

  useEffect(() => {
    const saved = localStorage.getItem("scrapedResults");
    if (saved) {
      try {
        const parsed: FormattedLead[] = JSON.parse(saved);
        if (parsed.length > 0) {
          setScrapedResults(parsed);
          setShowResults(true);
          seenCompaniesRef.current = new Set(parsed.map(l => l.company.toLowerCase().trim()));
        }
      } catch (err) {
        console.error("Failed to parse saved scraped results:", err);
      }
    }
  }, []);

  useEffect(() => {
    if (scrapedResults.length > 0) {
      sessionStorage.setItem("leads", JSON.stringify(scrapedResults));
    }
  }, [scrapedResults]);


  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Company Finder</h2>
          <p className="text-muted-foreground">Find companies by industry and location</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Search Criteria</CardTitle>
          <CardDescription>Enter industry and location to find companies</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-6">
            <div className="flex flex-row items-end justify-between gap-4 w-full">
              <div className="flex flex-col flex-1 min-w-0 relative">
                <Label htmlFor="industry">Industry</Label>
                <Input
                  id="industry"
                  placeholder="Enter industry (e.g. Software, Healthcare)"
                  value={industry}
                  onChange={handleIndustryChange}
                  onFocus={() => {
                    if (industry.trim() !== "") {
                      setShowDropdown(true);
                    }
                  }}
                  onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
                  className="mt-1 h-10 text-sm"
                />
                {showDropdown && (
                  <ul
                    className="absolute left-0 top-full w-full border border-border rounded max-h-52 overflow-y-auto z-[1000] shadow-lg mt-1 bg-background text-foreground transition-colors duration-150"
                  >
                    {filteredIndustries.map((ind, index) => (
                      <li
                        key={index}
                        className="px-3 py-2 cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors duration-100"
                        onClick={() => {
                          setIndustry(ind);
                          setShowDropdown(false);
                        }}
                      >
                        {ind}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="flex flex-col flex-1 min-w-0 relative">
                <Label htmlFor="location">Location</Label>
                <div className="flex items-center gap-1 w-full">
                  {/* Country Selector */}
                  <div className="w-24">
                    <Select value={countryCode} onValueChange={(value) => {
                      setCountryCode(value as 'USA' | 'CAN' | 'UK')
                      setLocationInput('');
                      setLocationSuggestions([]);
                      setShowLocationDropdown(false);
                    }}>
                      <SelectTrigger className="h-10 text-sm pl-2 pr-2 bg-muted border rounded flex items-center justify-start">
                        <SelectValue>
                          <div className="flex items-center gap-2">
                            <img
                              src={countryOptions.find(opt => opt.code === countryCode)?.flag.src}
                              alt=""
                              className="w-5 h-5"
                            />
                            <span className="text-sm font-medium">{countryCode}</span>
                          </div>
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {countryOptions.map(({ code, label, flag }) => (
                          <SelectItem key={code} value={code} className="pl-2 pr-3 [&>svg]:hidden">
                            <div className="flex items-center gap-2">
                              <img src={flag.src} alt={code} className="w-5 h-5" />
                              <span>{label}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Location Input */}
                  <Input
                    id="location"
                    placeholder="Enter city or state"
                    value={locationInput}
                    onChange={handleLocationChange}
                    onFocus={() => locationInput.length >= 3 && setShowLocationDropdown(true)}
                    onBlur={() => setTimeout(() => setShowLocationDropdown(false), 200)}
                    className="flex-1 h-10 text-sm"
                  />
                  {showLocationDropdown && (
                    <ul className="absolute left-0 top-full w-full border border-border rounded max-h-52 overflow-y-auto z-[1000] shadow-lg mt-1 bg-background text-foreground transition-colors duration-150">
                      {isLoadingLocations ? (
                        <li className="px-3 py-2 text-muted-foreground">
                          Loading suggestions...
                        </li>
                      ) : locationSuggestions.length > 0 ? (
                        locationSuggestions.map((loc, index) => (
                          <li
                            key={index}
                            className="px-3 py-2 cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors duration-100"
                            onMouseDown={(e) => e.preventDefault()}
                            onClick={() => {
                              setLocationInput(loc);
                              setShowLocationDropdown(false);
                            }}
                          >
                            {loc}
                          </li>
                        ))
                      ) : (
                        <li className="px-3 py-2 text-muted-foreground">
                          No locations found
                        </li>
                      )}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
        <CardFooter className="flex justify-between">
          <Button variant="outline" onClick={handleClearSearch}>
            Clear
          </Button>
          <div className="flex gap-2">
            <Button
              className="bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600"
              onClick={handleCollectData}
              disabled={isScrapingActive || !industry || !buildLocation()}
            >
              <DatabaseIcon className="mr-2 h-4 w-4" />
              Find Companies
            </Button>
            <Button
              variant="destructive"
              disabled={!isScrapingActive}
              onClick={handleCancelScraping}
            >
              Cancel
            </Button>
          </div>
        </CardFooter>
      </Card>

      {isScrapingActive && (
        <Card>
          <CardHeader>
            <CardTitle>Search in Progress</CardTitle>
            <CardDescription>
              {scrapingSource === 'database' ? 'Finding' : 'Scraping additional'} companies in {locationInput} within the {industry} industry
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
              <p className="text-sm text-muted-foreground mt-2">
                This may take a few minutes depending on the search criteria
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {showResults && (
        <>
          {needMoreLeads && !isScrapingActive && (
            <div className="bg-muted/50 border border-border rounded-md p-4 flex items-center justify-between mb-4">
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 mr-3 flex-shrink-0 text-muted-foreground" />
                <div>
                  <p className="font-medium text-foreground">Only {scrapedResults.length} leads found</p>
                  <p className="text-sm text-muted-foreground">We recommend at least 100 leads for best results.</p>
                </div>
              </div>
              <Button
                onClick={handleStartScraping}
                className="bg-amber-500 hover:bg-amber-600 text-white ml-4 flex-shrink-0"
              >
                <AlertCircle className="mr-2 h-4 w-4" />
                Scrape More Leads
              </Button>
            </div>
          )}
          <ScraperResults
            data={scrapedResults}
            industry={industry}
            location={locationInput}
            country={countryCode}
            isScrapingActive={isScrapingActive}
          />
        </>
      )}
    </div>
  )
}