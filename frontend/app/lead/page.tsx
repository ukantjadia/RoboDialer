// app/lead/page.tsx
import { redirect } from "next/navigation";

export default function LeadRedirectPage() {
    redirect("/lead/companies");
}
