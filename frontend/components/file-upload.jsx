"use client"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Upload, FileUp, FileIcon, X, CheckCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export function FileUpload({ onFileUpload }) {
  const [isDragging, setIsDragging] = useState(false)
  const [file, setFile] = useState(null)
  const fileInputRef = useRef(null)

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.type === "text/csv") {
        setFile(droppedFile)
        onFileUpload(droppedFile)
      }
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0]
      if (selectedFile.type === "text/csv") {
        setFile(selectedFile)
        onFileUpload(selectedFile)
      }
    }
  }

  const handleButtonClick = () => {
    fileInputRef.current?.click()
  }

  const handleRemoveFile = () => {
    setFile(null)
  }

  return (
    <div className="space-y-6">
      <div
        className={cn(
          "flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-12 text-center transition-colors",
          isDragging ? "border-teal-500 bg-mint-50" : "border-gray-300",
          file ? "bg-mint-50" : "",
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {!file ? (
          <>
            <Upload className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-1">Upload CSV File</h3>
            <p className="text-sm text-muted-foreground mb-4">Drag and drop your CSV file here, or click to browse</p>
            <Button
              className="bg-gradient-to-r from-teal-500 to-blue-500 hover:from-teal-600 hover:to-blue-600"
              onClick={handleButtonClick}
            >
              <FileUp className="mr-2 h-4 w-4" />
              Browse Files
            </Button>
            <input type="file" ref={fileInputRef} className="hidden" accept=".csv" onChange={handleFileChange} />
          </>
        ) : (
          <div className="flex flex-col items-center">
            <CheckCircle className="h-12 w-12 text-teal-500 mb-4" />
            <h3 className="text-lg font-medium mb-1">File Uploaded</h3>
            <div className="flex items-center bg-white rounded-md border px-3 py-2 mt-2">
              <FileIcon className="h-5 w-5 text-teal-500 mr-2" />
              <span className="text-sm font-medium">{file.name}</span>
              <Button variant="ghost" size="icon" className="ml-2 h-6 w-6" onClick={handleRemoveFile}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="rounded-md bg-muted p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <FileIcon className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium">CSV File Requirements</h3>
            <div className="mt-2 text-sm text-muted-foreground">
              <ul className="list-disc space-y-1 pl-5">
                <li>File must be in CSV format</li>
                <li>First row should contain column headers</li>
                <li>File size should be under 10MB</li>
                <li>UTF-8 encoding is recommended</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
