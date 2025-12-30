import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, User, Bot } from 'lucide-react';

const ChatInterface = ({ sessionId, initialData }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [datasetInfo, setDatasetInfo] = useState(initialData || {}); // Fallback state
  const messagesEndRef = useRef(null);
  const isFetched = useRef(false);

  // Fetch history if initialData is missing (which happens when clicking sidebar)
  useEffect(() => {
    if (!initialData && !isFetched.current) {
        const fetchHistory = async () => {
           try {
                const API_URL = import.meta.env.VITE_API_URL || '/api';
                const response = await fetch(`${API_URL}/conversations/${sessionId}`, { credentials: 'include' });
                if (!response.ok) throw new Error("Failed to load history");
                
                const data = await response.json();
                
                // Set messages
                setMessages(data.messages);
                
                // Set dataset info basic (we don't get full preview from this endpoint yet, but maybe title)
                setDatasetInfo({
                    filename: data.title,
                    columns: [], // TODO: We might want connected dataset details
                    preview: null
                });
                
           } catch (e) {
               console.error("Error loading history", e);
           }
        };
        fetchHistory();
        isFetched.current = true;
    } 
    // If we have initialData (fresh upload), ensure we don't have empty state if we switch back and forth? 
    // Actually using key={sessionId} in App.jsx handles mount reset.
  }, [sessionId, initialData]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
        const API_URL = import.meta.env.VITE_API_URL || '/api';
        const response = await fetch(`${API_URL}/chat/${sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ message: userMsg.content }),
        });

        if (!response.ok) {
             throw new Error("Network response was not ok");
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMsg = { role: 'assistant', content: '' };
        let buffer = '';
        
        setMessages(prev => [...prev, assistantMsg]);

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            
            // The last item might be incomplete if it doesn't end with a newline
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const data = JSON.parse(line);
                    
                    if (data.type === 'delta') {
                        assistantMsg.content += data.content;
                    } else if (data.type === 'status' || data.type === 'error') {
                        if (data.content.startsWith("Code Output")) {
                             // Format output as a code block for cleanliness
                            const outputContent = data.content.replace("Code Output:\n", "");
                            assistantMsg.content += `\n**Output:**\n\`\`\`\n${outputContent}\n\`\`\`\n`;
                        } else if (data.content.startsWith("Code Error")) {
                            assistantMsg.content += `\n🚨 **Error:**\n\`\`\`\n${data.content}\n\`\`\`\n`;
                        } else {
                            // General status like "Running code..."
                            assistantMsg.content += `\n*${data.content}*\n`;
                        }
                    }

                    // Update the last message
                    setMessages(prev => {
                        const newMsgs = [...prev];
                        newMsgs[newMsgs.length - 1] = { ...assistantMsg };
                        return newMsgs;
                    });
                } catch (e) {
                    console.error("Error parsing JSON chunk", e);
                }
            }
        }

    } catch (error) {
        console.error("Chat error", error);
        setMessages(prev => [...prev, { role: 'assistant', content: "Error: Could not reach the server." }]);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="container" style={{display: 'flex', flexDirection: 'column', height: '100vh', paddingBottom: '2rem'}}>
        <div className="header" style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
           <h2 style={{fontSize: '1.5rem'}}>CSV Chat</h2>
           <span style={{fontSize: '0.9rem', color: '#666'}}>{datasetInfo.filename}</span>
        </div>

        <div style={{flex: 1, overflowY: 'auto', marginBottom: '1rem', paddingRight: '0.5rem'}}>
            {datasetInfo.preview && (
                <div style={{marginBottom: '2rem'}}>
                    <h3>Data Preview</h3>
                    <div style={{overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: '0.5rem', marginTop: '0.5rem'}}>
                         <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem'}}>
                             <thead>
                                 <tr style={{background: 'var(--secondary-bg)'}}>
                                     {datasetInfo.columns?.map(col => (
                                         <th key={col} style={{padding: '0.5rem', textAlign: 'left', borderBottom: '1px solid var(--border-color)'}}>{col}</th>
                                     ))}
                                 </tr>
                             </thead>
                             <tbody>
                                 {datasetInfo.preview.map((row, idx) => (
                                     <tr key={idx} style={{borderBottom: '1px solid #eee'}}>
                                         {datasetInfo.columns.map(col => (
                                             <td key={`${idx}-${col}`} style={{padding: '0.5rem'}}>{row[col]}</td>
                                         ))}
                                     </tr>
                                 ))}
                             </tbody>
                         </table>
                    </div>
                </div>
            )}

            {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                    <div style={{display: 'flex', alignItems: 'flex-start'}}>
                        <div className="message-icon" style={{background: msg.role === 'user' ? '#ddd' : '#ff4b4b', color: msg.role === 'user' ? '#333' : 'white'}}>
                            {msg.role === 'user' ? <User size={18}/> : <Bot size={18}/>}
                        </div>
                        <div style={{flex: 1, overflowWrap: 'anywhere'}}>
                             <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                    </div>
                </div>
            ))}
             <div ref={messagesEndRef} />
        </div>

        <form onSubmit={sendMessage} className="input-group">
            <input 
                type="text" 
                className="input-field" 
                placeholder="Ask something about your data..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
            />
            <button type="submit" className="btn" disabled={isLoading} style={{display: 'flex', alignItems: 'center'}}>
                <Send size={18} />
            </button>
        </form>
    </div>
  );
};

export default ChatInterface;
