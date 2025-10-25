import Link from "next/link";
import { User, Bell, ChevronDown, ChevronUp, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Image from "next/image";
import { useEffect, useState } from "react";
import axios from "axios";
import dayjs from "dayjs";
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL_P2;
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Inbox as InboxIcon } from "lucide-react";
import PopupBig from "@/components/ui/popup-big"; // Adjust path if needed
import Inbox from "@/components/inbox"; // adjust path if needed

export function Header({ onToggleSidebar }) {
  const [userEmail, setUserEmail] = useState("");
  const pathname = usePathname();
  const [showInbox, setShowInbox] = useState(false);
  const [showReleaseNotes, setShowReleaseNotes] = useState(false);
  const [releaseNotes, setReleaseNotes] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadingReleaseNotes, setLoadingReleaseNotes] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [pendingInvitationsCount, setPendingInvitationsCount] = useState(0);

  
  useEffect(() => {
    if (typeof window !== "undefined") {
      const user = JSON.parse(sessionStorage.getItem("user") || "{}");
      setUserEmail(user.email || "user@example.com");
    }
  }, []);

  useEffect(() => {
    // Try to load from sessionStorage first
    const stored = typeof window !== 'undefined' ? sessionStorage.getItem('releaseNotes') : null;
    if (stored) {
      try {
        const parsedNotes = JSON.parse(stored);
        // Ensure stored notes have the correct structure for ReleaseNotesPopup
        const mappedNotes = Array.isArray(parsedNotes) ? parsedNotes.map(note => ({
          id: note.id,
          title: note.title,
          description: note.description || note.body || note.content,
          content: note.content || note.body,
          read: note.read !== undefined ? note.read : note.is_read,
          created_at: note.created_at,
          type: note.type
        })) : [];
        setReleaseNotes(mappedNotes);
        
        // Calculate unread count from stored notes
        const unreadCount = mappedNotes.filter(note => !note.read).length;
        setUnreadCount(unreadCount);
      } catch {}
    }
    
    const fetchPendingInvitationsCount = async () => {
      try {
        const res = await axios.get(`${DATABASE_URL}/invitations/pending`, { withCredentials: true });
        const pendingCount = Array.isArray(res.data) ? res.data.length : 0;
        setPendingInvitationsCount(pendingCount);
      } catch (err) {
        setPendingInvitationsCount(0);
      }
    };
    
    fetchPendingInvitationsCount();
  }, []);

  // Fetch release notes when dropdown opens, and update sessionStorage
  useEffect(() => {
    if (!showReleaseNotes) return;
    setLoadingReleaseNotes(true);
    axios.get(`${DATABASE_URL}/release-notes`, { withCredentials: true })
      .then(res => {
        // Map API response to match ReleaseNotesPopup component expectations
        const mappedNotes = (res.data.notes || []).map(note => ({
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
        
        // Update unread count
        const unreadCount = mappedNotes.filter(note => !note.read).length;
        setUnreadCount(unreadCount);
      })
      .catch(() => setReleaseNotes([]))
      .finally(() => setLoadingReleaseNotes(false));
  }, [showReleaseNotes]);

  // Mark as read handler
  const handleMarkAsRead = async (noteId) => {
    try {
      await axios.post(`${DATABASE_URL}/release-notes/${noteId}/read`, {}, { withCredentials: true });
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {}
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-[#1A2133] border-b border-[#2E3A59]">
      <div className="flex h-24 items-center px-4 sm:px-6 lg:px-10 gap-2 sm:gap-4 lg:gap-8">
        {/* Sidebar Toggle Button */}
        <button
          className="mr-4 p-2 rounded-md hover:bg-[#23272f] focus:outline-none"
          aria-label="Toggle sidebar"
          type="button"
          onClick={onToggleSidebar}
        >
          <Menu className="w-7 h-7 text-white" />
        </button>
        {/* Logo */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="h-12 sm:h-14 lg:h-16 w-auto relative">
            <Link href="/">
              <Image
                src="/images/logo_horizontal.png"
                alt="SaaSquatch Logo"
                width={270}
                height={96}
                className="object-contain w-auto h-full"
              />
            </Link>
          </div>
        </div>

        {/* Navigation */}
        <nav className="ml-auto flex items-center gap-4 sm:gap-6 lg:gap-8 xl:gap-12 text-sm sm:text-base uppercase tracking-wider font-bold">
          <Link
            href="/"
            className={cn(
              "hover:text-yellow-400 transition-colors hidden sm:block",
              pathname === "/" ? "text-yellow-400" : "text-white"
            )}
          >
            Home
          </Link>

          <Link
            href="/scraper"
            className={cn(
              "hover:text-yellow-400 transition-colors",
              pathname.startsWith("/scraper") ? "text-yellow-400" : "text-white"
            )}
          >
            Enrich
          </Link>

          {/* Help Dropdown */}
          <DropdownMenu open={helpOpen} onOpenChange={setHelpOpen}>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className={`uppercase tracking-wider font-bold text-xs sm:text-sm lg:text-base px-1 sm:px-2 flex items-center !text-white ${helpOpen ? "text-yellow-400" : ""} hover:!text-yellow-400`}
              >
                <span className="hidden sm:inline">Help</span>
                <span className="sm:hidden">?</span>
                {helpOpen ? (
                  <ChevronUp className="ml-1 sm:ml-2 w-3 h-3 sm:w-4 sm:h-4" />
                ) : (
                  <ChevronDown className="ml-1 sm:ml-2 w-3 h-3 sm:w-4 sm:h-4" />
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-48 bg-[#181c23] border border-[#23272f] rounded-2xl shadow-2xl overflow-hidden" align="center">
              <DropdownMenuItem asChild>
                <Link
                  href="/documentation"
                  className="w-full block px-4 py-2 hover:bg-dark-hover focus:bg-dark-hover transition-colors text-white hover:text-yellow-400 focus:text-yellow-400"
                >
                  Documentation
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link
                  href="/contact"
                  className="w-full block px-4 py-2 hover:bg-dark-hover focus:bg-dark-hover transition-colors text-white hover:text-yellow-400 focus:text-yellow-400"
                >
                  Contact Us
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Inbox Bell Icon as Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="relative focus:outline-none"
                title="Inbox"
              >
                <Bell className="w-5 h-5 sm:w-6 sm:h-6 text-white hover:text-yellow-400" />
                {(unreadCount + pendingInvitationsCount) > 0 && (
                  <span className="absolute -top-1 -right-1 sm:-top-2 sm:-right-2 bg-red-500 text-white text-xs rounded-full px-1 sm:px-1.5 py-0.5">
                    {unreadCount + pendingInvitationsCount}
                  </span>
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-[500px] max-h-[600px] overflow-y-auto p-4 mt-2 bg-[#181c23] border border-[#23272f] rounded-2xl shadow-2xl" align="end">
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-[#23272f] pb-2">
                  <h3 className="text-lg font-semibold text-white">Inbox</h3>
                </div>
                
                <Inbox />
               
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Avatar */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="group rounded-full text-gray-300 hover:text-white hover:bg-dark-hover flex items-center justify-center p-0 h-9 w-9 sm:h-11 sm:w-11"
              >
                <div className={`flex items-center justify-center rounded-full border-2 h-9 w-9 sm:h-11 sm:w-11 ${pathname === "/userSetting" ? "border-yellow-400" : "border-white"} group-hover:border-yellow-400`}>
                  <User
                    className={`h-7 w-7 sm:h-9 sm:w-9 ${pathname === "/userSetting" ? "text-yellow-400" : "text-white"} group-hover:text-yellow-400`}
                    strokeWidth={4}
                  />
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="w-56 bg-dark-tertiary border-dark-border text-gray-200"
              align="end"
              forceMount
            >
              <DropdownMenuLabel className="font-normal text-gray-400">
                <div className="flex flex-col space-y-1">
                  <p className="text-xs leading-none text-gray-400">
                    {userEmail}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-dark-border" />
              <DropdownMenuItem
                asChild
                className="hover:bg-dark-hover focus:bg-dark-hover cursor-pointer"
              >
                <Link href="/userSetting" className="flex items-center w-full">
                  <User className="mr-2 h-4 w-4 text-teal-400" />
                  <span>Profile</span>
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={async () => {

                  // 2) Perform logout
                  try {
                    const res = await fetch(`${DATABASE_URL}/auth/logout`, {
                      method: "POST",
                      credentials: "include",
                    });

                    if (res.ok) {
                      sessionStorage.clear(); // ✅ Clear client-side session
                      localStorage.clear();
                      window.location.href = "/auth"; // ⬅️ Redirect to login
                    } else {
                      const data = await res.json();
                      alert(
                        `Logout failed: ${data.message || "Unknown error"}`
                      );
                    }
                  } catch (error) {
                    console.error("❌ Logout error:", error);
                    alert("Network error during logout. Try again.");
                  }
                }}
                className="hover:bg-dark-hover focus:bg-dark-hover cursor-pointer"
              >
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>
      </div>
      <PopupBig show={showInbox} onClose={() => setShowInbox(false)}>
        <h2 className="text-2xl font-bold mb-4">Inbox</h2>
        <Inbox />
      </PopupBig>
    </header>
  );
}
