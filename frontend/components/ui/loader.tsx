// components/ui/Loader.tsx
import React from "react"

const Loader = () => {
    return (
        <div className="relative w-32 h-32 rounded-full border border-gray-700 shadow-lg flex items-center justify-center">
            <div className="absolute inset-4 border border-dashed border-gray-600 rounded-full shadow-inner"></div>
            <div className="absolute w-12 h-12 border border-dashed border-gray-600 rounded-full shadow-inner"></div>
            <div className="absolute top-1/2 left-1/2 w-1/2 h-full origin-top-left animate-spin">
                <div className="absolute top-0 left-0 w-full h-full rotate-[-55deg] bg-green-500 opacity-30 blur-xl shadow-2xl rounded-br-full"></div>
                <div className="absolute top-0 left-0 w-full h-full border-t border-dashed border-white"></div>
            </div>
        </div>
    )
}

export default Loader
