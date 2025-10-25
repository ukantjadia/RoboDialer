"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import Notif from "@/components/ui/notif";
import { validateField, validateForm, FormErrors, FormData } from "@/lib/formValidation";
import Link from "next/link";
import FeedbackPopup from "@/components/FeedbackPopup";

const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL!;

const termsContent = (
  <div className="p-4 text-sm space-y-3">
    <h3 className="font-bold text-lg mb-2">SquatchLeads Terms &amp; Conditions</h3>
    <div className="text-xs text-muted-foreground mb-2">
      <strong>Operated by Caprae Capital Partners LLC</strong><br />
      <span>Last Updated: May 31, 2025</span>
    </div>
    <div>
      <strong>1. Acceptance of Terms</strong><br />
      By accessing or using <strong>SquatchLeads</strong> ("Service"), you agree to these Terms. Discontinue use if you do not accept all provisions.
    </div>
    <div>
      <strong>2. Service Description</strong><br />
      SquatchLeads is a SaaS platform operated by <strong>Caprae Capital Partners LLC</strong> that generates business leads ("Leads") via automated aggregation of publicly available data. Leads may include contact details, job titles, or company information.
    </div>
    <div>
      <strong>3. User Obligations</strong>
      <ul className="list-disc ml-5">
        <li><strong>Legality</strong>: Comply with all applicable laws (GDPR, CCPA, TCPA, CAN-SPAM) when using Leads.</li>
        <li><strong>Ethics</strong>: No spamming, harassment, fraud, or unauthorized data resale.</li>
        <li><strong>Verification</strong>: Independently validate Lead accuracy before use.</li>
        <li><strong>Account Security</strong>: You are responsible for all activities under your account.</li>
      </ul>
    </div>
    <div>
      <strong>4. Intellectual Property</strong>
      <ul className="list-disc ml-5">
        <li><strong>Service</strong>: All software, trademarks, and content are owned by <strong>Caprae Capital Partners LLC</strong>.</li>
        <li><strong>Leads</strong>: You receive a limited license to use purchased Leads for lawful purposes only.</li>
      </ul>
    </div>
    <div>
      <strong>5. Data &amp; Privacy</strong>
      <ul className="list-disc ml-5">
        <li><strong>Sources</strong>: Leads are derived from public sources; we claim no ownership of underlying data.</li>
        <li><strong>Your Responsibility</strong>: You must comply with privacy laws (e.g., obtain consent for outreach, honor opt-outs).</li>
        <li><strong>Your Data</strong>: Governed by our <a href="#" className="underline text-primary">Privacy Policy</a> (link to be added).</li>
      </ul>
    </div>
    <div>
      <strong>6. Payment &amp; Refunds</strong>
      <ul className="list-disc ml-5">
        <li><strong>Fees</strong>: Subscriptions are non-refundable unless legally required.</li>
        <li><strong>Renewals</strong>: Plans auto-renew unless canceled ≥48 hours before renewal.</li>
      </ul>
    </div>
    <div>
      <strong>7. Disclaimers</strong>
      <ul className="list-disc ml-5">
        <li><strong>"AS IS" Service</strong>: No warranties of accuracy, completeness, or fitness for purpose.</li>
        <li><strong>Liability Cap</strong>: Our maximum liability is limited to fees paid in the prior 6 months. We exclude indirect/consequential damages.</li>
      </ul>
    </div>
    <div>
      <strong>8. Termination</strong><br />
      We may suspend/terminate accounts for violations. All rights cease immediately upon termination.
    </div>
    <div>
      <strong>9. Amendments</strong><br />
      We reserve the right to modify these Terms. Continued use constitutes acceptance of updates.
    </div>
    <div>
      <strong>10. Governing Law</strong><br />
      Governed by Delaware law without regard to conflict of laws principles.
    </div>
    <div>
      <strong>11. Contact</strong><br />
      <span>Caprae Capital Partners LLC<br />
      611 N Brand Blvd<br />
      Glendale, CA 91203<br />
      United States<br />
      <strong>Email</strong>: partners@capraecapital.com</span>
    </div>
    <div className="border-t border-border pt-3 mt-3 text-xs text-muted-foreground">
      <strong>⚠️ Critical Legal Notes</strong><br />
      <span className="block mb-1">Caprae Capital Partners LLC advises:</span>
      <ol className="list-decimal ml-5 mb-1">
        <li>
          <strong>Consult an attorney</strong> to ensure compliance with:
          <ul className="list-disc ml-5">
            <li>Data privacy laws (CCPA for California residents, GDPR for EU leads)</li>
            <li>Anti-spam regulations (TCPA for calls/texts, CAN-SPAM for emails)</li>
            <li>Industry-specific rules (e.g., FINRA if used in financial prospecting)</li>
          </ul>
        </li>
        <li>
          <strong>Explicitly prohibit</strong> high-risk activities in your final T&amp;Cs (e.g., scraping social media, healthcare data).
        </li>
        <li>
          <strong>Include indemnification clauses</strong> to protect against user misuse of Leads.
        </li>
      </ol>
      <span className="block mt-1 italic">
        DISCLAIMER: This template is informational only and not legal advice. Caprae Capital Partners LLC assumes no liability for users' compliance with laws.
      </span>
    </div>
  </div>
);

