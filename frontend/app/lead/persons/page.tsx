"use client"
import axios from 'axios';
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { DialogFooter } from "@/components/ui/dialog"
import FeedbackPopup from "@/components/FeedbackPopup";
import { SortDropdown } from "@/app/lead/persons/sort-dropdown"
import { NewTag } from "@/components/ui/new-tag"
import { normalizeLinkedInValue, normalizeWebsiteValue, normalizeEmailValue, normalizePhoneValue, isPhoneMissing, isEmailMissing } from "@/lib/leadUtils"
import {
  Search,
  Download,
  Edit,
  Mail,
  FileText,
  Filter,
  X,
  ExternalLink as LinkIcon,
  Eye,
  Building,
  MapPin,
  Calendar,
  Users,
  Globe,
  Phone,
  Linkedin,
  Pencil,
  StickyNote,
  MessageSquare,
  Star,
  Save,
  Copy,
  Check,
  Edit3, Plus,ThumbsUp, ThumbsDown,
  MoreHorizontal,
  RefreshCw,
  ChevronDown,
  BookOpen,
  CheckCircle,
  Smartphone,
  Clock,
  Info,
} from "lucide-react"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import Notif from "@/components/ui/notif"
import { NotesPopup } from "@/components/NotesPopup";
import { Textarea } from "@/components/ui/textarea"
import EnrichPersons from "./EnrichPersons";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

// Database URLs
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;
const DATABASE_URL_NOAPI = DATABASE_URL?.replace(/\/api\/?$/, "");

// Person interface - updated to match actual data structure
interface Person {
  id: string;
  lead_id?: string; // Added lead_id field for API calls
  draft_id?: string; // Added optional draft_id
  name: string;
  title: string;
  website: string;
  email: string;
  location: string;
  company: string;
  phone: string;
  linkedin: string;
  industry: string;
  employees: number;
  yearFounded: string;
  businessType: string;
  address: string;
  updated?: string; // Added optional updated field
  is_favorite?: boolean; // Added optional is_favorite field
  seniority?: string; // Added optional seniority field
}

type SortOption = "filled" | "company" | "employees" | "owner" | "recent"

// Message settings interface
interface MessageSettings {
  tone: string;
  focus: string;
  companyName?: string;
  industry?: string;
  additionalContext: string[]; // Changed from string to string[]
  modelChoice?: string;
}

// Constants moved to top level
const overviewFields = [
  { key: "name", label: "Name" },
  { key: "title", label: "Title" },
  { key: "company", label: "Company" },
  { key: "industry", label: "Industry" },
  { key: "businessType", label: "Business Type" },
  { key: "website", label: "Website" },
  { key: "employees", label: "Employees Count" },
  { key: "yearFounded", label: "Year Founded" },
  { key: "address", label: "Address" },
  { key: "location", label: "Location" }
];

const contactFields = [
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone Number" },
  { key: "linkedin", label: "LinkedIn Profile" }
];

// EmailMessageGenerator Component
// EmailMessageGenerator Component - Fixed Version
interface EmailMessageGeneratorProps {
  person: Person;
  onClose: () => void;
  onGenerate: () => Promise<void>;
  onRegenerate: () => Promise<void>;
  onUpvote: () => Promise<void>;
  onDownvote: () => Promise<void>;
  generatedMessage: string;
  generatedSubject: string;
  isGenerating: boolean;
  settings: MessageSettings;
  onSettingsChange: (settings: MessageSettings) => void;
  onSave: () => Promise<void>;
  onCopy: () => Promise<void>;
  isSaving: boolean;
  copied: boolean;
  isEditing: boolean;
  editedMessage: string;
  editedSubject: string;
  onStartEditing: () => void;
  onSaveEdits: () => void;
  onCancelEditing: () => void;
  onEditMessageChange: (message: string) => void;
  onEditSubjectChange: (subject: string) => void;
  // New props for multi-tone functionality
  generatedVariants: Array<{
    email: string;
    template_id: string;
    template_name: string;
    variant: number;
    message_id: string;
  }>;
  setGeneratedVariants: (variants: Array<{
    email: string;
    template_id: string;
    template_name: string;
    variant: number;
    message_id: string;
  }>) => void;
  // Add these for the edit modal and feedback
  editingCard: any;
  setEditingCard: (card: any) => void;
  feedbackGiven: Record<string, 'upvote' | 'downvote' | null>;
  setFeedbackGiven: (feedback: Record<string, 'upvote' | 'downvote' | null>) => void;
  onToneChange?: (tone: string) => void;
  feedbackStatus?: Record<string, { type: string; timestamp: string }>;
  feedbackSubmitting?: boolean;
  currentMessageId?: string;
  getButtonState?: (feedbackType: string) => { disabled: boolean; active: boolean };
  templates: Array<{ template_id: string; template_name: string }>;
  selectedTemplateIds: string[];
  setSelectedTemplateIds: (ids: string[]) => void;
  openTemplateEditDialog: (template: any) => void;
  // Generated item editing props
  editingGeneratedItem: string | null;
  startEditingGeneratedItem: (item: any) => void;
  saveGeneratedItemEdits: () => void;
  cancelGeneratedItemEditing: () => void;
  editedGeneratedMessage: string;
  setEditedGeneratedMessage: (message: string) => void;
}

// Add this new interface for the generated messages structure
interface GeneratedMessages {
  professional?: {
    message: string;
    subject: string;
  };
  friendly?: {
    message: string;
    subject: string;
  };
  direct?: {
    message: string;
    subject: string;
  };
  casual?: {
    message: string;
    subject: string;
  };
}
const EmailMessageGenerator: React.FC<EmailMessageGeneratorProps> = ({
  person,
  onClose,
  onGenerate,
  onRegenerate,
  onUpvote,
  onDownvote,
  generatedMessage,
  generatedSubject,
  isGenerating,
  settings,
  onSettingsChange,
  onSave,
  onCopy,
  isSaving,
  copied,
  isEditing,
  editedMessage,
  editedSubject,
  onStartEditing,
  onSaveEdits,
  onCancelEditing,
  onEditMessageChange,
  onEditSubjectChange,
  generatedVariants,
  setGeneratedVariants,
  editingCard,
  setEditingCard,
  feedbackGiven,
  setFeedbackGiven,
  onToneChange,
  feedbackStatus = {},
  feedbackSubmitting = false,
  currentMessageId,
  getButtonState,
  templates,
  selectedTemplateIds,
  setSelectedTemplateIds,
  openTemplateEditDialog,
  editingGeneratedItem,
  startEditingGeneratedItem,
  saveGeneratedItemEdits,
  cancelGeneratedItemEditing,
  editedGeneratedMessage,
  setEditedGeneratedMessage,
}) => {
  // Add the missing state variables for loading states
  const [regeneratingItems, setRegeneratingItems] = useState<Record<string, boolean>>({});
  const [savingItems, setSavingItems] = useState<Record<string, boolean>>({});

  // Handle undefined person prop
  if (!person) {
    return (
      <div className="space-y-6 p-6">
        <div className="text-white">
          <p>No person data available</p>
        </div>
      </div>
    );
  }

  const isFormValid = () => {
    // Check if industry is filled (either from settings or person data)
    const industryValue = settings.industry || person?.industry || '';
    if (!industryValue.trim()) return false;

    // Check if first 3 context points have at least 20 words each
    const contexts = settings.additionalContext || [];
    if (contexts.length < 3) return false;

    const contextsValid = contexts.slice(0, 3).every(context => {
      const wordCount = context.trim().split(/\s+/).filter(word => word.length > 0).length;
      return wordCount >= 20;
    });

    // Check if at least one template is selected
    const templateSelected = selectedTemplateIds.length > 0;

    return contextsValid && templateSelected;
  };

  // Helper function to count words properly
  const countWords = (text: string) => {
    if (!text || !text.trim()) return 0;
    return text.trim().split(/\s+/).filter(word => word.length > 0).length;
  };

  // Helper function to get word count color
  const getWordCountColor = (wordCount: number, required: boolean = true) => {
    if (!required && wordCount === 0) return 'text-gray-400';
    if (wordCount >= 20) return 'text-green-400';
    if (wordCount < 20) return 'text-yellow-400';
    return 'text-red-400';
  };

  // Modified context change handler
  const handleContextChange = (index: number, value: string) => {
    const newContext = [...(settings.additionalContext || [])];
    while (newContext.length < 4) {
      newContext.push('');
    }
    newContext[index] = value;
    onSettingsChange({...settings, additionalContext: newContext});
  };

  // Get the display industry value - prioritize settings, then person data
  const getDisplayIndustry = () => {
    if (settings.industry !== undefined && settings.industry !== null) {
      return settings.industry;
    }
    return person?.industry || '';
  };

  // Add the missing handler functions
  const handleFeedback = async (item: any, type: 'upvote' | 'downvote') => {
    try {
      const response = await fetch('https://sandbox-api.saasquatchleads.com/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message_id: item.message_id,
          parent_message_id: null,
          feedback_type: type,
          company_name: person.company,
          industry: person.industry,
          tone: settings.tone,
          focus: "template_based_generation",
          context: settings.additionalContext?.join(' ') || '',
          model_used: settings.modelChoice || 'deepseek',
          prompt_template: item.template_name,
          prompt_text: `Generated using template: ${item.template_name}`,
          generated_message: {
            message: item.email,
            template_id: item.template_id,
            template_name: item.template_name,
            variant: item.variant,
            generated_at: new Date().toISOString()
          }
        }),
      });
      if (response.ok) {
        setFeedbackGiven(prev => ({ ...prev, [item.message_id]: type }));
      }
    } catch (error) {
      console.error('Feedback error:', error);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleSave = async (item: any) => {
    // Set saving state for this specific item
    setSavingItems(prev => ({ ...prev, [item.message_id]: true }));

    try {
      // Parse the email to extract subject and body
      const emailLines = item.email.split('\n');
      const subjectLine = emailLines.find((line: string) => line.startsWith('Subject:'));
      const subject = subjectLine ? subjectLine.replace('Subject:', '').trim() : 'Email from LeadGenAI';

      // Get the message body (everything after the subject line)
      const subjectIndex = emailLines.findIndex((line: string) => line.startsWith('Subject:'));
      const messageBody = subjectIndex >= 0
        ? emailLines.slice(subjectIndex + 1).join('\n').trim()
        : item.email;

      const response = await fetch('https://sandbox-api.saasquatchleads.com/save_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          type: 'email',
          company_name: person.company,
          message: messageBody,
          subject: subject,
          template_id: item.template_id,
          variant: item.variant,
        }),
      });

      if (response.ok) {
        console.log('Email saved successfully');
      }
    } catch (error) {
      console.error('Save error:', error);
    } finally {
      // Clear saving state
      setSavingItems(prev => ({ ...prev, [item.message_id]: false }));
    }
  };

  const handleOpenInEmail = (email: string) => {
    // Parse the email content to extract subject and body
    const emailLines = email.split('\n');
    const subjectLine = emailLines.find((line: string) => line.startsWith('Subject:'));
    const subject = subjectLine ? subjectLine.replace('Subject:', '').trim() : 'Email from LeadGenAI';
    const subjectIndex = emailLines.findIndex((line: string) => line.startsWith('Subject:'));
    const body = subjectIndex >= 0
      ? emailLines.slice(subjectIndex + 1).join('\n').trim()
      : email;

    // Create Gmail compose URL with proper encoding
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(gmailUrl, '_blank');
  };

  const handleRegenerate = async (item: any) => {
    // Set regenerating state for this specific item
    setRegeneratingItems(prev => ({ ...prev, [item.message_id]: true }));

    try {
      const response = await fetch('https://sandbox-api.saasquatchleads.com/api/regenerate_template_variant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          original_message_id: item.message_id,
          template_id: item.template_id,
          context_point_index: item.variant - 1, // Convert to 0-based index
          company_name: person.company,
          industry: person.industry,
          person_name: person.name,
          tone: settings.tone,
          model_choice: settings.modelChoice || 'deepseek',
          additional_context: settings.additionalContext || []
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Update the specific variant in generatedVariants
        setGeneratedVariants((prev: Array<{
          email: string;
          template_id: string;
          template_name: string;
          variant: number;
          message_id: string;
        }>) =>
          prev.map((variant) =>
            variant.message_id === item.message_id
              ? { ...variant, email: data.message }
              : variant
          )
        );
      }
    } catch (error) {
      console.error('Regeneration error:', error);
    } finally {
      // Clear regenerating state
      setRegeneratingItems(prev => ({ ...prev, [item.message_id]: false }));
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="space-y-4">
        <div className="p-4 border rounded-lg text-white bg-gray-600">
          <div className="flex items-baseline gap-2">
            <p className="font-medium">Person:</p>
            <p className="text-lg">{person.name}</p>
          </div>
          <p className="text-sm text-white mt-1">Company: {person.company}</p>
          <p className="text-sm text-white mt-1">Industry: {person.industry}</p>
          {person.email && (
            <p className="text-sm text-white mt-1">
              Email: <span className="text-blue-200">{person.email}</span>
            </p>
          )}
        </div>

        <div className="space-y-3">
          {/* Company Name Input */}
          <div>
            <label className="block text-sm font-medium text-white mb-1">Company Name<span className="text-red-400">*</span></label>
            <Input
              value={settings.companyName || person?.company || ''}
              onChange={(e) => onSettingsChange({...settings, companyName: e.target.value})}
              placeholder="Enter company name"
              className="bg-gray-800 border-gray-600 text-white"
            />
          </div>

          {/* Industry Input - Pre-populated from person data but editable */}
          <div>
            <label className="block text-sm font-medium text-white mb-1">
              Industry <span className="text-red-400">*</span>
            </label>
            <Input
              value={settings.industry || person?.industry || ''}
    onChange={(e) => onSettingsChange({...settings, industry: e.target.value})}
              placeholder="e.g., Fintech, Healthcare, SaaS"
    className={`bg-gray-800 border-gray-600 text-white ${
      !(settings.industry || person?.industry || '').trim() ? 'border-red-500' : ''
                }`}
            />
            {!(settings.industry || person?.industry || '').trim() && (
              <p className="text-red-400 text-xs mt-1">Industry is required</p>
            )}
          </div>

          {/* <div>
            <label className="block text-sm font-medium text-white mb-1">Focus</label>
            <Select
              value={settings.focus}
              onValueChange={(value) => onSettingsChange({...settings, focus: value})}
            >
              <SelectTrigger className="w-full bg-gray-800 border-gray-600 text-white">
                <SelectValue placeholder="Select focus" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="partnership">Partnership</SelectItem>
                <SelectItem value="collaboration">Collaboration</SelectItem>
                <SelectItem value="networking">Networking</SelectItem>
                <SelectItem value="sales">Sales</SelectItem>
              </SelectContent>
            </Select>
          </div> */}
          <div>
            <label className="block text-sm font-medium text-white mb-1">Tone</label>
            <Select
              value={settings.tone}
              onValueChange={(value) => onSettingsChange({...settings, tone: value})}
            >
              <SelectTrigger className="w-full bg-gray-800 border-gray-600 text-white">
                <SelectValue placeholder="Select tone" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="casual">Casual</SelectItem>
                <SelectItem value="friendly">Friendly</SelectItem>
                {/* <SelectItem value="networking">Networking</SelectItem>
                <SelectItem value="sales">Sales</SelectItem> */}
              </SelectContent>
            </Select>
          </div>
          {/* Context Points - Replace single input with multiple fields */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-white mb-1">
              Context Points <span className="text-red-400">*</span>
              <span className="text-xs text-gray-400 ml-2">(First 3 required, 4th optional)</span>
            </label>
            {[0, 1, 2, 3].map((index) => (
              <div key={index}>
                <label className="block text-xs text-gray-300 mb-1">
                  Context Point {index + 1} {index < 3 && <span className="text-red-400">*</span>}
                  {index < 3 && (
                    <span className="text-xs text-gray-400 ml-2">
                      ({countWords(settings.additionalContext?.[index] || '')} words - min 20)
                      </span>
                  )}
                </label>
                    <Textarea
                  value={settings.additionalContext?.[index] || ''}
                  onChange={(e) => {
                    const newContext = [...(settings.additionalContext || ['', '', '', ''])];
                    newContext[index] = e.target.value;
                    onSettingsChange({...settings, additionalContext: newContext});
                  }}
                  placeholder={index < 3 ? `Context point ${index + 1} (minimum 20 words)` : `Context point ${index + 1} (optional)`}
                  className={`bg-gray-800 border-gray-600 text-white min-h-[80px] resize-none ${
                    index < 3 && countWords(settings.additionalContext?.[index] || '') < 20
                      ? 'border-red-500'
                      : ''
                  }`}
                />
                {index < 3 && countWords(settings.additionalContext?.[index] || '') < 20 && (
                  <p className="text-red-400 text-xs mt-1">
                    Context point {index + 1} must be at least 20 words
                      </p>
                    )}
                  </div>
            ))}
                </div>

          {/* Template Selection */}
          <div>
            <label className="block text-sm font-medium text-white mb-1">
              Templates <span className="text-red-400">*</span>
              <span className="text-xs text-gray-400 ml-2">(Select at least 1)</span>
            </label>
            <div className="space-y-2">
              {templates.map((template) => (
                <div key={template.template_id} className="flex items-center space-x-2">
                  <Checkbox
                    id={template.template_id}
                    checked={selectedTemplateIds.includes(template.template_id)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedTemplateIds([...selectedTemplateIds, template.template_id]);
                      } else {
                        setSelectedTemplateIds(selectedTemplateIds.filter(id => id !== template.template_id));
                      }
                    }}
                  />
                  <label
                    htmlFor={template.template_id}
                    className="text-sm text-white cursor-pointer flex-1"
                  >
                    {template.template_name}
                  </label>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => openTemplateEditDialog(template)}
                    className="text-xs"
                  >
                    Edit
                  </Button>
              </div>
              ))}
            </div>
            {selectedTemplateIds.length === 0 && (
              <p className="text-red-400 text-xs mt-1">Please select at least one template.</p>
            )}
          </div>

          {/* Model Choice */}
          <div>
            <label className="block text-sm font-medium text-white mb-1">Model</label>
            <Select
              value={settings.modelChoice || 'deepseek'}
              onValueChange={(value) => onSettingsChange({...settings, modelChoice: value})}
            >
              <SelectTrigger className="w-full bg-gray-800 border-gray-600 text-white">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="deepseek">DeepSeek</SelectItem>
                <SelectItem value="groq">Groq</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Form Validation Summary */}
        {!isFormValid() && (
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-3">
            <p className="text-red-400 text-sm font-medium">Please complete the following:</p>
            <ul className="text-red-400 text-xs mt-1 space-y-1">
              {!getDisplayIndustry().trim() && <li>• Industry is required</li>}
              {(settings.additionalContext || []).slice(0, 3).map((context, index) => {
                const wordCount = countWords(context);
                if (wordCount < 20) {
                  return <li key={index}>• Context Point {index + 1} must have at least 20 words (currently {wordCount})</li>;
                }
                return null;
              })}
            </ul>
          </div>
        )}

        {/* Generate Buttons */}
        <div className="flex gap-3 pt-2">
          <Button
            onClick={onGenerate}
            disabled={isGenerating || !isFormValid()}
            className="flex-1 bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600"
          >
            {isGenerating ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Generating...
              </div>
            ) : "Generate Message"}
          </Button>
        </div>

        {/* Generated Message Display - REPLACED */}
        {generatedVariants && generatedVariants.length > 0 && (
          <div className="mt-6 space-y-8">
            {/* Group by template_id for colored borders */}
            {Object.entries(
              generatedVariants.reduce((acc, item) => {
                if (!acc[item.template_id]) acc[item.template_id] = [];
                acc[item.template_id].push(item);
                return acc;
              }, {} as Record<string, any[]>)
            ).map(([templateId, items], idx) => (
              <div
                key={templateId}
                style={{ border: `2px solid ${['#FFD600', '#FF9800', '#4CAF50'][idx % 3]}`, borderRadius: 8, padding: 16 }}
              >
                <div className="font-bold mb-2 text-white text-lg">{items[0].template_name}</div>
                {/* Change from grid to vertical layout - one card per row */}
                <div className="space-y-4">
                  {items.map((item, i) => (
                    <div key={item.variant} className="bg-gray-800 p-4 rounded mb-4 flex flex-col justify-between">
                      <div>
                        <div className="mb-2 font-semibold text-blue-300">Customized Context {item.variant}</div>

                        {/* Parse email to separate subject and body */}
                        {(() => {
                          const emailLines = item.email.split('\n');
                          const subjectLine = emailLines.find((line: string) => line.startsWith('Subject:'));
                          const subject = subjectLine ? subjectLine.replace('Subject:', '').trim() : 'Email from LeadGenAI';
                          const subjectIndex = emailLines.findIndex((line: string) => line.startsWith('Subject:'));
                          const body = subjectIndex >= 0
                            ? emailLines.slice(subjectIndex + 1).join('\n').trim()
                            : item.email;

                          return (
                            <div className="space-y-3">
                              {/* Subject Box */}
                              <div>
                                <div className="text-sm font-medium text-gray-300 mb-1">Subject</div>
                                <div className="bg-gray-900 p-3 rounded text-white text-sm border-l-4 border-blue-500">
                                  {subject}
            </div>
          </div>

                              {/* Body Box */}
                              <div>
                                <div className="text-sm font-medium text-gray-300 mb-1">Body</div>
                                <div className="bg-gray-900 p-3 rounded text-white text-sm border-l-4 border-green-500 whitespace-pre-line">
                                  {body}
              </div>
            </div>
            </div>
                          );
                        })()}
              </div>
                      <div className="flex gap-2 mt-2">
                        <Button size="sm" variant="outline" onClick={() => startEditingGeneratedItem(item)}>
                          <Edit3 className="h-4 w-4 mr-1" /> Edit
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                          onClick={() => handleRegenerate(item)}
                          disabled={regeneratingItems[item.message_id]}
                          className={regeneratingItems[item.message_id] ? 'opacity-70 cursor-not-allowed' : ''}
                        >
                          {regeneratingItems[item.message_id] ? (
                            <>
                              <div className="animate-spin h-4 w-4 mr-1 border-2 border-gray-300 border-t-blue-600 rounded-full"></div>
                              Regenerating...
                    </>
                  ) : (
                    <>
                              <RefreshCw className="h-4 w-4 mr-1" />
                              Regenerate
                    </>
                  )}
                </Button>
                        <Button size="sm" variant="outline" onClick={() => handleCopy(item.email)}>
                          <Copy className="h-4 w-4 mr-1" /> Copy
                </Button>
                <Button
                  size="sm"
                          variant="outline"
                          onClick={() => handleSave(item)}
                          disabled={savingItems[item.message_id]}
                          className={savingItems[item.message_id] ? 'opacity-70 cursor-not-allowed' : ''}
                        >
                          {savingItems[item.message_id] ? (
                            <>
                              <div className="animate-spin h-4 w-4 mr-1 border-2 border-gray-300 border-t-blue-600 rounded-full"></div>
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-1" />
                      Save
                    </>
                  )}
                </Button>
                <Button
                      size="sm"
                          variant="outline"
                          disabled={feedbackGiven[item.message_id] !== undefined && feedbackGiven[item.message_id] !== null}
                          onClick={() => handleFeedback(item, 'upvote')}
                          style={{
                            backgroundColor: feedbackGiven[item.message_id] === 'upvote' ? '#059669' : 'transparent',
                            color: feedbackGiven[item.message_id] === 'upvote' ? 'white' : '#34D399',
                            borderColor: feedbackGiven[item.message_id] === 'upvote' ? '#059669' : '#34D399',
                            opacity: feedbackGiven[item.message_id] !== undefined && feedbackGiven[item.message_id] !== null && feedbackGiven[item.message_id] !== 'upvote' ? 0.5 : 1,
                            cursor: feedbackGiven[item.message_id] !== undefined && feedbackGiven[item.message_id] !== null ? 'not-allowed' : 'pointer'
                          }}
                        >
                          <ThumbsUp className="h-4 w-4 mr-1" />
                          {feedbackGiven[item.message_id] === 'upvote' ? 'Upvoted' : 'Upvote'}
                    </Button>
                    <Button
                  size="sm"
                          variant="outline"
                          disabled={feedbackGiven[item.message_id] !== undefined && feedbackGiven[item.message_id] !== null}
                          onClick={() => handleFeedback(item, 'downvote')}
                          style={{
                            backgroundColor: feedbackGiven[item.message_id] === 'downvote' ? '#DC2626' : 'transparent',
                            color: feedbackGiven[item.message_id] === 'downvote' ? 'white' : '#F87171',
                            borderColor: feedbackGiven[item.message_id] === 'downvote' ? '#DC2626' : '#F87171',
                            opacity: feedbackGiven[item.message_id] !== undefined && feedbackGiven[item.message_id] !== null && feedbackGiven[item.message_id] !== 'downvote' ? 0.5 : 1,
                            cursor: feedbackGiven[item.message_id] !== undefined && feedbackGiven[item.message_id] !== null ? 'not-allowed' : 'pointer'
                          }}
                        >
                          <ThumbsDown className="h-4 w-4 mr-1" />
                          {feedbackGiven[item.message_id] === 'downvote' ? 'Downvoted' : 'Downvote'}
                    </Button>
                        <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => handleOpenInEmail(item.email)}>
                          <Mail className="h-4 w-4 mr-1" /> Open in Email
                </Button>
              </div>
            </div>
                  ))}
            </div>
              </div>
            ))}
          </div>
        )}

            {/* Action Buttons */}
            <div className="flex justify-between items-center gap-2 pt-2">
              {/* Feedback Buttons - Left Side */}


              {/* Feedback Buttons - Left Side */}

              </div>
      </div>
    </div>
  );
};
interface LinkedInHistoryItem {
  id: string;
  created_at: string;
  message_content: {
    company_name: string;
    generated_message: string;
    person_name?: string;
    timestamp?: string;
  };
  message_type: string;
}
// LinkedIn Message Generator Component
interface LinkedInMessageGeneratorProps {
  person: Person;
  onClose: () => void;
  onGenerate: () => Promise<void>;
  generatedMessage: string;
  isGenerating: boolean;
  settings: MessageSettings;
  onSettingsChange: (settings: MessageSettings) => void;
  onSave: () => Promise<void>;
  onCopy: () => Promise<void>;
  isSaving: boolean;
  copied: boolean;
  // Edit functionality props
  isEditing: boolean;
  editedMessage: string;
  onStartEditing: () => void;
  onSaveEdits: () => void;
  onCancelEditing: () => void;
  onEditMessageChange: (message: string) => void;
}

