"use client";

import { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { RefreshCw, ChevronDown, Save, BookOpen, MoreVertical, Copy, Trash2, Newspaper, Square } from "lucide-react";
import axios from "axios";

const AI_NEWS_API_URL = process.env.NEXT_PUBLIC_AI_NEWS_API_URL;
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;
const DATABASE_URL_NOAPI = DATABASE_URL?.replace(/\/api\/?$/, "");

const newsRangeLabel = {
  today: "Today",
  week: "This Week",
  month: "This Month",
  year: "This Year",
  "5years": "Last 5 Years"
};
const newsRangeToTimeOption = {
  today: "today",
  week: "this_week",
  month: "this_month",
  year: "this_year",
  "5years": "5_years"
};
type NewsRange = "today" | "week" | "month" | "year" | "5years";

// Helper to render *text* as italic in insights
function renderInsightWithItalics(insight: string) {
  const parts = insight.split(/(\*[^*]+\*)/g);
  return parts.map((part, idx) =>
    part.startsWith('*') && part.endsWith('*') ? (
      <em key={idx}>{part.slice(1, -1)}</em>
    ) : (
      <span key={idx}>{part}</span>
    )
  );
}

export default function AiNewsPage() {
  const [company, setCompany] = useState("");
  const [newsList, setNewsList] = useState<Record<string, any>[]>([]);
  const [newsRange, setNewsRange] = useState<NewsRange>("today");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchedCompany, setSearchedCompany] = useState("");

  const [savedInsights, setSavedInsights] = useState<Record<string, any>[]>([]);
  // Progress tracking states
const [sessionId, setSessionId] = useState<string | null>(null);
const [progress, setProgress] = useState({
  status: 'Initializing...',
  message: '',
  processed: 0,
  total: 0,
  articles: []
});
const [progressInterval, setProgressInterval] = useState<NodeJS.Timeout | null>(null);
  
  // Add refs for tracking abort controller and reader for stop functionality
  const abortControllerRef = useRef<AbortController | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);

  // Only one expanded at a time for saved insights
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  useEffect(() => {
    const fetchSavedInsights = async () => {
      try {
        // Fetch from both endpoints
        const [regularResponse, standaloneResponse] = await Promise.allSettled([
          axios.get(`${DATABASE_URL}/news_insights/`, { withCredentials: true }),
          axios.get(`${DATABASE_URL}/news_insights/standalone/`, { withCredentials: true })
        ]);

        const allInsights: Record<string, any>[] = [];

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

  // Cleanup effect to clear refs and intervals on unmount
  useEffect(() => {
    return () => {
      // Clear interval first
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      
      // Cancel reader before aborting controller
      if (readerRef.current) {
        try {
          readerRef.current.cancel();
        } catch (error) {
          console.log('Reader already cancelled or disposed');
        }
      }
      
      // Clear abort controller last
      if (abortControllerRef.current) {
        try {
          abortControllerRef.current.abort();
        } catch (error) {
          console.log('Abort controller already aborted or disposed');
        }
      }
    };
  }, [progressInterval]);

const POLLING_TIMEOUT_MS = 60000; // 60 seconds

const fetchCompanyNews = async (companyName: string, range: NewsRange = newsRange) => {
  setLoading(true);
  setError("");
  setNewsList([]);
  setSearchedCompany(companyName);

  // Clear any existing progress interval
  if (progressInterval) {
    clearInterval(progressInterval);
    setProgressInterval(null);
  }

  // Initialize progress state
  setProgress({
    status: 'Searching for articles...',
    message: 'Searching for articles...',
    processed: 0,
    total: 0,
    articles: []
  });

  // Use SSE for real-time progress updates with single connection
  fetchCompanyNewsSSE(companyName, range);
};

const fetchCompanyNewsSSE = async (companyName: string, range: NewsRange = newsRange) => {
  // SSE approach - single connection with real-time progress updates
  try {
    // Create abort controller for cancellation
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Create a POST request to the SSE endpoint
    const response = await fetch(`${AI_NEWS_API_URL}/news/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company: companyName,
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
    readerRef.current = reader;

    const decoder = new TextDecoder();

    // Helper function to cleanup resources
    const cleanup = () => {
      abortControllerRef.current = null;
      readerRef.current = null;
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
              setProgress({
                status: progressData.status,
                message: progressData.message,
                processed: progressData.processed || 0,
                total: progressData.total || 0,
                articles: progressData.articles || []
              });
            } else if (data.event === 'article_complete') {
              // Handle individual article completion
              const articleData = JSON.parse(data.data);
              if (articleData.article) {
                setNewsList(prevList => {
                  // Add the new article to the list
                  const newList = [...prevList, articleData.article];
                  // Sort by match score
                  return newList.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
                });
              }
            } else if (data.event === 'complete') {
              const completeData = JSON.parse(data.data);
              if (completeData.status === 'complete' && completeData.result) {
                // Don't overwrite the news list since articles are already being added in real-time
                // Just ensure we have the final sorted list
                setNewsList(prevList => {
                  const finalList = [...prevList];
                  return finalList.sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
                });
              }
              
              setProgress({
                status: 'Complete',
                message: 'Processing complete',
                processed: 0,
                total: 0,
                articles: []
              });
              
              setLoading(false);
              cleanup();
              return;
            } else if (data.event === 'error') {
              const errorData = JSON.parse(data.data);
              setError(errorData.message || "An error occurred while fetching news.");
              setLoading(false);
              cleanup();
              return;
            }
          } catch (err) {
            console.error('SSE data parsing failed:', err);
          }
        }
      }
    }

  } catch (e: any) {
    console.error('SSE connection failed:', e);
    
    // Don't fall back to polling if this was an intentional abort
    if (e.name === 'AbortError' || e.message?.includes('aborted') || e.message?.includes('BodyStreamBuffer was aborted')) {
      console.log('SSE connection was intentionally aborted');
      // Clear refs on intentional abort
      abortControllerRef.current = null;
      readerRef.current = null;
      return;
    }
    
    // Clear refs on error
    abortControllerRef.current = null;
    readerRef.current = null;
    
    // Fallback to polling if SSE fails for other reasons
    console.log('SSE failed, falling back to polling...');
    fetchCompanyNewsPolling(companyName, range);
  }
};

const fetchCompanyNewsOptimized = async (companyName: string, range: NewsRange = newsRange) => {
  // Single request approach - no polling needed
  try {
    // Show loading state
    setProgress({
      status: 'Searching for articles...',
      message: 'Searching for news articles...',
      processed: 0,
      total: 0,
      articles: []
    });

    const response = await axios.post(
      `${AI_NEWS_API_URL}/news`,
      {
        company: companyName,
        time_option: newsRangeToTimeOption[range] || "this_week",
        max_items: 10,
        streaming: true  // Use single request mode
      }
    );

    const responseData = response.data;

    if (responseData.status === 'complete' && responseData.result) {
      let newsData: Record<string, any>[] = responseData.result.news || [];
      newsData = newsData.slice().sort((a: Record<string, any>, b: Record<string, any>) =>
        (b.match_score || 0) - (a.match_score || 0)
      );
      setNewsList(newsData);

      setProgress({
        status: 'Complete',
        message: 'Processing complete',
        processed: 0,
        total: 0,
        articles: []
      });
    } else if (responseData.status === 'error') {
      setError(responseData.message || "An error occurred while fetching news.");
    }

    setLoading(false);

  } catch (e: any) {
    if (e.response && e.response.status === 429) {
      setError("Too many requests right now, please try again later.");
    } else if (e.response && e.response.status === 500) {
      // Fallback to polling if single request fails
      console.log('Single request failed, falling back to polling...');
      fetchCompanyNewsPolling(companyName, range);
      return;
    } else {
      setError("Failed to fetch news.");
    }
    setLoading(false);
  }
};

const fetchCompanyNewsPolling = async (companyName: string, range: NewsRange = newsRange) => {
  // Fallback to original polling method
  try {
    // Initialize progress state for polling
    setProgress({
      status: 'Searching for articles...',
      message: 'Searching for articles...',
      processed: 0,
      total: 0,
      articles: []
    });

    const response = await axios.post(
      `${AI_NEWS_API_URL}/news`,
      {
        company: companyName,
        time_option: newsRangeToTimeOption[range] || "this_week",
        max_items: 10
      }
    );

    const { session_id } = response.data;
    setSessionId(session_id);
    
    // Check if session_id exists before proceeding
    if (!session_id) {
      console.error('No session_id received from API');
      setError("Failed to start news search. Please try again.");
      setLoading(false);
      return;
    }

    const startTime = Date.now();

    const interval = setInterval(async () => {
      try {
        // Timeout check
        if (Date.now() - startTime > POLLING_TIMEOUT_MS) {
          clearInterval(interval);
          setProgressInterval(null);
          setLoading(false);
          setError("Request timed out. Please try again later.");
          return;
        }

        const progressResponse = await axios.get(`${AI_NEWS_API_URL}/progress/${session_id}`);
        const progressData = progressResponse.data;

        setProgress({
          status: progressData.status,
          message: progressData.message,
          processed: progressData.processed || 0,
          total: progressData.total || 0,
          articles: progressData.articles || []
        });

        if (progressData.complete) {
          clearInterval(interval);
          setProgressInterval(null);

          if (progressData.status === 'complete' && progressData.result) {
            let newsData: Record<string, any>[] = progressData.result.news || [];
            newsData = newsData.slice().sort((a: Record<string, any>, b: Record<string, any>) =>
              (b.match_score || 0) - (a.match_score || 0)
            );
            setNewsList(newsData);

            setProgress({
              status: 'Complete',
              message: 'Processing complete',
              processed: 0,
              total: 0,
              articles: []
            });
          } else if (progressData.status === 'error') {
            setError(progressData.message || "An error occurred while fetching news.");
          }

          setLoading(false);
          // Clear refs
          abortControllerRef.current = null;
          readerRef.current = null;
        }
      } catch (err) {
        console.error('Progress check failed:', err);
        clearInterval(interval);
        setProgressInterval(null);
        setError("Failed to check progress.");
        setLoading(false);
        // Clear refs
        abortControllerRef.current = null;
        readerRef.current = null;
      }
    }, 1000);

    setProgressInterval(interval);

  } catch (e: any) {
    if (e.response && e.response.status === 429) {
      setError("Too many requests right now, please try again later.");
    } else {
      setError("Failed to fetch news.");
    }
    setLoading(false);
  }
};

  const handleSearch = () => {
    if (company.trim()) {
      fetchCompanyNews(company.trim(), newsRange);
    }
  };

  const handleStop = () => {
    // Clear the progress interval if it exists
    if (progressInterval) {
      clearInterval(progressInterval);
      setProgressInterval(null);
    }

    // Cancel the reader if it exists (do this before aborting the controller)
    if (readerRef.current) {
      try {
        readerRef.current.cancel();
      } catch (error) {
        console.log('Reader already cancelled or disposed');
      }
      readerRef.current = null;
    }

    // Cancel the abort controller if it exists
    if (abortControllerRef.current) {
      try {
        abortControllerRef.current.abort();
      } catch (error) {
        console.log('Abort controller already aborted or disposed');
      }
      abortControllerRef.current = null;
    }

    // Reset loading state but keep current results
    setLoading(false);
    setProgress({
      status: 'Stopped',
      message: 'Search stopped by user',
      processed: 0,
      total: 0,
      articles: []
    });
  };

  const handleRangeChange = (range: NewsRange) => {
    setNewsRange(range);
    if (searchedCompany) {
      fetchCompanyNews(searchedCompany, range);
    }
  };

  const handleSaveInsight = async (newsItem: Record<string, any>) => {
    try {
      // Check if article failed to extract
      const isFailed = newsItem.processing_failed || (newsItem.scraped_content && (
        newsItem.scraped_content.includes('CAPTCHA') || 
        newsItem.scraped_content.includes('unusual activity') ||
        newsItem.scraped_content.includes('robot') ||
        newsItem.scraped_content.includes('Block reference ID') ||
        newsItem.summary?.includes('does not contain any relevant information')
      ));

      const payload = {
        company_name: newsItem.company_name || newsItem.company || '',
        headline: newsItem.headline || newsItem.title || '',
        insights: isFailed ? [] : (newsItem.ai_insights?.insights || []), // Empty insights for failed articles
        source: newsItem.source || newsItem.link || '',
        tags: isFailed ? {} : newsItem.tags, // Empty tags for failed articles
        published_at: newsItem.published,
      };
      const response = await axios.post(`${DATABASE_URL}/news_insights/standalone/`, payload, { withCredentials: true });
      setSavedInsights((prev) => [response.data, ...prev]);
    } catch (err) {
      // Optionally show error notification
    }
  };
  const handleDeleteInsight = async (news: Record<string, any>) => {
    try {
      await axios.delete(`${DATABASE_URL}/news_insights/${news.id}`, { withCredentials: true });
      setSavedInsights((prev) => prev.filter((n) => n.id !== news.id));
    } catch (err) {
      // Optionally show error notification
    }
  };

  return (
    <div className="bg-dark-primary text-gray-100 min-h-screen">
      <main className="flex-1 p-6">
        {/* Header Section */}
        <div className="flex flex-col space-y-2 mb-6">
          <div className="flex items-center space-x-2">
            <Newspaper className="h-8 w-8 text-green-500" />
            <h1 className="text-3xl font-bold text-white">AI News</h1>
          </div>
          <p className="text-gray-400">Discover the latest news and AI-powered insights about any company</p>
        </div>

        {/* Main Two-Column Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch min-h-[420px]">
          {/* Search Controls */}
          <Card className="bg-dark-secondary border-dark-border w-full h-full min-h-[400px] flex flex-col px-6 py-8">
            <div className="text-center pt-2 pb-6">
              <div className="text-white text-2xl lg:text-3xl font-bold">Search Company News</div>
              <div className="text-gray-400 text-lg lg:text-xl mt-1">Enter a company name to find recent news and AI insights</div>
            </div>
            <div className="flex-1 flex flex-col justify-center items-center w-full">
              <Input
                type="text"
                placeholder="Enter company name..."
                value={company}
                onChange={e => setCompany(e.target.value)}
                className="w-full text-lg lg:text-xl px-6 py-4 text-center bg-dark-primary border-dark-border text-white rounded-lg"
                onKeyDown={e => { if (e.key === 'Enter') handleSearch(); }}
              />
              <div className="flex flex-col items-center w-full mt-6">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      disabled={loading || !company.trim()}
                      className="w-40 py-3 text-lg font-semibold rounded bg-gradient-to-r from-green-400 via-blue-500 to-blue-600 hover:from-green-500 hover:to-blue-700 border-0 text-white flex items-center justify-center gap-2 shadow-md mx-auto"
                    >
                      Search
                      <ChevronDown className="h-5 w-5 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuItem onClick={() => { setNewsRange('today'); fetchCompanyNews(company.trim(), 'today'); }}>
                      Today
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setNewsRange('week'); fetchCompanyNews(company.trim(), 'week'); }}>
                      This Week
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setNewsRange('month'); fetchCompanyNews(company.trim(), 'month'); }}>
                      This Month
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setNewsRange('year'); fetchCompanyNews(company.trim(), 'year'); }}>
                      This Year
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => { setNewsRange('5years'); fetchCompanyNews(company.trim(), '5years'); }}>
                      Last 5 Years
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                
                {/* Stop Button - appears when loading */}
                {loading && (
                  <Button
                    onClick={handleStop}
                    variant="destructive"
                    className="w-40 py-3 text-lg font-semibold rounded shadow-md mx-auto mt-3"
                  >
                    Stop
                  </Button>
                )}
              </div>
              {error && <div className="text-red-500 py-2 text-center text-lg">{error}</div>}
            </div>
          </Card>

          {/* Results */}
          <Card className="bg-dark-secondary border-dark-border max-h-[520px] overflow-y-auto flex flex-col justify-start">
            <CardHeader>
              <CardTitle className="text-white">Results</CardTitle>
            </CardHeader>
            <CardContent className="p-0 space-y-6 h-full text-base md:text-lg">
              {loading && (
  <div className="text-gray-100 text-center py-4 space-y-4">
    {/* Progress Message */}
    <div className="text-lg font-medium">{progress.message || 'Loading...'}</div>
    
    {/* Processing Info */}
    {progress.total > 0 && (
      <div className="text-sm text-gray-400">
        Processing {progress.total} articles found
      </div>
    )}
    
    {/* Progress Bar */}
    {progress.total > 0 && (
      <div className="max-w-md mx-auto px-4">
        <div className="flex justify-between text-sm text-gray-400 mb-2">
          <span>Processing articles</span>
          <span>{progress.processed} / {progress.total}</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <div 
            className="bg-gradient-to-r from-green-400 to-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(progress.processed / progress.total) * 100}%` }}
          />
        </div>
      </div>
    )}
    
    {/* Status */}
    <div className="text-sm text-gray-400">
      Status: <span className="text-gray-200 capitalize">{progress.status || 'Initializing...'}</span>
    </div>
    
    {/* Additional Progress Info */}
    {progress.articles && progress.articles.length > 0 && (
      <div className="text-xs text-gray-400 mt-2">
        Articles found: {progress.articles.length}
      </div>
    )}
  </div>
)}
              {!loading && searchedCompany && newsList.length === 0 && (
                <div className="text-gray-100 text-center py-8">No results found for <b>{searchedCompany}</b>.</div>
              )}
              {(newsList.length > 0 || !loading) && (
                <div className="flex flex-col items-center w-full">
                  {newsList.map((news: Record<string, any>) => {
                    // Check if article failed to extract (has CAPTCHA content, error, or processing_failed flag)
                    const isFailed = news.processing_failed || (news.scraped_content && (
                      news.scraped_content.includes('CAPTCHA') || 
                      news.scraped_content.includes('unusual activity') ||
                      news.scraped_content.includes('robot') ||
                      news.scraped_content.includes('Block reference ID') ||
                      news.summary?.includes('does not contain any relevant information')
                    ));
                    
                    return (
                    <Card key={String(news.link) + String(news.title)} className="bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-700 p-3 flex flex-col gap-1 max-w-2xl w-full mx-auto mb-4">
                      <div className="font-bold text-base text-indigo-700 dark:text-indigo-300 mb-1">
                        {news.title}
                      </div>
                      {news.published && (
                        <div className="text-xs text-gray-500 mb-1">
                          {new Date(news.published).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                        </div>
                      )}
                      {news.link && (
                        <a href={news.link} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 underline mb-1 inline-block">
                          View Source
                        </a>
                      )}
                      {isFailed ? (
                        <div className="text-gray-500 dark:text-gray-400 mb-1 italic">We cannot extract the article content</div>
                      ) : news.summary && (
                        <div className="text-gray-700 dark:text-gray-200 mb-1">{news.summary}</div>
                      )}
                      {/* Tag topic - only show for successful articles */}
                      {!isFailed && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {news.tags && typeof news.tags === 'object' && news.tags !== null ? (
                            <>
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
                                  ? (news.tags.topic as string[]).map((topic: string, i: number) => (
                                      <span key={i} className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold mr-1">
                                        Topic: {topic}
                                      </span>
                                    ))
                                  : <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-semibold">Topic: {news.tags.topic}</span>
                              )}
                            </>
                          ) : (
                            news.tags && Array.isArray(news.tags) ? news.tags.map((tag: string, i: number) => (
                              <span key={i} className="bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded text-xs">{tag}</span>
                            )) : null
                          )}
                        </div>
                      )}
                      {/* AI Insights - only show for successful articles */}
                      {!isFailed && news.ai_insights && (
                        <div className="bg-gray-100 dark:bg-zinc-800 rounded p-3 mt-3">
                          <div className="font-semibold text-sm text-gray-800 dark:text-gray-100 mb-2">Insights</div>
                          {(() => {
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
                                return <div className="text-red-500 text-sm">This source cannot be extracted: {news.ai_insights.error}</div>;
                              } else {
                                return <div className="text-gray-500 text-sm">No insights available</div>;
                              }

                              if (insightsArray.length === 0) {
                                return <div className="text-gray-500 text-sm">No insights available</div>;
                              }

                              return (
                                <ul className="list-disc pl-6 text-gray-700 dark:text-gray-200 text-sm space-y-1">
                                  {insightsArray.map((insight: string, idx: number) => (
                                    <li key={idx}>{renderInsightWithItalics(insight)}</li>
                                  ))}
                                </ul>
                              );
                            } catch (error) {
                              console.error('Error parsing insights:', error);
                              // If parsing fails, try to display the raw string as a fallback
                              return (
                                <div className="text-gray-700 dark:text-gray-200 text-sm">
                                  {typeof news.ai_insights === 'string' ? news.ai_insights : 'Error parsing insights'}
                                </div>
                              );
                            }
                          })()}
                        </div>
                      )}
                      {/* Save button - show for all articles */}
                      <div className="flex justify-end mt-1">
                        <Button variant="outline" size="sm" onClick={() => handleSaveInsight(news)}>
                          <Save className="h-4 w-4 mr-1" /> Save as Insight
                        </Button>
                      </div>
                    </Card>
                  );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Saved Insights Section */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold text-white mb-4">Saved Insights</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 items-start">
            {savedInsights.length === 0 && <div className="text-gray-400 text-center py-6 text-lg col-span-full">No saved insights yet.</div>}
            {savedInsights.map((news) => {
              const key = String(news.link || news.source) + String(news.headline || news.title);
              // For saved insights, the insights are stored directly in the 'insights' field as an array
              const insights = news.insights || [];
              const published = news.published || news.published_at;
              const expanded = expandedKey === key;
              return (
                <Card
                  key={key}
                  className={`bg-black text-white border border-gray-800 flex flex-col shadow-md relative transition-all duration-200 ${expanded ? 'p-6 min-h-[180px]' : 'p-4 min-h-[60px]'}`}
                >
                  {/* Dropdown menu at top-right */}
                  <div className="absolute top-2 right-2 z-10">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button className="p-1 rounded-full hover:bg-gray-800 focus:outline-none"><MoreVertical className="w-5 h-5 text-gray-300" /></button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start">
                        <DropdownMenuItem onClick={() => {
                          const text = insights.map((i: string) => `• ${i}`).join('\n');
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
                  <div className="flex flex-col gap-1 mb-2">
                    <div className="font-extrabold text-lg text-white leading-tight mb-0.5 text-left pr-8 break-words whitespace-pre-line">{news.headline || news.title}</div>
                    {/* Source as hyperlink */}
                    {(news.source || news.link) && (
                      <a
                        href={news.source || news.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-300 underline mb-1 text-left opacity-80"
                      >
                        Source
                      </a>
                    )}
                    {/* Date */}
                    {published && (
                      <div className="text-xs text-gray-400 mb-1 text-left">
                        {new Date(published).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                      </div>
                    )}
                  </div>
                  <button
                    className="text-xs text-blue-200 underline mb-2 self-start hover:text-blue-400 focus:outline-none"
                    onClick={() => {
                      if (expanded) {
                        setExpandedKey(null);
                      } else {
                        setExpandedKey(key);
                      }
                    }}
                  >
                    {expanded ? 'Hide Details' : 'Show Details'}
                  </button>
                  {expanded ? (
                    <>
                      <hr className="border-gray-700 my-2" />
                      {insights.length > 0 ? (
                        <div className="bg-indigo-50 dark:bg-zinc-800 rounded p-3 mb-2">
                          <div className="font-semibold text-sm text-gray-800 dark:text-gray-100 mb-2">Insights</div>
                          {(() => {
                            // For saved insights, insights is already an array
                            if (Array.isArray(insights) && insights.length > 0) {
                              // Handle case where insights might be wrapped in markdown code blocks
                              const processedInsights: string[] = [];
                              insights.forEach(insight => {
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
                                  {processedInsights.map((insight: string, idx: number) => (
                                    <li key={idx}>{renderInsightWithItalics(insight)}</li>
                                  ))}
                                </ul>
                              );
                            } else {
                              return <div className="text-gray-500 text-sm">No insights available</div>;
                            }
                          })()}
                        </div>
                      ) : (
                        <div className="text-gray-400 italic mb-2">Our AI cannot access this source.</div>
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
                              ? news.tags.topic.map((topic: string, i: number) => (
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
                    </>
                  ) : null}
                </Card>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}