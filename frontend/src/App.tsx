import React, { useState } from "react";
import Layout from "@/components/Layout";
import FileUpload from "./components/FileUpload";
import { Button } from "./components/ui/button";
import { convertAudio } from "./services/conversion";
import { AuthProvider } from "./context/AuthContext";

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
  };

  const handleConvert = async (format: string) => {
    if (selectedFile) {
      try {
        const response = await convertAudio(selectedFile, format);
        console.log(`Conversion to ${format} successful:`, response);
        alert(`Conversion to ${format} successful! Download link: ${response.downloadUrl}`);
      } catch (error) {
        console.error(`Conversion to ${format} failed:`, error);
        alert(`Conversion to ${format} failed.`);
      }
    } else {
      alert("Please upload an audio file first.");
    }
  };

  return (
    <AuthProvider>
      <Layout>
        <div className="container relative flex-col items-center justify-center md:grid lg:max-w-none lg:grid-cols-2 lg:px-0">
          <div className="lg:p-8">
            <div className="mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
              <div className="flex flex-col space-y-2 text-center">
                <h1 className="text-2xl font-semibold tracking-tight">
                  Upload Audio for Conversion
                </h1>
                <p className="text-sm text-muted-foreground">
                  Select an audio file to convert.
                </p>
              </div>
              <FileUpload onFileSelect={handleFileSelect} />
              <div className="flex flex-col space-y-2 text-center">
                <h1 className="text-2xl font-semibold tracking-tight">
                  Convert Audio
                </h1>
                <p className="text-sm text-muted-foreground">
                  Choose your desired output format and convert.
                </p>
              </div>
              <div className="grid gap-2">
                <Button onClick={() => handleConvert("mp3")} disabled={!selectedFile}>Convert to MP3</Button>
                <Button onClick={() => handleConvert("wav")} disabled={!selectedFile}>Convert to WAV</Button>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    </AuthProvider>
  );
}

export default App;