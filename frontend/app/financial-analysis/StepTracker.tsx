import { CheckCircle } from "lucide-react";

const steps = [
  "Upload",
  "Map Data",
  "Choose Analysis",
  "Dashboard"
];

export default function StepTracker({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center justify-center mb-4 w-full">
      <div className="flex items-center justify-center mx-auto max-w-2xl">
        {steps.map((step, idx) => (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`flex items-center justify-center rounded-full w-8 h-8 text-sm font-bold
                  ${idx < currentStep
                    ? "bg-green-500 text-white"
                    : idx === currentStep
                    ? "bg-green-600 text-white"
                    : "bg-dark-border text-gray-400"}
                `}
              >
                {idx < currentStep ? <CheckCircle className="w-5 h-5" /> : idx + 1}
              </div>
              <span className={`mt-2 text-xs font-medium ${idx <= currentStep ? "text-green-600" : "text-gray-400"}`}>
                {step}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`h-1 w-12 mx-2 rounded
                  ${idx < currentStep ? "bg-green-500" : "bg-dark-border"}
                `}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}