import os
import io
import json
import logging
import PyPDF2
from google import genai
from google.genai import types
from .database import get_db
from . import models
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("teaching_platform.content")

# Initialize ChromaDB (Persistent)
CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Try to use Ollama embeddings, fallback to default if not available
try:
    logger.info("Attempting to initialize Ollama embedding function...")
    embedding_function = embedding_functions.OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text:latest",
    )
    test_embedding = embedding_function(["test"])
    if not test_embedding or len(test_embedding) == 0:
        raise ValueError("Ollama returned empty embeddings")
    logger.info(f"Ollama embeddings initialized successfully (dimension: {len(test_embedding[0])})")
    collection = chroma_client.get_or_create_collection(
        name="teaching_content", 
        embedding_function=embedding_function
    )
except Exception as e:
    logger.warning(f"Could not initialize Ollama embeddings: {e}. Falling back to default SentenceTransformer (all-MiniLM-L6-v2)")
    collection = chroma_client.get_or_create_collection(
        name="teaching_content"
    )

# Helper to read file content
async def read_file_content(file, filename) -> str:
    content = ""
    if filename.lower().endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(await file.read()))
        for page in pdf_reader.pages:
            content += page.extract_text() + "\n"
    else:
        # Assume text/markdown
        content = (await file.read()).decode("utf-8")
    return content

async def chunk_and_enhance_content(text: str) -> list[dict]:
    """
    Uses LLM to split text into meaningful chunks, enhance them, and extract topics.
    Returns: List of dicts { "text": str, "topics": [str] }
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # We might need to split very large text first if it exceeds context, 
    # but for now let's assume reasonable size or simple split.
    # A simple split by paragraphs or chars to stay within initial context if needed.
    
    prompt = f"""
    You are an expert educational content curator.
    Process the following raw learning material.
    
    Tasks:
    1. Break the text into distinct, meaningful learning chunks (concepts/sections).
    2. For each chunk:
       - **Reconstruct/Enhance**: Rewrite it to be clear, factual, and pedagogically sound. Fix errors or missing context.
       - **Topics**: Identify 3-5 relevant topics/subtopics.
       
    Return a pure JSON object with a key "chunks", which is a list of objects.
    Each object must have:
    - "text": The enhanced content string.
    - "topics": List of strings.
    
    Raw Text:
    {text[:30000]}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        return data.get("chunks", [])
    except Exception as e:
        logger.error(f"Error chunking content: {e}")
        return [{"text": text[:1000], "topics": ["General"]}]

async def index_chunk(chunk_id: str, text: str, topics: list, item_id: str):
    """
    Embeds and indexes a verified chunk into ChromaDB.
    """
    try:
        topics_str = ", ".join(topics) if topics else ""
        
        try:
            collection.delete(ids=[str(chunk_id)])
        except Exception:
            pass  # It's okay if it doesn't exist
        
        collection.add(
            documents=[text],
            metadatas=[{"topics": topics_str, "item_id": str(item_id)}],
            ids=[str(chunk_id)]
        )
        return True
    except Exception as e:
        logger.error(f"Error indexing chunk {chunk_id}: {e}")
        return False

async def query_content(query_text: str, n_results: int = 3, filter: dict = None) -> list[str]:
    """
    Query Chroma for relevant chunks.
    """
    try:
        count = collection.count()
        if count == 0:
            return []

        limit = min(n_results, count)
        query_kwargs = {
            "query_texts": [query_text],
            "n_results": limit,
        }
        if filter:
            query_kwargs["where"] = filter

        results = collection.query(**query_kwargs)
        documents = results.get("documents", [[]])[0] if results and "documents" in results else []
        logger.debug(f"Chroma query returned {len(documents)} documents")
        return documents
    except Exception as e:
        if filter:
            try:
                limit = min(n_results, collection.count())
                results = collection.query(query_texts=[query_text], n_results=limit)
                documents = results.get("documents", [[]])[0] if results and "documents" in results else []
                logger.debug(f"Chroma query fallback returned {len(documents)} documents")
                return documents
            except Exception as fallback_err:
                logger.error(f"Error querying content (fallback): {fallback_err}")
                return []
        logger.error(f"Error querying content: {e}")
        return []
        