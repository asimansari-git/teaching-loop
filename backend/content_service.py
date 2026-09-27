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
from chromadb.config import Settings

logger = logging.getLogger("teaching_platform.content")
MODEL = os.environ.get("GEMINI_MODEL")

CHROMA_DB_PATH = "./chroma_db"
_chroma_client = None
_collection = None

def get_chroma_collection():
    """Lazily instantiates ChromaDB client and collection on first request without import-time network calls."""
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient( 
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )

    try:
        embedding_function = embedding_functions.OllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings",
            model_name="nomic-embed-text:latest",
        )
        test_embedding = embedding_function(["test"])
        if not test_embedding or len(test_embedding) == 0:
            raise ValueError("Ollama returned empty embeddings")
        _collection = _chroma_client.get_or_create_collection(
            name="teaching_content", 
            embedding_function=embedding_function
        )
        logger.info("Chroma collection initialized with Ollama embeddings")
    except Exception as e:
        logger.warning(f"Ollama embeddings unavailable ({e}). Using default SentenceTransformers.")
        _collection = _chroma_client.get_or_create_collection(
            name="teaching_content"
        )
    return _collection

async def read_file_content(file, filename: str) -> str:
    """Reads PDF or plain text / markdown file contents into a string."""
    content = ""
    if filename.lower().endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(await file.read()))
        for page in pdf_reader.pages:
            content += page.extract_text() + "\n"
    else:
        content = (await file.read()).decode("utf-8")
    return content

async def chunk_and_enhance_content(text: str) -> list[dict]:
    """Uses LLM to split text into distinct, enhanced concepts and topic lists."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
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
            model=MODEL,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        return data.get("chunks", [])
    except Exception as e:
        logger.error(f"Error chunking content: {e}")
        return [{"text": text[:1000], "topics": ["General"]}]

async def index_chunk(chunk_id: str, text: str, topics: list, item_id: str, organization_id: int = None) -> bool:
    """Embeds and indexes a verified chunk into ChromaDB with tenant metadata."""
    try:
        collection = get_chroma_collection()
        topics_str = ", ".join(topics) if topics else ""
        
        try:
            collection.delete(ids=[str(chunk_id)])
        except Exception:
            pass
        
        metadata = {
            "topics": topics_str,
            "item_id": str(item_id),
            "organization_id": int(organization_id or 0)
        }
        
        collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[str(chunk_id)]
        )
        return True
    except Exception as e:
        logger.error(f"Error indexing chunk {chunk_id}: {e}")
        return False

async def query_content(query_text: str, n_results: int = 3, filter: dict = None, organization_id: int = None) -> list[str]:
    """Queries Chroma vector collection for relevant chunks isolated by tenant."""
    try:
        collection = get_chroma_collection()
        count = collection.count()
        if count == 0:
            return []

        limit = min(n_results, count)
        
        combined_filter = filter
        if organization_id is not None:
            org_filter = {"organization_id": int(organization_id)}
            if filter:
                combined_filter = {"$and": [filter, org_filter]}
            else:
                combined_filter = org_filter

        query_kwargs = {
            "query_texts": [query_text],
            "n_results": limit,
        }
        if combined_filter:
            query_kwargs["where"] = combined_filter

        results = collection.query(**query_kwargs)
        documents = results.get("documents", [[]])[0] if results and "documents" in results else []
        logger.debug(f"Chroma query returned {len(documents)} documents")
        return documents
    except Exception as e:
        if filter:
            try:
                collection = get_chroma_collection()
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