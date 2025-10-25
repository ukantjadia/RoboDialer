"use client"

<<<<<<< HEAD
import { Building, Users, Mail, MessageSquare, Users2, Newspaper, DollarSign } from "lucide-react"
=======
import { Building, Users, Mail, MessageSquare, Users2, Newspaper, BotMessageSquare, CheckCircle, BarChart3 } from "lucide-react"
>>>>>>> 2e5892d59ddc5de81b3f0e8cd3feec3532ed95e7
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useRouter, usePathname } from "next/navigation"
import { useIsMobile } from "@/hooks/use-mobile"
import { NewTag } from "@/components/ui/new-tag"

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const router = useRouter()
  const pathname = usePathname()

  const isActive = (route: string) => pathname === route

  const handleNavigation = (route: string) => {
    router.push(route)
    // Close sidebar on mobile after navigation
    if (onClose) {
      onClose()
    }
  }

  return (
    <div className="w-64 border-r border-dark-border bg-dark-secondary h-full flex flex-col min-h-0 overflow-y-auto">
      <div className="flex flex-col gap-2 p-4">
        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover",
            isActive("/lead/companies") && "bg-dark-hover text-white"
          )}
          onClick={() => handleNavigation("/lead/companies")}
        >
          <Building className="h-5 w-5" />
          Companies
        </Button>

        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover",
            isActive("/lead/persons") && "bg-dark-hover text-white"
          )}
          onClick={() => handleNavigation("/lead/persons")}
        >
          <Users className="h-5 w-5" />
          Persons
        </Button>

        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover",
            isActive("/ai-news") && "bg-dark-hover text-white"
          )}
          onClick={() => handleNavigation("/ai-news")}
        >
          <Newspaper className="h-5 w-5" />
          AI News
        </Button>

        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover",
            isActive("/email-generator") && "bg-dark-hover text-white"
          )}
          onClick={() => handleNavigation("/email-generator")}
        >
          <Mail className="h-5 w-5" />
          Email Generator
        </Button>

        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover",
            isActive("/validators") && "bg-dark-hover text-white"
          )}
          onClick={() => handleNavigation("/validators")}
        >
          <CheckCircle className="h-5 w-5" />
          Validators
          <NewTag text="NEW" />
        </Button>

        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover opacity-50 cursor-not-allowed"
          )}
          disabled
        >
          <MessageSquare className="h-5 w-5" />
          LinkedIn Messenger
          <NewTag text="Soon" />
        </Button>

        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover opacity-50 cursor-not-allowed"
          )}
          disabled
        >
          <Users2 className="h-5 w-5" />
          Teams
          <NewTag text="Soon" />
        </Button>

        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover opacity-50 cursor-not-allowed"
          )}
          disabled
        >
          <BotMessageSquare className="h-5 w-5" />
          AI Web Scanner
          <NewTag text="Soon" />
        </Button>

        <Button
          variant="ghost"
          className={cn(
            "justify-start gap-2 text-gray-400 hover:text-white hover:bg-dark-hover opacity-50 cursor-not-allowed"
          )}
          disabled
        >
          <BarChart3 className="h-5 w-5" />
          Financial Analysis
          <NewTag text="Soon" />
        </Button>

      </div>
    </div>
  )
}
