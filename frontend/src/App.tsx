import { useState, useEffect } from "react";
import axios from "axios";

import Layout from "@/components/Layout";
import FileUpload from "./components/FileUpload";
import { Button } from "./components/ui/button";
import { convertAudio } from "./services/conversion";
import { AuthProvider } from "./context/AuthContext";
import AnalysisResults from "./components/AnalysisResults";

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any | null>(null);

  const handleFileSelect = (file: File | null) => {
    setSelectedFile(file);
  };

  const handleUploadSuccess = (newJobId: string) => {
    setJobId(newJobId);
    setAnalysisResult(null); // Clear previous results
  };

  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const API_URL = "http://localhost:8000";
        const response = await axios.get(`${API_URL}/api/v1/jobs/${jobId}/status`);
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(interval);
          if (response.data.status === 'completed') {
            console.log("Completed job:", response.data, typeof(response.data));
            const detailsResponse = await axios.get(`${API_URL}/api/v1/jobs/${jobId}`);
            console.log("Job details:", detailsResponse.data);
            setAnalysisResult(detailsResponse.data);
          } else {
            // Handle failed job
            console.error("Job failed:", response.data);
            setAnalysisResult({ error: "Job failed. Please check the logs." });
          }
        }
      } catch (error) {
        console.error("Error fetching job status:", error);
        clearInterval(interval);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [jobId]);

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
              <FileUpload onFileSelect={handleFileSelect} onUploadSuccess={handleUploadSuccess} />
              <div className="flex flex-col space-y-2 text-center">
                <h1 className="text-2xl font-semibold tracking-tight">
                  Convert Audio
                </h1>
                <p className="text-sm text-muted-foreground">
                  Choose your desired output format and convert.
                </p>
              </div>
              <div className="flex gap-2">
                <Button onClick={() => handleConvert("mp3")} disabled={!selectedFile}>Convert to MP3</Button>
                <Button onClick={() => handleConvert("wav")} disabled={!selectedFile}>Convert to WAV</Button>
              </div>
            </div>
          </div>
          <div className="lg:p-8">
            <AnalysisResults results={analysisResult} />
          </div>
        </div>
      </Layout>
    </AuthProvider>
  );
}

export default App;