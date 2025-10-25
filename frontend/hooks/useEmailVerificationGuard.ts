// frontend/hooks/useEmailVerificationGuard.ts
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function useEmailVerificationGuard() {
  const router = useRouter();
  const [showPopup, setShowPopup] = useState(false);

  useEffect(() => {
    const userRaw = sessionStorage.getItem("user");
    if (!userRaw) {
      router.push("/auth");
      return;
    }

    try {
      const user = JSON.parse(userRaw);
      if (!user.is_email_verified) {
        // show the “not verified” popup instead of immediate redirect
        setShowPopup(true);
      }
    } catch (err) {
      console.error("Invalid session user data:", err);
      router.push("/auth");
    }
  }, [router]);

  const handleClose = () => {
    setShowPopup(false);
    router.push("/auth");
  };

  return { showPopup, handleClose };
}