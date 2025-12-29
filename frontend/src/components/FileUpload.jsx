import React, { useCallback } from 'react';
import { UploadCloud } from 'lucide-react';
import axios from 'axios';

const FileUpload = ({ onUploadSuccess }) => {
  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      alert("Please upload a CSV file.");
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        // In dev, we might need to point to localhost:8000 if proxy isn't set
        // But let's assume we configure proxy or use full URL
        const response = await axios.post('http://localhost:8000/api/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        
        onUploadSuccess(response.data);
    } catch (error) {
        console.error("Upload failed", error);
        alert("Upload failed: " + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="card">
        <div className="header">
            <h1>Chat with your CSV</h1>
            <p style={{marginTop: '0.5rem', color: '#666'}}>Upload a CSV file to start analyzing.</p>
        </div>
        
        <label className="upload-area" htmlFor="file-upload">
            <UploadCloud size={48} color="#666" style={{marginBottom: '1rem'}} />
            <h3>Drag & Drop or Click to Upload</h3>
            <p style={{fontSize: '0.9rem', color: '#888', marginTop: '0.5rem'}}>Limit 200MB per file • CSV</p>
            <input 
                id="file-upload" 
                type="file" 
                accept=".csv" 
                onChange={handleFileChange} 
                style={{display: 'none'}} 
            />
        </label>
    </div>
  );
};

export default FileUpload;
