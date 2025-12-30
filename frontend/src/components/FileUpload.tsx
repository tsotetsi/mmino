import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

interface FileUploadProps {
  onFileSelect: (file: File | null) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect }) => {
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

  const handleUpload = () => {
    if (selectedFile) {
      console.log("Uploading file:", selectedFile.name);
      // Placeholder for actual upload logic
      alert(`Uploading: ${selectedFile.name}`);
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