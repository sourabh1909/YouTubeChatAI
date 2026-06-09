import React, { useState, useEffect, useRef } from "react";
import { Streamlit } from "streamlit-component-lib";
import { 
  Send, Sparkles, Youtube, User, ArrowRight,
  Volume2, VolumeX, Copy, Check, Search, 
  Settings, FileText, Download, Moon, Sun, 
  HelpCircle, ArrowLeft, RefreshCw, Palette, Mic
} from "lucide-react";
import { marked } from "marked";

// Configure marked options
marked.setOptions({
  breaks: true,
  gfm: true
});

export default function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [videoId, setVideoId] = useState("");
  const [transcriptText, setTranscriptText] = useState("");
  
  // Custom interactive states
  const [activeTab, setActiveTab] = useState("chat"); // "chat" | "transcript" | "settings"
  const [searchQuery, setSearchQuery] = useState(""); // transcript search
  const [chatSearchQuery, setChatSearchQuery] = useState(""); // chat history search
  const [showChatSearch, setShowChatSearch] = useState(false);
  const [theme, setTheme] = useState("cyberpunk"); // "cyberpunk" | "synthwave" | "matrix"
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [activeTtsIndex, setActiveTtsIndex] = useState(null);
  const [ttsRate, setTtsRate] = useState(1.0);
  const [ttsPitch, setTtsPitch] = useState(1.0);

  const messagesEndRef = useRef(null);

  // Set up Streamlit rendering event listeners
  useEffect(() => {
    const onRender = (event) => {
      const { args } = event.detail;
      
      if (args.messages) {
        setMessages(args.messages);
      }
      if (args.hasOwnProperty("loading")) {
        setLoading(args.loading);
      }
      if (args.video_id) {
        setVideoId(args.video_id);
      }
      if (args.transcript_text) {
        setTranscriptText(args.transcript_text);
      }
      
      // Auto-set the iframe height once we have the initial payload
      setTimeout(() => Streamlit.setFrameHeight(), 50);
    };

    Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
    Streamlit.setComponentReady();
    Streamlit.setFrameHeight(); // Initial check-in with Streamlit

    return () => {
      Streamlit.events.removeEventListener(Streamlit.RENDER_EVENT, onRender);
    };
  }, []);

  // Auto scroll to bottom when messages list changes or loading triggers
  useEffect(() => {
    if (activeTab === "chat") {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    
    // Ensure iframe height is adjusted when content size changes
    const timer = setTimeout(() => {
      Streamlit.setFrameHeight();
    }, 120);
    return () => clearTimeout(timer);
  }, [messages, loading, activeTab, transcriptText, showChatSearch]);

  const handleSend = (e) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || loading) return;

    const queryText = inputValue.trim();
    setInputValue("");
    setLoading(true);

    // Send data to Streamlit. Streamlit will capture this in the Python function return value.
    Streamlit.setComponentValue({
      text: queryText,
      timestamp: Date.now()
    });
  };

  const handleSuggestedPrompt = (promptText) => {
    if (loading) return;
    setLoading(true);
    Streamlit.setComponentValue({
      text: promptText,
      timestamp: Date.now()
    });
  };

  const renderMarkdown = (text) => {
    try {
      const html = marked.parse(text);
      return { __html: html };
    } catch (e) {
      return { __html: text };
    }
  };

  // Text to Speech
  const speakText = (text, index) => {
    if ("speechSynthesis" in window) {
      if (activeTtsIndex === index) {
        window.speechSynthesis.cancel();
        setActiveTtsIndex(null);
      } else {
        window.speechSynthesis.cancel();
        
        // Strip markdown and HTML tags for cleaner narration
        let cleanText = text
          .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // link text only
          .replace(/[*#`_\-]/g, '')                 // markdown formatting
          .replace(/<[^>]*>/g, '');                 // HTML tags
          
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = ttsRate;
        utterance.pitch = ttsPitch;
        
        utterance.onend = () => setActiveTtsIndex(null);
        utterance.onerror = () => setActiveTtsIndex(null);
        
        setActiveTtsIndex(index);
        window.speechSynthesis.speak(utterance);
      }
    } else {
      alert("Text-to-speech is not supported in this browser.");
    }
  };

  // Stop TTS when tab changes
  useEffect(() => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setActiveTtsIndex(null);
    }
  }, [activeTab]);

  // Copy to clipboard
  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    });
  };

  // Export chat log
  const exportChatAsMarkdown = () => {
    if (messages.length === 0) return;
    
    let content = `# YouTube Chat AI - Conversation Log\n`;
    content += `* **Video ID:** ${videoId}\n`;
    content += `* **Date/Time:** ${new Date().toLocaleString()}\n\n`;
    content += `---\n\n`;
    
    messages.forEach((msg) => {
      const roleName = msg.role === "user" ? "User" : "AI Assistant";
      content += `### 👤 ${roleName}\n${msg.content}\n\n`;
    });
    
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `chat_log_${videoId || "video"}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Highlight keywords in transcript
  const getHighlightedText = (text, highlight) => {
    if (!highlight.trim()) return text;
    const parts = text.split(new RegExp(`(${highlight})`, 'gi'));
    return (
      <span>
        {parts.map((part, i) => 
          part.toLowerCase() === highlight.toLowerCase() 
            ? <mark key={i} className="highlighted-term">{part}</mark> 
            : part
        )}
      </span>
    );
  };

  // Compute stats
  const getStats = () => {
    if (!transcriptText) return { words: 0, time: 0, chars: 0, chunks: 0 };
    const chars = transcriptText.length;
    const words = transcriptText.trim().split(/\s+/).filter(Boolean).length;
    const time = Math.ceil(words / 180); // Average speaking speed
    const chunks = Math.ceil(chars / 800); // Rough split estimate
    return { words, time, chars, chunks };
  };

  const stats = getStats();

  // Filter messages based on chat search query
  const filteredMessages = messages.filter(msg => 
    !chatSearchQuery || msg.content.toLowerCase().includes(chatSearchQuery.toLowerCase())
  );

  return (
    <div className={`chat-app theme-${theme}`}>
      {/* Header */}
      <div className="chat-header">
        <div className="header-title-container">
          <div className="header-icon">
            <Youtube size={20} />
          </div>
          <div className="header-info">
            <h2>Video Assistant</h2>
            <p>
              <span className="status-dot"></span>
              {videoId ? `Active ID: ${videoId}` : "Ready"}
            </p>
          </div>
        </div>

        {/* Tab Buttons */}
        <div className="header-tabs">
          <button 
            className={`tab-btn ${activeTab === "chat" ? "active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            <Sparkles size={14} />
            <span>Chat</span>
          </button>
          <button 
            className={`tab-btn ${activeTab === "transcript" ? "active" : ""}`}
            onClick={() => setActiveTab("transcript")}
          >
            <FileText size={14} />
            <span>Transcript</span>
          </button>
          <button 
            className={`tab-btn ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            <Settings size={14} />
            <span>Control Center</span>
          </button>
        </div>
      </div>

      {/* Tab Contents: 1. Chat */}
      {activeTab === "chat" && (
        <>
          {/* Chat Utility Bar */}
          {messages.length > 0 && (
            <div className="chat-utility-bar">
              <button 
                className={`utility-icon-btn ${showChatSearch ? "active" : ""}`}
                onClick={() => {
                  setShowChatSearch(!showChatSearch);
                  if (showChatSearch) setChatSearchQuery("");
                }}
                title="Search Messages"
              >
                <Search size={14} />
              </button>
              
              {showChatSearch && (
                <input 
                  type="text"
                  className="chat-history-search-input"
                  placeholder="Filter chat messages..."
                  value={chatSearchQuery}
                  onChange={(e) => setChatSearchQuery(e.target.value)}
                  autoFocus
                />
              )}
              
              <button 
                className="utility-text-btn ml-auto"
                onClick={exportChatAsMarkdown}
                title="Export conversation to Markdown file"
              >
                <Download size={13} />
                <span>Export Chat</span>
              </button>
            </div>
          )}

          {/* Message Feed */}
          <div className="chat-window">
            {filteredMessages.length === 0 ? (
              <div className="welcome-screen">
                <div className="welcome-logo">
                  <Sparkles size={32} />
                </div>
                <h3>YouTube Transcript AI</h3>
                <p>
                  I've indexed this video. Ask me anything about the content, or select one of the templates below:
                </p>
                <div className="suggested-prompts">
                  <div 
                    className="prompt-card"
                    onClick={() => handleSuggestedPrompt("Give me a comprehensive summary of this video.")}
                  >
                    <span>Summarize this video</span>
                    <ArrowRight size={14} className="arrow-icon" />
                  </div>
                  <div 
                    className="prompt-card"
                    onClick={() => handleSuggestedPrompt("What are the key takeaways or action points?")}
                  >
                    <span>What are the key takeaways?</span>
                    <ArrowRight size={14} className="arrow-icon" />
                  </div>
                  <div 
                    className="prompt-card"
                    onClick={() => handleSuggestedPrompt("List out any tools, links, or resources mentioned.")}
                  >
                    <span>List tools & resources mentioned</span>
                    <ArrowRight size={14} className="arrow-icon" />
                  </div>
                </div>
              </div>
            ) : (
              filteredMessages.map((msg, index) => (
                <div key={index} className={`message-wrapper ${msg.role}`}>
                  <div className="message-avatar">
                    {msg.role === "user" ? <User size={15} /> : <Sparkles size={15} />}
                  </div>
                  <div className="message-bubble-container">
                    <div className="message-bubble">
                      {msg.role === "user" ? (
                        <div>{msg.content}</div>
                      ) : (
                        <div dangerouslySetInnerHTML={renderMarkdown(msg.content)} />
                      )}
                    </div>
                    
                    {/* Message Action Strip */}
                    <div className="message-action-strip">
                      <button 
                        onClick={() => copyToClipboard(msg.content, index)}
                        className="msg-action-btn"
                        title="Copy message"
                      >
                        {copiedIndex === index ? (
                          <>
                            <Check size={11} className="success-icon" />
                            <span>Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy size={11} />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                      
                      {msg.role === "assistant" && (
                        <button 
                          onClick={() => speakText(msg.content, index)}
                          className={`msg-action-btn ${activeTtsIndex === index ? "speaking" : ""}`}
                          title={activeTtsIndex === index ? "Stop voice narration" : "Voice narration"}
                        >
                          {activeTtsIndex === index ? (
                            <>
                              <VolumeX size={11} />
                              <span>Mute</span>
                            </>
                          ) : (
                            <>
                              <Volume2 size={11} />
                              <span>Read Aloud</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}

            {/* Loading Indicator */}
            {loading && (
              <div className="typing-indicator">
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input Tray */}
          <div className="chat-input-container">
            <form onSubmit={handleSend} className="chat-input-form">
              <input
                type="text"
                className="chat-input"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Type your question about the video..."
                disabled={loading}
              />
              <button 
                type="submit" 
                className="send-button"
                disabled={!inputValue.trim() || loading}
              >
                <Send size={15} />
              </button>
            </form>
          </div>
        </>
      )}

      {/* Tab Contents: 2. Transcript Explorer */}
      {activeTab === "transcript" && (
        <div className="transcript-panel">
          {/* Stats Bar */}
          <div className="transcript-stats-grid">
            <div className="stat-card">
              <span className="stat-value">{stats.words.toLocaleString()}</span>
              <span className="stat-label">Total Words</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">~{stats.time} min</span>
              <span className="stat-label">Speaking Time</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.chunks}</span>
              <span className="stat-label">Vector Chunks</span>
            </div>
          </div>

          {/* Search bar */}
          <div className="transcript-search-wrapper">
            <Search size={16} className="search-icon" />
            <input 
              type="text"
              className="transcript-search-input"
              placeholder="Search keyword in transcripts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button 
                className="clear-search-btn"
                onClick={() => setSearchQuery("")}
              >
                Clear
              </button>
            )}
          </div>

          {/* Transcript Scroll Area */}
          <div className="transcript-content-scroll">
            {transcriptText ? (
              <div className="transcript-paragraphs">
                {getHighlightedText(transcriptText, searchQuery)}
              </div>
            ) : (
              <div className="empty-panel-state">
                <FileText size={32} />
                <p>No video transcript loaded yet. Go back to Streamlit and load a video.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab Contents: 3. Control Center (Settings) */}
      {activeTab === "settings" && (
        <div className="settings-panel">
          <div className="settings-section">
            <div className="section-title">
              <Palette size={16} />
              <h3>Aesthetic Theme Configuration</h3>
            </div>
            <p className="section-desc">Choose a design variant to instantly transform your chat experience.</p>
            
            <div className="theme-grid">
              <div 
                className={`theme-selector-card cyberpunk ${theme === "cyberpunk" ? "active" : ""}`}
                onClick={() => setTheme("cyberpunk")}
              >
                <div className="theme-preview-glow purple-blue"></div>
                <h4>Neon Cyberpunk</h4>
                <p>Deep space, purple accents and cyan glows.</p>
              </div>
              
              <div 
                className={`theme-selector-card synthwave ${theme === "synthwave" ? "active" : ""}`}
                onClick={() => setTheme("synthwave")}
              >
                <div className="theme-preview-glow pink-orange"></div>
                <h4>Synthwave Sunrise</h4>
                <p>Retro-futurism, glowing pinks and hot roses.</p>
              </div>
              
              <div 
                className={`theme-selector-card matrix ${theme === "matrix" ? "active" : ""}`}
                onClick={() => setTheme("matrix")}
              >
                <div className="theme-preview-glow emerald-green"></div>
                <h4>Matrix Console</h4>
                <p>Digital darknet, neon green matrix vibes.</p>
              </div>
            </div>
          </div>

          <div className="settings-section">
            <div className="section-title">
              <Mic size={16} />
              <h3>Text-To-Speech Narrator Settings</h3>
            </div>
            <p className="section-desc">Adjust the speed and pitch of the Read Aloud narrations.</p>
            
            <div className="control-sliders">
              <div className="control-slider-group">
                <div className="slider-header">
                  <span>Speed Rate</span>
                  <span>{ttsRate}x</span>
                </div>
                <input 
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={ttsRate}
                  onChange={(e) => setTtsRate(parseFloat(e.target.value))}
                  className="settings-range"
                />
              </div>

              <div className="control-slider-group">
                <div className="slider-header">
                  <span>Voice Pitch</span>
                  <span>{ttsPitch}x</span>
                </div>
                <input 
                  type="range"
                  min="0.5"
                  max="1.5"
                  step="0.1"
                  value={ttsPitch}
                  onChange={(e) => setTtsPitch(parseFloat(e.target.value))}
                  className="settings-range"
                />
              </div>
            </div>
          </div>

          <div className="settings-section">
            <div className="section-title">
              <Download size={16} />
              <h3>Data Export</h3>
            </div>
            <p className="section-desc">Download your entire current conversation history as a formatted Markdown document.</p>
            <button 
              className="export-big-btn"
              onClick={exportChatAsMarkdown}
              disabled={messages.length === 0}
            >
              <Download size={16} />
              <span>Download Markdown Transcript ({messages.length} messages)</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
