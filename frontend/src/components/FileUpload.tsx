import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import axios from 'axios';

const API_URL = "http://localhost:8000";

interface FileUploadProps {
  onFileSelect: (file: File | null) => void;
  onUploadSuccess: (jobId: string, analysisResults: any) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, onUploadSuccess }) => { // Updated prop destructuring
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      const file = event.target.files[0];
      setSelectedFile(file);
      onFileSelect(file);
    } else {
      setSelectedFile(null);
      onFileSelect(null);
    }
  };

  const handleUpload = async () => { // Made async
    if (selectedFile) {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("operation", "analyze"); // Assuming 'analyze' is an operation type for pre-upload analysis

      try {
        const response = await axios.post(`${API_URL}/api/v1/upload/`, formData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });
        console.log("Upload successful:", response.data);
        alert(`Upload successful! Job ID: ${response.data.job_id}`);
        onUploadSuccess(response.data.job_id, response.data.analysis_results); // Pass job ID and analysis results
      } catch (error) {
        console.error("Upload failed:", error);
        alert("Upload failed. Please try again.");
      }
    } else {
      alert("Please select a file first.");
    }
  };

  return (
    <div className="grid w-full max-w-sm items-center gap-1.5">
      <Input
        id="audioFile"
        type="file"
        accept="audio/*"
        onChange={handleFileChange}
        className={`bg-white border ${selectedFile ? 'border-blue-500' : 'border-gray-400'}`}
      />
      <Button onClick={handleUpload} disabled={!selectedFile}>
        Upload Audio
      </Button>
      {selectedFile && <p className="text-sm text-muted-foreground">Selected file: {selectedFile.name}</p>}
    </div>
  );
};

export default FileUpload;