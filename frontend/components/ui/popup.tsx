"use client";

import { ReactNode } from "react";

interface PopupProps {
    show: boolean;
    onClose: () => void;
    children: ReactNode;
}

export default function Popup({ show, onClose, children }: PopupProps) {
    if (!show) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center">
            <div className="bg-card text-card-foreground rounded-xl p-6 w-full max-w-md relative shadow-lg">
                <button
                    onClick={onClose}
                    className="absolute top-2 right-3 text-xl text-muted-foreground hover:text-foreground"
                >
                    &times;
                </button>
                {children}
            </div>
        </div>
    );
}
