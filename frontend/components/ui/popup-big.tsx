"use client";

import { ReactNode } from "react";

interface PopupProps {
    show: boolean;
    onClose: () => void;
    children: ReactNode;
}

export default function PopupBig({ show, onClose, children }: PopupProps) {
    if (!show) return null;

    return (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="relative bg-card text-card-foreground rounded-2xl w-full max-w-4xl shadow-2xl">
                {/* Header with Close Button - separated from scrollable area */}
                <div className="flex justify-end p-4">
                    <button
                        onClick={onClose}
                        className="text-2xl text-muted-foreground hover:text-foreground"
                    >
                        &times;
                    </button>
                </div>

                {/* Scrollable content */}
                <div className="px-6 pb-6 max-h-[80vh] overflow-y-auto">
                    {children}
                </div>
            </div>
        </div>
    );
}