const LinkedInMessageGenerator: React.FC<LinkedInMessageGeneratorProps> = ({
  person,
  onClose,
  onGenerate,
  generatedMessage,
  isGenerating,
  settings,
  onSettingsChange,
  onSave,
  onCopy,
  isSaving,
  copied,
  isEditing,
  editedMessage,
  onStartEditing,
  onSaveEdits,
  onCancelEditing,
  onEditMessageChange
}) => {
  return (
    <div className="space-y-6 p-6">
      {/* Removed duplicate title */}
      <div className="space-y-4">
        <div className="p-4 border rounded-lg text-white bg-blue-600">
          <div className="flex items-baseline gap-2">
            <p className="font-medium">Person:</p>
            <p className="text-lg">{person.name}</p>
          </div>
          <p className="text-sm text-white mt-1">Company: {person.company}</p>
          {person.linkedin && (
            <p className="text-sm text-white mt-1">
              LinkedIn: <span className="text-blue-200">{person.linkedin}</span>
            </p>
          )}
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-white mb-1">Tone</label>
            <Select
              value={settings.tone}
                onValueChange={(value) => onSettingsChange({...settings, tone: value})}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select tone" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="professional">Professional</SelectItem>
                <SelectItem value="friendly">Friendly</SelectItem>
                <SelectItem value="direct">Direct</SelectItem>
                <SelectItem value="casual">Casual</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-1">Focus</label>
            <Select
              value={settings.focus}
                onValueChange={(value) => onSettingsChange({...settings, focus: value})}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select focus" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="partnership">Partnership</SelectItem>
                <SelectItem value="collaboration">Collaboration</SelectItem>
                <SelectItem value="networking">Networking</SelectItem>
                <SelectItem value="sales">Sales</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-1">Additional Content</label>
            <Input
              value={Array.isArray(settings.additionalContext) ? settings.additionalContext.join(', ') : settings.additionalContext}
              onChange={(e) => onSettingsChange({...settings, additionalContext: e.target.value.split(',').map(s => s.trim()).filter(s => s)})}
              placeholder="Any special notes or context (comma-separated)"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <Button
            onClick={onGenerate}
            disabled={isGenerating}
            className="flex-1"
          >
            {isGenerating ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Generating...
              </div>
            ) : "Generate Message"}
          </Button>
        </div>

        {generatedMessage && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-medium text-white">Generated Message</label>
              {!isEditing && generatedMessage && (
                <Button
                  onClick={onStartEditing}
                  className="bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600 text-white font-semibold px-4 py-1 rounded"
                >
                  Edit
                </Button>
              )}
              {isEditing && generatedMessage && (
                <div className="flex gap-2">
                  <Button
                    onClick={onSaveEdits}
                    size="icon"
                    className="bg-green-600 hover:bg-green-700 text-white p-1 h-auto"
                  >
                    <Check className="h-4 w-4" />
                  </Button>
                  <Button
                    onClick={onCancelEditing}
                    size="icon"
                    className="bg-red-600 hover:bg-red-700 text-white p-1 h-auto"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
            {isEditing ? (
              <Textarea
                value={editedMessage}
                onChange={(e) => onEditMessageChange(e.target.value)}
                className="bg-dark-primary border-dark-border text-white min-h-[200px] resize-none"
                placeholder="Edit your LinkedIn message..."
              />
            ) : (
              <div className="p-4 border rounded-lg text-white bg-blue-600 whitespace-pre-wrap max-h-60 overflow-y-auto">
                {generatedMessage}
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              {isEditing ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onSaveEdits}
                  >
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onCancelEditing}
                  >
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={onCopy}
                    title="Copy to clipboard"
                  >
                    {copied ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={onSave}
                    disabled={isSaving}
                    title="Save message"
                  >
                    {isSaving ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                  </Button>
                  <Button onClick={() => {
                    if (person.linkedin) {
                      window.open(person.linkedin, '_blank');
                    }
                  }}>
                    Open LinkedIn Profile
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// PopupBig Component
interface PopupBigProps {
  show: boolean;
  onClose: () => void;
  person: Person | null;
  isEditing: boolean;
  popupTab: string;
  setPopupTab: (tab: string) => void;
  setPopupData: (person: Person) => void;
  onSave: () => void;
}
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

const PopupBig: React.FC<PopupBigProps> = ({
  show,
  onClose,
  person,
  isEditing,
  popupTab,
  setPopupTab,
  setPopupData,
  onSave
}) => {
  if (!person) return null;

  const handleClose = () => {
    onClose();
    setPopupTab('overview');
  };



  return (
    <Dialog open={show} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">{person.name}</DialogTitle>
        </DialogHeader>

        <div className="space-y-8">
          {/* Tab Navigation */}
          <div className="border-b pb-4">
            <div className="flex space-x-4">
              <button
                onClick={() => setPopupTab('overview')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                  popupTab === 'overview'
                    ? 'border-teal-500 text-teal-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
              >
                Overview
              </button>
              <button
                onClick={() => setPopupTab('contact')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                  popupTab === 'contact'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
              >
                Contact Info
              </button>
            </div>
          </div>

          {/* Overview Tab Content */}
          {popupTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {overviewFields.map(({ key, label }) => {
                let value = person[key as keyof Person] || "";
                const isLink = key === "website" || key === "linkedin";

                // Special handling for website field
                if (key === "website" && value && !value.toString().startsWith('http')) {
                  value = `https://${value}`;
                }

                return (
                  <div key={key} className="space-y-1">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      {label}
                    </label>
                    {isEditing ? (
                      <Input
                        value={value.toString()}
                        onChange={(e) =>
                          setPopupData({ ...person, [key]: e.target.value })
                        }
                        className="text-sm"
                        placeholder={isLink ? "https://..." : ""}
                      />
                    ) : (
                      <div className="px-3 py-2 rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-zinc-800 text-sm text-gray-900 dark:text-white">
                        {isLink && value ? (
                          <a
                            href={value.toString()}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {value.toString()}
                          </a>
                        ) : value || <span className="italic text-gray-400">N/A</span>}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Contact Tab Content */}
          {popupTab === 'contact' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {contactFields.map(({ key, label }) => {
                const value = person[key as keyof Person] || "";
                const isLink = key === "linkedin";

                return (
                  <div key={key} className="space-y-1">
                    <label className="block text-sm font-medium text-gray-700">
                      {label}
                    </label>
                    {isEditing ? (
                      <Input
                        value={value.toString()}
                        onChange={(e) =>
                          setPopupData({ ...person, [key]: e.target.value })
                        }
                        className="text-sm"
                        placeholder={isLink ? "https://..." : ""}
                      />
                    ) : (
                      <div className="px-3 py-2 rounded-md border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-zinc-800 text-sm text-gray-900 dark:text-white">
                        {isLink && value ? (
                          <a
                            href={value.toString()}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            {value.toString()}
                          </a>
                        ) : value || <span className="italic text-gray-400">N/A</span>}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end gap-4 pt-4 border-t">
            {isEditing ? (
              <Button size="sm" onClick={onSave}>
                Save Changes
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => person.email && isValidEmail(person.email) && window.open(`mailto:${person.email}`, '_blank')}
                  disabled={!isValidEmail(person.email)}
                  className={!isValidEmail(person.email) ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  <Mail className="h-4 w-4 mr-2" />
                  Send Email
                </Button>

                <Button
                  variant="outline"
                  onClick={() => person.linkedin && normalizeLinkedInValue(person.linkedin) !== 'N/A' && window.open(person.linkedin, '_blank')}
                  disabled={!person.linkedin || normalizeLinkedInValue(person.linkedin) === 'N/A'}
                  className={normalizeLinkedInValue(person.linkedin) === 'N/A' ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  <Linkedin className="h-4 w-4 mr-2" />
                  LinkedIn
                </Button>

                <Button
                  variant="outline"
                  onClick={() => person.website && normalizeWebsiteValue(person.website) !== 'N/A' && window.open(person.website.startsWith('http') ? person.website : `https://${person.website}`, '_blank')}
                  disabled={!person.website || normalizeWebsiteValue(person.website) === 'N/A'}
                  className={normalizeWebsiteValue(person.website) === 'N/A' ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  <Globe className="h-4 w-4 mr-2" />
                  Website
                </Button>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

const ExpandableCell: React.FC<{ text: string }> = ({ text }) => {
  const [expanded, setExpanded] = useState(false);
  const isLong = text && text.length > 30;
  if (!isLong) return <span>{text}</span>;

  return (
    <div className="whitespace-pre-wrap">
      <span>
        {expanded ? text : `${text.slice(0, 30)}...`}
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

// Main PersonsPage Component
export default function PersonsPage() {
  const router = useRouter()
  // State declarations
  const [persons, setPersons] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage, setItemsPerPage] = useState(25)
  const [selectedPersons, setSelectedPersons] = useState<string[]>([])
  const [showFilters, setShowFilters] = useState(false)
  const [popupData, setPopupData] = useState<Person | null>(null)
  const [popupTab, setPopupTab] = useState('overview')
  const [isEditing, setIsEditing] = useState(false)
  const [user, setUser] = useState<{ tier?: string }>({});
  const [showUpgradePopup, setShowUpgradePopup] = useState(false);
  const [favoriteLeads, setFavoriteLeads] = useState<Set<string>>(new Set()); // Track favorite status
  const [leadsWithNotes, setLeadsWithNotes] = useState<Set<string>>(new Set());

  // Email popup states
  const [emailPopupTab, setEmailPopupTab] = useState('generator') // 'generator' or 'history'
  const [emailPopupData, setEmailPopupData] = useState<Person | null>(null); // Add this state for emailPopupData
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<HistoryItem | null>(null)
  const [showHistoryPopup, setShowHistoryPopup] = useState(false)
  const [isEditingHistory, setIsEditingHistory] = useState(false)
  const [editedHistoryMessage, setEditedHistoryMessage] = useState("")
  const [isHistorySaving, setIsHistorySaving] = useState(false)
  const [generatedVariants, setGeneratedVariants] = useState<any[]>([]);
  const [generatedMessage, setGeneratedMessage] = useState("")
  const [generatedSubject, setGeneratedSubject] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [isEmailSaving, setIsEmailSaving] = useState(false)
  const [emailCopied, setEmailCopied] = useState(false)
  const [currentMessageId, setCurrentMessageId] = useState<string | null>(null);
  const [currentMessageData, setCurrentMessageData] = useState<any>(null);
  const [messageSettings, setMessageSettings] = useState<MessageSettings>({
    tone: "casual",
    focus: "partnership",
    additionalContext: ["", "", "", ""], // Initialize as array
  })
  // Email edit states
  const [isEmailEditing, setIsEmailEditing] = useState(false)
  const [editedEmailMessage, setEditedEmailMessage] = useState("")
  const [editedEmailSubject, setEditedEmailSubject] = useState("")

  const [linkedinPopupData, setLinkedinPopupData] = useState<Person | null>(null)
  const [linkedinGeneratedMessage, setLinkedinGeneratedMessage] = useState("")
  const [linkedinIsGenerating, setLinkedinIsGenerating] = useState(false)
  const [isLinkedInSaving, setIsLinkedInSaving] = useState(false)
  const [linkedInCopied, setLinkedInCopied] = useState(false)
  const [linkedinPopupTab, setLinkedinPopupTab] = useState('generator') // 'generator' or 'history'
  const [linkedInHistoryItems, setLinkedInHistoryItems] = useState<LinkedInHistoryItem[]>([])
  const [isLoadingLinkedInHistory, setIsLoadingLinkedInHistory] = useState(false)
  const [selectedLinkedInHistoryItem, setSelectedLinkedInHistoryItem] = useState<LinkedInHistoryItem | null>(null)
  const [showLinkedInHistoryPopup, setShowLinkedInHistoryPopup] = useState(false)
  const [isEditingLinkedInHistory, setIsEditingLinkedInHistory] = useState(false)
  const [editedLinkedInHistoryMessage, setEditedLinkedInHistoryMessage] = useState("")

  const [linkedinMessageSettings, setLinkedinMessageSettings] = useState<MessageSettings>({
    tone: "casual",
    focus: "partnership",
    additionalContext: []
  })
  // LinkedIn edit states
  const [isLinkedInEditing, setIsLinkedInEditing] = useState(false)
  const [editedLinkedInMessage, setEditedLinkedInMessage] = useState("")
  const [feedbackStatus, setFeedbackStatus] = useState<Record<string, { type: string; timestamp: string }>>({});
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  
  // Phone and Email validation states
  const [showPhoneValidator, setShowPhoneValidator] = useState(false);
  const [selectedPersonForPhoneValidation, setSelectedPersonForPhoneValidation] = useState<Person | null>(null);
  const [showEmailValidator, setShowEmailValidator] = useState(false);
  const [selectedPersonForEmailValidation, setSelectedPersonForEmailValidation] = useState<Person | null>(null);
  const [phoneValidationResult, setPhoneValidationResult] = useState<any>(null);
  const [emailValidationResult, setEmailValidationResult] = useState<any>(null);
  const [isValidatingPhone, setIsValidatingPhone] = useState(false);
  const [isValidatingEmail, setIsValidatingEmail] = useState(false);
  
  // Apollo enrichment states
  const [apolloSearchLoading, setApolloSearchLoading] = useState(false);
  const [selectedApolloPerson, setSelectedApolloPerson] = useState<any>(null);
  const [enrichedPersonData, setEnrichedPersonData] = useState<any>(null);
  const [enrichPersonName, setEnrichPersonName] = useState("");
  const [enrichPersonCompany, setEnrichPersonCompany] = useState("");
  const [enrichCompanyDomain, setEnrichCompanyDomain] = useState("");
  const getButtonState = (feedbackType: string) => {
    const currentFeedback = feedbackStatus[currentMessageId || ''];

    if (!currentFeedback) {
      return { disabled: false, active: false };
    }

    if (currentFeedback.type === feedbackType) {
      return { disabled: true, active: true };
    }

    return { disabled: false, active: false };
  };

  // Action preview popup states
  const [actionPreviewPopup, setActionPreviewPopup] = useState<{
    show: boolean;
    type: 'email' | 'linkedin' | 'website';
    person: Person | null;
  }>({
    show: false,
    type: 'email',
    person: null
  })

  // Notification state
  const [notif, setNotif] = useState<{
    show: boolean;
    message: string;
    type: "success" | "error" | "info";
  }>({
    show: false,
    message: "",
    type: "success",
  })

  // Filter states
  const [titleFilter, setTitleFilter] = useState("")
  const [companyFilter, setCompanyFilter] = useState("")
  const [industryFilter, setIndustryFilter] = useState("")
  const [businessTypeFilter, setBusinessTypeFilter] = useState("")
  const [addressFilter, setAddressFilter] = useState("")

  // Notes popup states
  const [notesPopupOpen, setNotesPopupOpen] = useState(false);
  const [notesLeadId, setNotesLeadId] = useState<string | null>(null);
  const [notesName, setNotesName] = useState<string>("");





  // Phone and Email validation handlers
  const handlePhoneValidatorClick = async (person: Person, skipLookup: boolean = false) => {
    try {
      console.log('🚀 Starting phone validation for:', person.phone);
      setSelectedPersonForPhoneValidation(person);
      setShowPhoneValidator(true);
      setIsValidatingPhone(true);
      setPhoneValidationResult(null);
      
      let existingContact = null;
      let useFallback = false;
      
      // Step 1: Lookup contact in database (skip if re-validating)
      if (!skipLookup) {
        console.log('📋 Looking up contact in database...');
        console.log('🌐 Lookup URL:', `${process.env.NEXT_PUBLIC_DATABASE_URL}/contact_verification/standalone/lookup?contact_type=phone&contact_value=${encodeURIComponent(person.phone)}`);
        
        const lookupResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/contact_verification/standalone/lookup?contact_type=phone&contact_value=${encodeURIComponent(person.phone)}`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        console.log('📡 Lookup response status:', lookupResponse.status);
        
        if (lookupResponse.ok) {
          const lookupData = await lookupResponse.json();
          console.log('📊 Lookup response data:', lookupData);
          
          if (lookupData.success && lookupData.found && lookupData.data) {
            existingContact = lookupData.data;
            console.log('✅ Contact found in database:', existingContact);
          } else {
            console.log('⚠️ Contact not found in database, using fallback');
            console.log('🔍 LookupData.success:', lookupData.success);
            console.log('🔍 LookupData.found:', lookupData.found);
            console.log('🔍 LookupData.data:', lookupData.data);
            useFallback = true;
          }
        } else {
          console.log('❌ Failed to lookup contact, using fallback');
          useFallback = true;
        }
        
        console.log('🔄 Fallback status:', useFallback);
      } else {
        console.log('🔄 Skipping database lookup (re-validation mode)');
        useFallback = true;
      }
      console.log('🔄 About to proceed to external validation...');
      
      // Step 2: Validate phone number (external service) - ALWAYS CALL THIS
      console.log('📞 Calling external phone validation API...');
      console.log('🌐 API URL:', `${process.env.NEXT_PUBLIC_PHONEVALIDATOR_API_URL}/validate_phone`);
      console.log('�� Request payload:', { phone: person.phone });
      
      // Add a small delay to see the logs clearly
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_PHONEVALIDATOR_API_URL}/validate_phone`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone: person.phone
        }),
      });

      console.log('📡 External validation response status:', response.status);
      console.log('📡 External validation response received!');
      
      if (response.ok) {
        const validationResult = await response.json();
        console.log('✅ Phone validation result:', validationResult);
        
        // Extract phone_result data for display
        const phoneData = validationResult.phone_result || validationResult;
        
        // Set the result for display with timestamp
        const timestamp = new Date().toISOString();
        if (useFallback) {
          console.log('🔄 Setting fallback result');
          setPhoneValidationResult({ 
            ...phoneData, 
            fallback: true,
            message: 'Used fallback validation (contact not in DB)',
            timestamp
          });
        } else {
          console.log('✅ Setting normal result');
          setPhoneValidationResult({
            ...phoneData,
            timestamp
          });
        }
        
        // Step 3: Store validation results in database with lead_id
        console.log('💾 Storing validation results in database...');
        const leadId = person.lead_id || person.id;
        const storageResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/contact_verification/phone`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            lead_id: leadId,
            phone: person.phone,
            verification_data: {
              status: phoneData.valid ? "valid" : "invalid",
              score: 0.9, // Default score, could be calculated based on validation results
              details: {
                format_valid: phoneData.valid || false,
                country_code: phoneData.country || "Unknown",
                carrier: phoneData['prefix-network'] || "Unknown",
                line_type: phoneData.type || "unknown",
                timezone: phoneData.location || "Unknown",
                valid: phoneData.valid || false
              },
              timestamp: new Date().toISOString()
            }
          }),
        });

        if (storageResponse.ok) {
          console.log('✅ Phone validation stored successfully');
        } else {
          console.error('❌ Failed to store phone validation in DB');
        }
      } else {
        console.error('❌ Phone validation failed:', response.statusText);
        setPhoneValidationResult({ error: 'Validation failed' });
      }
    } catch (error) {
      console.error('💥 Error validating phone:', error);
      setPhoneValidationResult({ error: 'Network error' });
    } finally {
      console.log('🏁 Phone validation process completed');
      setIsValidatingPhone(false);
    }
  };

  const handleEmailValidationClick = async (person: Person, skipLookup: boolean = false) => {
    try {
      console.log('🚀 Starting email validation for:', person.email);
      setSelectedPersonForEmailValidation(person);
      setShowEmailValidator(true);
      setIsValidatingEmail(true);
      setEmailValidationResult(null);
      
      let existingContact = null;
      let useFallback = false;
      
      // Step 1: Lookup contact in database (skip if re-validating)
      if (!skipLookup) {
        console.log('📋 Looking up contact in database...');
        console.log('🌐 Lookup URL:', `${process.env.NEXT_PUBLIC_DATABASE_URL}/contact_verification/standalone/lookup?contact_type=email&contact_value=${encodeURIComponent(person.email)}`);
        
        const lookupResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/contact_verification/standalone/lookup?contact_type=email&contact_value=${encodeURIComponent(person.email)}`, {
          method: 'GET',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        console.log('📡 Lookup response status:', lookupResponse.status);
        
        if (lookupResponse.ok) {
          const lookupData = await lookupResponse.json();
          console.log('📊 Lookup response data:', lookupData);
          
          if (lookupData.success && lookupData.found && lookupData.data) {
            existingContact = lookupData.data;
            console.log('✅ Contact found in database:', existingContact);
          } else {
            console.log('⚠️ Contact not found in database, using fallback');
            console.log('🔍 LookupData.success:', lookupData.success);
            console.log('🔍 LookupData.found:', lookupData.data);
            console.log('🔍 LookupData.data:', lookupData.data);
            useFallback = true;
          }
        } else {
          console.log('❌ Failed to lookup contact, using fallback');
          useFallback = true;
        }
        
        console.log('🔄 Fallback status:', useFallback);
      } else {
        console.log('🔄 Skipping database lookup (re-validation mode)');
        useFallback = true;
      }
      console.log('🔄 About to proceed to external validation...');
      
      // Step 2: Validate email address (external service) - ALWAYS CALL THIS
      console.log('📧 Calling external email validation API...');
      console.log('🌐 API URL:', `${process.env.NEXT_PUBLIC_PHONEVALIDATOR_API_URL}/validate_email`);
      console.log('📤 Request payload:', { email: person.email });
      
      // Add a small delay to see the logs clearly
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_PHONEVALIDATOR_API_URL}/validate_email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: person.email
        }),
      });

      console.log('📡 External validation response status:', response.status);
      console.log('📡 External validation response received!');
      
      if (response.ok) {
        const validationResult = await response.json();
        console.log('✅ Email validation result:', validationResult);
        
        // Extract email_result data for display
        const emailData = validationResult.email_result || validationResult;
        
        // Set the result for display with timestamp
        const timestamp = new Date().toISOString();
        if (useFallback) {
          console.log('🔄 Setting fallback result');
          setEmailValidationResult({ 
            ...emailData, 
            fallback: true,
            message: 'Used fallback validation (contact not in DB)',
            timestamp
          });
        } else {
          console.log('✅ Setting normal result');
          setEmailValidationResult({
            ...emailData,
            timestamp
          });
        }
        
        // Step 3: Store validation results in database with lead_id
        console.log('💾 Storing validation results in database...');
        const leadId = person.lead_id || person.id;
        const storageResponse = await fetch(`${process.env.NEXT_PUBLIC_DATABASE_URL}/contact_verification/email`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            lead_id: leadId,
            email: person.email,
            verification_data: {
              status: emailData.active || emailData.valid ? "valid" : "invalid",
              score: 0.9, // Default score, could be calculated based on validation results
              details: {
                format_valid: emailData.valid || false,
                domain_exists: emailData.domain_exists || false,
                disposable: emailData.disposable || false,
                mx_record: emailData.mx_record || false,
                smtp_check: emailData.smtp_check || false
              },
              timestamp: new Date().toISOString()
            }
          }),
        });

        if (storageResponse.ok) {
          console.log('✅ Email validation stored successfully');
        } else {
          console.error('❌ Failed to store email validation in DB');
        }
      } else {
        console.error('❌ Email validation failed:', response.statusText);
        setEmailValidationResult({ error: 'Validation failed' });
      }
    } catch (error) {
      console.error('💥 Error validating email:', error);
      setEmailValidationResult({ error: 'Network error' });
    } finally {
      console.log('🏁 Email validation process completed');
      setIsValidatingEmail(false);
    }
  };

  // --- Save from Action Preview Popup ---
  const [isActionSaving, setIsActionSaving] = useState(false);
  // Removed duplicate declaration of handleToneChange
  // Declare the handleToneChange function properly
  // Removed duplicate declaration of handleToneChange
  // Save email message function
  const [selectedTemplate, setSelectedTemplate] = useState<{
    template_id: string;
    template_name: string;
    template_content: string;
    updated_at: string;
  } | null>(null);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const saveEmailMessage = async () => {
    if (!generatedMessage || !emailPopupData) {
      showNotification('No message to save or person data missing.', 'error');
      return;
    }

    setIsEmailSaving(true);
    try {
      const emailWithSubject = generatedSubject
        ? `Subject: ${generatedSubject}\n\n${generatedMessage}`
        : generatedMessage;

      const response = await fetch(`https://sandbox-api.saasquatchleads.com/save_message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          type: "email",
          company_name: emailPopupData.company,
          message: emailWithSubject
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save email message");
      }

      showNotification('Email message saved successfully!', 'success');
      if (emailPopupTab === 'history') {
        fetchEmailHistory(emailPopupData.company);
      }
    } catch (error) {
      console.error("Error saving email message:", error);
      showNotification('Failed to save email message. Please try again.', 'error');
    } finally {
      setIsEmailSaving(false);
    }
  };

  // Fetch email history filtered by company
  const fetchEmailHistory = async (companyName: string) => {
    setIsLoadingHistory(true);
    try {
      const response = await fetch(`https://sandbox-api.saasquatchleads.com/generated_history/email`, {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch email message history");
      }

      const data = await response.json();
      // Filter by company name
      const filteredHistory = data.filter((item: any) =>
        item.message_content.company_name === companyName
      );
      setHistoryItems(filteredHistory);
    } catch (error) {
      console.error("Error fetching email message history:", error);
      setHistoryItems([]);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // History popup handlers
  const openHistoryPopup = (item: HistoryItem) => {
    setSelectedHistoryItem(item);
    setShowHistoryPopup(true);
  };

  const closeHistoryPopup = () => {
    setShowHistoryPopup(false);
    setSelectedHistoryItem(null);
    setIsEditingHistory(false);
    setEditedHistoryMessage("");
  };

  // History editing handlers
  const startEditingHistory = () => {
    if (selectedHistoryItem) {
      setEditedHistoryMessage(selectedHistoryItem.message_content.generated_message);
      setIsEditingHistory(true);
    }
  };

  const saveHistoryEdits = () => {
    if (selectedHistoryItem && editedHistoryMessage) {
      setSelectedHistoryItem({
        ...selectedHistoryItem,
        message_content: {
          ...selectedHistoryItem.message_content,
          generated_message: editedHistoryMessage
        }
      });
      setIsEditingHistory(false);
      showNotification("Changes saved successfully!", "success");
    }
  };

  const cancelHistoryEditing = () => {
    setIsEditingHistory(false);
    setEditedHistoryMessage("");
  };

  // Copy to clipboard for history
  const copyHistoryToClipboard = async (message: string) => {
    try {
      await navigator.clipboard.writeText(message);
      showNotification("Email copied to clipboard!", "success");
    } catch (error) {
      showNotification("Failed to copy to clipboard", "error");
    }
  };

  // Open in Gmail for history
  const openHistoryInEmail = (message: string) => {
    // For history items, the message format is: "Subject\n\nBody" or just "Body"
    const lines = message.split('\n');
    let subject, body;

    // Check if the first line looks like a subject (no colon, reasonable length)
    if (lines.length > 1 && lines[0].trim() && !lines[0].includes(':') && lines[0].length < 100 && lines[1].trim() === '') {
      // First line is subject, body starts after the empty line
      subject = lines[0].trim();
      body = lines.slice(2).join('\n').trim();
    } else {
      // No clear subject/body separation, treat as body only
      subject = 'Generated Email';
      body = message;
    }

    // Create Gmail compose URL with proper encoding
    const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(gmailUrl, '_blank');
  };

  // Format date utility
  // Removed duplicate declaration of formatDate
  // template staes
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>([]);


  // Save LinkedIn message function
  const saveLinkedInMessage = async () => {
    if (!linkedinGeneratedMessage || !linkedinPopupData) {
      showNotification('No message to save or person data missing.', 'error');
      return;
    }
    if (linkedinPopupTab === 'history') {
      fetchLinkedInHistory(linkedinPopupData.company);
    }

    setIsLinkedInSaving(true);
    try {
      const response = await fetch(`${DATABASE_URL_NOAPI}/save_message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          type: "linkedin",
          company_name: linkedinPopupData.company,
          message: linkedinGeneratedMessage
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save LinkedIn message");
      }

      showNotification('LinkedIn message saved successfully!', 'success');
    } catch (error) {
      console.error("Error saving LinkedIn message:", error);
      showNotification('Failed to save LinkedIn message. Please try again.', 'error');
    } finally {
      setIsLinkedInSaving(false);
    }
  };
  const fetchLinkedInHistory = async (companyName: string) => {
    setIsLoadingLinkedInHistory(true);
    try {
      const response = await fetch(`${DATABASE_URL_NOAPI}/generated_history/linkedin`, {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch LinkedIn message history");
      }

      const data = await response.json();
      // Filter by company name
      const filteredHistory = data.filter((item: any) =>
        item.message_content.company_name === companyName
      );
      setLinkedInHistoryItems(filteredHistory);
    } catch (error) {
      console.error("Error fetching LinkedIn message history:", error);
      setLinkedInHistoryItems([]);
    } finally {
      setIsLoadingLinkedInHistory(false);
    }
  };

  // LinkedIn history popup handlers
  const openLinkedInHistoryPopup = (item: LinkedInHistoryItem) => {
    setSelectedLinkedInHistoryItem(item);
    setShowLinkedInHistoryPopup(true);
  };

  const closeLinkedInHistoryPopup = () => {
    setShowLinkedInHistoryPopup(false);
    setSelectedLinkedInHistoryItem(null);
    setIsEditingLinkedInHistory(false);
    setEditedLinkedInHistoryMessage("");
  };

  // LinkedIn history editing handlers
  const startEditingLinkedInHistory = () => {
    if (selectedLinkedInHistoryItem) {
      setEditedLinkedInHistoryMessage(selectedLinkedInHistoryItem.message_content.generated_message);
      setIsEditingLinkedInHistory(true);
    }
  };

  const saveLinkedInHistoryEdits = () => {
    if (selectedLinkedInHistoryItem && editedLinkedInHistoryMessage) {
      setSelectedLinkedInHistoryItem({
        ...selectedLinkedInHistoryItem,
        message_content: {
          ...selectedLinkedInHistoryItem.message_content,
          generated_message: editedLinkedInHistoryMessage
        }
      });
      setIsEditingLinkedInHistory(false);
      showNotification("Changes saved successfully!", "success");
    }
  };

  const cancelLinkedInHistoryEditing = () => {
    setIsEditingLinkedInHistory(false);
    setEditedLinkedInHistoryMessage("");
  };

  // Copy to clipboard for LinkedIn history
  const copyLinkedInHistoryToClipboard = async (message: string) => {
    try {
      await navigator.clipboard.writeText(message);
      showNotification("LinkedIn message copied to clipboard!", "success");
    } catch (error) {
      showNotification("Failed to copy to clipboard", "error");
    }
  };

  // Open LinkedIn profile for history
  const openLinkedInProfile = (personName?: string) => {
    if (linkedinPopupData?.linkedin) {
      window.open(linkedinPopupData.linkedin, '_blank');
    } else {
      // If no direct LinkedIn URL, open LinkedIn search
      const searchQuery = personName || linkedinPopupData?.name || '';
      window.open(`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(searchQuery)}`, '_blank');
    }
  };

  // Format date utility (same as email)
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric'
    });
  };

  // Copy email message function
  const copyEmailMessage = async () => {
    try {
      const emailWithSubject = generatedSubject
        ? `Subject: ${generatedSubject}\n\n${generatedMessage}`
        : generatedMessage;

      await navigator.clipboard.writeText(emailWithSubject);
      setEmailCopied(true);
      showNotification('Email copied to clipboard!', 'success');
      setTimeout(() => setEmailCopied(false), 2000);
    } catch (error) {
      showNotification('Failed to copy to clipboard.', 'error');
    }
  };

  // Copy LinkedIn message function
  const copyLinkedInMessage = async () => {
    try {
      await navigator.clipboard.writeText(linkedinGeneratedMessage);
      setLinkedInCopied(true);
      showNotification('LinkedIn message copied to clipboard!', 'success');
      setTimeout(() => setLinkedInCopied(false), 2000);
    } catch (error) {
      showNotification('Failed to copy to clipboard.', 'error');
    }
  };

  const handleActionSave = async () => {
    if (!actionPreviewPopup.person) return;
    setIsActionSaving(true);
    try {
      if (actionPreviewPopup.type === 'email') {
        if (!generatedMessage) return;
        await saveEmailMessage();
      } else if (actionPreviewPopup.type === 'linkedin') {
        if (!linkedinGeneratedMessage) return;
        await saveLinkedInMessage();
      }
    } catch (err) {
      showNotification('Failed to save message.', 'error');
    } finally {
      setIsActionSaving(false);
    }
  };

  // Clear all filters function
  const clearAllFilters = () => {
    setTitleFilter("")
    setCompanyFilter("")
    setIndustryFilter("")
    setBusinessTypeFilter("")
    setAddressFilter("")
    setValidationFilter("all")
  }

  // Function to show notifications
  const showNotification = (message: string, type: "success" | "error" | "info" = "success") => {
    setNotif({ show: true, message, type });
    setTimeout(() => {
      setNotif(prev => ({ ...prev, show: false }));
    }, 3500);
  };

  // Function to toggle favorite status
  const handleToggleFavorite = async (leadId: string) => {
    console.log("handleToggleFavorite called with leadId:", leadId);
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

        // Update the person in persons array with favorite status
        setPersons(prev =>
          prev.map(person =>
            (person.lead_id || person.id) === leadId
              ? { ...person, is_favorite: isFavorite }
              : person
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

  // Fetch persons data from API
  useEffect(() => {
    const fetchPersons = async () => {
      try {
        setLoading(true)
        setError(null)

        const storedUser = typeof window !== "undefined"
          ? JSON.parse(sessionStorage.getItem("user") || "{}")
          : {};
        setUser(storedUser);

        const draftsRes = await fetch(`${DATABASE_URL}/leads/drafts`, {
          method: "GET",
          credentials: "include",
        });

        if (!draftsRes.ok) {
          throw new Error(`HTTP error! status: ${draftsRes.status}`)
        }

        const data = await draftsRes.json()

        // Debug: Log the first few items to see the data structure
        console.log("API Response data structure:", data.slice(0, 2));

        // Helper function to check if a name contains placeholder strings
        const isPlaceholderName = (name: string): boolean => {
          const placeholderPatterns = [
            'contact information not available on linkedin',
            'contact information',
            'not available on linkedin',
            'n/a',
            'na',
            'not available',
            'unavailable',
            'no information',
            'information not available',
            "couldn't locate a key contact",
            'no person of interest identified',
            'no decision maker found'
          ];
          
          const normalizedName = name.toLowerCase().trim();
          return placeholderPatterns.some(pattern => normalizedName.includes(pattern));
        };

        // Map the API response to Person interface - accessing draft_data
        let mappedPersons: Person[] = [];
        data.forEach((item: any, index: number) => {
          const draftData = item.draft_data || {};
          if (Array.isArray(draftData.contacts) && draftData.contacts.length > 0) {
            draftData.contacts.forEach((contact: any, cIdx: number) => {
              // Check if the constructed name would be empty or contain placeholder strings
              const constructedName = `${contact.owner_first_name || ''} ${contact.owner_last_name || ''}`.trim();
              if (!constructedName || isPlaceholderName(constructedName)) {
                return; // Skip contacts with no name or placeholder names
              }
              mappedPersons.push({
                id: `${item.id || item.lead_id || index.toString()}-${cIdx}`,
                lead_id: item.lead_id,
                draft_id: item.draft_id,
                name: constructedName,
                title: contact.owner_title || 'N/A',
                website: normalizeWebsiteValue(draftData.website || ''),
                email: normalizeEmailValue(contact.owner_email || ''),
                location: `${draftData.city || ''}, ${draftData.state || ''}`.replace(', ', '').trim() || 'N/A',
                company: draftData.company || 'N/A',
                phone: contact.owner_phone_number || draftData.company_phone || '',
                linkedin: normalizeLinkedInValue(contact.owner_linkedin || draftData.company_linkedin || ''),
                industry: draftData.industry || 'N/A',
                employees: draftData.employees || 0,
                yearFounded: draftData.year_founded || 'N/A',
                businessType: draftData.business_type || 'N/A',
                address: `${draftData.street || ''} ${draftData.city || ''} ${draftData.state || ''}`.trim() || 'N/A',
                is_favorite: item.is_favorite || false,
                seniority: contact.seniority || 'N/A'
              });
            });
          } else {
            // Check if the constructed name would be empty or contain placeholder strings
            const constructedName = `${draftData.owner_first_name || ''} ${draftData.owner_last_name || ''}`.trim();
            if (!constructedName || isPlaceholderName(constructedName)) {
              return; // Skip leads with no name or placeholder names
            }
            mappedPersons.push({
              id: item.id || item.lead_id || index.toString(),
              lead_id: item.lead_id, // Only use lead_id, don't fall back to id
              draft_id: item.draft_id,
              name: constructedName,
              title: draftData.owner_title || 'N/A',
              website: normalizeWebsiteValue(draftData.website || ''),
              email: normalizeEmailValue(draftData.owner_email || ''),
              location: `${draftData.city || ''}, ${draftData.state || ''}`.replace(', ', '').trim() || 'N/A',
              company: draftData.company || 'N/A',
              phone: draftData.owner_phone_number || draftData.company_phone || '',
              linkedin: normalizeLinkedInValue(draftData.owner_linkedin || draftData.company_linkedin || ''),
              industry: draftData.industry || 'N/A',
              employees: draftData.employees || 0,
              yearFounded: draftData.year_founded || 'N/A',
              businessType: draftData.business_type || 'N/A',
              address: `${draftData.street || ''} ${draftData.city || ''} ${draftData.state || ''}`.trim() || 'N/A',
              is_favorite: item.is_favorite || false,
              seniority: draftData.seniority || 'N/A'
            });
          }
        });

        setPersons(mappedPersons)

        // Build favoriteLeads set from the drafts response
        const favoriteIds = new Set<string>();
        const notesIds = new Set<string>();
        data.forEach((entry: any) => {
          const leadId = entry.lead_id || entry.id;
          if (entry.is_favorite && leadId) {
            favoriteIds.add(leadId);
          }
          // Highlight notes if person_notes.content exists and is not empty
          if (
            entry.person_notes &&
            entry.person_notes.content &&
            entry.person_notes.content.trim() !== "" &&
            leadId
          ) {
            notesIds.add(leadId);
          }
        });
        setFavoriteLeads(favoriteIds);
        setLeadsWithNotes(notesIds);

      } catch (err) {
        console.error('Error fetching persons:', err)
        setError('Failed to fetch persons data')
      } finally {
        setLoading(false)
      }
    }

    fetchPersons()
  }, [])

  // Add validation filter state
  const [validationFilter, setValidationFilter] = useState("all");

  // Helper function to check if email is valid
  const isValidEmail = (email: string) => {
    if (!email) return false;
    // Use isEmailMissing to check for placeholder patterns
    if (isEmailMissing(email)) return false;
    const normalizedEmail = normalizeEmailValue(email);
    return normalizedEmail !== 'N/A' && normalizedEmail.includes('@') && normalizedEmail.includes('.');
  };

  // Helper function to check if phone is valid
  const isValidPhone = (phone: string) => {
    if (!phone) return false;
    // Use isPhoneMissing to check for placeholder patterns
    if (isPhoneMissing(phone)) return false;
    // Remove any non-digit characters and check length
    const digits = phone.replace(/\D/g, '');
    return digits.length >= 10;
  };

  // Handle search and filters
  const filteredPersons = persons.filter(person => {
    // Search term filter
    const matchesSearch = person.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      person.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      person.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
      person.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      person.industry.toLowerCase().includes(searchTerm.toLowerCase()) ||
      person.businessType.toLowerCase().includes(searchTerm.toLowerCase())

    // Individual filters
    const matchTitle = person.title?.toLowerCase().includes(titleFilter.toLowerCase())
    const matchCompany = person.company?.toLowerCase().includes(companyFilter.toLowerCase())
    const matchIndustry = person.industry?.toLowerCase().includes(industryFilter.toLowerCase())
    const matchBusinessType = person.businessType?.toLowerCase().includes(businessTypeFilter.toLowerCase())
    const matchAddress = person.address?.toLowerCase().includes(addressFilter.toLowerCase())

    // Validation filter
    let matchesValidation = true;
    if (validationFilter === "valid-email") {
      matchesValidation = isValidEmail(person.email);
    } else if (validationFilter === "valid-phone") {
      matchesValidation = isValidPhone(person.phone);
    } else if (validationFilter === "both-valid") {
      matchesValidation = isValidEmail(person.email) && isValidPhone(person.phone);
    }

    return matchesSearch && matchTitle && matchCompany && matchIndustry && matchBusinessType && matchAddress && matchesValidation
  })

  // Pagination
  const totalPages = Math.ceil(filteredPersons.length / itemsPerPage)
  const indexOfLastItem = currentPage * itemsPerPage
  const indexOfFirstItem = indexOfLastItem - itemsPerPage
  const currentItems = filteredPersons.slice(indexOfFirstItem, indexOfLastItem)

  // Reset to first page when search term or filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm, titleFilter, companyFilter, industryFilter, businessTypeFilter, addressFilter])

  // Handle sort functionality
  const handleSortBy = (sortBy: SortOption, direction: "most" | "least") => {
    // Count how many non-empty fields each row has
    const getFilledCount = (person: Person) =>
      Object.entries(person).filter(([key, value]) => {
        if (
          ["id", "draft_id", "updated"].includes(key) ||
          value === null ||
          value === undefined ||
          value === "" ||
          value === "N/A"
        ) {
          return false;
        }
        return true;
      }).length;

    // Determine the base array to sort
    const base = [...persons];

    // Sort based on the selected criteria
    const sorted = base.sort((a, b) => {
      if (sortBy === "filled") {
        const aCount = getFilledCount(a);
        const bCount = getFilledCount(b);
        return direction === "most" ? bCount - aCount : aCount - bCount;
      }

      if (sortBy === "company") {
        return direction === "most"
          ? a.company.localeCompare(b.company)
          : b.company.localeCompare(a.company);
      }

      if (sortBy === "employees") {
        return direction === "most" ? b.employees - a.employees : a.employees - b.employees;
      }

      if (sortBy === "owner") {
        // Sort by whether they have contact info (email or phone)
        const aHasContact = (a.email && a.email !== 'N/A') || (a.phone && a.phone !== 'N/A') ? 1 : 0;
        const bHasContact = (b.email && b.email !== 'N/A') || (b.phone && b.phone !== 'N/A') ? 1 : 0;
        return direction === "most" ? bHasContact - aHasContact : aHasContact - bHasContact;
      }

      if (sortBy === "recent") {
        // Sort by name as a fallback for "recent" since we don't have date info
        return direction === "most"
          ? a.name.localeCompare(b.name)
          : b.name.localeCompare(a.name);
      }

      return 0;
    });

    // Update the persons state with sorted data
    setPersons(sorted);
    setCurrentPage(1); // reset pagination to page 1
  };

  // Handle email message click
  const handleEmailMessageClick = (person: Person) => {
    setEmailPopupData(person);
    setGeneratedMessage(""); // Clear any previous message
    setGeneratedSubject("");
    // Fetch templates immediately when email popup is opened
    fetchTemplatesForGenerator();
  };
  const handleLinkedInMessageClick = (person: Person) => {
    setLinkedinPopupData(person);
    setLinkedinGeneratedMessage(""); // Clear any previous message
  };

  const handleGeneratorClick = (person: Person, generatorType: 'email' | 'linkedin') => {
    // Check if user is a developer first
    const storedUser = typeof window !== "undefined"
      ? JSON.parse(sessionStorage.getItem("user") || "{}")
      : {};
    const userRole = storedUser.role || "";

    // If user is a developer, allow access
    if (userRole === "developer") {
      if (generatorType === 'email') {
        handleEmailMessageClick(person);
      } else {
        handleLinkedInMessageClick(person);
      }
      return;
    }

    // Otherwise, check tier restrictions
    const allowedTiers = ['silver', 'gold', 'platinum', 'enterprise'];
    const userTier = user.tier?.toLowerCase() || 'free';

    if (!allowedTiers.includes(userTier)) {
      setShowUpgradePopup(true);
      return;
    }

    if (generatorType === 'email') {
      handleEmailMessageClick(person);
    } else {
      handleLinkedInMessageClick(person);
    }
  };

  // Handle checkbox selection
  const handleSelectPerson = (personId: string) => {
    setSelectedPersons(prev =>
      prev.includes(personId)
        ? prev.filter(id => id !== personId)
        : [...prev, personId]
    )
  }

  const handleSelectAll = () => {
    if (selectedPersons.length === currentItems.length) {
      setSelectedPersons([])
    } else {
      setSelectedPersons(currentItems.map(person => person.id))
    }
  }

  // Save person to API using the same pattern as companies page
  const savePersonToAPI = async (person: any) => {
    // Helper to convert camelCase keys into snake_case
    const toSnake = (str: string) => str.replace(/([A-Z])/g, "_$1").toLowerCase();
    const normalizeKeys = (obj: any) => {
      const result: any = {};
      for (const [k, v] of Object.entries(obj)) {
        result[toSnake(k)] = v;
      }
      return result;
    };

    const normalizedPerson = normalizeKeys(person);
    normalizedPerson.user_id = getCurrentUserId();

    try {
      // First POST
      const postResponse = await axios.post(
        `${DATABASE_URL_NOAPI}/leads/${person.id}/edit`,
        normalizedPerson,
        { withCredentials: true }
      );

      // Then POST to drafts
      const payload = {
        draft_data: normalizedPerson,
        change_summary: "Updated from persons page",
        phase: "draft",
        status: "pending",
      };
      const actualDraftId = postResponse.data?.draft?.draft_id || person.draft_id;

      await axios.post(`${DATABASE_URL}/leads/drafts/${actualDraftId}`, payload, {
        withCredentials: true,
      });

      return { success: true, updatedPerson: { ...person, ...normalizedPerson } };
    } catch (err) {
      console.error("❌ Error saving person:", err);
      return { success: false, error: err };
    }
  };

  // Handle popup save
  const handlePopupSave = async () => {
    if (!popupData) return;

    const result = await savePersonToAPI(popupData);

    if (result.success) {
      // Update local state with the saved changes
      setPersons((prev) => prev.map((p) => p.id === popupData.id ? { ...popupData, updated: new Date().toLocaleString() } : p));
      setIsEditing(false);
      setPopupData(null);
      showNotification("Changes saved successfully.", "success");
    } else {
      showNotification("Failed to save changes.", "error");
    }
  };

  // Function to save enriched person data to both upload_leads and drafts APIs
  const handleSaveEnrichedPerson = async () => {
    if (!enrichedPersonData) {
      showNotification("No enriched data to save", "error");
      return;
    }

    try {
      // Get current user ID
      const userId = getCurrentUserId();
      if (!userId) {
        showNotification("User authentication required", "error");
        return;
      }

      // Transform enriched data to match API format
      const basePayload = {
        user_id: userId,
        lead_id: "", // Empty for new leads
        company: enrichedPersonData.company || "",
        website: "", // Not provided in person enrichment
        industry: "", // Not provided in person enrichment
        product_category: "", // Not provided in person enrichment
        business_type: "", // Not provided in person enrichment
        employees: "", // Not provided in person enrichment
        revenue: "", // Not provided in person enrichment
        year_founded: "", // Not provided in person enrichment
        bbb_rating: "", // Not provided in person enrichment
        street: enrichedPersonData.companyAddress && enrichedPersonData.companyAddress !== "N/A" ? enrichedPersonData.companyAddress : "",
        city: enrichedPersonData.companyLocation && enrichedPersonData.companyLocation !== "N/A" ? enrichedPersonData.companyLocation.split(',')[0]?.trim() || "" : "",
        state: enrichedPersonData.companyLocation && enrichedPersonData.companyLocation !== "N/A" ? enrichedPersonData.companyLocation.split(',')[1]?.trim() || "" : "",
        country: enrichedPersonData.companyLocation && enrichedPersonData.companyLocation !== "N/A" ? enrichedPersonData.companyLocation.split(',')[2]?.trim() || "" : "",
        company_phone: "", // Not provided in person enrichment
        company_linkedin: "", // Not provided in person enrichment
        owner_first_name: enrichedPersonData.name && enrichedPersonData.name !== "N/A" ? enrichedPersonData.name.split(' ')[0] || "" : "",
        owner_last_name: enrichedPersonData.name && enrichedPersonData.name !== "N/A" ? enrichedPersonData.name.split(' ').slice(1).join(' ') || "" : "",
        owner_title: enrichedPersonData.title && enrichedPersonData.title !== "N/A" ? enrichedPersonData.title : "",
        owner_email: enrichedPersonData.email && enrichedPersonData.email !== "N/A" ? enrichedPersonData.email : "",
        owner_phone_number: enrichedPersonData.phone && enrichedPersonData.phone !== "N/A" ? enrichedPersonData.phone : "",
        owner_linkedin: enrichedPersonData.linkedin && enrichedPersonData.linkedin !== "N/A" ? enrichedPersonData.linkedin : "",
        source: `Person enrichment from multiple sources`,
        contacts: []
      };

      let lead_id = "";
      let uploadPayload = { ...basePayload };

      // Step 1: Call upload_leads API
      try {
        const uploadRes = await axios.post(
          `${DATABASE_URL}/upload_leads`,
          JSON.stringify([uploadPayload]),
          { headers: { "Content-Type": "application/json" } }
        );
        
        const detailedResults = uploadRes.data?.stats?.detailed_results ?? [];
        const leadFromResponse = detailedResults[0] || {};
        if (leadFromResponse.lead_id) {
          lead_id = leadFromResponse.lead_id;
          uploadPayload.lead_id = lead_id;
        }
        
        console.log("✅ Upload leads successful:", uploadRes.data);
      } catch (uploadErr) {
        console.error("❌ Failed to upload lead:", uploadPayload, uploadErr);
        showNotification("Failed to upload lead data", "error");
      }

      // Step 2: Call drafts API
      try {
        const draftPayload = {
          lead_id,
          draft_data: uploadPayload,
          change_summary: `Person enrichment from multiple sources`
        };

        const response = await axios.post(
          `${DATABASE_URL}/leads/drafts`,
          draftPayload,
          {
            headers: { "Content-Type": "application/json" },
            withCredentials: true
          }
        );

        if (response.data && response.data.draft_id) {
          showNotification("Person data saved successfully to both upload_leads and drafts!", "success");
          // Optionally clear the form after successful save
          // clearEnrichmentFields();
        } else {
          showNotification("Failed to create draft", "error");
        }
      } catch (draftErr) {
        console.error("❌ Failed to create draft:", draftErr);
        showNotification("Failed to create draft", "error");
      }

      // Step 3: Call deduct credit API if lead_id was obtained
      if (lead_id) {
        try {
          await axios.post(
            `${DATABASE_URL}/user/deduct_credit/${lead_id}`,
            {},
            { withCredentials: true }
          );
          console.log("✅ Credit deducted successfully for lead:", lead_id);
        } catch (deductErr) {
          console.error(`❌ Credit deduction failed for lead ${lead_id}`, deductErr);
          // Don't show error to user as this is not critical
        }
      }

    } catch (error) {
      console.error("Error saving enriched person data:", error);
      showNotification("Failed to save person data. Please try again.", "error");
    }
  };

  // Generate page numbers for pagination
  const getPageNumbers = () => {
    const pageNumbers: (number | string)[] = []

    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) {
        pageNumbers.push(i)
      }
    } else {
      pageNumbers.push(1)

      let startPage = Math.max(2, currentPage - 2)
      let endPage = Math.min(totalPages - 1, currentPage + 2)

      if (currentPage <= 4) {
        endPage = 5
      } else if (currentPage >= totalPages - 3) {
        startPage = totalPages - 4
      }

      if (startPage > 2) {
        pageNumbers.push('ellipsis')
      }

      for (let i = startPage; i <= endPage; i++) {
        pageNumbers.push(i)
      }

      if (endPage < totalPages - 1) {
        pageNumbers.push('ellipsis')
      }

      pageNumbers.push(totalPages)
    }

    return pageNumbers
  }

  // Export functions
  const exportCSV = (personsToExport: Person[]) => {
    const headers = [
      "Name",
      "Title",
      "Phone Number",
      "Company",
      "Industry",
      "Business Type",
      "Address",
      "Email",
      "LinkedIn",
      "Website",
      "Employees",
      "Year Founded"
    ];

    // Create a mapping from header names to actual field names
    const headerToFieldMap: Record<string, keyof Person> = {
      "Name": "name",
      "Title": "title",
      "Phone Number": "phone",
      "Company": "company",
      "Industry": "industry",
      "Business Type": "businessType",
      "Address": "address",
      "Email": "email",
      "LinkedIn": "linkedin",
      "Website": "website",
      "Employees": "employees",
      "Year Founded": "yearFounded"
    };

    const csvContent = [
      headers.join(","), // Header row
      ...personsToExport.map((person) =>
        headers
          .map((h) => {
            const fieldName = headerToFieldMap[h];
            const value = person[fieldName];
            return `"${value || ""}"`;
          })
          .join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "persons-selected.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleExport = async () => {
    if (selectedPersons.length === 0) {
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
      const requiredCredits = selectedPersons.length;
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
      const personsToExport = filteredPersons.filter(p => selectedPersons.includes(p.id));
      if (isDeveloper) {
        exportCSV(personsToExport);
        showNotification(`Successfully exported ${personsToExport.length} selected items.`, "success");
        return;
      }
      if (availableCredits < requiredCredits) {
        showNotification(
          "Insufficient credits to export all selected leads. Please upgrade or reduce selection.",
          "error"
        );
        return;
      }
      exportCSV(personsToExport);
      showNotification(`Successfully exported ${personsToExport.length} selected items.`, "success");
    } catch (err) {
      console.error("❌ Failed to verify subscription:", err);
      showNotification(
        "Failed to verify your subscription. Please try again later.",
        "error"
      );
    }
  };

  // Action handlers
  const handleEdit = (person: Person) => {
    setPopupData(person);
    setIsEditing(true);
    setPopupTab('overview');
  };

  const handleNotes = (person: Person) => {
    setNotesLeadId(person.lead_id || person.id);
    setNotesName(person.name);
    setNotesPopupOpen(true);
  };

  // const handleEmail = (person: Person) => {
  //   if (person.email && normalizeEmailValue(person.email) !== 'N/A') {
  //     window.open(`mailto:${person.email}`, '_blank')
  //   }
  // }

  // const handleLinkedIn = (person: Person) => {
  //   if (person.linkedin && normalizeLinkedInValue(person.linkedin) !== 'N/A') {
  //     window.open(person.linkedin, '_blank')
  //   }
  // }

  const handleViewPerson = (person: Person) => {
    setPopupData(person);
  }

  // Generate AI email message
  // Generate Email
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

  // Generate Email
  // Replace your existing generateEmailMessage function with this:
  const generateEmailMessage = async () => {
    if (!emailPopupData) return;

    setIsGenerating(true);
    setGeneratedVariants([]); // Reset variants

    try {
      // Prepare the payload for the new API
      const payload = {
        company_name: messageSettings.companyName || emailPopupData.company,
        industry: messageSettings.industry || emailPopupData.industry || '',
        focus: messageSettings.focus,
        tone: messageSettings.tone,
        additional_context: messageSettings.additionalContext || [],
        model_choice: messageSettings.modelChoice || 'deepseek',
        user_id: getCurrentUserId(),
        person_name: emailPopupData.name || '',
        template_ids: selectedTemplateIds
      };

      console.log('Sending payload:', payload);

      const response = await fetch("https://sandbox-api.saasquatchleads.com/api/generate_template_variants", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('API Response:', data);

      // Set the generated variants directly
      setGeneratedVariants(data);

      // Set the first variant as the current message for backward compatibility
      if (data && data.length > 0) {
        const firstVariant = data[0];
        setGeneratedMessage(firstVariant.email);
        setGeneratedSubject(""); // Subject is included in the email content
        setCurrentMessageId(firstVariant.message_id || `variant_${firstVariant.template_id}_${firstVariant.variant}`);
      }

      showNotification('Email generated successfully!', 'success');
    } catch (error) {
      console.error('Error generating email:', error);
      showNotification('Error generating email: ' + error.message, 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const regenerateEmailMessage = async () => {
    if (!emailPopupData || !currentMessageId) return;

    setIsGenerating(true);

    try {
      const payload = {
        company_name: messageSettings.companyName || emailPopupData.company,
        industry: messageSettings.industry || emailPopupData.industry || '',
        tone: messageSettings.tone,
        focus: messageSettings.focus,
        context: messageSettings.additionalContext?.join(' ') || '',
        model_choice: messageSettings.modelChoice || 'deepseek',
        parent_message_id: currentMessageId,
        user_id: getCurrentUserId()
      };

      const response = await fetch(`https://sandbox-api.saasquatchleads.com/emailg/regenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('Failed to regenerate email');

      const data = await response.json();

      // Handle the response
      // setGeneratedMessage(data.message);
      setGeneratedVariants(data);
      setGeneratedSubject(`Connecting regarding ${messageSettings.focus}`);
      setCurrentMessageId(data.message_id);
      setCurrentMessageData(data);

      // Update the generatedVariants object with the new regenerated message
      if (generatedVariants) {
        const updatedVariants = [
          ...generatedVariants,
          {
            template_id: data.template_id,
            variant: data.variant,
            email: data.message,
            subject: `Connecting regarding ${messageSettings.focus}`,
            message_id: data.message_id,
            fullData: data
          }
        ];
        setGeneratedVariants(updatedVariants);
      }

      // Submit regeneration feedback
      await submitFeedback('regeneration');

    } catch (error) {
      console.error('Error regenerating email:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const submitFeedback = async (feedbackType: string) => {
    if (!currentMessageData || !currentMessageId || feedbackSubmitting) return;

    // Check if user has already given feedback for this message
    const currentFeedback = feedbackStatus[currentMessageId];
    if (currentFeedback && currentFeedback.type === feedbackType) {
      console.log(`Already ${feedbackType}d this message`);
      return;
    }

    setFeedbackSubmitting(true);

    try {
      const payload = {
        message_id: currentMessageId,
        parent_message_id: currentMessageData.parent_message_id,
        feedback_type: feedbackType,
        user_id: getCurrentUserId(),
        company_name: messageSettings.companyName || emailPopupData?.company,
        industry: messageSettings.industry || '',
        tone: messageSettings.tone,
        focus: messageSettings.focus,
        context: messageSettings.additionalContext?.join(' ') || '',
        model_used: messageSettings.modelChoice || 'deepseek',
        prompt_template: currentMessageData.prompt_template || currentMessageData.prompt_version || '',
        prompt_text: currentMessageData.prompt_text || '',
        generated_message: {
          message: generatedMessage,
          generated_at: new Date().toISOString()
        }
      };

      const response = await fetch(`https://sandbox-api.saasquatchleads.com/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('Failed to submit feedback');

      // Update feedback status for this message
      setFeedbackStatus(prev => ({
        ...prev,
        [currentMessageId]: {
          type: feedbackType,
          timestamp: new Date().toISOString()
        }
      }));

      console.log(`${feedbackType} feedback submitted successfully`);

    } catch (error) {
      console.error('Error submitting feedback:', error);
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  // Keep your existing feedback handlers:
  const handleUpvote = async () => {
    const currentFeedback = feedbackStatus[currentMessageId || ''];
    if (currentFeedback && currentFeedback.type === 'upvote') {
      console.log('Message already upvoted');
      return;
    }
    await submitFeedback('upvote');
  };
  const handleDownvote = async (): Promise<void> => {
    const currentFeedback = feedbackStatus[currentMessageId || ''];
    if (currentFeedback && currentFeedback.type === 'downvote') {
      console.log('Message already downvoted');
      return;
    }
    await submitFeedback('downvote');
  };
  // Helper function to parse subject and message from the combined content
  const parseMessageContent = (fullMessage: string) => {
    const lines = fullMessage.split('\n');
    const subjectLine = lines.find((line: string) => line.startsWith('Subject:'));
    const subject = subjectLine ? subjectLine.replace('Subject:', '').trim() : '';

    // Get the message content (everything after the subject line)
    const subjectIndex = lines.findIndex((line: string) => line.startsWith('Subject:'));
    const messageContent = lines.slice(subjectIndex + 1).join('\n').trim();

    return { subject, messageContent };
  };

  // REPLACE your existing handleToneChange function with this:
  const handleToneChange = (newTone: string) => {
    console.log('Switching from tone:', messageSettings.tone, 'to:', newTone);

    // Update the tone in settings
  setMessageSettings({...messageSettings, tone: newTone});

    // If we have generated messages for all tones, switch to the new tone
    const toneVariant = generatedVariants?.find(variant => variant.template_name === newTone);
    if (toneVariant) {
      console.log('Found message for tone:', newTone);
      console.log('Message ID:', toneVariant.message_id);

      // Parse the subject and message content
      const { subject, messageContent } = parseMessageContent(toneVariant.message);

      // Update the displayed message and subject
      setGeneratedMessage(messageContent);
      setGeneratedSubject(subject);

      // ✅ CRITICAL FIX: Update the current message ID to match the new tone
      setCurrentMessageId(toneVariant.message_id);

      // ✅ CRITICAL FIX: Update the current message data to match the new tone
      setCurrentMessageData({
        ...toneVariant,
        parent_message_id: currentMessageData?.parent_message_id,
        prompt_template: currentMessageData?.prompt_template,
        prompt_text: currentMessageData?.prompt_text,
      });

      console.log('Updated currentMessageId to:', toneVariant.message_id);
    } else {
      console.log('No message found for tone:', newTone);
      console.log('Available tones:', Object.keys(generatedVariants || {}));
    }
  };
  const generateLinkedInMessage = async (person: Person, settings: MessageSettings) => {
    setLinkedinIsGenerating(true);
    try {
      const response = await axios.post(
        `${DATABASE_URL_NOAPI}/emailgen/scrape`,
        {
          company_name: person.company,
          homepage_url: person.website,
          // Optionally, you can send more context if your backend supports it
          tone: settings.tone,
          focus: settings.focus,
          additional_context: settings.additionalContext,
        },
        { withCredentials: true }
      );
      setLinkedinGeneratedMessage(response.data.linkedin_message || "No LinkedIn message returned.");
    } catch (error) {
      console.error("Error generating LinkedIn message:", error);
      showNotification("Error generating LinkedIn message", "error");
    } finally {
      setLinkedinIsGenerating(false);
    }
  };

  const handleActionPreview = (person: Person, type: 'email' | 'linkedin' | 'website') => {
    setActionPreviewPopup({
      show: true,
      type,
      person
    });
  };

  const handleActionConfirm = (type: 'email' | 'linkedin' | 'website') => {
    if (!actionPreviewPopup.person) return;

    const person = actionPreviewPopup.person;

    if (type === 'email' && person.email && isValidEmail(person.email)) {
      window.open(`mailto:${person.email}`, '_blank');
    } else if (type === 'linkedin' && person.linkedin && normalizeLinkedInValue(person.linkedin) !== 'N/A') {
      window.open(person.linkedin, '_blank');
    } else if (type === 'website' && person.website && normalizeWebsiteValue(person.website) !== 'N/A') {
      const url = person.website.startsWith('http') ? person.website : `https://${person.website}`;
      window.open(url, '_blank');
    }

    setActionPreviewPopup({ show: false, type: 'email', person: null });
  };

  const handleActionClose = () => {
    setActionPreviewPopup({ show: false, type: 'email', person: null });
  };

  // Email edit functions
  const startEmailEditing = () => {
    setEditedEmailMessage(generatedMessage);
    setEditedEmailSubject(generatedSubject);
    setIsEmailEditing(true);
  };

  const saveEmailEdits = () => {
    setGeneratedMessage(editedEmailMessage);
    setGeneratedSubject(editedEmailSubject);
    setIsEmailEditing(false);
    showNotification('Email edits saved successfully!', 'success');
  };

  const cancelEmailEditing = () => {
    setEditedEmailMessage("");
    setEditedEmailSubject("");
    setIsEmailEditing(false);
  };

  // LinkedIn edit functions
  const startLinkedInEditing = () => {
    setEditedLinkedInMessage(linkedinGeneratedMessage);
    setIsLinkedInEditing(true);
  };

  const saveLinkedInEdits = () => {
    setLinkedinGeneratedMessage(editedLinkedInMessage);
    setIsLinkedInEditing(false);
    showNotification('LinkedIn edits saved successfully!', 'success');
  };

  const cancelLinkedInEditing = () => {
    setEditedLinkedInMessage("");
    setIsLinkedInEditing(false);
  };

  // Template states for the main component
  const [templates, setTemplates] = useState<Array<{
    template_id: string;
    template_name: string;
    template_content: string;
    updated_at: string;
  }>>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [templatesError, setTemplatesError] = useState<string | null>(null);

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [templateToEdit, setTemplateToEdit] = useState<{
    template_id: string;
    template_name: string;
    template_content: string;
    updated_at: string;
  } | null>(null);

  const openTemplateEditDialog = (template: any) => {
    setTemplateToEdit(template);
    setEditDialogOpen(true);
  };

  // Template edit dialog states
  const [editTemplateName, setEditTemplateName] = useState("");
  const [editTemplateContent, setEditTemplateContent] = useState("");
  const [editTemplateMode, setEditTemplateMode] = useState(false);
  const [editTemplateSaving, setEditTemplateSaving] = useState(false);

  // Template edit dialog handlers
  const handleEditTemplateSave = async () => {
    if (!templateToEdit) {
      showNotification("No template selected for editing.", "error");
      return;
    }
    if (!editTemplateName.trim()) {
      showNotification("Template name is required.", "error");
      return;
    }
    if (!editTemplateContent.includes("{{context}}")) {
      showNotification("Template content must include {{context}}.", "error");
      return;
    }

    setEditTemplateSaving(true);
    try {
      const res = await fetch(`https://sandbox-api.saasquatchleads.com/api/emailgen_templates/${templateToEdit.template_id}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_name: editTemplateName,
          template_content: editTemplateContent
        })
      });
      if (!res.ok) throw new Error("Failed to update template");
      showNotification("Template updated successfully!", "success");
      setEditDialogOpen(false);
      setEditTemplateMode(false);
      setEditTemplateName("");
      setEditTemplateContent("");
      setTemplateToEdit(null);
      // Refresh templates
      setTemplateRefreshTrigger(prev => prev + 1);
    } catch (err) {
      showNotification(err instanceof Error ? err.message : "Failed to save template.", "error");
    } finally {
      setEditTemplateSaving(false);
    }
  };

  const handleEditTemplateCancel = () => {
    setEditDialogOpen(false);
    setEditTemplateMode(false);
    setEditTemplateName("");
    setEditTemplateContent("");
    setTemplateToEdit(null);
  };

  const handleEditTemplateStart = () => {
    if (templateToEdit) {
      setEditTemplateName(templateToEdit.template_name);
      setEditTemplateContent(templateToEdit.template_content);
      setEditTemplateMode(true);
    }
  };

  // State to trigger template refresh
  const [templateRefreshTrigger, setTemplateRefreshTrigger] = useState(0);

  // Function to fetch templates for the main component
  const fetchTemplatesForGenerator = async () => {
    setLoadingTemplates(true);
    setTemplatesError(null);
    try {
      const response = await fetch("https://sandbox-api.saasquatchleads.com/api/emailgen_templates/", {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch templates");
      }

      const data = await response.json();
      console.log('Fetched templates for generator:', data);
      setTemplates(data);
    } catch (err) {
      console.error('Error fetching templates:', err);
      setTemplatesError(err instanceof Error ? err.message : 'Failed to fetch templates');
    } finally {
      setLoadingTemplates(false);
    }
  };

  // Function to refresh templates - will be called when templates tab is clicked
  const refreshTemplates = () => {
    setTemplateRefreshTrigger(prev => prev + 1);
  };

  // For edit modal
  const [editingCard, setEditingCard] = useState<any>(null);
  const [editValue, setEditValue] = useState({ subject: '', body: '' });

  // For feedback
  const [feedbackGiven, setFeedbackGiven] = useState<Record<string, 'upvote' | 'downvote' | null>>({});
  // Generated item editing states
  const [editingGeneratedItem, setEditingGeneratedItem] = useState<string | null>(null);
  const [editedGeneratedMessage, setEditedGeneratedMessage] = useState("");
  const [showGeneratedItemEditDialog, setShowGeneratedItemEditDialog] = useState(false);
  const [selectedGeneratedItem, setSelectedGeneratedItem] = useState<any>(null);

  const handleFeedback = async (item: any, type: 'upvote' | 'downvote') => {
    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: item.message_id,
          template_id: item.template_id,
          variant: item.variant,
          feedback_type: type,
          generated_message: {
            message: item.email,
            template_id: item.template_id,
            template_name: item.template_name,
            variant: item.variant,
            generated_at: new Date().toISOString()
          }
        }),
      });
      if (response.ok) {
        setFeedbackGiven(prev => ({ ...prev, [item.message_id]: type }));
        // Show success notification
        showNotification(`${type === 'upvote' ? 'Upvoted' : 'Downvoted'} successfully!`, "success");
      }
    } catch (error) {
      console.error('Feedback error:', error);
      showNotification('Failed to submit feedback. Please try again.', "error");
    }
  };

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showNotification("Email copied to clipboard!", "success");
    } catch (error) {
      showNotification("Failed to copy to clipboard", "error");
    }
  };



  // const handleOpenInEmail = (email: string) => {
  //   const subject = encodeURIComponent("Email from LeadGenAI");
  //   const body = encodeURIComponent(email);
  //   window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
  // };

  // Generated item editing handlers
  const startEditingGeneratedItem = (item: any) => {
    setSelectedGeneratedItem(item);
    setEditedGeneratedMessage(item.email);
    setShowGeneratedItemEditDialog(true);
  };

  const saveGeneratedItemEdits = () => {
    if (selectedGeneratedItem && editedGeneratedMessage) {
      setGeneratedVariants((prev) =>
        prev.map((variant) =>
          variant.message_id === selectedGeneratedItem.message_id
            ? { ...variant, email: editedGeneratedMessage }
            : variant
        )
      );
      setShowGeneratedItemEditDialog(false);
      setSelectedGeneratedItem(null);
      setEditedGeneratedMessage("");
      showNotification("Changes saved successfully!", "success");
    }
  };

  const cancelGeneratedItemEditing = () => {
    setShowGeneratedItemEditDialog(false);
    setSelectedGeneratedItem(null);
    setEditedGeneratedMessage("");
  };

  // Initialize user templates on page load
  useEffect(() => {
    const initializeUserTemplates = async () => {
      try {
        const response = await fetch('https://sandbox-api.saasquatchleads.com/api/emailgen_templates/init_user_templates', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          console.log('Template initialization result:', data);

          // If templates were initialized, the existing fetchTemplates will pick them up
          if (data.status === 'initialized' || data.status === 'already_initialized') {
            console.log('Templates ready:', data.templates);
          }
        } else {
          console.error('Failed to initialize templates');
        }
      } catch (error) {
        console.error('Error initializing templates:', error);
      }
    };

    initializeUserTemplates();
  }, []);

  // Function to handle Apollo person selection and enrichment
  const handleApolloPersonSelection = async (selectedPerson: any) => {
      try {
          setApolloSearchLoading(true);
          setSelectedApolloPerson(selectedPerson);
          
          // Close the search dialog
          // Apollo dialog no longer used
          
          // Now call the apollo-enrich-people endpoint with the selected person's details
          const user = JSON.parse(sessionStorage.getItem("user") || "{}");
          const user_id = user.user_id || "";
          
          if (!user_id) {
              showNotification("User not authenticated. Please log in again.", "error");
              return;
          }

          const apiEndpoint = `${process.env.NEXT_PUBLIC_BACKEND_URL_P2}/apollo-enrich-people`;
          
          // Build payload with the selected person's details
          let apolloPayload: any = {
              name: selectedPerson.name || enrichPersonName.trim()
          };
          
          // Add company name if available
          if (selectedPerson.company && selectedPerson.company.trim() !== "") {
              apolloPayload.organization_name = selectedPerson.company.trim();
          } else if (enrichPersonCompany.trim() !== "") {
              apolloPayload.organization_name = enrichPersonCompany.trim();
          }
          
          // Add domain if available
          if (selectedPerson.domain && selectedPerson.domain.trim() !== "") {
              apolloPayload.domain = selectedPerson.domain.trim();
          } else if (enrichCompanyDomain.trim() !== "") {
              let cleanDomain = enrichCompanyDomain.trim().replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0];
              apolloPayload.domain = cleanDomain;
          }
          
          console.log("🚀 Calling Apollo apollo-enrich-people with selected person:", apolloPayload);
          
          const response = await fetch(apiEndpoint, {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify(apolloPayload)
          });
          
          if (!response.ok) {
              console.error(`❌ Apollo apollo-enrich-people API failed with status: ${response.status}`);
              throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          const apolloResult = await response.json();
          console.log("✅ Apollo apollo-enrich-people API response:", apolloResult);
          
          if (apolloResult.success && apolloResult.data) {
              const apolloData = apolloResult.data;
              
              // Convert to our expected format and display in result card
              const convertedData = {
                  name: apolloData.name || selectedPerson.name || enrichPersonName || "Unknown",
                  title: apolloData.title || selectedPerson.title || "No title found",
                  company: apolloData.company || selectedPerson.company || enrichPersonCompany || "Unknown",
                  email: apolloData.email || selectedPerson.email || "No email found",
                  phone: apolloData.phone || selectedPerson.phone || "No phone found",
                  linkedin: apolloData.linkedin || selectedPerson.linkedin || "No LinkedIn found",
                  companyLocation: apolloData.location || selectedPerson.location || "No location found",
                  companyAddress: apolloData.address || selectedPerson.address || "No address found"
              };
              
              // Set the enriched data to display in the result card
              setEnrichedPersonData(convertedData);
              showNotification("Person enrichment completed successfully using Apollo!", "success");
          } else {
              // Use the selected person's data directly if enrichment fails
              const fallbackData = {
                  name: selectedPerson.name || enrichPersonName || "Unknown",
                  title: selectedPerson.title || "No title found",
                  company: selectedPerson.company || enrichPersonCompany || "Unknown",
                  email: selectedPerson.email || "No email found",
                  phone: selectedPerson.phone || "No phone found",
                  linkedin: selectedPerson.linkedin || "No LinkedIn found",
                  companyLocation: selectedPerson.location || "No location found",
                  companyAddress: selectedPerson.address || "No address found"
              };
              
              // Set the fallback data to display in the result card
              setEnrichedPersonData(fallbackData);
              showNotification("Person data loaded from Apollo search results!", "success");
          }
          
      } catch (error) {
          console.error("❌ Error enriching selected Apollo person:", error);
          
          // Fallback to using the selected person's data directly
          const fallbackData = {
              name: selectedPerson.name || enrichPersonName || "Unknown",
              title: selectedPerson.title || "No title found",
              company: selectedPerson.company || enrichPersonCompany || "Unknown",
              email: selectedPerson.email || "No email found",
              phone: selectedPerson.phone || "No phone found",
              linkedin: selectedPerson.linkedin || "No LinkedIn found",
              companyLocation: selectedPerson.location || "No location found",
              companyAddress: selectedPerson.address || "No address found"
          };
          
          // Set the fallback data to display in the result card
          setEnrichedPersonData(fallbackData);
          showNotification("Person data loaded from Apollo search results (enrichment failed)!", "info");
      } finally {
          setApolloSearchLoading(false);
      }
  };

  return (
    <div className="flex flex-col h-screen">
      <FeedbackPopup />

      {/* Below: Sidebar + Main content */}
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 p-6 overflow-auto">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Persons</CardTitle>
                <div className="flex items-center gap-4">
                  {/* Search Bar */}
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="search"
                      placeholder="Search persons, companies, industries..."
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
                      onClick={() => setShowFilters(f => !f)}
                      title={showFilters ? "Hide Filters" : "Show Filters"}
                    >
                      <Filter className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleExport}
                      title={selectedPersons.length > 0 ? `Export ${selectedPersons.length} selected items` : "Select items to export"}
                      disabled={selectedPersons.length === 0}
                      className={`relative ${selectedPersons.length === 0 ? "opacity-50 cursor-not-allowed" : ""}`}
                    >
                      <Download className="h-4 w-4" />
                      {selectedPersons.length > 0 && (
                        <span className="absolute -top-2 -right-2 text-xs bg-blue-500 text-white rounded-full px-1.5 py-0.5 min-w-[1.2rem] flex items-center justify-center">
                          {selectedPersons.length}
                        </span>
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              {/* Filter Section */}
              {showFilters && (
                <div className="flex flex-wrap gap-4 my-4">
                  <div className="flex flex-wrap gap-4">
                    <Input
                      placeholder="Title"
                      value={titleFilter}
                      onChange={(e) => setTitleFilter(e.target.value)}
                      className="w-[240px]"
                    />
                    <Input
                      placeholder="Company"
                      value={companyFilter}
                      onChange={(e) => setCompanyFilter(e.target.value)}
                      className="w-[240px]"
                    />
                    <Input
                      placeholder="Industry"
                      value={industryFilter}
                      onChange={(e) => setIndustryFilter(e.target.value)}
                      className="w-[240px]"
                    />
                    <Input
                      placeholder="Business Type"
                      value={businessTypeFilter}
                      onChange={(e) => setBusinessTypeFilter(e.target.value)}
                      className="w-[240px]"
                    />
                    <Input
                      placeholder="Address"
                      value={addressFilter}
                      onChange={(e) => setAddressFilter(e.target.value)}
                      className="w-[240px]"
                    />
                    <Select
                      value={validationFilter}
                      onValueChange={setValidationFilter}
                    >
                      <SelectTrigger className="w-[240px]">
                        <SelectValue placeholder="Filter by validation" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Show All</SelectItem>
                        <SelectItem value="valid-email">Valid Emails Only</SelectItem>
                        <SelectItem value="valid-phone">Valid Phone Numbers Only</SelectItem>
                        <SelectItem value="both-valid">Both Valid</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button variant="ghost" size="sm" onClick={clearAllFilters}>
                    <X className="h-4 w-4 mr-1" />
                    Clear All
                  </Button>
                </div>
              )}
            </CardHeader>

            <CardContent>
              {/* Persons Table */}
              <div className="w-full overflow-x-auto relative border rounded-md">
                {loading ? (
                  <div className="p-8 text-center">
                    <div className="text-lg">Loading persons data...</div>
                  </div>
                ) : error ? (
                  <div className="p-8 text-center text-red-500">
                    <div className="text-lg">{error}</div>
                    <Button
                      variant="outline"
                      className="mt-4"
                      onClick={() => window.location.reload()}
                    >
                      Retry
                    </Button>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="sticky top-0 left-0 z-40 bg-background w-12 text-base font-bold text-white">
                          <Checkbox
                            checked={selectedPersons.length === currentItems.length && currentItems.length > 0}
                            onCheckedChange={handleSelectAll}
                            aria-label="Select all"
                          />
                        </TableHead>
                        <TableHead className="sticky top-0 left-12 z-30 bg-background border-r text-base font-bold text-white px-6 py-3 whitespace-nowrap min-w-[200px]">
                          Name
                        </TableHead>
                        <TableHead className="w-[140px] sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">Actions</TableHead>
                        <TableHead className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">Title</TableHead>
                        <TableHead className="w-[120px] sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">Links</TableHead>
                        <TableHead className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">Phone Number</TableHead>
                        <TableHead className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">Company</TableHead>
                        <TableHead className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">Industry</TableHead>
                        <TableHead className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">Business Type</TableHead>
                        <TableHead className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap">Address</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {currentItems.length > 0 ? (
                        currentItems.map((person) => {
                          return (
                            <TableRow key={person.id}>
                              <TableCell className="w-12 sticky left-0 z-20 bg-inherit">
                                <Checkbox
                                  checked={selectedPersons.includes(person.id)}
                                  onCheckedChange={() => handleSelectPerson(person.id)}
                                  aria-label={`Select ${person.name}`}
                                />
                              </TableCell>
                              <TableCell className="sticky left-12 z-10 bg-inherit border-r px-6 py-2 max-w-[240px] align-top">
                                <ExpandableCell text={person.name} />
                              </TableCell>
                              <TableCell>
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <button className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-zinc-800 focus:outline-none">
                                      <MoreHorizontal className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                                    </button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="start">
                                    <DropdownMenuItem onClick={() => handleViewPerson(person)}>
                                      <Eye className="w-4 h-4 mr-2 text-blue-500" /> View Details
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => handleEdit(person)}>
                                      <Pencil className="w-4 h-4 mr-2 text-blue-600" /> Edit
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => handleNotes(person)}>
                                      <StickyNote className={`w-4 h-4 mr-2 ${leadsWithNotes.has(String(person.lead_id || person.id || "")) ? "fill-current text-yellow-400" : "text-yellow-500"}`} /> Notes
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => handleGeneratorClick(person, 'email')} disabled={!isValidEmail(person.email)}>
                                      <Mail className="w-4 h-4 mr-2 text-green-600" /> Generate Email
                                    </DropdownMenuItem>
                                    <DropdownMenuItem disabled className="opacity-50 cursor-not-allowed">
                                      <Linkedin className="w-4 h-4 mr-2 text-blue-700" /> Generate LinkedIn
                                      <span className="ml-2">
                                        <NewTag text="Coming Soon" />
                                      </span>
                                    </DropdownMenuItem>
                                    <DropdownMenu>
                                      <DropdownMenuTrigger asChild>
                                        <DropdownMenuItem 
                                          disabled={!isValidPhone(person.phone) && !isValidEmail(person.email)}
                                          className="flex items-center justify-between"
                                        >
                                          <div className="flex items-center">
                                            <CheckCircle className="w-4 h-4 mr-2 text-purple-600" /> Validator
                                            <span className="ml-2">
                                              <NewTag text="NEW" />
                                            </span>
                                          </div>
                                          <ChevronDown className="w-3 h-3 ml-2" />
                                        </DropdownMenuItem>
                                      </DropdownMenuTrigger>
                                      <DropdownMenuContent align="start" className="w-48">
                                        <DropdownMenuItem 
                                          onClick={() => handleEmailValidationClick(person)}
                                          disabled={!isValidEmail(person.email)}
                                          className={!isValidEmail(person.email) ? 'opacity-50 cursor-not-allowed' : ''}
                                        >
                                          <Mail className={`w-4 h-4 mr-2 ${(!person.email || normalizeEmailValue(person.email) === 'N/A') ? 'text-gray-400' : 'text-green-600'}`} /> Email
                                        </DropdownMenuItem>
                                        <DropdownMenuItem 
                                          onClick={() => handlePhoneValidatorClick(person)}
                                          disabled={!isValidPhone(person.phone)}
                                          className={!isValidPhone(person.phone) ? 'opacity-50 cursor-not-allowed' : ''}
                                        >
                                          <Phone className={`w-4 h-4 mr-2 ${(!person.phone || person.phone === 'N/A') ? 'text-gray-400' : 'text-purple-600'}`} /> Phone
                                        </DropdownMenuItem>
                                      </DropdownMenuContent>
                                    </DropdownMenu>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={() => handleToggleFavorite(person.lead_id || person.id)}>
                                      <Star className={`w-4 h-4 mr-2 ${favoriteLeads.has(person.lead_id || person.id) ? "text-yellow-500 fill-current" : "text-yellow-500"}`} />
                                      {favoriteLeads.has(person.lead_id || person.id) ? "Unfavorite" : "Favorite"}
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </TableCell>
                              <TableCell>
                                {person.title}
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-4">
                                  <div className="flex items-center gap-1">
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleActionPreview(person, 'email')}
                                      title="Send Email"
                                      disabled={!person.email || !isValidEmail(person.email)}
                                      className={!isValidEmail(person.email) ? 'opacity-50 cursor-not-allowed' : ''}
                                    >
                                      <Mail className="h-4 w-4 text-green-600" />
                                    </Button>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleActionPreview(person, 'linkedin')}
                                      title="LinkedIn Profile"
                                      disabled={!person.linkedin || normalizeLinkedInValue(person.linkedin) === 'N/A'}
                                      className={normalizeLinkedInValue(person.linkedin) === 'N/A' ? 'opacity-50 cursor-not-allowed' : ''}
                                    >
                                      <Linkedin className="h-4 w-4 text-blue-700" />
                                    </Button>
                                  </div>
                                </div>
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  {person.phone ? (
                                    <span>{person.phone}</span>
                                  ) : (
                                    <span className="text-gray-400">N/A</span>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell>
                                {person.company}
                              </TableCell>
                              <TableCell>
                                {person.industry}
                              </TableCell>
                              <TableCell>
                                {person.businessType}
                              </TableCell>
                              <TableCell>
                                {person.address}
                              </TableCell>
                            </TableRow>
                          );
                        })
                      ) : (
                        <TableRow>
                          <TableCell colSpan={10} className="h-24 text-center">
                            {searchTerm || titleFilter || companyFilter || industryFilter || businessTypeFilter || addressFilter ? "No persons found matching your search and filters." : "No persons found."}
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                )}
              </div>

              {/* Pagination at the bottom */}
              {filteredPersons.length > 0 && (
                <div className="flex flex-col md:flex-row justify-between items-center mt-4 gap-4 px-4 py-2">
                  <div className="text-sm text-muted-foreground">
                    Showing {indexOfFirstItem + 1}-{Math.min(indexOfLastItem, filteredPersons.length)} of {filteredPersons.length} persons
                    {selectedPersons.length > 0 && (
                      <span className="ml-2 text-blue-600">
                        ({selectedPersons.length} selected)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 px-3 py-2">
                    <Select
                      value={itemsPerPage.toString()}
                      onValueChange={(value) => {
                        setItemsPerPage(Number(value));
                        setCurrentPage(1);
                      }}
                    >
                      <SelectTrigger className="w-[120px]">
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
                            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                            aria-disabled={currentPage === 1}
                            className={currentPage === 1 ? "pointer-events-none opacity-50" : ""}
                          />
                        </PaginationItem>

                        {getPageNumbers().map((page, index) => (
                          <PaginationItem key={index}>
                            {page === 'ellipsis' ? (
                              <PaginationEllipsis />
                            ) : (
                              <PaginationLink
                                isActive={page === currentPage}
                                onClick={() => setCurrentPage(Number(page))}
                              >
                                {page}
                              </PaginationLink>
                            )}
                          </PaginationItem>
                        ))}

                        <PaginationItem>
                          <PaginationNext
                            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                            aria-disabled={currentPage === totalPages}
                            className={currentPage === totalPages ? "pointer-events-none opacity-50" : ""}
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Enrich Persons Section */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            <EnrichPersons 
              showNotification={showNotification}
              onPersonEnriched={(enrichedData) => {
                // Handle enriched person data
                console.log("Person enriched:", enrichedData);
                // You can add additional logic here if needed
              }}
            />
          </div>
        </main>
      </div>



      {/* Apollo Search Results Dialog - Removed, now shown in External Results tab */}

      {/* PopupBig Component */}
      <PopupBig
        show={!!popupData}
        onClose={() => {
          setPopupData(null);
          setIsEditing(false);
          setPopupTab('overview');
        }}
        person={popupData}
        isEditing={isEditing}
        popupTab={popupTab}
        setPopupTab={setPopupTab}
        setPopupData={setPopupData}
        onSave={handlePopupSave}
      />

      {/* Email Popup Dialog */}
      {emailPopupData !== null && (
        <Dialog open={!!emailPopupData} onOpenChange={(isOpen) => {
          if (!isOpen) setEmailPopupData(null);
          setEmailPopupData(null);
          setEmailPopupTab('generator');
        }}>
          <DialogContent className="max-w-6xl max-h-[86vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-2xl text-center">Email Message Generator</DialogTitle>
              {/* Tab Navigation */}
              <div className="flex space-x-4 mt-4 border-b border-gray-700">
                <button
                  onClick={() => {
                    setEmailPopupTab('templates');
                    refreshTemplates();
                  }}
                  className={`px-4 py-2 font-medium ${emailPopupTab === 'templates' ? 'border-b-2 border-blue-500 text-blue-400' : 'text-gray-400 hover:text-gray-300'}`}
                >
                  Templates
                </button>
                <button
                  onClick={() => {
                    setEmailPopupTab('generator');
                    fetchTemplatesForGenerator();
                  }}
                  className={`px-4 py-2 font-medium ${emailPopupTab === 'generator' ? 'border-b-2 border-blue-500 text-blue-400' : 'text-gray-400 hover:text-gray-300'}`}
                >
                  Generator
                </button>
                <button
                  onClick={() => {
                    setEmailPopupTab('history');
                    fetchEmailHistory(emailPopupData.company);
                  }}
                  className={`px-4 py-2 font-medium ${emailPopupTab === 'history' ? 'border-b-2 border-blue-500 text-blue-400' : 'text-gray-400 hover:text-gray-300'}`}
                >
                  History
                </button>
              </div>
            </DialogHeader>
            {/* Tab Content */}



            {/* History Detail Popup */}
            {showHistoryPopup && selectedHistoryItem && (
              <Dialog open={showHistoryPopup} onOpenChange={closeHistoryPopup}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto bg-gray-900 border-gray-700">
                  <DialogHeader>
                    <DialogTitle>
                      <div>
                        <h3 className="text-xl font-bold text-white">{selectedHistoryItem.message_content.company_name}</h3>
                        <p className="text-sm text-gray-400">
                          {formatDate(selectedHistoryItem.created_at)}
                        </p>
                      </div>
                    </DialogTitle>
                  </DialogHeader>
                  <div className="flex justify-end space-x-2 mt-2">
                    <button
                      onClick={() => copyHistoryToClipboard((selectedHistoryItem.message_content.subject ? selectedHistoryItem.message_content.subject + "\n\n" : "") +
                        selectedHistoryItem.message_content.generated_message)}
                      className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm"
                    >
                      Copy
                    </button>
                    <button
                      onClick={() => openHistoryInEmail((selectedHistoryItem.message_content.subject ? selectedHistoryItem.message_content.subject + "\n\n" : "") +
                        selectedHistoryItem.message_content.generated_message)}
                      className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm"
                    >
                      Gmail
                    </button>
                    {isEditingHistory ? (
                      <>
                        <button
                          onClick={saveHistoryEdits}
                          className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-sm"
                        >
                          {isHistorySaving ? (
                            <>
                              <div className="animate-spin h-4 w-4 mr-1 border-2 border-gray-300 border-t-green-600 rounded-full inline-block"></div>
                              Saving...
                            </>
                          ) : (
                            "Save"
                          )}
                        </button>
                        <button
                          onClick={cancelHistoryEditing}
                          className="px-3 py-1 bg-gray-600 hover:bg-gray-500 text-white rounded text-sm"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={startEditingHistory}
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm"
                      >
                        Edit
                      </button>
                    )}
                  </div>
                  <div className="mt-4">
                    {isEditingHistory ? (
                      <textarea
                        value={editedHistoryMessage}
                        onChange={(e) => setEditedHistoryMessage(e.target.value)}
                        className="w-full h-64 p-3 bg-gray-800 border border-gray-600 rounded-lg resize-none text-white placeholder-gray-400"
                        placeholder="Edit your email message..."
                      />
                    ) : (
                      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 whitespace-pre-wrap max-h-64 overflow-y-auto text-white">
                        {(selectedHistoryItem.message_content.subject ? selectedHistoryItem.message_content.subject + "\n\n" : "") +
        selectedHistoryItem.message_content.generated_message}
                      </div>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
            )}

            {/* Conditional Content */}
            {emailPopupTab === 'generator' ? (
              <EmailMessageGenerator
                person={emailPopupData}
                onClose={() => setEmailPopupData(null)}
                onGenerate={generateEmailMessage}
                onRegenerate={regenerateEmailMessage}
                onUpvote={handleUpvote}
                onDownvote={handleDownvote}
                generatedMessage={generatedMessage}
                generatedSubject={generatedSubject}
                isGenerating={isGenerating}
                settings={messageSettings}
                onSettingsChange={setMessageSettings}
                onSave={saveEmailMessage}
                onCopy={copyEmailMessage}
                isSaving={isEmailSaving}
                copied={emailCopied}
                isEditing={isEmailEditing}
                editedMessage={editedEmailMessage}
                editedSubject={editedEmailSubject}
                onStartEditing={startEmailEditing}
                onSaveEdits={saveEmailEdits}
                onCancelEditing={cancelEmailEditing}
                onEditMessageChange={(message) => setEditedEmailMessage(message)}
                onEditSubjectChange={(subject) => setEditedEmailSubject(subject)}
                generatedVariants={generatedVariants}
                setGeneratedVariants={setGeneratedVariants}
                onToneChange={handleToneChange}
                feedbackStatus={feedbackStatus}
                feedbackSubmitting={feedbackSubmitting}
                getButtonState={getButtonState}
                currentMessageId={currentMessageId || undefined}
                templates={templates}
                selectedTemplateIds={selectedTemplateIds}
                setSelectedTemplateIds={setSelectedTemplateIds}
                openTemplateEditDialog={openTemplateEditDialog}
                editingCard={editingCard}
                setEditingCard={setEditingCard}
                feedbackGiven={feedbackGiven}
                setFeedbackGiven={setFeedbackGiven}
                editingGeneratedItem={editingGeneratedItem}
                startEditingGeneratedItem={startEditingGeneratedItem}
                saveGeneratedItemEdits={saveGeneratedItemEdits}
                cancelGeneratedItemEditing={cancelGeneratedItemEditing}
                editedGeneratedMessage={editedGeneratedMessage}
                setEditedGeneratedMessage={setEditedGeneratedMessage}
              />
            ) : emailPopupTab === 'templates' ? (
              <TemplatesTab
                refreshTrigger={templateRefreshTrigger}
                onTemplatesUpdate={setTemplates}
                showNotification={showNotification}
              />
            ) : (
              // History Tab Content - Replace the existing history section
              <div className="mt-4">
                {isLoadingHistory ? (
                  <div className="flex justify-center items-center h-32">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  </div>
                ) : historyItems.length > 0 ? (
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {historyItems.map((item) => (
                      <div key={item.id} className="bg-gray-800 border border-gray-700 rounded-lg p-4 cursor-pointer hover:bg-gray-750 text-white" onClick={() => openHistoryPopup(item)}>
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                            <h4 className="font-semibold text-white">{item.message_content.subject && item.message_content.subject.trim() !== "" ? item.message_content.subject : "No Subject"}</h4>
                            <p className="text-sm text-gray-300 mt-1 line-clamp-2">{item.message_content.generated_message}</p>
                              <p className="text-xs text-gray-400 mt-2">{formatDate(item.created_at)}</p>
                            </div>
                            <div className="flex space-x-2 ml-4">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  copyHistoryToClipboard(item.message_content.generated_message);
                                }}
                                className="p-2 text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded"
                                title="Copy message"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openHistoryInEmail((item.message_content.subject ? item.message_content.subject + "\n\n" : "") + item.message_content.generated_message);
                                }}
                                className="p-2 text-blue-400 hover:text-blue-300 bg-blue-900 hover:bg-blue-800 rounded"
                                title="Open in Gmail"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                              </button>
                            </div>
                          </div>
                        </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400 bg-gray-800 rounded-lg border border-gray-700">
                    No emails generated for {emailPopupData.company}
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      )}

      {/* Template Edit Dialog */}
      {editDialogOpen && templateToEdit && (
        <Dialog open={editDialogOpen} onOpenChange={handleEditTemplateCancel}>
          <DialogContent className="max-w-xl max-h-[80vh] overflow-y-auto bg-gray-900 border-gray-700">
            <DialogHeader>
              <DialogTitle asChild>
                <div className="sr-only">
                  {editTemplateMode ? "Edit Template" : templateToEdit.template_name}
                </div>
              </DialogTitle>
              <div className="flex flex-row justify-between items-center">
                <div className="flex flex-col">
                  <h3 className="text-xl font-bold text-white mb-1">
                    {editTemplateMode ? (
                      <input
                        className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-white font-bold w-full mb-2"
                        value={editTemplateName}
                        onChange={e => setEditTemplateName(e.target.value)}
                        placeholder="Template Name"
                        disabled={editTemplateSaving}
                      />
                    ) : (
                      templateToEdit.template_name
                    )}
                  </h3>
                  <p className="text-sm text-gray-400">
                    Last updated: {templateToEdit.updated_at ? new Date(templateToEdit.updated_at).toLocaleDateString() : 'N/A'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    You can add variables like {'{{person}}'}, {'{{company}}'}, {'{{industry}}'} in double curly braces.
                    <br />
                    <span className="bg-blue-600 text-white px-1 rounded text-xs font-medium">{'{{context}}'}</span> is required.
                  </p>
                </div>
                {!editTemplateMode && (
                  <div className="flex flex-row gap-2 ml-6">
                    <button
                      className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded"
                      onClick={handleEditTemplateStart}
                    >
                      Edit
                    </button>
                  </div>
                )}
              </div>
            </DialogHeader>
            <div className="mt-4">
              {editTemplateMode ? (
                <>
                  <textarea
                    className="w-full h-48 p-3 bg-gray-800 border border-gray-600 rounded-lg resize-none text-white placeholder-gray-400 mb-4"
                    value={editTemplateContent}
                    onChange={e => setEditTemplateContent(e.target.value)}
                    placeholder="Enter your template content here. Use {{context}} as a placeholder for dynamic content."
                    disabled={editTemplateSaving}
                  />
                  <div className="flex justify-end space-x-2">
                    <button
                      onClick={handleEditTemplateSave}
                      disabled={editTemplateSaving}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded disabled:opacity-50"
                    >
                      {editTemplateSaving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={handleEditTemplateCancel}
                      disabled={editTemplateSaving}
                      className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 whitespace-pre-wrap max-h-64 overflow-y-auto text-white">
                  {templateToEdit.template_content}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Generated Item Edit Dialog */}
      {showGeneratedItemEditDialog && selectedGeneratedItem && (
        <Dialog open={showGeneratedItemEditDialog} onOpenChange={cancelGeneratedItemEditing}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto bg-gray-900 border-gray-700">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold text-white">
                Edit Generated Message
              </DialogTitle>
              <p className="text-sm text-gray-400">
                Template: {selectedGeneratedItem.template_name} - Variant {selectedGeneratedItem.variant}
              </p>
            </DialogHeader>
            <div className="mt-4">
              <div className="space-y-4 mb-4">
                {/* Subject Section */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Subject</label>
                  <input
                    type="text"
                    value={(() => {
                      const emailLines = editedGeneratedMessage.split('\n');
                      const subjectLine = emailLines.find((line: string) => line.startsWith('Subject:'));
                      return subjectLine ? subjectLine.replace('Subject:', '').trim() : '';
                    })()}
                    onChange={(e) => {
                      const emailLines = editedGeneratedMessage.split('\n');
                      const subjectIndex = emailLines.findIndex((line: string) => line.startsWith('Subject:'));
                      if (subjectIndex >= 0) {
                        emailLines[subjectIndex] = `Subject: ${e.target.value}`;
                      } else {
                        emailLines.unshift(`Subject: ${e.target.value}`);
                      }
                      setEditedGeneratedMessage(emailLines.join('\n'));
                    }}
                    className="w-full p-3 bg-gray-800 border border-gray-600 rounded text-white text-sm"
                    placeholder="Enter subject..."
                  />
                </div>

                {/* Body Section */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Body</label>
                  <textarea
                    value={(() => {
                      const emailLines = editedGeneratedMessage.split('\n');
                      const subjectIndex = emailLines.findIndex((line: string) => line.startsWith('Subject:'));
                      return subjectIndex >= 0
                        ? emailLines.slice(subjectIndex + 1).join('\n').trim()
                        : editedGeneratedMessage;
                    })()}
                    onChange={(e) => {
                      const emailLines = editedGeneratedMessage.split('\n');
                      const subjectIndex = emailLines.findIndex((line: string) => line.startsWith('Subject:'));
                      const subjectLine = subjectIndex >= 0 ? emailLines[subjectIndex] : 'Subject: ';

                      const newLines = [subjectLine, ...e.target.value.split('\n')];
                      setEditedGeneratedMessage(newLines.join('\n'));
                    }}
                    className="w-full h-48 p-3 bg-gray-800 border border-gray-600 rounded text-white text-sm resize-none"
                    placeholder="Enter message body..."
                  />
                </div>
              </div>
              <div className="flex justify-end space-x-2">
                <button
                  onClick={saveGeneratedItemEdits}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded"
                >
                  Save
                </button>
                <button
                  onClick={cancelGeneratedItemEditing}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded"
                >
                  Cancel
                </button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {linkedinPopupData && (
        <Dialog open={!!linkedinPopupData} onOpenChange={() => {
          setLinkedinPopupData(null);
          setLinkedinPopupTab('generator');
        }}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-2xl text-center">LinkedIn Message Generator</DialogTitle>
              {/* Tab Navigation */}
              <div className="flex space-x-4 mt-4 border-b border-gray-700">
                <button
                  onClick={() => setLinkedinPopupTab('generator')}
                  className={`px-4 py-2 font-medium ${linkedinPopupTab === 'generator' ? 'border-b-2 border-blue-500 text-blue-400' : 'text-gray-400 hover:text-gray-300'}`}
                >
                  Generator
                </button>
                <button
                  onClick={() => {
                    setLinkedinPopupTab('history');
                    fetchLinkedInHistory(linkedinPopupData.company);
                  }}
                  className={`px-4 py-2 font-medium ${linkedinPopupTab === 'history' ? 'border-b-2 border-blue-500 text-blue-400' : 'text-gray-400 hover:text-gray-300'}`}
                >
                  History
                </button>
              </div>
            </DialogHeader>

            {/* Conditional Content */}
            {linkedinPopupTab === 'generator' ? (
              <LinkedInMessageGenerator
                person={linkedinPopupData}
                onClose={() => setLinkedinPopupData(null)}
                onGenerate={() => generateLinkedInMessage(linkedinPopupData, linkedinMessageSettings)}
                generatedMessage={linkedinGeneratedMessage}
                isGenerating={linkedinIsGenerating}
                settings={linkedinMessageSettings}
                onSettingsChange={setLinkedinMessageSettings}
                onSave={saveLinkedInMessage}
                onCopy={copyLinkedInMessage}
                isSaving={isLinkedInSaving}
                copied={linkedInCopied}
                isEditing={isLinkedInEditing}
                editedMessage={editedLinkedInMessage}
                onStartEditing={startLinkedInEditing}
                onSaveEdits={saveLinkedInEdits}
                onCancelEditing={cancelLinkedInEditing}
                onEditMessageChange={(message) => setEditedLinkedInMessage(message)}
              />
            ) : (
              // History Tab Content
              <div className="mt-4">
                {isLoadingLinkedInHistory ? (
                  <div className="flex justify-center items-center h-32">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                  </div>
                ) : linkedInHistoryItems.length > 0 ? (
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {linkedInHistoryItems.map((item) => {
                      const displayMessage = item.message_content.generated_message;
                      const personName = item.message_content.person_name || 'Unknown';

                      return (
                        <div
                          key={item.id}
                          className="bg-gray-800 border border-gray-700 rounded-lg p-4 cursor-pointer hover:bg-gray-750 text-white"
                          onClick={() => openLinkedInHistoryPopup(item)}
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <h4 className="font-semibold text-white">To: {personName}</h4>
                              <p className="text-sm text-gray-300 mt-1 line-clamp-2">{displayMessage}</p>
                              <p className="text-xs text-gray-400 mt-2">{formatDate(item.created_at)}</p>
                            </div>
                            <div className="flex space-x-2 ml-4">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  copyLinkedInHistoryToClipboard(item.message_content.generated_message);
                                }}
                                className="p-2 text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 rounded"
                                title="Copy message"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openLinkedInProfile(item.message_content.person_name);
                                }}
                                className="p-2 text-blue-400 hover:text-blue-300 bg-blue-900 hover:bg-blue-800 rounded"
                                title="Open LinkedIn"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-400 bg-gray-800 rounded-lg border border-gray-700">
                    No LinkedIn messages generated for {linkedinPopupData.company}
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      )}

      {/* LinkedIn History Detail Popup */}
      {showLinkedInHistoryPopup && selectedLinkedInHistoryItem && (
        <Dialog open={showLinkedInHistoryPopup} onOpenChange={closeLinkedInHistoryPopup}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto bg-gray-900 border-gray-700">
            <DialogHeader>
              <DialogTitle>
                <div>
                  <h3 className="text-xl font-bold text-white">{selectedLinkedInHistoryItem.message_content.company_name}</h3>
                  <p className="text-sm text-gray-300">
                    To: {selectedLinkedInHistoryItem.message_content.person_name || 'Unknown'}
                  </p>
                  <p className="text-sm text-gray-400">
                    {formatDate(selectedLinkedInHistoryItem.created_at)}
                  </p>
                </div>
              </DialogTitle>
            </DialogHeader>
            <div className="flex justify-end space-x-2 mt-2">
              <button
                onClick={() => copyLinkedInHistoryToClipboard(selectedLinkedInHistoryItem.message_content.generated_message)}
                className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm"
              >
                Copy
              </button>
              <button
                onClick={() => openLinkedInProfile(selectedLinkedInHistoryItem.message_content.person_name)}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm"
              >
                LinkedIn
              </button>
              {isEditingLinkedInHistory ? (
                <>
                  <button
                    onClick={saveLinkedInHistoryEdits}
                    className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-sm"
                  >
                    Save
                  </button>
                  <button
                    onClick={cancelLinkedInHistoryEditing}
                    className="px-3 py-1 bg-gray-600 hover:bg-gray-500 text-white rounded text-sm"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  onClick={startEditingLinkedInHistory}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm"
                >
                  Edit
                </button>
              )}
            </div>
            <div className="mt-4">
              {isEditingLinkedInHistory ? (
                <textarea
                  value={editedLinkedInHistoryMessage}
                  onChange={(e) => setEditedLinkedInHistoryMessage(e.target.value)}
                  className="w-full h-64 p-3 bg-gray-800 border border-gray-600 rounded-lg resize-none text-white placeholder-gray-400"
                  placeholder="Edit your LinkedIn message..."
                />
              ) : (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 whitespace-pre-wrap max-h-64 overflow-y-auto text-white">
                  {selectedLinkedInHistoryItem.message_content.generated_message}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Upgrade Popup Dialog */}
      <Dialog open={showUpgradePopup} onOpenChange={setShowUpgradePopup}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-xl font-bold">Upgrade Your Plan</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-gray-600 dark:text-gray-300">
              You've discovered an advanced feature! Generating AI messages is available for users on the Silver tier and above.
            </p>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              Upgrade now to unlock this and many other powerful tools to accelerate your lead generation.
            </p>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <Button variant="outline" onClick={() => setShowUpgradePopup(false)}>
              Maybe Later
            </Button>
            <Button onClick={() => router.push('/subscription')}>
              Upgrade Now
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Notification */}
      <Notif
        show={notif.show}
        message={notif.message}
        type={notif.type}
        onClose={() => setNotif((prev) => ({ ...prev, show: false }))}
      />

      {/* Notes Popup */}
      <NotesPopup
        leadId={notesLeadId || ""}
        type="person"
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
                  {actionPreviewPopup.person?.name} - {actionPreviewPopup.person?.company}
                </p>
                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                  <p className="font-mono text-sm break-all">
                    {actionPreviewPopup.type === 'email' && actionPreviewPopup.person?.email}
                    {actionPreviewPopup.type === 'linkedin' && actionPreviewPopup.person?.linkedin}
                    {actionPreviewPopup.type === 'website' && actionPreviewPopup.person?.website}
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
              {['email', 'linkedin'].includes(actionPreviewPopup.type) && (
                <>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      if (actionPreviewPopup.type === 'email') {
                        copyEmailMessage();
                      } else {
                        copyLinkedInMessage();
                      }
                    }}
                    title="Copy to clipboard"
                  >
                    {((actionPreviewPopup.type === 'email' && emailCopied) ||
                      (actionPreviewPopup.type === 'linkedin' && linkedInCopied)) ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    onClick={handleActionSave}
                    disabled={isActionSaving || (actionPreviewPopup.type === 'email' ? !generatedMessage : !linkedinGeneratedMessage)}
                    variant="outline"
                    size="icon"
                    title="Save message"
                  >
                    {isActionSaving ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                    ) : (
                      <Save className="h-4 w-4" />
                    )}
                  </Button>
                </>
              )}
              <Button onClick={() => handleActionConfirm(actionPreviewPopup.type)}>
                {actionPreviewPopup.type === 'email' ? 'Send Email' :
                  actionPreviewPopup.type === 'linkedin' ? 'Open LinkedIn' :
                    'Open Website'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Phone Validator Popup */}
      {showPhoneValidator && selectedPersonForPhoneValidation && (
        <Dialog open={showPhoneValidator} onOpenChange={() => {}}>
          <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto [&>button]:hidden">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Phone className="h-5 w-5 text-blue-400" />
                Phone Validation Details
              </DialogTitle>
              <DialogDescription>
                Phone number validation results for {selectedPersonForPhoneValidation.name}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 relative">
              {/* Loading Overlay */}
              {isValidatingPhone && (
                <div className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-50 rounded-lg">
                  <div className="text-center space-y-4">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
                    <div className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                      Validating Phone Number...
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Please wait while we verify the phone number
                    </div>
                  </div>
                </div>
              )}

              {/* Validation Details */}
              <div className="p-4 bg-gray-800/50 rounded-lg">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {/* Basic Information */}
                  <div className="flex justify-between">
                    <span className="text-gray-400">Phone Number:</span>
                    <span className="text-white font-mono">{selectedPersonForPhoneValidation.phone}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Type:</span>
                    <Badge variant="outline">
                      {phoneValidationResult?.type || 'unknown'}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Status:</span>
                    {phoneValidationResult?.error ? (
                      <Badge variant="destructive">Invalid</Badge>
                    ) : phoneValidationResult?.valid ? (
                      <Badge variant="default" className="bg-green-600">Valid</Badge>
                    ) : isValidatingPhone ? (
                      <Badge variant="secondary">Validating...</Badge>
                    ) : (
                      <Badge variant="secondary">Ready</Badge>
                    )}
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Is Mobile:</span>
                    <span className={phoneValidationResult?.['is-mobile'] ? 'text-green-400' : 'text-red-400'}>
                      {phoneValidationResult?.['is-mobile'] !== undefined 
                        ? (phoneValidationResult['is-mobile'] ? 'Yes' : 'No')
                        : 'N/A'
                      }
                    </span>
                  </div>

                  {/* Phone-specific details - ordered logically */}
                  {phoneValidationResult && !phoneValidationResult.error && (
                    <>
                      {phoneValidationResult['international-number'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">International Number:</span>
                          <span className="text-white font-mono">{phoneValidationResult['international-number']}</span>
                        </div>
                      )}
                      {phoneValidationResult['local-number'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Local Number:</span>
                          <span className="text-white font-mono">{phoneValidationResult['local-number']}</span>
                        </div>
                      )}
                      {phoneValidationResult.country && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Country:</span>
                          <span className="text-white">{phoneValidationResult.country}</span>
                        </div>
                      )}
                      {phoneValidationResult['country-code'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Country Code:</span>
                          <span className="text-white">{phoneValidationResult['country-code']}</span>
                        </div>
                      )}
                      {phoneValidationResult['prefix-network'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Carrier:</span>
                          <span className="text-white">{phoneValidationResult['prefix-network']}</span>
                        </div>
                      )}
                      {phoneValidationResult.location && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Location:</span>
                          <span className="text-white">{phoneValidationResult.location}</span>
                        </div>
                      )}
                      {phoneValidationResult['international-calling-code'] && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Calling Code:</span>
                          <span className="text-white">+{phoneValidationResult['international-calling-code']}</span>
                        </div>
                      )}
                    </>
                  )}

                  {/* Loading state */}
                  {isValidatingPhone && (
                    <div className="flex justify-between col-span-2">
                      <span className="text-gray-400">Status:</span>
                      <span className="text-yellow-400 flex items-center">
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Validating...
                      </span>
                    </div>
                  )}

                  {/* Error state */}
                  {phoneValidationResult?.error && (
                    <div className="flex justify-between col-span-2">
                      <span className="text-gray-400">Error:</span>
                      <span className="text-red-400">{phoneValidationResult.error}</span>
                    </div>
                  )}

                  {/* Timestamp at the end */}
                  <div className="flex justify-between col-span-2">
                    <span className="text-gray-400">Last Verified:</span>
                    <span className="text-white">
                      {phoneValidationResult?.timestamp 
                        ? new Date(phoneValidationResult.timestamp).toLocaleString()
                        : new Date().toLocaleString()
                      }
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button 
                variant="outline"
                onClick={() => handlePhoneValidatorClick(selectedPersonForPhoneValidation, true)}
                disabled={isValidatingPhone}
              >
                {isValidatingPhone ? (
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
              <Button onClick={() => setShowPhoneValidator(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Email Validator Popup */}
      {showEmailValidator && selectedPersonForEmailValidation && (
        <Dialog open={showEmailValidator} onOpenChange={() => {}}>
          <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto [&>button]:hidden">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5 text-green-400" />
                Email Validation Details
              </DialogTitle>
              <DialogDescription>
                Email validation results for {selectedPersonForEmailValidation.name}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 relative">
              {/* Loading Overlay */}
              {isValidatingEmail && (
                <div className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm flex items-center justify-center z-50 rounded-lg">
                  <div className="text-center space-y-4">
                    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-green-600 mx-auto"></div>
                    <div className="text-lg font-semibold text-gray-700 dark:text-gray-300">
                      Validating Email Address...
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      Please wait while we verify the email address
                    </div>
                  </div>
                </div>
              )}

              {/* Validation Details */}
              <div className="p-4 bg-gray-800/50 rounded-lg">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {/* Basic Information */}
                  <div className="flex justify-between">
                    <span className="text-gray-400">Email Address:</span>
                    <span className="text-white font-mono">{selectedPersonForEmailValidation.email}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Type:</span>
                    <Badge variant="outline">email</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Status:</span>
                    {emailValidationResult?.error ? (
                      <Badge variant="destructive">Invalid</Badge>
                    ) : emailValidationResult?.active || emailValidationResult?.valid ? (
                      <Badge variant="default" className="bg-green-600">Valid</Badge>
                    ) : isValidatingEmail ? (
                      <Badge variant="secondary">Validating...</Badge>
                    ) : (
                      <Badge variant="secondary">Ready</Badge>
                    )}
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Domain Exists:</span>
                    <span className={emailValidationResult?.domain_exists ? 'text-green-400' : 'text-red-400'}>
                      {emailValidationResult?.domain_exists !== undefined 
                        ? (emailValidationResult.domain_exists ? 'Yes' : 'No')
                        : 'N/A'
                      }
                    </span>
                  </div>

                  {/* Email-specific details - ordered logically */}
                  {emailValidationResult && !emailValidationResult.error && (
                    <>
                      {emailValidationResult.active !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Active:</span>
                          <span className={emailValidationResult.active ? 'text-green-400' : 'text-red-400'}>
                            {emailValidationResult.active ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                      {emailValidationResult.is_personal !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Is Personal:</span>
                          <span className={emailValidationResult.is_personal ? 'text-green-400' : 'text-red-400'}>
                            {emailValidationResult.is_personal ? 'Yes' : 'No'}
                          </span>
                        </div>
                      )}
                      {emailValidationResult.smtp_status && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">SMTP Status:</span>
                          <span className="text-white">{emailValidationResult.smtp_status}</span>
                        </div>
                      )}
                      {emailValidationResult.email && (
                        <div className="flex justify-between">
                          <span className="text-gray-400">Email:</span>
                          <span className="text-white font-mono">{emailValidationResult.email}</span>
                        </div>
                      )}
                    </>
                  )}

                  {/* Loading state */}
                  {isValidatingEmail && (
                    <div className="flex justify-between col-span-2">
                      <span className="text-gray-400">Status:</span>
                      <span className="text-yellow-400 flex items-center">
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Validating...
                      </span>
                    </div>
                  )}

                  {/* Error state */}
                  {emailValidationResult?.error && (
                    <div className="flex justify-between col-span-2">
                      <span className="text-gray-400">Error:</span>
                      <span className="text-red-400">{emailValidationResult.error}</span>
                    </div>
                  )}

                  {/* Timestamp at the end */}
                  <div className="flex justify-between col-span-2">
                    <span className="text-gray-400">Last Verified:</span>
                    <span className="text-white">
                      {emailValidationResult?.timestamp 
                        ? new Date(emailValidationResult.timestamp).toLocaleString()
                        : new Date().toLocaleString()
                      }
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button 
                variant="outline"
                onClick={() => handleEmailValidationClick(selectedPersonForEmailValidation, true)}
                disabled={isValidatingEmail}
              >
                {isValidatingEmail ? (
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
              <Button onClick={() => setShowEmailValidator(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
// Add this component at the bottom of the file (or in the same file for now)
  function TemplatesTab({ refreshTrigger, onTemplatesUpdate, showNotification }: { refreshTrigger: number; onTemplatesUpdate?: (templates: any[]) => void; showNotification: (message: string, type?: "success" | "error" | "info") => void }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [addMode, setAddMode] = useState(false);
  const [editName, setEditName] = useState("");
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);

  // Helper: case-insensitive name uniqueness
  const isNameUnique = (name: string, excludeId: string | null = null) => {
    return !templates.some((t: any) => t.template_name.trim().toLowerCase() === name.trim().toLowerCase() && t.template_id !== excludeId);
  };

  // Helper: validate content
  const isContentValid = (content: string) => content.includes("{{context}}");

  // Fetch templates
  const fetchTemplates = () => {
    setLoading(true);
    setError(null);
    fetch("https://sandbox-api.saasquatchleads.com/api/emailgen_templates/", {
      method: "GET",
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch templates");
        return res.json();
      })
      .then((data) => {
        setTemplates(data);
        if (onTemplatesUpdate) {
          onTemplatesUpdate(data);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTemplates();
  }, [refreshTrigger]);

  // Add Template
  const handleAdd = () => {
    if (templates.length >= 2) {
        showNotification("Maximum 2 templates allowed. Please delete an existing template first.", "error");
      return;
    }
    setAddMode(true);
    setEditMode(true); // Set editMode to true to show input fields
    setEditName("");
    setEditContent("{{context}}"); // Set default content with context placeholder
    setShowTemplateDialog(true);
  };

  // Edit Template
  const handleEdit = (template: any) => {
    setAddMode(false);
    setEditMode(true);
    setEditName(template.template_name);
    setEditContent(template.template_content);
    setSelectedTemplate(template);
    setShowTemplateDialog(true);
  };

  // Save (Add or Edit)
  const handleSave = async () => {
    if (!editName.trim() || !isNameUnique(editName, addMode ? null : selectedTemplate?.template_id)) {
      window.showNotification && window.showNotification("Template name must be unique.", "error");
      return;
    }
    if (!isContentValid(editContent)) {
      window.showNotification && window.showNotification("Template content must include {{context}}.", "error");
      return;
    }

    // Check template count for add operations
    if (addMode && templates.length >= 2) {
      window.showNotification && window.showNotification("Maximum 2 templates allowed. Please delete an existing template first.", "error");
      return;
    }

    setSaving(true);
    try {
      if (addMode) {
        // Add
        const res = await fetch("https://sandbox-api.saasquatchleads.com/api/emailgen_templates/", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ template_name: editName, template_content: editContent })
        });
        if (!res.ok) throw new Error("Failed to add template");
        showNotification("Template added successfully!", "success");
      } else {
        // Edit
        const res = await fetch(`https://sandbox-api.saasquatchleads.com/api/emailgen_templates/${selectedTemplate.template_id}`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ template_name: editName, template_content: editContent })
        });
        if (!res.ok) throw new Error("Failed to update template");
        showNotification("Template updated successfully!", "success");
      }
      setShowTemplateDialog(false);
      setEditMode(false);
      setAddMode(false);
      fetchTemplates();
    } catch (err) {
        showNotification(err.message || "Failed to save template.", "error");
    } finally {
      setSaving(false);
    }
  };

  // Delete Template
  const handleDelete = async () => {
    // Show confirmation dialog
    const isConfirmed = confirm(`Are you sure you want to delete the template "${selectedTemplate.template_name}"?`);
    if (!isConfirmed) {
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`https://sandbox-api.saasquatchleads.com/api/emailgen_templates/${selectedTemplate.template_id}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to delete template");
              showNotification("Template deleted successfully!", "success");
      setShowTemplateDialog(false);
      setEditMode(false);
      setAddMode(false);
      fetchTemplates();
    } catch (err) {
        showNotification(err.message || "Failed to delete template.", "error");
    } finally {
      setSaving(false);
    }
  };

  // Cancel edit/add
  const handleCancel = () => {
    setEditMode(false);
    setAddMode(false);
    setShowTemplateDialog(false);
  };

  return (
    <div className="mt-4">
      <DialogHeader>
        <div className="flex items-center justify-between mb-4">
          <DialogTitle className="text-xl font-bold">
            Your Email Templates ({templates.length}/2)
          </DialogTitle>
          <button
            className={`px-3 py-1 rounded font-semibold ml-2 ${
              templates.length >= 2
                ? 'bg-gray-500 text-gray-300 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
            onClick={handleAdd}
            disabled={templates.length >= 2}
            title={templates.length >= 2 ? "Maximum 2 templates reached" : "Add new template"}
          >
            Add
          </button>
        </div>
      </DialogHeader>
      {loading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : error ? (
        <div className="text-center py-8 text-red-400 bg-gray-800 rounded-lg border border-gray-700">
          {error}
        </div>
      ) : templates.length === 0 ? (
        <div className="text-center py-8 text-gray-400 bg-gray-800 rounded-lg border border-gray-700">
          No templates found.
        </div>
      ) : (
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {templates.map((template) => (
            <div
              key={template.template_id}
              className="bg-gray-800 border border-gray-700 rounded-lg p-4 cursor-pointer hover:bg-gray-750 text-white"
              onClick={() => {
                setSelectedTemplate(template);
                setShowTemplateDialog(true);
                setEditMode(false);
                setAddMode(false);
              }}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h4 className="font-semibold text-white underline hover:text-blue-400 cursor-pointer">
                    {template.template_name}
                  </h4>
                  <p className="text-sm text-gray-300 mt-1 line-clamp-2">
                    {template.template_content.split('\n').slice(0, 3).join(' ')}
                  </p>
                  <p className="text-xs text-gray-400 mt-2">
                    Last updated: {template.updated_at ? new Date(template.updated_at).toLocaleDateString() : 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Template Detail/Edit Dialog */}
      {showTemplateDialog && (
        <Dialog open={showTemplateDialog} onOpenChange={setShowTemplateDialog}>
          <DialogContent className="max-w-xl max-h-[80vh] overflow-y-auto bg-gray-900 border-gray-700">
            <DialogHeader>
              {/* Always include DialogTitle for accessibility */}
              <DialogTitle asChild>
                <div className="sr-only">
                  {editMode
                    ? editName || "New Template"
                    : selectedTemplate?.template_name || "New Template"}
                </div>
              </DialogTitle>
              {/* Your custom flex layout */}
              <div className="flex flex-row justify-between items-center">
                {/* Left: Title and Date */}
                <div className="flex flex-col">
                  <h3 className="text-xl font-bold text-white mb-1">
                    {editMode ? (
                      <input
                        className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-white font-bold w-full mb-2"
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        placeholder="Template Name"
                        disabled={saving}
                      />
                    ) : (
                      selectedTemplate?.template_name || "New Template"
                    )}
                  </h3>
                  <p className="text-sm text-gray-400">
                    Last updated: {addMode ? 'N/A' : (selectedTemplate?.updated_at ? new Date(selectedTemplate.updated_at).toLocaleDateString() : 'N/A')}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    You can add variables like {'{{person}}'}, {'{{company}}'}, {'{{industry}}'} in double curly braces.
                    <br />
                    <span className="bg-blue-600 text-white px-1 rounded text-xs font-medium">{'{{context}}'}</span> is required.
                  </p>
                </div>
                {/* Right: Buttons */}
                {!editMode && (
                  <div className="flex flex-row gap-2 ml-6">
                    <button
                      className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded"
                      onClick={() => handleEdit(selectedTemplate)}
                    >
                      Edit
                    </button>
                    <button
                      className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded"
                      onClick={() => handleDelete()}
                      disabled={saving}
                    >
                      {saving ? (
                        <>
                          <div className="animate-spin h-4 w-4 mr-1 border-2 border-gray-300 border-t-red-600 rounded-full inline-block"></div>
                          Deleting...
                        </>
                      ) : (
                        "Delete"
                      )}
                    </button>
                  </div>
                )}
              </div>
            </DialogHeader>
            <div className="mt-4">
              {editMode ? (
                <>
                  <textarea
                    className="w-full h-48 p-3 bg-gray-800 border border-gray-600 rounded-lg resize-none text-white placeholder-gray-400 mb-4"
                    value={editContent}
                    onChange={e => setEditContent(e.target.value)}
                    placeholder="Template Content (must include {{context}})"
                    disabled={saving}
                  />
                  <div className="flex gap-2 justify-end">
                    <button
                      className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded"
                      onClick={handleSave}
                      disabled={saving}
                    >
                      {saving ? (
                        <>
                          <div className="animate-spin h-4 w-4 mr-1 border-2 border-gray-300 border-t-green-600 rounded-full inline-block"></div>
                          Saving...
                        </>
                      ) : (
                        "Save"
                      )}
                    </button>
                    <button
                      className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded"
                      onClick={handleCancel}
                      disabled={saving}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 whitespace-pre-wrap max-h-64 overflow-y-auto text-white">
                  {selectedTemplate && selectedTemplate.template_content}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}