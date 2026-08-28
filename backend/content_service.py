import os
from google import genai
from google.genai import types
from .database import get_db
from . import models
import json
import PyPDF2
import io
import chromadb
from chromadb.utils import embedding_functions

# Initialize ChromaDB (Persistent)
CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Try to use Ollama embeddings, fallback to default if not available
try:
    print("Attempting to initialize Ollama embedding function...")
    embedding_function = embedding_functions.OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="nomic-embed-text:latest",
    )
    # Test the embedding function
    test_embedding = embedding_function(["test"])
    if not test_embedding or len(test_embedding) == 0:
        raise ValueError("Ollama returned empty embeddings")
    print(f"✓ Ollama embeddings initialized successfully (dimension: {len(test_embedding[0])})")
    collection = chroma_client.get_or_create_collection(
        name="teaching_content", 
        embedding_function=embedding_function
    )
except Exception as e:
    print(f"⚠ Warning: Could not initialize Ollama embeddings: {e}")
    print("Falling back to default SentenceTransformer embeddings (all-MiniLM-L6-v2)")
    # Use default embeddings (SentenceTransformers)
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
    {text[:30000]} # Limit input to avoid overload for now
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest", # Strong model for logic
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        return data.get("chunks", [])
    except Exception as e:
        print(f"Error chunking content: {e}")
        # Fallback: verified simple chunking?
        return [{"text": text[:1000], "topics": ["General"]}]

async def index_chunk(chunk_id: str, text: str, topics: list, item_id: str):
    """
    Embeds and indexes a verified chunk into ChromaDB.
    """
    try:
        # Prepare metadata (topics as string for metadata filter mostly only supports simple types)
        # We can store topics as comma-sep string
        topics_str = ", ".join(topics) if topics else ""
        
        # Check if chunk already exists and delete it first to avoid duplicates
        try:
            collection.delete(ids=[str(chunk_id)])
        except:
            pass  # It's okay if it doesn't exist
        
        # Add with the embedding function automatically generating embeddings
        collection.add(
            documents=[text],
            metadatas=[{"topics": topics_str, "item_id": str(item_id)}],
            ids=[str(chunk_id)]
        )
        return True
    except Exception as e:
        print(f"Error indexing chunk: {e}")
        import traceback
        traceback.print_exc()
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
        print("Results: ", documents)
        return documents
    except Exception as e:
        # If query failed (e.g., filter mismatch), attempt fallback query without filter
        if filter:
            try:
                limit = min(n_results, collection.count())
                results = collection.query(query_texts=[query_text], n_results=limit)
                documents = results.get("documents", [[]])[0] if results and "documents" in results else []
                print("Results (fallback without filter): ", documents)
                return documents
            except Exception as fallback_err:
                print(f"Error querying content (fallback): {fallback_err}")
                return []
        print(f"Error querying content: {e}")
        return []
        