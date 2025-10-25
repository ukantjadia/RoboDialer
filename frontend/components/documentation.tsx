// app/documentation/components/documentation.tsx
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { FC } from "react";

export const DocumentationContent: FC = () => {
  return (
    <Card className="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>Documentation</CardTitle>
        <CardDescription>
          Learn how to use our platform with tutorials and frequently asked questions.
        </CardDescription>
      </CardHeader>
      <CardContent>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Video Tutorial Section */}
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-foreground">Video Tutorial</h2>
            <p className="text-muted-foreground">
              Watch our comprehensive tutorial to get started with lead generation and enrichment.
            </p>
            <div className="bg-background p-4 rounded-xl shadow-lg border border-border">
              <div className="aspect-video rounded-lg overflow-hidden">
                <iframe
                  src="https://www.loom.com/embed/f39263d166604137ba506a86a4970a30?sid=a8b5c3d2-e1f4-5g6h-7i8j-9k0l1m2n3o4p"
                  allowFullScreen
                  className="w-full h-full border-0"
                ></iframe>
              </div>
            </div>
          </div>

          {/* FAQ Section */}
          <div className="bg-background p-6 md:p-8 rounded-xl shadow-lg border border-border">
            <h2 className="text-xl font-semibold text-foreground mb-6">Frequently Asked Questions</h2>
            <div className="space-y-6">
              {/* FAQ Item 1 */}
              <div className="border-b border-border pb-4">
                <h3 className="text-lg font-medium text-foreground mb-2">Are the leads free?</h3>
                <p className="text-muted-foreground">
                  Yes! The leads scraped through our platform are completely free. Additionally, you can enrich up to 5 leads at no cost.
                </p>
              </div>
              {/* FAQ Item 2 */}
               <div className="border-b border-border pb-4">
                <h3 className="text-lg font-medium text-foreground mb-2">What does 'enrichment/enhancement' mean?</h3>
                <p className="text-muted-foreground">
                Lead enrichment/enhancement means adding valuable contact information and business details to your basic lead data. Our platform enriches leads by adding details such as email addresses, phone numbers, and other professional information using services like Apollo and Growjo.
                </p>
              </div>
              {/* FAQ Item 3 */}
              <div className="border-b border-border pb-4">
                <h3 className="text-lg font-medium text-foreground mb-2">How does lead enrichment work?</h3>
                <p className="text-muted-foreground">
                  Our lead enrichment process adds valuable contact information and business details to your scraped leads, making them more actionable for your outreach campaigns.
                </p>
              </div>

              {/* FAQ Item 4 */}
              <div className="border-b border-border pb-4">
                <h3 className="text-lg font-medium text-foreground mb-2">What data sources do you use?</h3>
                <p className="text-muted-foreground">
                  We aggregate data from multiple professional networks and public databases to provide accurate and up-to-date lead information.
                </p>
              </div>

              {/* FAQ Item 5 */}
              <div className="border-b border-border pb-4">
                <h3 className="text-lg font-medium text-foreground mb-2">How accurate are the scraped leads?</h3>
                <p className="text-muted-foreground">
                  Our platform maintains high accuracy standards by using advanced filtering and verification processes to ensure quality lead data.
                </p>
              </div>

              {/* FAQ Item 6 */}
              <div>
                <h3 className="text-lg font-medium text-foreground mb-2">Can I export my leads?</h3>
                <p className="text-muted-foreground">
                  Yes, you can export your leads in various formats including CSV and Excel for easy integration with your CRM or marketing tools.
                </p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};