const privacyContent = (
  <div className="p-4 text-sm space-y-3">
    <h3 className="font-bold text-lg mb-2">Privacy Policy</h3>
    <div className="text-xs text-muted-foreground mb-2">
      <strong>Operated by Caprae Capital Partners LLC</strong><br />
      <span>Last Updated: May 31, 2025</span>
    </div>
    <div>
      <strong>1. Information We Collect</strong>
      <ul className="list-disc ml-5">
        <li>Information you provide (e.g., registration, contact forms)</li>
        <li>Usage data (e.g., pages visited, IP address, browser type)</li>
        <li>Cookies and similar technologies</li>
      </ul>
    </div>
    <div>
      <strong>2. How We Use Information</strong>
      <ul className="list-disc ml-5">
        <li>To provide and improve our services</li>
        <li>To communicate with you</li>
        <li>To comply with legal obligations</li>
        <li>For analytics and security</li>
      </ul>
    </div>
    <div>
      <strong>3. Sharing of Information</strong>
      <ul className="list-disc ml-5">
        <li>We do not sell your personal information</li>
        <li>We may share with service providers or as required by law</li>
      </ul>
    </div>
    <div>
      <strong>4. Data Security</strong><br />
      We use reasonable measures to protect your data, but no system is 100% secure.
    </div>
    <div>
      <strong>5. Your Rights</strong>
      <ul className="list-disc ml-5">
        <li>You may request access, correction, or deletion of your data</li>
        <li>Contact us at partners@capraecapital.com for privacy requests</li>
      </ul>
    </div>
    <div>
      <strong>6. Changes to This Policy</strong><br />
      We may update this policy. Continued use of our service means you accept the revised policy.
    </div>
    <div>
      <strong>7. Contact</strong><br />
      Caprae Capital Partners LLC<br />
      611 N Brand Blvd<br />
      Glendale, CA 91203<br />
      United States<br />
      <strong>Email</strong>: partners@capraecapital.com
    </div>
  </div>
);


