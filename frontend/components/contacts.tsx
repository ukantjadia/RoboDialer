// app/contact/components/ContactForm.tsx
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FC } from "react";

export const ContactForm: FC = () => {
  return (
    <Card className="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>Contact Us</CardTitle>
        <CardDescription>
          Have questions or need assistance? Reach out to our team.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Contact Information */}
          <div className="space-y-6">
            <h2 className="text-xl font-semibold text-foreground">Get in Touch</h2>
            <p className="text-muted-foreground">
              Our team is ready to assist you with any inquiries. We'll respond promptly.
            </p>
            <div className="space-y-4">
              {/* Phone */}
              <div className="flex items-start">
                <div className="flex-shrink-0 bg-accent p-3 rounded-full">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-foreground">LinkedIn</h3>
                  <p className="mt-1 text-muted-foreground"><a href="https://www.linkedin.com/company/saasquatchleads/">https://www.linkedin.com/company/saasquatchleads/</a></p>
                </div>
              </div>
              {/* Email */}
              <div className="flex items-start">
                <div className="flex-shrink-0 bg-accent p-3 rounded-full">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-foreground">Email</h3>
                  <p className="mt-1 text-muted-foreground">support@saasquatchleads.com</p>
                </div>
              </div>
              {/* Office */}
              <div className="flex items-start">
                <div className="flex-shrink-0 bg-accent p-3 rounded-full">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-medium text-foreground">Office</h3>
                  <p className="mt-1 text-muted-foreground">
                    Caprae Capital Partners<br />
                    Glendale, California
                  </p>
                </div>
              </div>
            </div>
          </div>
          {/* Contact Form */}
          <div className="bg-background p-6 md:p-8 rounded-xl shadow-lg border border-border">
            <h2 className="text-xl font-semibold text-foreground mb-6">Send us a message</h2>
            <form action="https://formsubmit.co/support@saasquatchleads.com" method="POST" className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-foreground mb-1">
                    Full Name
                  </label>
                  <Input
                    type="text"
                    id="name"
                    name="name"
                    placeholder="Your name"
                    className="w-full"
                  />
                </div>
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1">
                    Email Address
                  </label>
                  <Input
                    type="email"
                    id="email"
                    name="email"
                    placeholder="you@company.com"
                    className="w-full"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="subject" className="block text-sm font-medium text-foreground mb-1">
                  Subject
                </label>
                <Input
                  type="text"
                  id="subject"
                  name="subject"
                  placeholder="How can we help?"
                  className="w-full"
                />
              </div>
              <div>
                <label htmlFor="message" className="block text-sm font-medium text-foreground mb-1">
                  Message
                </label>
                <Textarea
                  id="message"
                  name="message"
                  rows={5}
                  placeholder="Your message here..."
                  className="w-full"
                />
              </div>
              <Button
                type="submit"
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
              >
                Send Message
              </Button>
            </form>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};