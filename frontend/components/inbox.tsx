"use client";

import { useState, useEffect } from "react";
import { MailOpen, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import axios from "axios";
import dayjs from "dayjs";

interface ReleaseNote {
  id: number;
  title: string;
  description?: string;
  content?: string;
  read: boolean;
  created_at: string;
  type?: string;
}

interface InboxMessage {
  id: number;
  title: string;
  body: string;
  description?: string;
  content?: string;
  is_read: boolean;
  read?: boolean;
  created_at: string;
  type?: string;
}

interface WorkspaceInvitation {
  invitation_id: string;
  invitation_token: string;
  workspace_id: string;
  workspace_name: string;
  invited_by_email: string;
  role: string;
  status: "pending" | "accepted" | "declined";
  sent_at: string;
  expires_at: string;
  is_expired: boolean;
  days_until_expiry: number;
  decline_reason?: string;
  declined_at?: string;
  sent_by: string;
  email: string;
  release_note_id?: string;
}



export default function Inbox() {
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [subscriptionInfo, setSubscriptionInfo] = useState(null);
  const [showSubReminder, setShowSubReminder] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [invitationsLoading, setInvitationsLoading] = useState(false);
  const [invitationsError, setInvitationsError] = useState<string | null>(null);
  const [processingInvitation, setProcessingInvitation] = useState<string | null>(null);
  const [releaseNotes, setReleaseNotes] = useState<ReleaseNote[]>([]);
  const [releaseNotesLoading, setReleaseNotesLoading] = useState(false);
  const [expandedReleaseNotes, setExpandedReleaseNotes] = useState<Set<number>>(new Set());

  // Fetch subscription info on mount
  useEffect(() => {
    const fetchSub = async () => {
      try {
        const res = await axios.get("/api/user/subscription_info", { withCredentials: true });
        setSubscriptionInfo(res.data?.subscription || null);
        const expiration = res.data?.subscription?.plan_expiration_timestamp;
        if (expiration) {
          const daysLeft = dayjs(expiration).diff(dayjs(), 'day');
          if (daysLeft >= 0 && daysLeft <= 7) {
            setShowSubReminder(true);
          }
        }
      } catch {}
    };
    fetchSub();
  }, []);

  // Fetch workspace invitations
  useEffect(() => {
    const fetchInvitations = async () => {
      setInvitationsLoading(true);
      setInvitationsError(null);
      
      try {
        // Get invitations from session storage first (if available)
        const storedInvitations = sessionStorage.getItem('workspaceInvitations');
        if (storedInvitations) {
          try {
            const parsed = JSON.parse(storedInvitations);
            setInvitations(parsed);
          } catch (e) {
            console.error('Error parsing stored invitations:', e);
          }
        }
        
        // Fetch fresh invitations from API
        const response = await axios.get(`${process.env.NEXT_PUBLIC_DATABASE_URL}/invitations/pending`, {
          withCredentials: true
        });
        
        if (response.data && Array.isArray(response.data)) {
          setInvitations(response.data);
          sessionStorage.setItem('workspaceInvitations', JSON.stringify(response.data));
        }
      } catch (error) {
        console.error('Error fetching invitations:', error);
        setInvitationsError('Failed to load invitations');
      } finally {
        setInvitationsLoading(false);
      }
    };
    
    fetchInvitations();
  }, []);

  // Fetch release notes
  useEffect(() => {
    const fetchReleaseNotes = async () => {
      setReleaseNotesLoading(true);
      
      try {
        // Try to load from sessionStorage first
        const stored = sessionStorage.getItem('releaseNotes');
        if (stored) {
          try {
            const parsedNotes = JSON.parse(stored);
            const mappedNotes = Array.isArray(parsedNotes) ? parsedNotes.map((note: any) => ({
              id: note.id,
              title: note.title,
              description: note.description || note.body || note.content,
              content: note.content || note.body,
              read: note.read !== undefined ? note.read : note.is_read,
              created_at: note.created_at,
              type: note.type
            })) : [];
            setReleaseNotes(mappedNotes);
          } catch (e) {
            console.error('Error parsing stored release notes:', e);
          }
        }
        
        // Fetch fresh release notes from API
        const response = await axios.get(`${process.env.NEXT_PUBLIC_DATABASE_URL}/release-notes`, {
          withCredentials: true
        });
        
        if (response.data && response.data.notes) {
          const mappedNotes = response.data.notes.map((note: any) => ({
            id: note.id,
            title: note.title,
            description: note.content,
            content: note.content,
            read: note.read,
            created_at: note.created_at,
            type: note.type
          }));
          setReleaseNotes(mappedNotes);
          sessionStorage.setItem('releaseNotes', JSON.stringify(mappedNotes));
        }
      } catch (error) {
        console.error('Error fetching release notes:', error);
      } finally {
        setReleaseNotesLoading(false);
      }
    };
    
    fetchReleaseNotes();
  }, []);

  // Handle invitation actions
  const handleInvitationAction = async (invitation: WorkspaceInvitation, action: 'accept' | 'decline') => {
    setProcessingInvitation(invitation.invitation_token);
    
    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_DATABASE_URL}/invitations/${invitation.invitation_id}/${action}`,
        {},
        { withCredentials: true }
      );
      
      if (response.status === 200) {
        // Update local state
        setInvitations(prev => prev.map(inv => 
          inv.invitation_id === invitation.invitation_id 
            ? { ...inv, status: action === 'accept' ? 'accepted' : 'declined' }
            : inv
        ));
        
        // Update session storage
        const updatedInvitations = invitations.map(inv => 
          inv.invitation_id === invitation.invitation_id 
            ? { ...inv, status: action === 'accept' ? 'accepted' : 'declined' }
            : inv
        );
        sessionStorage.setItem('workspaceInvitations', JSON.stringify(updatedInvitations));
        
        // Show success message
        alert(`Invitation ${action}ed successfully!`);
      }
    } catch (error) {
      console.error(`Error ${action}ing invitation:`, error);
      alert(`Failed to ${action} invitation. Please try again.`);
    } finally {
      setProcessingInvitation(null);
    }
  };

  const markAsRead = (id: number) => {
    setMessages((msgs) =>
      msgs.map((msg) => (msg.id === id ? { ...msg, is_read: true } : msg))
    );
  };

  const markReleaseNoteAsRead = async (noteId: number) => {
    try {
      // Optimistically update the UI first
      setReleaseNotes(prev => prev.map(note => 
        note.id === noteId ? { ...note, read: true } : note
      ));
      
      // Update session storage
      const updatedNotes = releaseNotes.map(note => 
        note.id === noteId ? { ...note, read: true } : note
      );
      sessionStorage.setItem('releaseNotes', JSON.stringify(updatedNotes));
      
      // Then call the API
      await axios.post(`${process.env.NEXT_PUBLIC_DATABASE_URL}/release-notes/${noteId}/read`, {}, { withCredentials: true });
    } catch (error) {
      console.error('Error marking release note as read:', error);
      // Revert the optimistic update if the API call fails
      setReleaseNotes(prev => prev.map(note => 
        note.id === noteId ? { ...note, read: false } : note
      ));
      
      // Revert session storage
      const revertedNotes = releaseNotes.map(note => 
        note.id === noteId ? { ...note, read: false } : note
      );
      sessionStorage.setItem('releaseNotes', JSON.stringify(revertedNotes));
    }
  };

  const toggleReleaseNoteExpansion = (noteId: number) => {
    setExpandedReleaseNotes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(noteId)) {
        newSet.delete(noteId);
      } else {
        newSet.add(noteId);
      }
      return newSet;
    });
  };

  // Filter pending invitations
  const pendingInvitations = invitations.filter(inv => inv.status === 'pending');
  const allItems = [...pendingInvitations, ...releaseNotes];

  if (allItems.length === 0) {
    return (
      <div className="flex flex-col items-center text-muted-foreground py-10">
        <MailOpen className="h-10 w-10 mb-2" />
        <p>No messages in your inbox.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Invitations Section */}
      <div className="space-y-3">
        <h4 className="text-lg font-semibold text-blue-400">Invitations</h4>
        
        {/* Loading state for invitations */}
        {invitationsLoading && (
          <div className="text-center py-4 text-gray-400">
            Loading invitations...
          </div>
        )}

        {/* Error state for invitations */}
        {invitationsError && (
          <div className="p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm">{invitationsError}</p>
          </div>
        )}

        {/* Invitations Content */}
        {!invitationsLoading && !invitationsError && (
          <>
            {pendingInvitations.length > 0 ? (
              pendingInvitations.map((invitation) => (
        <div
          key={invitation.invitation_token}
          className="border border-blue-500/30 p-4 rounded-lg bg-blue-900/10"
        >
          <div className="flex justify-between items-start mb-3">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-blue-400">
                🏢 Workspace Invitation
              </h3>
              <p className="text-sm text-gray-300 font-medium">
                {invitation.workspace_name}
              </p>
            </div>
            <div className="text-xs text-gray-400">
              {new Date(invitation.sent_at).toLocaleDateString()}
            </div>
          </div>
          
          <div className="space-y-2 mb-4">
            <p className="text-sm text-gray-300">
              <span className="text-blue-400">From:</span> {invitation.invited_by_email}
            </p>
            <p className="text-sm text-gray-300">
              <span className="text-blue-400">Role:</span> {invitation.role}
            </p>
            <p className="text-xs text-gray-400">
              Expires: {new Date(invitation.expires_at).toLocaleDateString()}
            </p>
            {invitation.days_until_expiry <= 3 && (
              <p className="text-xs text-orange-400">
                ⚠️ Expires in {invitation.days_until_expiry} days
              </p>
            )}
          </div>

          <div className="flex gap-2">
            <Button
              size="sm"
              className="bg-green-600 hover:bg-green-700 text-white"
              onClick={() => handleInvitationAction(invitation, 'accept')}
              disabled={processingInvitation === invitation.invitation_token}
            >
              {processingInvitation === invitation.invitation_token ? 'Processing...' : 'Accept'}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="border-red-500 text-red-400 hover:text-red-300"
              onClick={() => handleInvitationAction(invitation, 'decline')}
              disabled={processingInvitation === invitation.invitation_token}
            >
              {processingInvitation === invitation.invitation_token ? 'Processing...' : 'Decline'}
            </Button>
          </div>
        </div>
      ))
            ) : (
              <div className="text-center py-4 text-gray-400">
                No invitations
              </div>
            )}
          </>
        )}
        </div>

      {/* Release Notes Section */}
      {releaseNotes.length > 0 && (
        <div className="space-y-3 border-t border-[#23272f] pt-4">
          <h4 className="text-lg font-semibold text-yellow-400">Release Notes</h4>
          
          {releaseNotesLoading && (
            <div className="text-center py-4 text-gray-400">
              Loading release notes...
            </div>
          )}

          {releaseNotes.map((note) => {
            const isExpanded = expandedReleaseNotes.has(note.id);
            const hasLongContent = note.content && note.content.length > 200;
            
            return (
              <div
                key={note.id}
                style={{
                  backgroundColor: note.read ? '#1f2937' : '#111827',
                  border: '1px solid #374151',
                  padding: '1rem',
                  borderRadius: '0.5rem',
                  marginBottom: '1rem'
                }}
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-semibold flex-1">{note.title}</h3>
                  <Button
                    size="sm"
                    variant="outline"
                    className={`text-sm ml-2 flex-shrink-0 ${
                      !note.read 
                        ? 'border-red-500 text-red-400 hover:text-red-300 hover:border-red-400' 
                        : 'border-gray-600 text-gray-400 hover:text-gray-300'
                    }`}
                    onClick={() => markReleaseNoteAsRead(note.id)}
                  >
                    {note.read ? 'Marked as read' : 'Mark as read'}
                  </Button>
                </div>
                
                <div className="mb-2">
                  {isExpanded ? (
                    <div className="text-sm text-muted-foreground whitespace-pre-line">
                      {note.content}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {hasLongContent 
                        ? `${note.content?.substring(0, 200)}...` 
                        : note.content
                      }
                    </p>
                  )}
                </div>
                
                <div className="flex justify-between items-center">
                  <p className="text-xs text-gray-500 italic">
                    {new Date(note.created_at).toLocaleString()}
                  </p>
                  {hasLongContent && (
                    <button
                      onClick={() => toggleReleaseNoteExpansion(note.id)}
                      className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                    >
                      {isExpanded ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
