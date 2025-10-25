"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { loadStripe } from "@stripe/stripe-js";
import FeedbackPopup from "@/components/FeedbackPopup";
import { CheckCircle2, ArrowLeft } from 'lucide-react';

type Plan = {
    id: string;
    plan_name: string;
    price: number | string;
    lead_quota: number | string;
    cost_per_lead?: number | string;
    description?: string;
    has_ai_features?: boolean;
    features: string[] | string;
    initial_credits?: number | string;
    style?: string;
    recommended?: boolean;
    link?: string;
    isAnnual: boolean;
    monthly_price?: number | string;
};

const STRIPE = process.env.NEXT_PUBLIC_STRIPE_CODE!;
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;
const DATABASE_URL_NOAPI = DATABASE_URL?.replace(/\/api\/?$/, "");

export default function SubscriptionPage() {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [isAnnual, setIsAnnual] = useState(false);
    const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
    const [outreachPlan, setOutreachPlan] = useState<Plan | null>(null);
    const planOrder = [
        "bronze",
        "silver",
        "gold",
        "platinum",
        "enterprise",         // monthly
        "bronze_annual",
        "silver_annual",
        "gold_annual",
        "platinum_annual",
        "enterprise_annual"   // annual
    ];

    useEffect(() => {
        const fetchUpgradePlans = async () => {
            try {
                const cached = localStorage.getItem("upgradePlans");
                if (cached) {
                    const parsed = JSON.parse(cached);
                    setPlans(parsed);

                    const outreachRaw = localStorage.getItem("outreachPlan");
                    if (outreachRaw) {
                        setOutreachPlan(JSON.parse(outreachRaw));
                    }
                    return;
                }

                const res = await fetch(`${DATABASE_URL}/plans/all`, {
                    method: "GET",
                    credentials: "include",
                });

                const data = await res.json();
                const userRole = data.user_role?.toLowerCase() || "";
                const isStudent = userRole === "student";

                const studentPlans = isStudent
                    ? (data.plans || [])
                        .filter((plan: any) =>
                            plan.plan_name.toLowerCase().includes("student")
                        )
                        .map((plan: any) => ({
                            id: plan.plan_name.toLowerCase().replace(/\s+/g, "_"),
                            plan_name: plan.plan_name,
                            price: plan.monthly_price,
                            lead_quota: plan.monthly_lead_quota,
                            features: Array.isArray(plan.features)
                                ? plan.features
                                : JSON.parse(plan.features || "[]"),
                            isAnnual: false,
                        }))
                    : [];

                const parsedPlans = (data.plans || []).map((plan: any) => ({
                    ...plan,
                    features: Array.isArray(plan.features)
                        ? plan.features
                        : JSON.parse(plan.features || "[]"),
                }));
                // Remap annual plans to use features from their monthly counterparts
                parsedPlans.forEach((plan: any) => {
                    if (plan.plan_name && plan.plan_name.toLowerCase().endsWith('_annual')) {
                        const baseName = plan.plan_name.replace(/_Annual$/i, '');
                        const monthlyPlan = parsedPlans.find((p: any) => p.plan_name === baseName);
                        if (monthlyPlan) {
                            plan.features = monthlyPlan.features;
                        }
                    }
                });

                const outreachPlanParsed = parsedPlans.find((plan: any) => plan.plan_name.toLowerCase().includes("pro call outreach"));
                if (outreachPlanParsed) {
                    setOutreachPlan(outreachPlanParsed);
                    localStorage.setItem("outreachPlan", JSON.stringify(outreachPlanParsed));
                }

                const allPlans: Plan[] = [];
                parsedPlans.forEach((plan: any) => {
                    const rawPlanName = plan.plan_name.toLowerCase();
                    const planId = rawPlanName.replace(/\s+/g, "_");
                    const isEnterprise = rawPlanName.includes("enterprise");
                    const isAnnualPlan = planId.includes("annual");
                    const isOutreachPlan = rawPlanName.includes("pro call outreach");

                    const baseParsedPlan = {
                        id: planId,
                        plan_name: plan.plan_name,
                        cost_per_lead: plan.cost_per_lead,
                        description: plan.description,
                        has_ai_features: plan.has_ai_features,
                        features: Array.isArray(plan.features)
                            ? plan.features
                            : JSON.parse(plan.features || "[]"),
                        initial_credits: plan.initial_credits,
                        style: rawPlanName.includes("gold")
                            ? "default"
                            : rawPlanName.includes("free")
                                ? "secondary"
                                : "outline",
                        recommended: plan.recommended ?? rawPlanName.includes("gold"),
                        link:
                            plan.link || (isEnterprise ? "https://www.saasquatchleads.com/" : undefined),
                    };

                    if (isOutreachPlan) {
                        allPlans.push({
                            ...baseParsedPlan,
                            id: "call_outreach",
                            price: plan.monthly_price,
                            lead_quota: plan.monthly_lead_quota,
                            isAnnual: false,
                        });
                    } else if (isEnterprise) {
                        allPlans.push({
                            ...baseParsedPlan,
                            id: "enterprise",
                            price: plan.monthly_price,
                            lead_quota: plan.monthly_lead_quota,
                            isAnnual: false,
                        });

                        allPlans.push({
                            ...baseParsedPlan,
                            id: "enterprise_annual",
                            price: plan.annual_price,
                            lead_quota: plan.annual_lead_quota,
                            isAnnual: true,
                        });
                    } else {
                        allPlans.push({
                            ...baseParsedPlan,
                            id: planId,
                            price: isAnnualPlan ? plan.annual_price : plan.monthly_price,
                            lead_quota: isAnnualPlan
                                ? plan.annual_lead_quota
                                : plan.monthly_lead_quota,
                            isAnnual: isAnnualPlan,
                        });
                    }
                });

                const sortedPlans = allPlans.sort(
                    (a, b) =>
                        planOrder.indexOf(a.id.toLowerCase()) -
                        planOrder.indexOf(b.id.toLowerCase())
                );

                const combined = [...sortedPlans, ...studentPlans];
                setPlans(combined);
                localStorage.setItem("upgradePlans", JSON.stringify(combined));
            } catch (err) {
                console.error("❌ Failed to fetch upgrade plans:", err);
            }
        };

        fetchUpgradePlans();
    }, []);      

    useEffect(() => {
        if (plans.length > 0) {
            const defaultId = isAnnual ? 'bronze_annual' : 'bronze';
            const found = plans.find(p => p.id === defaultId);
            if (found) setSelectedPlan(defaultId);
        }
    }, [plans, isAnnual]);

    const handleSelectPlan = async (planId: string) => {
        if (planId === "free") {
            window.location.href = "/";
            return;
        }

        try {
            // console.log("Stripe key:", process.env.NEXT_PUBLIC_STRIPE_CODE);
            const res = await fetch(`${DATABASE_URL_NOAPI}/create-checkout-session`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "include",
                body: JSON.stringify({ plan_type: planId }),
            });

            const data = await res.json();
            if (res.ok && data.sessionId) {
                const stripe = await loadStripe(STRIPE);
                if (stripe) {
                    console.log("Stripe Mode:", process.env.STRIPE_MODE);
                    console.log("Session ID:", data.sessionId);
                    await stripe.redirectToCheckout({ sessionId: data.sessionId });
                } else {
                    alert("Stripe.js failed to load.");
                }
            } else {
                alert(data.error || "Failed to create checkout session");
            }
        } catch (err) {
            console.error("Error creating checkout session:", err);
            alert("Could not initiate payment. Try again later.");
        }
    };

    const allFeatures = getAllFeatures(plans, false);
    const tieredPlans = getTieredPlans(plans, isAnnual);
    const selectedIdx = tieredPlans.findIndex(p => p.id === selectedPlan);
    function displayPlanName(plan: Plan): string {
        if (plan.id === 'student_monthly') return 'Student';
        if (plan.id === 'student_semester') return 'Student Semester';
        return plan.id.replace('_annual', '').replace(/\b\w/g, (l: string) => l.toUpperCase());
    }

    // Add a helper to get the color class for each plan
    function getPlanColorClass(plan: Plan): string {
        const id = plan.id.replace('_annual', '');
        if (id === 'bronze') return 'text-amber-600';
        if (id === 'silver') return 'text-gray-400';
        if (id === 'gold') return 'text-yellow-500';
        if (id === 'platinum') return 'text-purple-500';
        return '';
    }

    // Assume you have a boolean isStudent from user context or API
    const isStudent = typeof window !== 'undefined' && localStorage.getItem('userRole') === 'student';

    let filteredPlans = plans;
    if (isStudent) {
        if (isAnnual) {
            filteredPlans = plans.filter(p => p.id === 'student_annual');
        } else {
            filteredPlans = plans.filter(p => p.id === 'student_monthly' || p.id === 'student_semester');
        }
        // Optionally, include the free plan:
        // filteredPlans = [...filteredPlans, ...plans.filter(p => p.id === 'free')];
    }

    // Helper to detect student plan
    function isStudentPlan(plan: Plan): boolean {
        return plan.id?.startsWith('student');
    }
    return (
        <div className="animate-fade-in-down min-h-screen pt-32 pb-16 px-4 sm:px-6 lg:px-8 bg-background text-foreground flex flex-col items-center relative">
            {/* Back to Home Arrow */}
            <a href="/" className="absolute left-4 top-4 flex items-center gap-2 text-muted-foreground hover:text-primary transition-colors p-3 rounded-lg">
                <ArrowLeft className="w-8 h-8" />
                <span className="hidden sm:inline text-lg font-semibold">Home</span>
            </a>
            <FeedbackPopup />
            <div className="max-w-4xl w-full mx-auto space-y-8">
                {/* Header */}
                <div className="text-center">
                    <h2 className="text-5xl font-extrabold tracking-tight">Choose Your Plan</h2>
                    <p className="text-lg text-muted-foreground mt-4 max-w-2xl mx-auto">
                        No contracts. No surprise fees.
                    </p>
                </div>

                {/* Toggle */}
                <div className="flex justify-center items-center gap-4">
                    <Button variant={!isAnnual ? "default" : "outline"} onClick={() => setIsAnnual(false)}>Monthly</Button>
                    <Button variant={isAnnual ? "default" : "outline"} onClick={() => setIsAnnual(true)} className="ml-2">Annual</Button>
                </div>

                {/* Plans and Details Side by Side */}
                <div className="flex flex-col md:flex-row gap-8 w-full min-h-[32rem] items-stretch">
                    {/* Plans as vertical radio cards */}
                    <div className="w-full md:w-1/2 bg-muted rounded-2xl shadow-lg p-8 flex flex-col gap-8 flex-1 justify-center">
                        {filteredPlans
                            .filter(plan => plan.id !== "free" && plan.id !== "enterprise" && plan.id !== "enterprise_annual" && plan.id !== "call_outreach" && plan.isAnnual === isAnnual)
                            .map(plan => (
                                <label
                                    key={plan.id}
                                    className={`flex items-center justify-between py-6 px-4 rounded-xl border-2 cursor-pointer transition-all ${selectedPlan === plan.id ? "border-primary bg-primary/10" : "border-border bg-background"}`}
                                    onClick={() => plan.id !== "enterprise" && setSelectedPlan(plan.id)}
                                >
                                    <div>
                                        <div className={`font-bold text-xl ${selectedPlan === plan.id ? getPlanColorClass(plan) : ''}`}>{displayPlanName(plan)}</div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <span className="text-2xl font-extrabold">${typeof plan.price === "number" ? plan.price : plan.price}</span>
                                        <span className="text-muted-foreground text-base">{plan.id === 'student_semester' ? '/semester' : isAnnual ? '/year' : '/month'}</span>
                                        <input
                                            type="radio"
                                            name="plan"
                                            checked={selectedPlan === plan.id}
                                            onChange={() => setSelectedPlan(plan.id)}
                                            className="ml-4 accent-primary w-6 h-6"
                                            onClick={e => e.stopPropagation()}
                                        />
                                    </div>
                                </label>
                            ))}
                    </div>

                    {/* Plan Details Box */}
                    <div className="w-full md:w-1/2 bg-muted/70 rounded-2xl shadow-lg p-8 flex flex-col gap-4 min-h-[300px] flex-1">
                        {(() => {
                            // Always get the selected plan from the full plans array
                            const plan = plans.find(p => p.id === selectedPlan);
                            if (!plan) return <div className="text-muted-foreground">Select a plan to see details.</div>;

                            // If the selected plan is a student plan, show only its own features
                            if (plan.id.startsWith('student')) {
                                return (
                                    <>
                                        <div className={`text-3xl font-bold mb-4 ${getPlanColorClass(plan)}`}>{displayPlanName(plan)}</div>
                                        {plan.initial_credits !== undefined && (
                                            <div className="mb-2 text-lg font-semibold text-primary">Credits: <span className="font-bold text-foreground">{plan.initial_credits}</span></div>
                                        )}
                                        <ul className="space-y-3">
                                            {(Array.isArray(plan.features) ? plan.features : []).map((feat, i) => (
                                                <li key={i} className="flex items-center gap-2 text-lg">
                                                    <CheckCircle2 className="text-green-500 w-5 h-5" />
                                                    <span className="text-foreground">{feat}</span>
                                                </li>
                                            ))}
                                        </ul>
                                        <Button
                                            className="mt-8 px-8 py-3 text-lg"
                                            disabled={!selectedPlan}
                                            onClick={() => {
                                                if (selectedPlan) handleSelectPlan(selectedPlan);
                                            }}
                                        >
                                            Continue
                                        </Button>
                                    </>
                                );
                            }

                            // For normal plans, use the cumulative/tiered checklist logic (existing)
                            const includedPlans = tieredPlans.slice(0, selectedIdx + 1);
                            const includedFeatures = new Set();
                            includedPlans.forEach(p => (Array.isArray(p.features) ? p.features : []).forEach(f => includedFeatures.add(f)));
                            return (
                                <>
                                    <div className={`text-3xl font-bold mb-4 ${getPlanColorClass(plan)}`}>{displayPlanName(plan)}</div>
                                    {plan.initial_credits !== undefined && (
                                        <div className="mb-2 text-lg font-semibold text-primary">Credits: <span className="font-bold text-foreground">{plan.initial_credits}</span></div>
                                    )}
                                    <ul className="space-y-3">
                                        {allFeatures.map((feat, i) => (
                                            <li key={i} className="flex items-center gap-2 text-lg">
                                                {includedFeatures.has(feat) ? (
                                                    <CheckCircle2 className="text-green-500 w-5 h-5" />
                                                ) : (
                                                    <span className="inline-block w-5 h-5 border border-muted-foreground rounded-full" />
                                                )}
                                                <span className={includedFeatures.has(feat) ? "text-foreground" : "text-muted-foreground line-through"}>{feat}</span>
                                            </li>
                                        ))}
                                    </ul>
                                    {plan.id === "enterprise" && (
                                        <Button className="mt-4" onClick={() => window.location.href = "/contact"}>Contact Us</Button>
                                    )}
                                    {plan.id !== "enterprise" && (
                                        <Button
                                            className="mt-8 px-8 py-3 text-lg"
                                            disabled={!selectedPlan}
                                            onClick={() => {
                                                if (selectedPlan) handleSelectPlan(selectedPlan);
                                            }}
                                        >
                                            Continue
                                        </Button>
                                    )}
                                </>
                            );
                        })()}
                    </div>
                </div>


                {outreachPlan && (
                    <div className="mt-12 flex justify-center">
                        <div className="w-full max-w-xl bg-gradient-to-r from-blue-900 via-blue-700 to-blue-500 border-4 border-primary rounded-3xl shadow-2xl p-8 flex flex-col items-center text-white">
                            <div className="text-3xl font-extrabold mb-2 tracking-wide">{outreachPlan.plan_name}</div>
                            <div className="text-2xl font-bold">
                              ${typeof outreachPlan.monthly_price === "number" ? outreachPlan.monthly_price : Number(outreachPlan.monthly_price)}
                              <span className="text-lg font-normal"> for 25 hours</span>
                            </div>
                            <ul className="space-y-3 mb-6 w-full max-w-md">
                                {(Array.isArray(outreachPlan.features) ? outreachPlan.features : []).map((feat: string, i: number) => (
                                    <li key={i} className="flex items-center gap-2 text-lg">
                                        <CheckCircle2 className="text-green-300 w-5 h-5" />
                                        <span>{feat}</span>
                                    </li>
                                ))}
                            </ul>
                            <Button className="rounded-full px-8 py-3 text-lg font-bold bg-white text-blue-900 hover:bg-blue-100" onClick={() => handleSelectPlan(outreachPlan.id)}>
                                {outreachPlan.plan_name}
                            </Button>
                        </div>
                    </div>
                )}

                {(() => {
                    const enterprisePlan = plans.find(plan => plan.id === (isAnnual ? 'enterprise_annual' : 'enterprise'));
                    if (!enterprisePlan) return null;
                    return (
                        <div className="mt-12 flex justify-center">
                            <div className="w-full max-w-xl bg-gradient-to-r from-gray-700 via-gray-500 to-gray-300 border-4 border-gray-400 rounded-3xl shadow-2xl p-8 flex flex-col items-center text-white">
                                <div className="text-3xl font-extrabold mb-2 tracking-wide">{enterprisePlan.plan_name}</div>
                                <div className="text-lg mb-4 text-gray-200">{enterprisePlan.description}</div>
                                <ul className="space-y-3 mb-6 w-full max-w-md">
                                    {(Array.isArray(enterprisePlan.features) ? enterprisePlan.features : []).map((feat: string, i: number) => (
                                        <li key={i} className="flex items-center gap-2 text-lg">
                                            <CheckCircle2 className="text-green-300 w-5 h-5" />
                                            <span>{feat}</span>
                                        </li>
                                    ))}
                                </ul>
                                <Button className="rounded-full px-8 py-3 text-lg font-bold bg-white text-gray-900 hover:bg-gray-100" onClick={() => window.location.href = '/contact'}>
                                    Contact Us
                                </Button>
                            </div>
                        </div>
                    );
                })()}
            </div>
        </div>
    );
}

function getAllFeatures(plans: Plan[], isAnnual: boolean): string[] {
    const filtered = plans.filter(
        (p: Plan) =>
            p.id !== 'free' &&
            p.id !== 'enterprise' &&
            p.id !== 'call_outreach' &&
            !p.id.startsWith('student') &&
            p.isAnnual === isAnnual
    );
    const features: string[] = [];
    filtered.forEach((plan: Plan) => {
        (Array.isArray(plan.features) ? plan.features : []).forEach((f: string) => {
            if (!features.includes(f)) features.push(f);
        });
    });
    return features;
}

function getTieredPlans(plans: Plan[], isAnnual: boolean): Plan[] {
    const order = ['bronze', 'silver', 'gold', 'platinum'];
    return order.map((tier: string) => plans.find((p: Plan) => (isAnnual ? p.id === `${tier}_annual` : p.id === tier))).filter(Boolean) as Plan[];
}      