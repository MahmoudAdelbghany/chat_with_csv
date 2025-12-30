import React, { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';

function App() {
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [initialData, setInitialData] = useState(null); // Used when creating new session

  const handleUploadSuccess = (data) => {
    setInitialData(data);
    setCurrentSessionId(data.sessionId);
  };

  const handleSelectSession = (sessionId) => {
    setCurrentSessionId(sessionId);
    setInitialData(null); // Context will be fetched by ChatInterface
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setInitialData(null);
  };

  return (
    <div className="app" style={{ display: 'flex', flexDirection: 'row', width: '100vw', height: '100vh' }}>
      <Sidebar 
         currentSessionId={currentSessionId}
         onSelectSession={handleSelectSession}
         onNewChat={handleNewChat}
      />
      <div style={{ flex: 1, position: 'relative' }}>
          {!currentSessionId ? (
            <div className="container" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh'}}>
               <FileUpload onUploadSuccess={handleUploadSuccess} />
            </div>
          ) : (
            <ChatInterface 
                key={currentSessionId} // Force re-mount when session changes
                sessionId={currentSessionId} 
                initialData={initialData} 
            />
          )}
      </div>
    </div>
  );
}

export default App;
