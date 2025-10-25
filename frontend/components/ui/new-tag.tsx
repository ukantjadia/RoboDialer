import { cn } from "@/lib/utils"

interface NewTagProps {
  className?: string
  text?: string
}

export function NewTag({ className, text = "NEW" }: NewTagProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-medium bg-red-500 text-white rounded-full ml-auto",
        className
      )}
    >
      {text}
    </span>
  )
} 