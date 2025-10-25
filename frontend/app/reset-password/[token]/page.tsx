"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import Notif from "@/components/ui/notif";

const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL!;

export default function ResetPasswordPage() {
    const { token } = useParams<{ token: string }>(); // Next 13+ `useParams()`
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
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
        setLoading(true);
        e.preventDefault();
        if (password.length < 8) {
            showNotification("Password must be at least 8 characters.", "error");
            return;
        }
        if (password !== confirmPassword) {
            showNotification("Passwords do not match.", "error");
            return;
        }
        try {
            const res = await fetch(`${DATABASE_URL}/auth/reset-password/${token}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ password }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || "Reset failed.");
            showNotification("Password reset successful! Redirecting…", "success");
            setTimeout(() => {
                router.push("/auth");
            }, 1500);
        } catch (err: any) {
            showNotification(err.message || "Something went wrong.", "error");
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-background text-foreground">
            <img
                src="/images/logo_horizontal.png"
                alt="SaaSquatch Leads Logo"
                className="w-96 mb-6"
            />
            <div className="w-full max-w-md bg-card rounded-xl shadow-md border border-border p-6">
                <h2 className="text-2xl font-bold mb-4">Set a New Password</h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <Label htmlFor="new-password">New Password</Label>
                        <Input
                            id="new-password"
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <div>
                        <Label htmlFor="confirm-new-password">Confirm New Password</Label>
                        <Input
                            id="confirm-new-password"
                            type="password"
                            placeholder="••••••••"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                    </div>
                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading ? "Resetting..." : "Reset Password"}
                    </Button>
                </form>
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
