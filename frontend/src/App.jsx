import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';

function App() {
  const [sessionData, setSessionData] = useState(null);

  return (
    <div className="app">
      {!sessionData ? (
        <div className="container" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh'}}>
           <FileUpload onUploadSuccess={setSessionData} />
        </div>
      ) : (
        <ChatInterface sessionId={sessionData.sessionId} initialData={sessionData} />
      )}
    </div>
  );
}

export default App;
