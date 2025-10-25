"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import Notif from "@/components/ui/notif";

const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL!;

export default function ForgotPasswordPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [notif, setNotif] = useState<{ show: boolean; message: string; type: "success" | "error" | "info" }>({
        show: false,
        message: "",
        type: "success",
    });

    const showNotification = (message: string, type: "success" | "error" | "info" = "success") => {
        setNotif({ show: true, message, type });
        setTimeout(() => setNotif(prev => ({ ...prev, show: false })), 4000);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email.trim()) {
            showNotification("Please enter your email.", "error");
            return;
        }
        try {
            const res = await fetch(`${DATABASE_URL}/auth/forgot-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || "Failed to request password reset.");
            showNotification("A reset link has been sent to your email.", "success");
        } catch (err: any) {
            showNotification(err.message || "Something went wrong.", "error");
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-background text-foreground">
            <img
                src="/images/logo_horizontal.png"
                alt="SaaSquatch Leads Logo"
                className="w-96 mb-6"
            />
            <div className="w-full max-w-md bg-card rounded-xl shadow-md border border-border p-6">
                <h2 className="text-2xl font-bold mb-4">Reset Your Password</h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <Label htmlFor="fp-email">Email Address</Label>
                        <Input
                            id="fp-email"
                            type="email"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <Button type="submit" className="w-full">
                        Send Reset Link
                    </Button>
                </form>
                <div className="mt-4 text-center text-sm">
                    <a
                        href="/auth"
                        className="text-blue-600 hover:text-blue-800 underline"
                    >
                        Return to Sign In
                    </a>
                </div>
            </div>
            <Notif
                show={notif.show}
                message={notif.message}
                type={notif.type}
                onClose={() => setNotif(prev => ({ ...prev, show: false }))}
            />
        </div>
    );
}
