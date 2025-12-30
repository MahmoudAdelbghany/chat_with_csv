import React, { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';

function App() {
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [initialData, setInitialData] = useState(null); 
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const handleUploadSuccess = (data) => {
    setInitialData(data);
    setCurrentSessionId(data.sessionId);
    // Close sidebar on mobile if it was open (though usually you upload first)
    setIsSidebarOpen(false);
  };

  const handleSelectSession = (sessionId) => {
    setCurrentSessionId(sessionId);
    setInitialData(null); 
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setInitialData(null);
  };

  return (
    <div className="app-layout">
      <Sidebar 
         currentSessionId={currentSessionId}
         onSelectSession={handleSelectSession}
         onNewChat={handleNewChat}
         isOpen={isSidebarOpen}
         onClose={() => setIsSidebarOpen(false)}
      />
      
      <div className="main-content">
          <div className="mobile-header">
              <button className="menu-btn" onClick={() => setIsSidebarOpen(true)}>
                  <Menu size={24} />
              </button>
              <h2 style={{ fontSize: '1.2rem', margin: 0 }}>Chat with CSV</h2>
          </div>

          {!currentSessionId ? (
            <div className="upload-center">
               <FileUpload onUploadSuccess={handleUploadSuccess} />
            </div>
          ) : (
            <ChatInterface 
                key={currentSessionId} 
                sessionId={currentSessionId} 
                initialData={initialData} 
            />
          )}
      </div>
    </div>
  );
}

export default App;