export default function AuthPage() {

    const [notif, setNotif] = useState({
        show: false,
        message: "",
        type: "success" as "success" | "error" | "info",
    });

    const [showTerms, setShowTerms] = useState(false);
    const [showPrivacy, setShowPrivacy] = useState(false);

    const showNotification = (message: string, type: "success" | "error" | "info" = "success") => {
        setNotif({ show: true, message, type });
        setTimeout(() => {
            setNotif(prev => ({ ...prev, show: false }));
        }, 3500);
    };

    const [isSignup, setIsSignup] = useState(false);
    const [formData, setFormData] = useState({
        username: "",
        email: "",
        linkedin: "",
        password: "",
        confirmPassword: "",
        gdpr: false,
        isStudent: false, // Added student checkbox
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { id, value, type, checked } = e.target;
        setFormData((prev) => ({
            ...prev,
            [id]: type === "checkbox" ? checked : value,
        }));
    };

    const [formErrors, setFormErrors] = useState<FormErrors>({});
    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
        const { id, value, type, checked } = e.target;
        const currentValue = type === "checkbox" ? checked.toString() : value;
        const error = validateField(id as keyof FormData, currentValue, {
            ...formData,
            [id]: type === "checkbox" ? checked : value,
        });
        setFormErrors(prev => ({ ...prev, [id]: error }));
    };

    const inputClass = (
        field: keyof typeof formErrors,
        base: string = "w-full"
    ) => `${base} ${formErrors[field] ? "border border-destructive outline-none ring-1 ring-destructive" : ""}`;
    

    const router = useRouter();

    // Function to check student email status
    const checkStudentEmail = async () => {
        try {
            const res = await fetch(`${DATABASE_URL}/api/auth/check-student-email`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
            });

            const result = await res.json();
            return { success: res.ok, data: result };
        } catch (error) {
            console.error("❌ Student email check error:", error);
            return { success: false, error: "Failed to check student email status" };
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const errors = validateForm(formData, isSignup);
        setFormErrors(errors);
        if (Object.keys(errors).length > 0) return;

        const endpoint = isSignup ? "/auth/register" : "/auth/login";
        const payload = isSignup ? {
            username: formData.username,
            email: formData.email,
            linkedin: formData.linkedin,
            password: formData.password,
            confirm_password: formData.confirmPassword,
            gdpr_accept: formData.gdpr,
            is_student: formData.isStudent, // Include student flag in payload
        } : {
            email: formData.email,
            password: formData.password,
        };

        try {
            const res = await fetch(`${DATABASE_URL}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify(payload),
            });

            // First check if response is JSON
            const contentType = res.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await res.text();
                throw new Error(`Expected JSON but got: ${text.substring(0, 100)}`);
            }

            const result = await res.json();

            if (!res.ok) {
                // Handle 401 specifically for login errors
                if (res.status === 401 && result.error) {
                    throw new Error(result.error);
                }
                throw new Error(result.message || `HTTP error! status: ${res.status}`);
            }

            if (result.user) {
                // Clear all storage before saving new user data
                localStorage.clear();
                sessionStorage.clear();
                
                // Save the user data
                sessionStorage.setItem("user", JSON.stringify(result.user));

                if (isSignup) {
                    try {
                        await fetch(`${DATABASE_URL}/auth/send-verification`, {
                            method: "POST",
                            credentials: "include",
                        });
                        
                        // Different messages based on student status
                        const verificationMessage = formData.isStudent 
                            ? "Your student account has been created successfully! Please verify your email to activate it."
                            : "Your account has been created. Please verify your email to activate it. A link has been sent to your email.";
                        
                        showNotification(verificationMessage, "info");

                        // If user checked "I am a student", check student email status after 2 seconds
                        if (formData.isStudent) {
                            setTimeout(async () => {
                                showNotification("Checking student email status...", "info");
                                
                                const studentCheck = await checkStudentEmail();
                                
                                if (studentCheck.success && studentCheck.data) {
                                    const { is_student, message } = studentCheck.data;
                                    
                                    if (is_student) {
                                        showNotification(message, "success");
                                    } else {
                                        showNotification(message, "error");
                                    }
                                } else {
                                    showNotification("Could not verify student status. Please contact support.", "error");
                                }
                            }, 2000); // 2 second delay to allow user data to be saved
                        }

                    } catch (err) {
                        console.error("❌ Failed to send verification email:", err);
                        showNotification("Account created, but failed to send verification email.", "error");
                    }
                } else {
                    showNotification("Successfully signed in!", "success");
                }

                setTimeout(() => {
                    const base = window.location.origin;
                    router.push(isSignup ? `${base}/subscription` : `${base}/`);
                }, formData.isStudent && isSignup ? 4000 : 100); // Delay navigation if student check is running
            }
        } catch (err: any) {
            console.error("❌ Registration/Login error:", err);
            showNotification(err.message || "Registration failed. Please check your information and try again.", "error");
        }
    };

    const toggleMode = (signup: boolean) => {
        setIsSignup(signup);
        setFormData({
            username: "",
            email: "",
            linkedin: "",
            password: "",
            confirmPassword: "",
            gdpr: false,
            isStudent: false, // Reset student checkbox
        });
        setFormErrors({});
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background text-foreground flex-col">
            <FeedbackPopup />
            {showTerms && (
                <div 
                className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
                >
                <div 
                    className="bg-card rounded-lg shadow-lg max-w-md w-full border border-border"
                    onClick={e => e.stopPropagation()}
                >
                    <div className="max-h-[60vh] overflow-y-auto">
                    {termsContent}
                    </div>
                    <div className="p-4 border-t border-border">
                    <Button 
                        className="w-full" 
                        onClick={() => setShowTerms(false)}
                    >
                        Close
                    </Button>
                    </div>
                </div>
                </div>
            )}
            {showPrivacy && (
                <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
                <div
                    className="bg-card rounded-lg shadow-lg max-w-md w-full border border-border"
                    onClick={e => e.stopPropagation()}
                >
                    <div className="max-h-[60vh] overflow-y-auto">
                    {privacyContent}
                    </div>
                    <div className="p-4 border-t border-border">
                    <Button className="w-full" onClick={() => setShowPrivacy(false)}>
                        Close
                    </Button>
                    </div>
                </div>
                </div>
            )}
            <img
                src="/images/logo_horizontal.png"
                alt="SaaSquatch Leads Logo"
                className="w-96 mx-auto mb-6"
            />
            <div className="w-full max-w-md bg-card text-card-foreground rounded-xl shadow-md border-8 border-border">
                <div className="flex">
                    <button
                        className={`w-1/2 py-3 text-sm font-semibold transition-colors ${!isSignup
                            ? "bg-background text-foreground border-b-2 border-primary"
                            : "bg-muted text-muted-foreground"
                            }`}
                        onClick={() => toggleMode(false)}
                    >
                        Sign In
                    </button>
                    <button
                        className={`w-1/2 py-3 text-sm font-semibold transition-colors ${isSignup
                            ? "bg-background text-foreground border-b-2 border-primary"
                            : "bg-muted text-muted-foreground"
                            }`}
                        onClick={() => toggleMode(true)}
                    >
                        Sign Up
                    </button>
                </div>

                <div className="p-6 space-y-4">
                    <form className="space-y-4" onSubmit={handleSubmit}>
                        {isSignup && (
                            <div>
                                <Label htmlFor="username">Username</Label>
                                <Input
                                    id="username"
                                    placeholder="Username"
                                    value={formData.username}
                                    onChange={handleChange}
                                    onBlur={handleBlur}
                                    className={inputClass("username")}
                                />
                                {formErrors.username && (
                                    <p className="text-sm text-red-500 mt-1">{formErrors.username}</p>
                                )}
                            </div>
                        )}

                        <div>
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="Email"
                                value={formData.email}
                                onChange={handleChange}
                                onBlur={handleBlur}
                                className={inputClass("email")}
                            />
                            {formErrors.email && (
                                <p className="text-sm text-red-500 mt-1">{formErrors.email}</p>
                            )}
                        </div>

                        {/* Student checkbox - positioned after email field */}
                        {isSignup && (
                            <div className="flex items-start space-x-2 text-sm bg-muted/50 p-3 rounded-lg border border-border">
                                <input
                                    type="checkbox"
                                    id="isStudent"
                                    checked={formData.isStudent}
                                    onChange={handleChange}
                                    className={inputClass("isStudent", "mt-1 accent-primary")}
                                />
                                <label htmlFor="isStudent" className="text-foreground font-medium">
                                    I am a student
                                    <span className="block text-xs text-muted-foreground mt-1 font-normal">
                                        Check this if you're using a school/university email domain to get student benefits
                                    </span>
                                </label>
                            </div>
                        )}

                        {isSignup && (
                            <div>
                                <Label htmlFor="linkedin">LinkedIn Profile (Optional)</Label>
                                <Input
                                    id="linkedin"
                                    type="url"
                                    placeholder="https://linkedin.com/in/your-profile"
                                    value={formData.linkedin}
                                    onChange={handleChange}
                                    onBlur={handleBlur}
                                    className={inputClass("linkedin")}
                                />
                                {formErrors.linkedin && (
                                    <p className="text-sm text-red-500 mt-1">{formErrors.linkedin}</p>
                                )}
                            </div>
                        )}

                        <div>
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                placeholder="Password"
                                value={formData.password}
                                onChange={handleChange}
                                onBlur={handleBlur}
                                className={inputClass("password")}
                            />
                            {formErrors.password && (
                                <p className="text-sm text-red-500 mt-1">{formErrors.password}</p>
                            )}
                        </div>

                        {/* Show "Forgot password?" only when NOT in Sign-Up mode */}
                        {!isSignup && (
                            <div className="mt-1 text-right">
                                <Link
                                    href="/forgot-password"
                                    className="text-sm text-blue-600 hover:text-blue-800 underline"
                                >
                                    Forgot password?
                                </Link>
                            </div>
                        )}

                        {isSignup && (
                            <div>
                                <Label htmlFor="confirmPassword">Confirm Password</Label>
                                <Input
                                    id="confirmPassword"
                                    type="password"
                                    placeholder="Repeat password"
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    onBlur={handleBlur}
                                    className={inputClass("confirmPassword")}
                                />
                                {formErrors.confirmPassword && (
                                    <p className="text-sm text-red-500 mt-1">{formErrors.confirmPassword}</p>
                                )}
                            </div>
                        )}

                        {isSignup && (
                        <div className="flex items-start space-x-2 text-sm">
                            <input
                            type="checkbox"
                            id="gdpr"
                            checked={formData.gdpr}
                            onChange={handleChange}
                            onBlur={handleBlur}
                            className={inputClass("gdpr", "mt-1")}
                            />
                            <label htmlFor="gdpr" className="text-muted-foreground">
                            I accept the{" "}
                            <button
                                type="button"
                                className="text-primary underline"
                                onClick={() => setShowTerms(true)}
                            >
                                terms and conditions
                            </button>{" "}
                            and the{" "}
                            <button
                                type="button"
                                className="text-primary underline"
                                onClick={() => setShowPrivacy(true)}
                            >
                                privacy policy
                            </button>
                            </label>
                        </div>
                        )}
                        {formErrors.gdpr && (
                            <p className="text-sm text-red-500 mt-1">{formErrors.gdpr}</p>
                        )}

                        <Button type="submit" className="w-full mt-2">
                            {isSignup ? "Sign Up" : "Sign In"}
                        </Button>
                    </form>
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