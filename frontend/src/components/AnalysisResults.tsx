import React from 'react';

interface AnalysisResultsProps {
  results: {
    duration?: number;
    bitrate?: number;
    sample_rate?: number;
    channels?: number;
    [key: string]: any;
  };
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({ results }) => {
  if (!results) {
    return null;
  }

  return (
    <div className="p-8">
      <h2 className="text-2xl font-semibold tracking-tight mb-4">Analysis Results</h2>
      <div className="space-y-2">
        { results.original_filename && (
          <p>
            <strong>Original File Name:</strong> {results.original_filename}
          </p>
        )}
        {results.duration && (
          <p>
            <strong>Duration:</strong> {results.duration.toFixed(2)}s
          </p>
        )}
        {results.bitrate && (
          <p>
            <strong>Bitrate:</strong> {Math.round(results.params.bitrate / 1000)} kbps
          </p>
        )}
        {results.sample_rate && (
          <p>
            <strong>Sample Rate:</strong> {results.sample_rate} Hz
          </p>
        )}
        {results.channels && (
          <p>
            <strong>Channels:</strong> {results.channels}
          </p>
        )}
      </div>
    </div>
  );
};

export default AnalysisResults;