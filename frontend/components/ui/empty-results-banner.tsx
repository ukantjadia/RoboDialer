import React from "react";
import { AlertCircle, Database } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "./alert";
import { Button } from "./button";

interface EmptyResultsBannerProps {
  enrichmentType: "company" | "people" | "both";
  hasDatabaseResults: boolean;
  hasScrapedResults: boolean;
  totalCompanies: number;
  onRetry?: () => void;
  onViewDatabaseResults?: () => void;
}

export function EmptyResultsBanner({
  enrichmentType,
  hasDatabaseResults,
  hasScrapedResults,
  totalCompanies,
  onRetry,
  onViewDatabaseResults,
}: EmptyResultsBannerProps) {
  const getBannerContent = () => {
    if (hasDatabaseResults && !hasScrapedResults) {
      // Database has results but scraped sources failed
      return {
        title: "Partial Results Available",
        description: `We found ${totalCompanies} companies in our database, but the enrichment services (Apollo/Growjo) couldn't provide additional data as it's not found in our external sources. You can still view the database results.`,
        icon: Database,
        variant: "default" as const,
        showDatabaseButton: true,
      };
    } else if (!hasDatabaseResults && !hasScrapedResults) {
      // Complete failure - no results from any source
      return {
        title: "No Results Found",
        description: `We couldn't find any data for the selected companies from our database or enrichment services. The companies are not found in our sources, which might be due to temporary service issues or the companies not being in our systems.`,
        icon: AlertCircle,
        variant: "destructive" as const,
        showDatabaseButton: false,
      };
         } else if (hasScrapedResults && !hasDatabaseResults) {
       // Only scraped results (unlikely but possible)
       return {
         title: "Enrichment Results Available",
         description: `We found enrichment data for ${totalCompanies} companies, but no existing database records were found as it's not available in our internal sources.`,
         icon: AlertCircle,
         variant: "default" as const,
         showDatabaseButton: false,
       };
     }
    
    // Default case
    return {
      title: "No Results Found",
      description: "We couldn't find any data for the selected companies as they are not found in our sources.",
      icon: AlertCircle,
      variant: "destructive" as const,
      showDatabaseButton: false,
    };
  };

  const content = getBannerContent();

  return (
    <Alert variant={content.variant} className="mb-6 bg-red-50 border-red-200 dark:bg-red-950 dark:border-red-800">
      <content.icon className="h-4 w-4 text-white" />
      <AlertTitle className="text-white">{content.title}</AlertTitle>
      <AlertDescription className="mt-2 text-white">
        <p className="mb-4 text-white">{content.description}</p>
        
        <div className="flex flex-wrap gap-2">
          {content.showDatabaseButton && onViewDatabaseResults && (
            <Button
              variant="outline"
              size="sm"
              onClick={onViewDatabaseResults}
              className="flex items-center gap-2"
            >
              <Database className="h-4 w-4" />
              View Database Results
            </Button>
          )}
        </div>
      </AlertDescription>
    </Alert>
  );
}
