from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from .. import models, database, auth, content_service
from ..models import User, ContentItem, ContentChunk

router = APIRouter(
    prefix="/content",
    tags=["content"]
)

@router.post("/upload")
async def upload_content(
    file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Read and Process
    try:
        raw_text = await content_service.read_file_content(file, file.filename)
        chunks_data = await content_service.chunk_and_enhance_content(raw_text)
        
        # Save Item
        new_item = ContentItem(
            filename=file.filename,
            content_type=file.content_type,
            teacher_id=current_user.id,
            status="processed"
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        # Save Chunks
        for chunk in chunks_data:
            new_chunk = ContentChunk(
                content_item_id=new_item.id,
                text=chunk.get("text", ""),
                topics=chunk.get("topics", []),
                status="pending"
            )
            db.add(new_chunk)
        
        db.commit()
        return {"item_id": new_item.id, "chunks_count": len(chunks_data), "status": "processed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pending", response_model=List[models.ContentItemOut])
async def get_pending_content(
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Items that have chunks
    items = db.query(ContentItem).filter(ContentItem.teacher_id == current_user.id).all()
    # Pydantic model will fetch relation chunks
    return items

@router.post("/chunk/{chunk_id}")
async def update_chunk(
    chunk_id: int,
    updates: dict,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    chunk = db.query(ContentChunk).filter(ContentChunk.id == chunk_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
        
    if "text" in updates:
        chunk.text = updates["text"]
    if "topics" in updates:
        chunk.topics = updates["topics"]
        
    db.commit()
    return {"status": "updated"}

@router.post("/verify/{item_id}")
async def verify_item(
    item_id: int,
    current_user: User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    item = db.query(ContentItem).filter(ContentItem.id == item_id).first()
    if not item:
         raise HTTPException(status_code=404, detail="Item not found")
         
    # Mark item as verified
    item.status = "verified"
    
    # Mark all chunks as verified/approved and Index
    print("Verifying items befor indexing")
    for chunk in item.chunks:
        chunk.status = "approved"
        # Trigger Chroma Embedding
        await content_service.index_chunk(chunk.id, chunk.text, chunk.topics or [], item.id)
        
    db.commit()
    return {"status": "verified"}
