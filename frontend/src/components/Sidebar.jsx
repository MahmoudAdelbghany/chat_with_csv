import React, { useEffect, useState } from 'react';
import { MessageSquare, Plus, Trash2 } from 'lucide-react';
import axios from 'axios';

const Sidebar = ({ currentSessionId, onSelectSession, onNewChat, isOpen, onClose }) => {
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    fetchConversations();
  }, [currentSessionId]); 

  const fetchConversations = async () => {
    try {
        const API_URL = import.meta.env.VITE_API_URL || '/api';
        const response = await axios.get(`${API_URL}/conversations`, { withCredentials: true });
        setConversations(response.data);
    } catch (error) {
        console.error("Failed to load conversations", error);
    }
  };

  return (
    <>
      {/* Mobile Overlay */}
      <div 
        className={`sidebar-overlay ${isOpen ? 'visible' : ''}`} 
        onClick={onClose}
      />
      
      <div className={`sidebar ${isOpen ? 'open' : ''}`}>
          <div className="sidebar-header">
              <button className="new-chat-btn" onClick={() => {
                  onNewChat();
                  if (window.innerWidth < 768) onClose(); // Close on mobile
              }}>
                  <Plus size={16} /> New Chat
              </button>
          </div>

          <div className="sidebar-list">
              <div style={{ fontSize: '0.75rem', color: '#888', padding: '0.5rem 0.5rem' }}>Recent</div>
              {conversations.map(conv => (
                  <div 
                      key={conv.id}
                      className={`sidebar-item ${conv.id === currentSessionId ? 'active' : ''}`}
                      onClick={() => {
                          onSelectSession(conv.id);
                          if (window.innerWidth < 768) onClose(); // Close on mobile
                      }}
                  >
                      <MessageSquare size={16} style={{ flexShrink: 0 }} />
                      <span className="sidebar-item-title">
                          {conv.title}
                      </span>
                      <button
                          className="delete-btn"
                          onClick={async (e) => {
                              e.stopPropagation();
                              if (window.confirm('Delete this chat?')) {
                                  try {
                                      const API_URL = import.meta.env.VITE_API_URL || '/api';
                                      await axios.delete(`${API_URL}/conversations/${conv.id}`, { withCredentials: true });
                                      fetchConversations();
                                      if (currentSessionId === conv.id) {
                                          onNewChat();
                                      }
                                  } catch (err) {
                                      console.error("Failed to delete", err);
                                  }
                              }
                          }}
                      >
                          <Trash2 size={14} />
                      </button>
                  </div>
              ))}
          </div>
      </div>
    </>
  );
};

export default Sidebar;
