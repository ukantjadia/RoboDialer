import { CheckIcon } from "lucide-react"
import { cn } from "@/lib/utils"

export function Stepper({ steps, currentStep }) {
  return (
    <div className="w-full mb-8">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={index} className="flex flex-col items-center relative">
            <div
              className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center border-2 z-10",
                index < currentStep
                  ? "bg-teal-500 border-teal-500 text-white"
                  : index === currentStep
                    ? "border-teal-500 text-teal-500"
                    : "border-gray-300 text-gray-300",
              )}
            >
              {index < currentStep ? <CheckIcon className="h-5 w-5" /> : <span>{index + 1}</span>}
            </div>
            <div className="text-center mt-2">
              <div className={cn("text-sm font-medium", index <= currentStep ? "text-teal-500" : "text-gray-400")}>
                {step.title}
              </div>
              <div className="text-xs text-muted-foreground hidden md:block">{step.description}</div>
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "absolute top-5 left-10 w-full h-0.5",
                  index < currentStep ? "bg-teal-500" : "bg-gray-200",
                )}
                style={{ width: "calc(100% - 2.5rem)" }}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
