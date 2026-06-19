import re
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

def extract_video_id(url_or_id):
    """
    Extracts the 11-character YouTube video ID from a URL or raw ID string.
    """
    url_or_id = url_or_id.strip()
    
    # Common YouTube URL patterns
    patterns = [
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?(?:[^&]*&)*v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # Raw ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None

def fetch_transcript_text(video_id, groq_api_key=None):
    """
    Fetches the transcript text for a given YouTube video ID.
    Attempts multiple methods to bypass restrictions:
    1. YouTubeTranscriptApi with custom browser headers & translation fallback.
    2. yt-dlp metadata extraction to parse json3 subtitles & translation fallback.
    3. Whisper API audio transcription via Groq as ultimate fallback.
    """
    import requests
    from requests import Session
    
    errors = []
    
    # Method 1: YouTubeTranscriptApi with custom browser headers & translation fallback
    try:
        session = Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        import os
        if os.path.exists("cookies.txt"):
            import http.cookiejar
            try:
                cookie_jar = http.cookiejar.MozillaCookieJar("cookies.txt")
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                session.cookies.update(cookie_jar)
            except Exception as ce:
                errors.append(f"Failed to load cookies.txt in YouTubeTranscriptApi: {str(ce)}")
        api = YouTubeTranscriptApi(http_client=session)
        transcript_list = api.list(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            # Look for a translatable transcript and translate to English
            translatable = None
            for t in transcript_list:
                if t.is_translatable:
                    translatable = t
                    break
            if translatable:
                transcript = translatable.translate('en')
            else:
                transcript = next(iter(transcript_list))
            
        data = transcript.fetch()
        full_text = " ".join([entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', '') for entry in data])
        if full_text.strip():
            return full_text
    except Exception as e:
        errors.append(f"YouTubeTranscriptApi failed: {str(e)}")

    # Method 2: yt-dlp metadata extraction
    try:
        import yt_dlp
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            subtitles = info.get('subtitles', {}) or info.get('automatic_captions', {})
            
            # Select english or any language
            lang = 'en'
            if lang not in subtitles:
                lang = next((l for l in subtitles.keys() if l.startswith('en')), None)
            if not lang and subtitles:
                lang = next(iter(subtitles.keys()))
                
            if lang:
                formats = subtitles[lang]
                json3_format = next((f for f in formats if f.get('ext') == 'json3'), None)
                if json3_format:
                    sub_url = json3_format['url']
                    if not lang.startswith('en'):
                        # Instruct YouTube timedtext API to translate to English
                        sub_url += '&tlang=en'
                        
                    res = requests.get(sub_url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    })
                    data = res.json()
                    text_parts = []
                    for event in data.get('events', []):
                        for seg in event.get('segs', []):
                            utf8_text = seg.get('utf8', '').strip()
                            if utf8_text:
                                text_parts.append(utf8_text)
                    full_text = " ".join(text_parts)
                    # Clean up spacing
                    full_text = " ".join(full_text.split())
                    if full_text.strip():
                        return full_text
    except Exception as e:
        errors.append(f"yt-dlp failed: {str(e)}")
        
    # Method 3: Whisper audio transcription fallback using Groq
    import os
    if not groq_api_key:
        groq_api_key = os.getenv("GROQ_API_KEY")
        
    if groq_api_key:
        try:
            import yt_dlp
            from groq import Groq
            
            # Create a temporary directory inside the workspace
            temp_dir = 'temp_audio'
            os.makedirs(temp_dir, exist_ok=True)
            audio_path = os.path.join(temp_dir, f"audio_{video_id}")
            
            # Download low-bitrate audio format (format 139 is ~48kbps AAC, format 249 is webm audio, etc.)
            ydl_opts = {
                'format': '139/249/140/251/bestaudio',
                'outtmpl': f"{audio_path}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
                'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
                
            # Find the downloaded file (matching any extension since we specified the base path)
            downloaded_file = None
            for f in os.listdir(temp_dir):
                if f.startswith(f"audio_{video_id}"):
                    downloaded_file = os.path.join(temp_dir, f)
                    break
                    
            if not downloaded_file:
                raise FileNotFoundError("Audio file download failed or not found on disk.")
                
            file_size = os.path.getsize(downloaded_file)
            # Limit size to 25MB for Groq Whisper API
            if file_size > 25 * 1024 * 1024:
                raise ValueError(
                    f"Downloaded audio file is {file_size / (1024*1024):.1f}MB, which exceeds "
                    "Groq's 25MB limit. The video is too long to transcribe automatically."
                )
                
            # Call Groq Whisper API
            client = Groq(api_key=groq_api_key)
            with open(downloaded_file, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    response_format="text"
                )
                
            # Whisper with response_format="text" returns a raw string
            # If it returns an object under default settings, get the text attribute
            full_text = transcript if isinstance(transcript, str) else getattr(transcript, 'text', '')
            
            if full_text.strip():
                return full_text
                
        except Exception as e:
            errors.append(f"Whisper transcription failed: {str(e)}")
        finally:
            # Clean up all downloaded audio files inside the temp folder
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    try:
                        os.remove(os.path.join(temp_dir, f))
                    except Exception:
                        pass
                try:
                    os.rmdir(temp_dir)
                except Exception:
                    pass
    else:
        errors.append("Groq API key not provided, skipped Whisper fallback.")
        
    # If all automated methods failed, raise error
    combined_errors = " | ".join(errors)
    raise ValueError(f"Could not retrieve transcript for YouTube video {video_id}: {combined_errors}")

import os
import streamlit as st

@st.cache_resource
def get_embeddings():
    """
    Loads and caches the HuggingFace embeddings model using Streamlit's cache.
    Uses GPU if available.
    """
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        device = "cpu"
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": device}
    )

def has_cached_index(video_id):
    """
    Checks if a local FAISS index exists for the given video ID.
    """
    index_path = f"faiss_indexes/index_{video_id}"
    return (
        os.path.exists(os.path.join(index_path, "index.faiss")) and
        os.path.exists(os.path.join(index_path, "transcript.txt"))
    )

def load_cached_vector_store(video_id):
    """
    Loads a cached FAISS index from disk.
    """
    index_path = f"faiss_indexes/index_{video_id}"
    embeddings = get_embeddings()
    return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)

def load_cached_transcript(video_id):
    """
    Loads raw transcript text from disk cache.
    """
    path = f"faiss_indexes/index_{video_id}/transcript.txt"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def create_vector_store(transcript_text, video_id):
    """
    Splits transcript text into chunks and creates a local FAISS vector store
    using local HuggingFace embeddings. Saves the created index to disk.
    """
    # Create document object
    doc = Document(page_content=transcript_text, metadata={"source": video_id})
    
    # Split document into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents([doc])
    
    # Get cached embeddings
    embeddings = get_embeddings()
    
    # Store chunks in a local FAISS database
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    # Cache the index to disk
    folder_path = f"faiss_indexes/index_{video_id}"
    os.makedirs(folder_path, exist_ok=True)
    vector_store.save_local(folder_path)
    
    # Save the raw transcript text file
    with open(f"{folder_path}/transcript.txt", "w", encoding="utf-8") as f:
        f.write(transcript_text)
        
    return vector_store

def get_rag_chain(vector_store, groq_api_key):
    """
    Creates the retrieval and QA chain using Groq and the FAISS vector store.
    """
    # Initialize Groq LLM
    llm = ChatGroq(
        model_name="llama-3.1-8b-instant",
        temperature=0.2,
        groq_api_key=groq_api_key
    )
    
    # Set up retriever
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    
    # System prompt for synthesis
    system_prompt = (
        "You are a helpful and intelligent YouTube video assistant. Use the following pieces of retrieved context "
        "from the video transcript to answer the user's question.\n\n"
        "Your answers should be highly detailed, informative, and directly reference what was said in the video where possible. "
        "If the answer cannot be found in the provided context, state that it is not mentioned in the video transcript, "
        "but do not make up facts. Formulate your response in clean Markdown with paragraphs, bullet points, and bold text for readability.\n\n"
        "Context:\n{context}"
    )
    
    # Build prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ])
    
    # Combine docs chain
    combine_docs_chain = create_stuff_documents_chain(llm, prompt)
    
    # Create retrieval chain
    retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)
    return retrieval_chain

def query_rag_engine(retrieval_chain, question, chat_history_list):
    """
    Queries the RAG chain and returns the generated answer.
    """
    # Format chat history for LangChain
    formatted_history = []
    for msg in chat_history_list:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            formatted_history.append(("human", content))
        elif role == "assistant":
            formatted_history.append(("assistant", content))
            
    response = retrieval_chain.invoke({
        "input": question,
        "chat_history": formatted_history
    })
    
    return response["answer"]
