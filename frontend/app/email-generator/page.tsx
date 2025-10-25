"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Loader2, Copy, Check, Mail, ChevronRight, ExternalLink, Edit3, Save, X, Clock } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import PopupBig from "@/components/ui/popup-big"

interface HistoryItem {
  id: string;
  created_at: string;
  message_content: {
    company_name: string;
    generated_message: string;
    subject?: string;
    timestamp?: string;
  };
  message_type: string;
}

export default function EmailGenerator() {
  const { toast } = useToast()

  return (
    <div className="bg-dark-primary text-gray-100">
      <div>
        <main className="flex-1 p-6">
          <div className="flex flex-col space-y-2">
            <div className="flex items-center space-x-2">
              <Mail className="h-8 w-8 text-green-500" />
              <h1 className="text-3xl font-bold text-white">Email Generator</h1>
            </div>
            <p className="text-gray-400">Generate personalized email messages for your leads</p>
          </div>

          {/* Coming Soon Banner */}
          <div className="mt-8">
            <Card className="bg-gradient-to-r from-blue-600 to-purple-600 border-0 shadow-xl">
              <CardContent className="p-12 text-center">
                <div className="flex flex-col items-center space-y-6">
                  <div className="bg-white/20 rounded-full p-4">
                    <Clock className="h-12 w-12 text-white" />
                  </div>
                  
                  <div className="space-y-4">
                    <h2 className="text-4xl font-bold text-white">Coming Soon!</h2>
                    <p className="text-xl text-white/90 max-w-2xl mx-auto">
                      Our AI-powered email generator is currently in development. 
                      You'll soon be able to create personalized, professional emails 
                      for your leads with just a few clicks.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8 max-w-4xl w-full">
                    <div className="bg-white/10 rounded-lg p-6 backdrop-blur-sm">
                      <div className="text-2xl mb-2">🤖</div>
                      <h3 className="text-lg font-semibold text-white mb-2">AI-Powered</h3>
                      <p className="text-white/80 text-sm">
                        Advanced AI that understands your business context and generates relevant content
                      </p>
                    </div>
                    
                    <div className="bg-white/10 rounded-lg p-6 backdrop-blur-sm">
                      <div className="text-2xl mb-2">🎯</div>
                      <h3 className="text-lg font-semibold text-white mb-2">Personalized</h3>
                      <p className="text-white/80 text-sm">
                        Tailored messages based on company info, recipient details, and your goals
                      </p>
                    </div>
                    
                    <div className="bg-white/10 rounded-lg p-6 backdrop-blur-sm">
                      <div className="text-2xl mb-2">⚡</div>
                      <h3 className="text-lg font-semibold text-white mb-2">Fast & Easy</h3>
                      <p className="text-white/80 text-sm">
                        Generate professional emails in seconds, not hours
                      </p>
                    </div>
                  </div>

                  <div className="mt-8 space-y-4">
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Feature Preview */}
          <div className="mt-12">
            <h2 className="text-2xl font-bold text-white mb-6 text-center">What to Expect</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-dark-secondary border-dark-border">
                <CardHeader>
                  <CardTitle className="text-white">Smart Email Generation</CardTitle>
                  <CardDescription className="text-gray-400">
                    AI that understands your business and creates compelling emails
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-white">Recipient Name</Label>
                    <Input
                      placeholder="John Doe"
                      className="bg-dark-primary border-dark-border text-white"
                      disabled
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-white">Company Name</Label>
                    <Input
                      placeholder="Acme Corporation"
                      className="bg-dark-primary border-dark-border text-white"
                      disabled
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-white">Focus</Label>
                    <Select disabled>
                      <SelectTrigger className="bg-dark-primary border-dark-border text-white">
                        <SelectValue placeholder="Partnership" />
                      </SelectTrigger>
                    </Select>
                  </div>
                  <Button disabled className="w-full bg-gray-600 text-gray-400">
                    Generate Email (Coming Soon)
                  </Button>
                </CardContent>
              </Card>

              <Card className="bg-dark-secondary border-dark-border">
                <CardHeader>
                  <CardTitle className="text-white">Generated Email Preview</CardTitle>
                  <CardDescription className="text-gray-400">
                    Your personalized email will appear here
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-dark-primary border border-dark-border rounded-lg p-6 min-h-[300px] flex items-center justify-center">
                    <div className="text-center space-y-2">
                      <Mail className="h-12 w-12 text-gray-500 mx-auto" />
                      <p className="text-gray-400">
                        Fill in the details and click "Generate Email" to create your personalized message
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}