import sys

import warnings
import logging

# Suppress all deprecation warnings and logging chatter from third-party models
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)

import os
import time
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
import rag_engine

# Load environment variables
load_dotenv()

# Streamlit page settings
st.set_page_config(
    page_title="YouTube Chat AI - RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Groq API Key from environment or Streamlit secrets
env_groq_key = os.getenv("GROQ_API_KEY", "")
if not env_groq_key:
    try:
        env_groq_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        pass
st.session_state.groq_api_key = env_groq_key

# Custom futuristic cyberpunk styling for Streamlit container
st.markdown("""
<style>
    /* Global Fonts & Cyberpunk Base */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.12) 0%, #05060b 80%) !important;
        color: #f1f5f9;
    }
    
    /* Hide Default Header/Footer for Application Vibe */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    footer {
        visibility: hidden !important;
    }
    #MainMenu {
        visibility: hidden !important;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Sidebar Cyber Glass styling */
    section[data-testid="stSidebar"] {
        background: rgba(10, 11, 22, 0.85) !important;
        border-right: 1px solid rgba(139, 92, 246, 0.15) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
    }
    
    /* Custom Title Styling with Neon Glow */
    .app-title-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 5px;
    }
    
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.6rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ffffff, #c7d2fe, #a5b4fc, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 40px rgba(139, 92, 246, 0.25);
    }
    
    .subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-top: -5px;
        margin-bottom: 30px;
    }
    
    /* Premium Futuristic Card Container */
    .premium-card {
        background: rgba(15, 17, 30, 0.6) !important;
        border: 1px solid rgba(139, 92, 246, 0.15) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4), 
                    inset 0 1px 0 0 rgba(255, 255, 255, 0.05) !important;
        margin-bottom: 25px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .premium-card:hover {
        border-color: rgba(6, 182, 212, 0.3) !important;
        box-shadow: 0 8px 32px 0 rgba(6, 182, 212, 0.08),
                    inset 0 1px 0 0 rgba(255, 255, 255, 0.08) !important;
        transform: translateY(-2px);
    }

    /* Input text box customization with pulsing shadow */
    div[data-testid="stTextInput"] > div {
        background-color: rgba(13, 14, 25, 0.8) !important;
        border: 1px solid rgba(139, 92, 246, 0.25) !important;
        border-radius: 12px !important;
        padding: 4px 6px !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25) !important;
        transition: all 0.3s ease !important;
    }
    
    div[data-testid="stTextInput"] > div:focus-within {
        border-color: #06b6d4 !important;
        box-shadow: 0 0 18px rgba(6, 182, 212, 0.35) !important;
    }
    
    div[data-testid="stTextInput"] input {
        color: #f8fafc !important;
        font-size: 14px !important;
    }
    
    /* Primary buttons (e.g. Initialize Chatbot) */
    div.stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 18px rgba(139, 92, 246, 0.4) !important;
        width: 100%;
    }
    div.stButton > button[data-testid="baseButton-primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 25px rgba(6, 182, 212, 0.6) !important;
        border-color: rgba(6, 182, 212, 0.5) !important;
        background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%) !important;
    }
    div.stButton > button[data-testid="baseButton-primary"]:active {
        transform: translateY(0px) !important;
    }
    
    /* Secondary buttons (e.g. suggestions and sidebar tools) */
    div.stButton > button[data-testid="baseButton-secondary"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: #94a3b8 !important;
        font-size: 13px !important;
        padding: 8px 18px !important;
        font-weight: 500 !important;
        box-shadow: none !important;
        width: 100%;
        transition: all 0.25s ease !important;
        text-overflow: ellipsis;
        white-space: nowrap;
        overflow: hidden;
    }
    div.stButton > button[data-testid="baseButton-secondary"]:hover {
        background: rgba(139, 92, 246, 0.08) !important;
        border-color: rgba(139, 92, 246, 0.35) !important;
        color: #f1f5f9 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.08) !important;
    }
    
    /* Custom text elements */
    .panel-subheader {
        font-family: 'Outfit', sans-serif;
        color: #f8fafc;
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .badge-ready {
        background: rgba(6, 182, 212, 0.1);
        border: 1px solid rgba(6, 182, 212, 0.25);
        color: #22d3ee;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    
    .badge-dot {
        width: 6px;
        height: 6px;
        background-color: #22d3ee;
        border-radius: 50%;
        box-shadow: 0 0 6px #22d3ee;
    }
</style>
""", unsafe_allow_html=True)

# Declare Custom Component
_RELEASE = True

parent_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = os.path.join(parent_dir, "frontend", "dist")

if not _RELEASE:
    custom_chat = components.declare_component(
        "custom_chat",
        url="http://localhost:3001"
    )
else:
    if not os.path.exists(build_dir):
        st.warning("Frontend build directory not found. Please run npm run build in the frontend directory.")
    custom_chat = components.declare_component(
        "custom_chat",
        path=build_dir
    )

# Initialize Session States
if "messages" not in st.session_state:
    st.session_state.messages = []
if "loading" not in st.session_state:
    st.session_state.loading = False
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "video_url" not in st.session_state:
    st.session_state.video_url = None
if "rag_chain" not in st.session_state:
    st.session_state.rag_chain = None
if "last_processed_timestamp" not in st.session_state:
    st.session_state.last_processed_timestamp = time.time() * 1000
if "temp_url_input" not in st.session_state:
    st.session_state.temp_url_input = ""
if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = ""
if "show_manual_transcript_input" not in st.session_state:
    st.session_state.show_manual_transcript_input = False
if "failed_video_id" not in st.session_state:
    st.session_state.failed_video_id = None

# Main Application Title
st.markdown("""
<div class='app-title-container'>
    <h1 class='main-title'>🎥 YouTube Chat AI</h1>
    <span class='badge-ready'><span class='badge-dot'></span>RAG Engine Active</span>
</div>
<p class='subtitle'>Futuristic video assistant. Index any transcript and query it in real-time.</p>
""", unsafe_allow_html=True)

# Sidebar UI
with st.sidebar:
    st.markdown("### 🖥️ Control Center")
    st.markdown("<p style='font-size: 12px; color: #64748b; margin-top: -10px; margin-bottom: 20px;'>Manage your RAG session</p>", unsafe_allow_html=True)
    
    # Verify Groq Key presence
    if st.session_state.groq_api_key:
        st.markdown("""
        <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 10px; padding: 12px; font-size: 12.5px; color: #4ade80; display: flex; align-items: center; gap: 8px;">
            <span>🤖 Groq LLM Connected</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 10px; padding: 12px; font-size: 12.5px; color: #f87171;">
            <span>⚠️ API Key missing! Add <b>GROQ_API_KEY</b> to your <b>.env</b> file.</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Active Video Dashboard info
    if st.session_state.video_id:
        st.markdown(f"""
        <div class='premium-card' style='padding: 15px !important;'>
            <div style='font-size: 11px; color: #06b6d4; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;'>Currently Loaded</div>
            <div style='font-size: 13.5px; font-weight: 600; color: #f8fafc;'>YouTube Video</div>
            <div style='font-size: 11.5px; color: #94a3b8; font-family: monospace; margin-top: 2px;'>ID: {st.session_state.video_id}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📺 Live Player")
        st.video(st.session_state.video_url)
        
        st.markdown("---")
        
        # Action Buttons
        if st.button("🧹 Clear Chat History", key="btn_clear"):
            st.session_state.messages = []
            st.session_state.last_processed_timestamp = time.time() * 1000
            st.rerun()
            
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        
        if st.button("🔄 Load New Video", key="btn_new_vid"):
            st.session_state.messages = []
            st.session_state.last_processed_timestamp = time.time() * 1000
            st.session_state.video_id = None
            st.session_state.video_url = None
            st.session_state.rag_chain = None
            st.session_state.temp_url_input = ""
            st.session_state.show_manual_transcript_input = False
            st.session_state.failed_video_id = None
            st.rerun()

# RAG Index Loader Screen
if not st.session_state.video_id:
    if st.session_state.show_manual_transcript_input:
        st.markdown(f"""
        <div class='premium-card' style='border-color: rgba(239, 68, 68, 0.4) !important;'>
            <h3 style='margin-bottom: 8px; font-family: Outfit; font-weight: 600; color: #f87171;'>📋 Manual Transcript Fallback</h3>
            <p style='color: #94a3b8; font-size: 13px; line-height: 1.5; margin-bottom: 0;'>
                YouTube blocked the server's IP address from fetching the transcript for video ID <b>{st.session_state.failed_video_id}</b>.
                Please copy the transcript of the video and paste it below to start your chat session.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        manual_text = st.text_area("Paste Transcript Text Here:", height=250, placeholder="Paste the video transcript here...")
        
        col_m1, col_m2 = st.columns([1, 1])
        with col_m1:
            submit_manual = st.button("Initialize Chatbot with Pasted Transcript", type="primary", disabled=not manual_text)
        with col_m2:
            cancel_manual = st.button("Cancel & Try Another Link", key="btn_cancel_manual")
            if cancel_manual:
                st.session_state.show_manual_transcript_input = False
                st.session_state.failed_video_id = None
                st.rerun()
                
        if submit_manual and manual_text:
            extracted_id = st.session_state.failed_video_id
            with st.spinner("⚡ Building local RAG index from pasted transcript... (Takes a few seconds)"):
                try:
                    st.toast("🧠 Generating embeddings and building FAISS index...", icon="⚙️")
                    vector_store = rag_engine.create_vector_store(manual_text, extracted_id)
                    st.session_state.transcript_text = manual_text
                    
                    rag_chain = rag_engine.get_rag_chain(vector_store, st.session_state.groq_api_key)
                    st.session_state.video_id = extracted_id
                    st.session_state.video_url = f"https://www.youtube.com/watch?v={extracted_id}"
                    st.session_state.rag_chain = rag_chain
                    st.session_state.messages = []
                    st.session_state.last_processed_timestamp = time.time() * 1000
                    st.session_state.show_manual_transcript_input = False
                    st.session_state.failed_video_id = None
                    st.success("🎉 RAG Index successfully created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to build index: {str(e)}")
    else:
        st.markdown("""
        <div class='premium-card'>
            <h3 style='margin-bottom: 8px; font-family: Outfit; font-weight: 600;'>Load YouTube Video Transcript</h3>
            <p style='color: #94a3b8; font-size: 13px; line-height: 1.5; margin-bottom: 0;'>
                Input a video link below. We'll download the captions, partition the text, embed the paragraphs using local <b>Hugging Face</b> vectors, and build a high-speed search index in a local <b>FAISS database</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # URL text input using state variable value
        url_input = st.text_input(
            "YouTube Video Link or ID:",
            placeholder="e.g., https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            value=st.session_state.temp_url_input
        )
        
        # Quick select templates
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("<span class='panel-subheader'>💡 Or select a quick example video:</span>", unsafe_allow_html=True)
        
        ec1, ec2, ec3 = st.columns(3)
        
        # Wrap columns in a custom css class for custom styled buttons
        st.markdown("<div class='sample-btn-col'>", unsafe_allow_html=True)
        with ec1:
            if st.button("🎵 Rick Astley (Verification)", key="ex_astley", type="secondary"):
                st.session_state.temp_url_input = "dQw4w9WgXcQ"
                st.rerun()
        with ec2:
            if st.button("🤖 Llama 3.1 & Groq RAG", key="ex_llama", type="secondary"):
                st.session_state.temp_url_input = "ycPr5-27vAk"
                st.rerun()
        with ec3:
            if st.button("⛓️ LangChain RAG Intro", key="ex_langchain", type="secondary"):
                st.session_state.temp_url_input = "LHNtUMefd8o"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        
        # Submit button
        load_btn = st.button("Initialize Chatbot", type="primary", disabled=not url_input or not st.session_state.groq_api_key)
        
        if load_btn and url_input:
            extracted_id = rag_engine.extract_video_id(url_input)
            if not extracted_id:
                st.error("❌ Invalid YouTube URL or Video ID format. Please verify the URL.")
            else:
                with st.spinner("⚡ Fetching transcript and building local RAG index... (Takes a few seconds)"):
                    try:
                        # Check if a cached index exists to avoid network request and re-embedding
                        if rag_engine.has_cached_index(extracted_id):
                            st.toast("⚡ Found cached index. Loading...", icon="💾")
                            vector_store = rag_engine.load_cached_vector_store(extracted_id)
                            st.session_state.transcript_text = rag_engine.load_cached_transcript(extracted_id)
                        else:
                            st.toast("🌐 Fetching transcript from YouTube...", icon="📥")
                            # Download transcripts
                            transcript_text = rag_engine.fetch_transcript_text(extracted_id)
                            
                            st.toast("🧠 Generating embeddings and building FAISS index...", icon="⚙️")
                            # Split and embed documents locally
                            vector_store = rag_engine.create_vector_store(transcript_text, extracted_id)
                            st.session_state.transcript_text = transcript_text
                        
                        # Instantiate Groq retriever chain
                        rag_chain = rag_engine.get_rag_chain(vector_store, st.session_state.groq_api_key)
                        
                        # Cache RAG session state
                        st.session_state.video_id = extracted_id
                        st.session_state.video_url = f"https://www.youtube.com/watch?v={extracted_id}"
                        st.session_state.rag_chain = rag_chain
                        st.session_state.messages = []
                        st.session_state.last_processed_timestamp = time.time() * 1000
                        
                        st.success("🎉 RAG Index successfully created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to index transcript: {str(e)}")
                        st.session_state.show_manual_transcript_input = True
                        st.session_state.failed_video_id = extracted_id
                        st.markdown("""
                        **Common troubleshooting steps:**
                        - Make sure the video is public and has subtitles (captions) enabled.
                        - Check if your internet connection is blocked from calling YouTube's scraping ports.
                        - Try loading another video ID.
                        """)
                        st.rerun()

else:
    # Render loaded Chat interface
    col1, col2 = st.columns([7, 3])
    
    with col1:
        # Embed custom React chatbot UI
        chat_return = custom_chat(
            messages=st.session_state.messages,
            loading=st.session_state.loading,
            video_id=st.session_state.video_id,
            transcript_text=st.session_state.transcript_text,
            key="youtube_rag_chat"
        )
        
        # Catch inputs from custom React Component
        if chat_return is not None:
            user_message_text = chat_return.get("text")
            message_timestamp = chat_return.get("timestamp")
            
            # Double check to prevent duplicate executions on streamlit redraw
            if message_timestamp is not None and message_timestamp > st.session_state.last_processed_timestamp:
                st.session_state.last_processed_timestamp = message_timestamp
                
                # Append user prompt
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_message_text
                })
                # Trigger assistant query loader
                st.session_state.loading = True
                st.rerun()

        # Execute assistant query
        if st.session_state.loading:
            latest_query = st.session_state.messages[-1]["content"]
            
            try:
                # Retrieve matching segments and query Llama 3.1 LLM
                answer = rag_engine.query_rag_engine(
                    st.session_state.rag_chain,
                    latest_query,
                    st.session_state.messages[:-1]
                )
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ **Error running query:** {str(e)}"
                })
            
            # Reset loader state
            st.session_state.loading = False
            st.rerun()
            
    with col2:
        # Video detail info pane
        st.markdown(f"""
        <div class='premium-card' style='height: 600px; overflow-y: auto;'>
            <h3 style='margin-bottom: 12px; font-size: 16px; font-family: Outfit;'>📋 RAG Index Status</h3>
            <img src="https://img.youtube.com/vi/{st.session_state.video_id}/hqdefault.jpg" style="width:100%; border-radius:10px; margin-bottom:12px; border: 1px solid rgba(139,92,246,0.2); box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
            <p style='font-size: 12.5px; color: #94a3b8; line-height: 1.5; margin-bottom: 15px;'>
                The captions are vector-partitioned into a high-density index. When you submit a question, the vector store fetches the top 5 most relevant segments to construct the prompt context.
            </p>
            <div style='background: rgba(139, 92, 246, 0.05); border: 1px solid rgba(139, 92, 246, 0.1); border-radius: 8px; padding: 12px; margin-bottom: 15px;'>
                <div style='font-size: 11px; font-weight: 600; color: #a5b4fc; text-transform: uppercase;'>Embeddings Model</div>
                <div style='font-size: 12.5px; color: #f8fafc; font-family: monospace;'>HuggingFace / all-MiniLM-L6-v2</div>
            </div>
            <div style='background: rgba(6, 182, 212, 0.05); border: 1px solid rgba(6, 182, 212, 0.1); border-radius: 8px; padding: 12px; margin-bottom: 15px;'>
                <div style='font-size: 11px; font-weight: 600; color: #22d3ee; text-transform: uppercase;'>LLM Model</div>
                <div style='font-size: 12.5px; color: #f8fafc; font-family: monospace;'>Groq / llama-3.1-8b-instant</div>
            </div>
            <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 15px 0;' />
            <h4 style='font-size: 13.5px; margin-bottom: 8px; font-family: Outfit; font-weight: 500;'>💡 Context-Aware Prompts:</h4>
            <ul style='font-size: 12px; color: #94a3b8; padding-left: 15px; line-height: 1.6;'>
                <li style='margin-bottom: 6px;'>Summarize the core takeaways.</li>
                <li style='margin-bottom: 6px;'>What tools, technologies or links are mentioned?</li>
                <li style='margin-bottom: 6px;'>Break down the tutorial step-by-step.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
