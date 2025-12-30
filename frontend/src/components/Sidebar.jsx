import React, { useEffect, useState } from 'react';
import { MessageSquare, Plus, Trash2 } from 'lucide-react';
import axios from 'axios';

const Sidebar = ({ currentSessionId, onSelectSession, onNewChat }) => {
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    fetchConversations();
  }, [currentSessionId]); // Refetch when session changes (to capture new one)

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
    <div className="sidebar" style={{
        width: '260px',
        height: '100vh',
        backgroundColor: '#262730', // Darker sidebar
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid #41424b'
    }}>
        <div style={{ padding: '1rem' }}>
            <button 
                onClick={onNewChat}
                style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '0.5rem',
                    border: '1px solid #41424b',
                    background: 'transparent',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    cursor: 'pointer',
                    transition: 'background 0.2s'
                }}
                onMouseOver={(e) => e.target.style.background = '#41424b'}
                onMouseOut={(e) => e.target.style.background = 'transparent'}
            >
                <Plus size={16} /> New Chat
            </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '0 0.5rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#888', padding: '0.5rem 0.5rem' }}>Recent</div>
            {conversations.map(conv => (
                <div 
                    key={conv.id}
                    onClick={() => onSelectSession(conv.id)}
                    style={{
                        padding: '0.75rem',
                        margin: '0.25rem 0',
                        borderRadius: '0.5rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        background: conv.id === currentSessionId ? '#41424b' : 'transparent',
                        fontSize: '0.9rem',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        position: 'relative',
                        paddingRight: '2rem' // Make space for delete button
                    }}
                    onMouseEnter={e => {
                        const btn = e.currentTarget.querySelector('.delete-btn');
                        if (btn) btn.style.display = 'block';
                    }}
                    onMouseLeave={e => {
                        const btn = e.currentTarget.querySelector('.delete-btn');
                        if (btn) btn.style.display = 'none';
                    }}
                >
                    <MessageSquare size={16} style={{ flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', flex: 1 }}>
                        {conv.title}
                    </span>
                    <button
                        className="delete-btn"
                        style={{
                            display: 'none',
                            background: 'transparent',
                            border: 'none',
                            color: '#ff4b4b',
                            cursor: 'pointer',
                            padding: '0.25rem',
                            position: 'absolute',
                            right: '0.5rem'
                        }}
                        onClick={async (e) => {
                            e.stopPropagation();
                            if (window.confirm('Delete this chat?')) {
                                try {
                                    const API_URL = import.meta.env.VITE_API_URL || '/api';
                                    await axios.delete(`${API_URL}/conversations/${conv.id}`, { withCredentials: true });
                                    // Refresh list
                                    fetchConversations();
                                    // If deleted current session, start new chat
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
  );
};

export default Sidebar;
