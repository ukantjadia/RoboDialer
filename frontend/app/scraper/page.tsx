// app/scraper/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Scraper } from "@/components/scraper";
import Popup from "@/components/ui/popup";
import FeedbackPopup from "@/components/FeedbackPopup";
import useEmailVerificationGuard from "@/hooks/useEmailVerificationGuard";
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;

export default function ScraperPage() {
    const router = useRouter();
    const [isCheckingAuth, setIsCheckingAuth] = useState(true);
    const { showPopup, handleClose } = useEmailVerificationGuard();
    useEffect(() => {
        const verifyLogin = async () => {
            try {
                const res = await fetch(`${DATABASE_URL}/ping-auth`, {
                    method: "GET",
                    credentials: "include",
                });

                if (res.status !== 204) {
                    router.replace("/auth");
                    return;
                  }

                setIsCheckingAuth(false);
            } catch (error) {
                console.error("❌ Auth error:", error);
                router.replace("/auth");
            }
        };

        verifyLogin();
    }, []);

    if (isCheckingAuth) {
        return (
            <div className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm z-50 flex items-center justify-center pointer-events-none">
                <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-yellow-400"></div>
            </div>
        );
    }

    return (
        <>
        <FeedbackPopup />
            {/* Email-not-verified popup */}
            <Popup show={showPopup} onClose={handleClose}>
                <h2 className="text-lg font-semibold">Account Not Verified</h2>
                <p className="mt-2">
                    Your account hasn't been verified yet. Please check your email for
                    the verification link.
                </p>
                <button
                    className="mt-4 px-4 py-2 rounded bg-blue-600 text-white"
                    onClick={handleClose}
                >
                    OK
                </button>
            </Popup>

            {/* Main app content */}
            <main className="px-20 py-16">
                <Scraper />
            </main>
        </>
    );
}
