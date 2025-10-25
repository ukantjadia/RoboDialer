"use client";

import { useState } from "react";
import { BarChart3, FileSpreadsheet, PieChart } from "lucide-react";
import UploadStep from "./UploadStep";
import MappingStep from "./MappingStep";
import StepTracker from "./StepTracker";

export default function FinancialAnalysisPage({ userName = "User" }: { userName?: string }) {
  const [showUpload, setShowUpload] = useState(false);
  const [showMapping, setShowMapping] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [columnsByFile, setColumnsByFile] = useState<Record<string, string[]>>({});

  // Simulate backend columns for demo (remove this in production)
  const mockColumns = {
    "sample1.csv": ["Sale Amount", "Transaction_Date", "Customer Name", "Product_Category"],
    "sample2.csv": ["Cost_Price", "Product_Category", "Customer Name"],
  };

  const handleSubmit = () => {
    const mappingColumns: Record<string, string[]> = {};
    selectedFiles.forEach(f => {
      mappingColumns[f.name] = mockColumns[f.name] || ["Column1", "Column2"];
    });
    setColumnsByFile(mappingColumns);
    setShowMapping(true);
  };

  const handleMappingContinue = (mappings: Record<string, Record<string, string>>) => {
    // Do something with mappings
  };

  // Determine current step index
  let stepIndex = 0;
  if (showMapping) stepIndex = 1;
  else if (showUpload) stepIndex = 0;

  if (showMapping) {
    return (
      <div className="flex flex-col items-center min-h-screen bg-dark-primary py-8">
        <div className="w-full flex justify-center mb-8">
          <StepTracker currentStep={stepIndex} />
        </div>
        <MappingStep
          files={selectedFiles}
          columnsByFile={columnsByFile}
          onBack={() => setShowMapping(false)}
          onContinue={handleMappingContinue}
        />
      </div>
    );
  }

  if (showUpload) {
    return (
      <div className="flex flex-col items-center min-h-screen bg-dark-primary py-8">
        <div className="w-full flex justify-center mb-8">
          <StepTracker currentStep={stepIndex} />
        </div>
        <UploadStep
          userName={userName}
          selectedFiles={selectedFiles}
          setSelectedFiles={setSelectedFiles}
          onSubmit={handleSubmit}
          onBack={() => setShowUpload(false)}
        />
      </div>
    );
  }

  // Landing page (no StepTracker here)
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-dark-primary py-8">
      <div className="w-full max-w-4xl mx-auto">
        <div className="flex flex-col items-center text-center">
          <h1 className="text-4xl font-bold text-white mb-4">Financial Analysis Tool</h1>
          <p className="text-gray-300 text-lg mb-6 max-w-2xl mx-auto">
            Unlock actionable insights from your financial data. Our Financial Analysis Tool helps you generate detailed reports, visualize trends, and make data-driven decisions for your business.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10 w-full">
          <div className="bg-dark-secondary rounded-xl p-6 flex flex-col items-center border border-dark-border text-center">
            <BarChart3 className="w-10 h-10 text-blue-400 mb-2" />
            <h3 className="text-white font-semibold mb-1">Interactive Dashboards</h3>
            <p className="text-gray-400 text-sm">Visualize your financial performance with dynamic charts and dashboards.</p>
          </div>
          <div className="bg-dark-secondary rounded-xl p-6 flex flex-col items-center border border-dark-border text-center">
            <FileSpreadsheet className="w-10 h-10 text-green-400 mb-2" />
            <h3 className="text-white font-semibold mb-1">Automated Reports</h3>
            <p className="text-gray-400 text-sm">Generate income statements, sales summaries, and more in seconds.</p>
          </div>
          <div className="bg-dark-secondary rounded-xl p-6 flex flex-col items-center border border-dark-border text-center">
            <PieChart className="w-10 h-10 text-yellow-400 mb-2" />
            <h3 className="text-white font-semibold mb-1">Trend Analysis</h3>
            <p className="text-gray-400 text-sm">Identify key trends and patterns to make informed business decisions.</p>
          </div>
        </div>
        <div className="bg-dark-secondary rounded-xl p-6 border border-dark-border mb-8 w-full max-w-2xl mx-auto text-left">
          <h2 className="text-lg font-semibold text-white mb-2">How does it work?</h2>
          <ul className="list-disc list-inside text-gray-300 text-base space-y-1">
            <li>Upload your Excel or CSV financial files securely.</li>
            <li>Our tool automatically processes and analyzes your data.</li>
            <li>Receive interactive dashboards and downloadable reports.</li>
            <li>Your data is protected with enterprise-grade security.</li>
          </ul>
        </div>
        <div className="flex justify-center">
          <button
            className="px-8 py-3 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg transition"
            onClick={() => setShowUpload(true)}
          >
            Get Started
          </button>
        </div>
      </div>
    </div>
  );
}