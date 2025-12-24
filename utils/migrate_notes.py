"""
Notes Migration Script
Migrates legacy markdown notes to VectorMemory
"""
import asyncio
import json
import os
from pathlib import Path
from config.settings import settings
from memory.vector_memory import VectorMemory

async def migrate_notes():
    print("🚀 Starting Notes Migration...")
    
    notes_dir = settings.STORAGE_DIR / "notes"
    index_file = notes_dir / "index.json"
    
    if not index_file.exists():
        print("❌ No notes index found.")
        return

    # Load index
    with open(index_file, "r") as f:
        index = json.load(f)
        
    memory = VectorMemory()
    count = 0
    
    print(f"found {len(index)} notes to migrate...")
    
    for title, meta in index.items():
        filename = meta.get("filename")
        if not filename:
            continue
            
        file_path = notes_dir / filename
        if not file_path.exists():
            print(f"⚠️ File missing: {filename}")
            continue
            
        # Read content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Construct memory content
        full_content = f"Note: {title}\n\n{content}"
        tags = meta.get("tags", [])
        
        # Add to memory
        print(f"💾 Migrating: {title}")
        await memory.add(
            content=full_content,
            memory_type="general",
            importance=0.8, # Notes are generally important
            source="migration",
            metadata={
                "original_title": title,
                "original_filename": filename,
                "tags": tags
            }
        )
        count += 1
        
    print(f"✅ Migration complete! {count} notes moved to memory.")

if __name__ == "__main__":
    asyncio.run(migrate_notes())
