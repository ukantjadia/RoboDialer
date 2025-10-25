"use client";

import { useRef } from "react";
import { UploadCloud, CheckCircle, AlertCircle, FileText, X } from "lucide-react";

interface UploadStepProps {
  userName?: string;
  selectedFiles: File[];
  setSelectedFiles: React.Dispatch<React.SetStateAction<File[]>>;
  onSubmit: () => void;
  onBack: () => void;
}

export default function UploadStep({
  userName = "User",
  selectedFiles,
  setSelectedFiles,
  onSubmit,
  onBack,
}: UploadStepProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleBoxClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setSelectedFiles((prev) => {
        const fileMap = new Map(prev.map(f => [f.name + f.size, f]));
        newFiles.forEach(f => fileMap.set(f.name + f.size, f));
        return Array.from(fileMap.values());
      });
      e.target.value = "";
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-dark-primary py-8">
      <div className="w-full max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-2 text-white text-center">
          Welcome, {userName}!
        </h1>
        <p className="text-gray-400 mb-8 text-center">
          Let's start by uploading your financial data to generate personalized insights
        </p>
        <div className="bg-dark-secondary rounded-xl border border-dark-border p-8">
          <h2 className="font-semibold text-lg mb-2 text-white">Upload Financial Files</h2>
          <p className="text-gray-400 mb-4">
            Upload your income statements, sales ledgers, or financial reports to begin analysis
          </p>
          <div
            className="border-2 border-dashed border-dark-border rounded-lg flex flex-col items-center justify-center py-10 mb-4 cursor-pointer transition hover:border-blue-400 bg-dark-primary"
            onClick={handleBoxClick}
          >
            <UploadCloud className="w-10 h-10 text-gray-500 mb-2" />
            <span className="text-gray-300 mb-1">
              Drop your files here, or{" "}
              <span
                className="text-blue-400 underline cursor-pointer"
                onClick={e => {
                  e.stopPropagation();
                  handleBoxClick();
                }}
              >
                browse
              </span>
            </span>
            <span className="text-gray-500 text-sm mb-2">
              Supports Excel and CSV files up to 10MB
            </span>
            <button
              className="mt-2 px-4 py-2 bg-dark-secondary border border-dark-border rounded hover:bg-dark-hover transition text-gray-200"
              onClick={e => {
                e.stopPropagation();
                handleBoxClick();
              }}
            >
              Choose File
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              className="hidden"
              multiple
              onChange={handleFileChange}
            />
          </div>
          <div className="flex flex-wrap gap-4 mb-4">
            <div className="flex items-center gap-2 text-green-400 text-sm">
              <CheckCircle className="w-4 h-4" /> Excel files (.xlsx, .xls)
            </div>
            <div className="flex items-center gap-2 text-green-400 text-sm">
              <CheckCircle className="w-4 h-4" /> CSV files (.csv)
            </div>
            <div className="flex items-center gap-2 text-yellow-400 text-sm">
              <AlertCircle className="w-4 h-4" /> Max size: 10MB
            </div>
          </div>
          {selectedFiles.length > 0 && (
            <>
              <div className="bg-dark-primary border border-dark-border rounded-lg p-4 mt-4 max-h-40 overflow-y-auto">
                <h3 className="text-white font-semibold mb-2 text-base">Selected Files:</h3>
                <ul>
                  {selectedFiles.map((file, idx) => (
                    <li
                      key={idx}
                      className="flex items-center justify-between text-gray-200 py-1 border-b border-dark-border last:border-b-0"
                    >
                      <span className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-blue-400" />
                        {file.name}
                      </span>
                      <button
                        className="flex items-center gap-1 px-3 py-1 rounded bg-dark-secondary border border-dark-border hover:bg-dark-hover text-red-400 text-sm transition ml-2"
                        onClick={() => handleRemoveFile(idx)}
                        aria-label="Remove file"
                        type="button"
                      >
                        <X className="w-4 h-4" />
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex justify-center mt-6">
                <button
                  className="px-6 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white font-semibold transition"
                  type="button"
                  onClick={onSubmit}
                >
                  Submit
                </button>
              </div>
            </>
          )}
          <div className="flex justify-center mt-8">
            <button
              className="px-6 py-2 rounded bg-gray-700 hover:bg-gray-600 text-white font-semibold transition"
              onClick={onBack}
            >
              Back to Overview
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}