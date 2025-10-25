"use client"

import { Checkbox } from "@/components/ui/checkbox"

import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Info } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

export function EnrichmentOptions() {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Configure Enrichment Options</h3>

      <Tabs defaultValue="sources">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="sources">Data Sources</TabsTrigger>
          <TabsTrigger value="fields">Fields to Enrich</TabsTrigger>
          <TabsTrigger value="advanced">Advanced Options</TabsTrigger>
        </TabsList>

        <TabsContent value="sources" className="space-y-4 pt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Apollo</CardTitle>
                <CardDescription>Contact information and company details</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="apollo-enabled">Enable Apollo</Label>
                      <p className="text-sm text-muted-foreground">Use Apollo as a data source</p>
                    </div>
                    <Switch id="apollo-enabled" defaultChecked />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="apollo-priority">Priority</Label>
                      <span className="text-sm text-muted-foreground">High</span>
                    </div>
                    <Slider defaultValue={[75]} max={100} step={25} />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Growjo</CardTitle>
                <CardDescription>Company growth and revenue data</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="growjo-enabled">Enable Growjo</Label>
                      <p className="text-sm text-muted-foreground">Use Growjo as a data source</p>
                    </div>
                    <Switch id="growjo-enabled" defaultChecked />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="growjo-priority">Priority</Label>
                      <span className="text-sm text-muted-foreground">Medium</span>
                    </div>
                    <Slider defaultValue={[50]} max={100} step={25} />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">LinkedIn</CardTitle>
                <CardDescription>Professional profiles and company information</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="linkedin-enabled">Enable LinkedIn</Label>
                      <p className="text-sm text-muted-foreground">Use LinkedIn as a data source</p>
                    </div>
                    <Switch id="linkedin-enabled" defaultChecked />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="linkedin-priority">Priority</Label>
                      <span className="text-sm text-muted-foreground">Medium</span>
                    </div>
                    <Slider defaultValue={[50]} max={100} step={25} />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Clearbit</CardTitle>
                <CardDescription>Company and contact enrichment</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="clearbit-enabled">Enable Clearbit</Label>
                      <p className="text-sm text-muted-foreground">Use Clearbit as a data source</p>
                    </div>
                    <Switch id="clearbit-enabled" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="clearbit-priority">Priority</Label>
                      <span className="text-sm text-muted-foreground">Low</span>
                    </div>
                    <Slider defaultValue={[25]} max={100} step={25} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="fields" className="space-y-4 pt-4">
          <Card>
            <CardHeader>
              <CardTitle>Fields to Enrich</CardTitle>
              <CardDescription>Select which fields you want to enrich with additional data</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-4">
                  <h4 className="text-sm font-medium">Company Information</h4>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox id="company" defaultChecked />
                      <Label htmlFor="company">Company Name</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="website" defaultChecked />
                      <Label htmlFor="website">Website</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="industry" defaultChecked />
                      <Label htmlFor="industry">Industry</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="product" defaultChecked />
                      <Label htmlFor="product">Product/Service Category</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="business-type" defaultChecked />
                      <Label htmlFor="business-type">Business Type</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="employees" defaultChecked />
                      <Label htmlFor="employees">Employees Count</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="revenue" defaultChecked />
                      <Label htmlFor="revenue">Revenue</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="founded" defaultChecked />
                      <Label htmlFor="founded">Year Founded</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="location" defaultChecked />
                      <Label htmlFor="location">Location (City, State)</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="linkedin" defaultChecked />
                      <Label htmlFor="linkedin">LinkedIn URL</Label>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="text-sm font-medium">Contact Information</h4>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox id="contact-name" defaultChecked />
                      <Label htmlFor="contact-name">Full Name</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="title" defaultChecked />
                      <Label htmlFor="title">Title</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="email" defaultChecked />
                      <Label htmlFor="email">Email</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="phone" defaultChecked />
                      <Label htmlFor="phone">Phone Number</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="contact-linkedin" defaultChecked />
                      <Label htmlFor="contact-linkedin">LinkedIn URL</Label>
                    </div>
                  </div>

                  <h4 className="text-sm font-medium mt-6">Engagement Details</h4>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox id="source" defaultChecked />
                      <Label htmlFor="source">Source</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="score" defaultChecked />
                      <Label htmlFor="score">Score</Label>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4 pt-4">
          <Card>
            <CardHeader>
              <CardTitle>Advanced Options</CardTitle>
              <CardDescription>Configure advanced enrichment settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <h4 className="text-sm font-medium">Conflict Resolution</h4>
                <RadioGroup defaultValue="priority">
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="priority" id="priority" />
                    <Label htmlFor="priority">Use source priority</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="most-recent" id="most-recent" />
                    <Label htmlFor="most-recent">Use most recent data</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="most-complete" id="most-complete" />
                    <Label htmlFor="most-complete">Use most complete data</Label>
                  </div>
                </RadioGroup>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="confidence-threshold">Confidence Threshold</Label>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="h-4 w-4 text-muted-foreground" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="w-80">
                            Only include data with confidence score above this threshold. Higher values mean more
                            accurate but potentially fewer results.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <span className="text-sm text-muted-foreground">70%</span>
                </div>
                <Slider defaultValue={[70]} max={100} step={5} />
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-medium">Rate Limiting</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="requests-per-minute">Requests per minute</Label>
                    <Input id="requests-per-minute" type="number" defaultValue="60" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="max-retries">Max retries</Label>
                    <Input id="max-retries" type="number" defaultValue="3" />
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox id="normalize" defaultChecked />
                <div className="grid gap-1.5 leading-none">
                  <Label htmlFor="normalize">Normalize data</Label>
                  <p className="text-sm text-muted-foreground">
                    Standardize formats for phone numbers, addresses, etc.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox id="deduplicate" defaultChecked />
                <div className="grid gap-1.5 leading-none">
                  <Label htmlFor="deduplicate">Deduplicate records</Label>
                  <p className="text-sm text-muted-foreground">Remove duplicate entries based on email or domain</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
