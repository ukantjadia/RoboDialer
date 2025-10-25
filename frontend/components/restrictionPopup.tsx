"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

interface RestrictionPopupProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  message?: string;
  showUpgradeButton?: boolean;
}

export default function RestrictionPopup({
  isOpen,
  onClose,
  title = "Feature Restricted",
  message = "This feature is only accessible for Bronze tier and above. Please upgrade your plan to continue.",
  showUpgradeButton = true
}: RestrictionPopupProps) {
  const router = useRouter();

  const handleUpgrade = () => {
    onClose();
    router.push('/subscription');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md mx-4">
        <div className="text-center">
          <div className="text-6xl mb-4">🔒</div>
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            {title}
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {message}
          </p>
          <div className="flex justify-center space-x-3">
            <Button
              variant="outline"
              onClick={onClose}
              className="px-4 py-2"
            >
              OK
            </Button>
            {showUpgradeButton && (
              <Button
                onClick={handleUpgrade}
                className="px-4 py-2"
              >
                Upgrade Plans
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
