
'use client';

import type { Metadata } from 'next';
import './globals.css';
import { AppProvider } from '@/components/app-provider';
import { useRouter } from 'next/navigation';

const metadata: Metadata = {
  title: 'Caprae Capital Partners',
  description: 'AI-powered softphone for your business.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" style={{colorScheme: 'dark'}} suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&family=Source+Code+Pro:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-body antialiased">
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
