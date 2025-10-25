"use client";

import Image from "next/image";
import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-[#0D0D0D] text-gray-400 px-6 md:px-12 lg:px-20 py-14 border-t border-gray-800">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:space-x-14 divide-y md:divide-y-0 md:divide-x divide-gray-700 text-sm">
        {/* Column 1: Logo + About */}
        <div className="flex-1 pb-10 md:pb-0 md:pr-10">
          <Image
            src="/images/logo_horizontal.png"
            alt="Your Logo"
            width={180}
            height={60}
            className="object-contain mb-4"
          />
          <p className="text-sm text-muted-foreground max-w-sm leading-relaxed">
            LeadGenAI is the platform built for modern prospecting. Smart enrichment,
            AI-powered messaging, and flexible tools mean you can do more — with less.
          </p>
          <div className="flex space-x-4 pt-4 text-white">
            <Link href="#"><i className="fab fa-youtube" /></Link>
            <Link href="#"><i className="fab fa-twitter" /></Link>
            <Link href="#"><i className="fab fa-instagram" /></Link>
            <Link href="#"><i className="fab fa-tiktok" /></Link>
          </div>
        </div>

        {/* Column 2: Product */}
        <div className="flex-1 pt-10 md:pt-0 md:px-10 space-y-3">
          <h4 className="text-white font-semibold mb-2">Product</h4>
          <ul className="space-y-2">
            <li><Link href="/scraper">Data enrichment Companies</Link></li>
            <li><Link href="/scraper">Data enrichment People</Link></li>
            <li><Link href="/lead">LinkedIn Message Generator</Link></li>
            <li><Link href="/lead">Email Generator</Link></li>
            <li><Link href="#">AI Features</Link></li>
            <li><Link href="/subscription">Outreach</Link></li>
          </ul>
        </div>

        {/* Column 3: Resources */}
        <div className="flex-1 pt-10 md:pt-0 md:px-10 space-y-3">
          <h4 className="text-white font-semibold mb-2">Resources</h4>
          <ul className="space-y-2">
            <li><Link href="/contact">Help Centre</Link></li>
            <li><Link href="/subscription">Pricing</Link></li>
          </ul>
        </div>

        {/* Column 4: Company */}
        <div className="flex-1 pt-10 md:pt-0 md:pl-10 space-y-3">
          <h4 className="text-white font-semibold mb-2">Company</h4>
          <ul className="space-y-2">
            <li><Link href="https://www.saasquatchleads.com" target="_blank" rel="noopener noreferrer">About Us</Link></li>
            <li><Link href="/contact">Contact Us</Link></li>
            <li><Link href="https://www.linkedin.com/company/saasquatchleads/" target="_blank" rel="noopener noreferrer">Press & Media</Link></li>
            <li><Link href="https://www.linkedin.com/company/saasquatchleads/" target="_blank" rel="noopener noreferrer">Accessibility Statement</Link></li>
            <li><Link href="#">Site Map</Link></li>
            <li><Link href="https://www.linkedin.com/company/saasquatchleads/" target="_blank" rel="noopener noreferrer">Careers</Link></li>
          </ul>
        </div>
      </div>
    </footer>
  );
}
