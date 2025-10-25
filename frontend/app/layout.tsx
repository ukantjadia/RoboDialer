import React from "react"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "../components/theme-provider"
import ClientRoot from "../components/ClientRoot"
import { LeadsProvider } from "../components/LeadsProvider"
import { EnrichmentProvider } from "../components/EnrichmentProvider" // ✅ Add this
import { Toaster } from "sonner"

const inter = Inter({ subsets: ["latin"] })

export const metadata = {
  title: "LeadGenAI - B2B Lead Generation & Enrichment",
  description: "Find and enrich B2B sales leads from multiple sources",
  generator: "v0.dev",
  icons: {
    icon: "/favicon.ico",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.className} bg-dark-primary text-gray-100`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false} disableTransitionOnChange>
          <LeadsProvider>
            <EnrichmentProvider> {/* ✅ Wrap here */}
              <ClientRoot>
                {children}
              </ClientRoot>
            </EnrichmentProvider>
          </LeadsProvider>
        </ThemeProvider>
        <Toaster position="top-right" richColors />
      </body>
    </html>
  )
}
