"use client";
import * as React from "react";
import { LeadsProvider } from "./LeadsProvider";
import { Header } from "@/components/header";
import { Sidebar } from "@/components/sidebar";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export default function ClientRoot({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const pathname = usePathname();
  const isAuthRoute = pathname.startsWith("/auth");

  const toggleSidebar = () => setSidebarOpen((open) => !open);

  return (
    <LeadsProvider>
      <div className="flex flex-col h-screen">
        {!isAuthRoute && <Header onToggleSidebar={toggleSidebar} />}
        <div className="flex flex-1 min-h-0 overflow-hidden relative">
          {!isAuthRoute && (
            <>
              {/* Backdrop */}
              <div
                className={cn(
                  "fixed inset-0 bg-black z-40 transition-opacity",
                  sidebarOpen
                    ? "bg-opacity-50"
                    : "bg-opacity-0 pointer-events-none"
                )}
                onClick={toggleSidebar}
              />
              {/* Sidebar */}
              <div
                className={cn(
                  "fixed left-0 top-24 bottom-0 w-64 bg-dark-secondary border-r border-dark-border z-50 transition-transform duration-100 ease-in-out",
                  sidebarOpen ? "translate-x-0" : "-translate-x-full"
                )}
              >
                <Sidebar onClose={toggleSidebar} />
              </div>
            </>
          )}

          <main
            className={cn(
              "flex-1 min-h-0 overflow-y-auto transition-all duration-300",
              sidebarOpen && "blur-sm"
            )}
          >
            {children}
          </main>
        </div>
      </div>
    </LeadsProvider>
  );
}