"use client";

import React from "react";
import Link from "next/link";

export default function NotFound(): React.JSX.Element {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
      <div className="text-center max-w-md">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
          Coming Soon!
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mb-8">
          This page is under construction. We're working hard to bring you something amazing!
        </p>
        <Link 
          href="/"
          className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors"
        >
          Go Home
        </Link>
        <p className="text-xs text-gray-400 mt-4">
          Error 404 - Page Not Found
        </p>
      </div>
    </div>
  );
} 