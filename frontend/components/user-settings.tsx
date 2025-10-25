"use client";
/* eslint-disable @next/next/no-img-element */
import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import Notif from "@/components/ui/notif"; // adjust path if needed
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;
const DATABASE_URL_NOAPI = DATABASE_URL?.replace(/\/api\/?$/, "");
type SettingsPageProps = {
    isEditing: boolean;
    setIsEditing: React.Dispatch<React.SetStateAction<boolean>>;
};

type User = {
    created_at: string;
    email: string;
    is_active: boolean;
    role: string;
    tier: string;
    user_id: string;
    username: string;
    linkedin_url?: string;
};

export default function SettingsPage({ isEditing, setIsEditing }: SettingsPageProps) {
    const [user, setUser] = useState<User | null>(null);
    const [username, setUsername] = useState("");
    const [linkedin, setLinkedin] = useState("");
    const [email, setEmail] = useState("");
    const [oldPassword, setOldPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [notif, setNotif] = useState<{
        show: boolean;
        message: string;
        type: "success" | "error";
    }>({ show: false, message: "", type: "success" });

    useEffect(() => {
        const sessionUser = sessionStorage.getItem("user");
        if (sessionUser) {
            const parsedUser: User = JSON.parse(sessionUser);
            setUser(parsedUser);
            setUsername(parsedUser.username);
            setEmail(parsedUser.email);
            setLinkedin(parsedUser.linkedin_url ?? "");
        }
    }, []);

    const handleManageSubscription = async () => {
        try {
            window.location.href = `${DATABASE_URL_NOAPI}/customer_portal`;
        } catch (error) {
            setNotif({
                show: true,
                message: "An error occurred while opening the billing portal.",
                type: "error",
            });
        }
    };

    const handlePauseSubscription = async () => {
        try {
            window.location.href = `${DATABASE_URL_NOAPI}/pause_subscription`;
        } catch (error) {
            setNotif({
                show: true,
                message: "An error occured while loading page",
                type: "error"
            });
        }
    };

    if (!user) return null;

    return (
        <div className="mx-auto max-w-4xl space-y-8 px-4 py-10">
            <div>
                <h1 className="text-4xl font-bold">User Settings</h1>
            </div>

            {/* PERSONAL INFORMATION */}
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <h2 className="text-lg font-semibold">Your Profile</h2>
                    <div className="flex gap-2">
                        {user?.tier.toLowerCase() !== "free" && (
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button size="sm" className="text-sm">
                                        Subscription
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            className="h-4 w-4"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                        >
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                        </svg>
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent>
                                    <DropdownMenuItem onClick={handleManageSubscription}>
                                        Manage subscription
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={handlePauseSubscription}>
                                        Pause subscription
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        )}
                        <Button
                            size="sm"
                            onClick={() => setIsEditing((prev: boolean) => !prev)}
                            className="text-sm"
                        >
                            {isEditing ? "Cancel" : "Edit Profile"}
                        </Button>
                    </div>
                </CardHeader>

                <CardContent className="space-y-6">
                    {/* Name + Email grid */}
                    <div className="grid gap-6 md:grid-cols-2">
                        <div className="flex flex-col gap-1.5">
                            <Label htmlFor="name">Name</Label>
                            <Input
                                id="name"
                                value={username}
                                readOnly={!isEditing}
                                onChange={(e) => setUsername(e.target.value)}
                                className={!isEditing ? "border-transparent bg-muted cursor-default" : ""}
                            />
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                readOnly={!isEditing}
                                className={!isEditing ? "border-transparent bg-muted cursor-default" : ""}
                            />
                        </div>
                    </div>

                    {/* LinkedIn Profile Input */}
                    <div className="flex flex-col gap-1.5">
                        <Label htmlFor="linkedin">LinkedIn Profile</Label>
                        <Input
                            id="linkedin"
                            placeholder="https://linkedin.com/in/..."
                            value={linkedin}
                            onChange={(e) => setLinkedin(e.target.value)}
                            readOnly={!isEditing}
                            className={!isEditing ? "border-transparent bg-muted cursor-default" : ""}
                        />
                        <p className="text-sm text-muted-foreground">
                            Add your LinkedIn profile URL to help others connect with you
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* CHANGE PASSWORD SECTION (Only visible in edit mode) */}
            {isEditing && (
                <Card>
                    <CardHeader>
                        <h2 className="text-lg font-semibold">Change Password</h2>
                    </CardHeader>

                    <CardContent>
                        <form className="grid gap-6 md:grid-cols-3">
                            <div className="flex flex-col gap-1.5">
                                <Label htmlFor="oldPassword">Old Password</Label>
                                <Input
                                    id="oldPassword"
                                    type="password"
                                    placeholder="Enter your old password"
                                    value={oldPassword}
                                    onChange={(e) => setOldPassword(e.target.value)}
                                />
                            </div>

                            <div className="flex flex-col gap-1.5">
                                <Label htmlFor="newPassword">New Password</Label>
                                <Input
                                    id="newPassword"
                                    type="password"
                                    placeholder="Enter new password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                />
                            </div>

                            <div className="flex flex-col gap-1.5">
                                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                                <Input
                                    id="confirmPassword"
                                    type="password"
                                    placeholder="Re-enter new password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                />
                            </div>
                        </form>
                    </CardContent>

                </Card>
            )}

            {/* SAVE BUTTON (Only in edit mode) */}
            {isEditing && (
                <Button
                    className="md:col-span-3 w-full"
                    type="button"
                    onClick={async () => {
                        if (newPassword && newPassword !== confirmPassword) {
                            setNotif({
                                show: true,
                                message: "New passwords do not match.",
                                type: "error",
                            });
                            return;
                        }

                        const payload: any = {
                            username,
                            email,
                            linkedin_url: linkedin,
                        };

                        if (newPassword) {
                            payload.password = newPassword;
                        }

                        try {
                            const res = await fetch(`${DATABASE_URL}/auth/update_user`, {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json",
                                },
                                credentials: "include",
                                body: JSON.stringify(payload),
                            });

                            const data = await res.json();

                            if (res.ok) {
                                setNotif({
                                    show: true,
                                    message: "Profile updated successfully!",
                                    type: "success",
                                });
                                sessionStorage.setItem("user", JSON.stringify(data.user));
                                setUser(data.user);
                                setIsEditing(false);
                            } else {
                                setNotif({
                                    show: true,
                                    message: "Update failed: " + (data.error || "Unknown error"),
                                    type: "error",
                                });
                            }
                        } catch (error) {
                            console.error("Update error:", error);
                            setNotif({
                                show: true,
                                message: "An error occurred while updating.",
                                type: "error",
                            });
                        }
                    }}
                >
                    Save Changes
                </Button>
            )}
            <Notif
                show={notif.show}
                message={notif.message}
                type={notif.type}
                onClose={() => setNotif((prev) => ({ ...prev, show: false }))}
            />
        </div>
    );
}