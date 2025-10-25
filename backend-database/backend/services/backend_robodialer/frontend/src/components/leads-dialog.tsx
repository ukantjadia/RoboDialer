
'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { useCall } from '@/contexts/call-context';
import type { Lead } from '@/lib/types';
import { Mail, Phone, Voicemail, RefreshCw } from 'lucide-react';
import { useEffect, useState, useMemo } from 'react';
import { useToast } from '@/hooks/use-toast';
import { Badge } from './ui/badge';

const LEADS_PER_PAGE = 5;

export default function LeadsDialog({
  open,
  onOpenChange,
  leads: initialLeads,
  onRefreshLeads,
  dataSource = 'csv',
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leads: Lead[];
  onRefreshLeads: () => void;
  dataSource?: 'csv' | 'enriched';
}) {
  const { startOutgoingCall, state, openVoicemailDialogForLead, sendMissedCallEmail } = useCall();
  const [currentPage, setCurrentPage] = useState(1);
  const [leads, setLeads] = useState<Lead[]>(initialLeads);
  const { toast } = useToast();

  useEffect(() => {
    setLeads(initialLeads);
  }, [initialLeads]);
  
  useEffect(() => {
    if(open) {
      setCurrentPage(1);
    }
  }, [open, leads]);

  const totalPages = Math.ceil(leads.length / LEADS_PER_PAGE);

  const paginatedLeads = useMemo(() => {
    const startIndex = (currentPage - 1) * LEADS_PER_PAGE;
    const endIndex = startIndex + LEADS_PER_PAGE;
    return leads.slice(startIndex, endIndex);
  }, [leads, currentPage]);

  const handleCall = (lead: Lead) => {
    const phoneNumber = lead.phoneNumber || lead.companyPhone;
    
    if (phoneNumber && /^\+?\d+$/.test(phoneNumber.replace(/[\s()-]/g, ''))) {
      startOutgoingCall(phoneNumber, lead.name || lead.company, lead.lead_id);
      onOpenChange(false);
    } else {
        toast({ 
            title: "Invalid or Missing Phone Number", 
            description: `The phone number for ${lead.company} is not valid.`,
            variant: "destructive" 
        });
    }
  };

  const handleVoicemail = (lead: Lead) => {
    if (openVoicemailDialogForLead) {
      openVoicemailDialogForLead(lead);
      onOpenChange(false);
    }
  };
  
  const handleEmail = (lead: Lead) => {
    if (sendMissedCallEmail) {
        sendMissedCallEmail(lead);
        onOpenChange(false);
    }
  };

  const handleRefresh = () => {
    onRefreshLeads();
  }

  const isLeadContacted = (leadId: string) => {
    return state.allCallHistory.some(call => call.leadId === leadId);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[70vh] flex flex-col pt-4">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Available Leads</DialogTitle>
            <Badge variant={dataSource === 'enriched' ? 'default' : 'secondary'}>
              {dataSource === 'enriched' ? 'Enriched Data' : 'CSV Data'}
            </Badge>
          </div>
          <DialogDescription>
            Select a lead from the list to initiate an action.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedLeads.length > 0 ? (
                paginatedLeads.map((lead, index) => {
                  const contacted = isLeadContacted(lead.lead_id);
                  // Create unique key combining lead_id with index to prevent duplicate key errors
                  const uniqueKey = `${lead.lead_id}-${index}-${currentPage}`;
                  return (
                    <TableRow key={uniqueKey} className="h-16">
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{lead.company}</span>
                          {contacted && <Badge variant="secondary">Contacted</Badge>}
                        </div>
                        <div className="text-sm text-muted-foreground">{lead.website}</div>
                      </TableCell>
                      <TableCell>{lead.phoneNumber || lead.companyPhone}</TableCell>
                      <TableCell>{lead.email}</TableCell>
                      <TableCell>
                        <div className="flex gap-2 justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleCall(lead)}
                            disabled={!!state.activeCall || contacted}
                            className="whitespace-nowrap"
                          >
                            <Phone className="mr-2 h-4 w-4" />
                            Call
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleVoicemail(lead)}
                            disabled={!!state.activeCall || contacted}
                            className="whitespace-nowrap"
                          >
                            <Voicemail className="mr-2 h-4 w-4" />
                            Voicemail
                          </Button>
                          <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleEmail(lead)}
                              disabled={!lead.email || !!state.activeCall || contacted}
                              className="whitespace-nowrap"
                          >
                              <Mail className="mr-2 h-4 w-4" />
                              Email
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    No leads found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
        <DialogFooter className="pt-4 border-t flex justify-between w-full">
          <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Upload New CSV
            </Button>
          <div className="flex items-center justify-end space-x-2">
            <span className="text-sm text-muted-foreground">
              Page {currentPage} of {totalPages > 0 ? totalPages : 1}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setCurrentPage((prev) => Math.min(prev + 1, totalPages))
              }
              disabled={currentPage === totalPages || totalPages === 0}
            >
              Next
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
