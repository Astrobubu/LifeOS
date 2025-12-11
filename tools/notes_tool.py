import json
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from config.settings import settings
from .base_tool import BaseTool, ToolResult


def fuzzy_match(query: str, candidates: list[str], threshold: float = 0.5) -> list[tuple[str, float]]:
    """Find fuzzy matches for a query in a list of candidates"""
    query_lower = query.lower().strip()
    results = []
    
    for candidate in candidates:
        candidate_lower = candidate.lower()
        
        # Exact match
        if query_lower == candidate_lower:
            results.append((candidate, 1.0))
            continue
        
        # Contains match
        if query_lower in candidate_lower or candidate_lower in query_lower:
            results.append((candidate, 0.9))
            continue
        
        # Word overlap
        query_words = set(query_lower.split())
        candidate_words = set(candidate_lower.split())
        overlap = len(query_words & candidate_words)
        if overlap > 0:
            score = overlap / max(len(query_words), len(candidate_words))
            if score >= threshold:
                results.append((candidate, score))
                continue
        
        # Sequence similarity
        ratio = SequenceMatcher(None, query_lower, candidate_lower).ratio()
        if ratio >= threshold:
            results.append((candidate, ratio))
    
    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    return results


class NotesTool(BaseTool):
    name = "notes"
    description = "Create, read, update, and delete notes"
    
    def __init__(self):
        self.notes_dir = settings.NOTES_DIR
        self.index_file = self.notes_dir / "index.json"
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure index file exists"""
        if not self.index_file.exists():
            self._save_index({})
    
    def _load_index(self) -> dict:
        """Load notes index"""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def _save_index(self, index: dict):
        """Save notes index"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
    
    def get_function_schemas(self) -> list[dict]:
        return [
            self._make_schema(
                name="create_note",
                description="Create a new note with a title and content",
                parameters={
                    "title": {"type": "string", "description": "Title of the note"},
                                                "content": {
                                                    "type": "string",
                                                    "description": "The exact literal content of the note. Do NOT elaborate, summarize, or add extra text. Just save exactly what the user said."
                                                },
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for the note"}
                },
                required=["title", "content"]
            ),
            self._make_schema(
                name="read_note",
                description="Read a note by its title",
                parameters={
                    "title": {"type": "string", "description": "Title of the note to read"}
                },
                required=["title"]
            ),
            self._make_schema(
                name="update_note",
                description="Update an existing note's content",
                parameters={
                    "title": {"type": "string", "description": "Title of the note to update"},
                    "content": {"type": "string", "description": "New content for the note"},
                    "append": {"type": "boolean", "description": "If true, append to existing content instead of replacing"}
                },
                required=["title", "content"]
            ),
            self._make_schema(
                name="delete_note",
                description="Delete a note by its title",
                parameters={
                    "title": {"type": "string", "description": "Title of the note to delete"}
                },
                required=["title"]
            ),
            self._make_schema(
                name="list_notes",
                description="List all notes, optionally filtered by tags",
                parameters={
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"}
                },
                required=[]
            ),
            self._make_schema(
                name="search_notes",
                description="Search notes by keyword",
                parameters={
                    "query": {"type": "string", "description": "Search query"}
                },
                required=["query"]
            )
        ]
    
    async def execute(self, function_name: str, arguments: dict) -> ToolResult:
        try:
            if function_name == "create_note":
                return await self._create_note(**arguments)
            elif function_name == "read_note":
                return await self._read_note(**arguments)
            elif function_name == "update_note":
                return await self._update_note(**arguments)
            elif function_name == "delete_note":
                return await self._delete_note(**arguments)
            elif function_name == "list_notes":
                return await self._list_notes(**arguments)
            elif function_name == "search_notes":
                return await self._search_notes(**arguments)
            else:
                return ToolResult(success=False, error=f"Unknown function: {function_name}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def _title_to_filename(self, title: str) -> str:
        """Convert title to safe filename"""
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        return safe.strip().replace(" ", "_")[:50] + ".md"
    
    async def _create_note(self, title: str, content: str, tags: list = None) -> ToolResult:
        index = self._load_index()
        
        if title in index:
            return ToolResult(success=False, error=f"Note '{title}' already exists. Use update_note to modify it.")
        
        filename = self._title_to_filename(title)
        filepath = self.notes_dir / filename
        
        # Write note file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Update index
        index[title] = {
            "filename": filename,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._save_index(index)
        
        return ToolResult(success=True, data=f"Note '{title}' created successfully")
    
    def _find_note(self, title: str, index: dict) -> str | None:
        """Find a note by title using fuzzy matching"""
        if title in index:
            return title
        
        matches = fuzzy_match(title, list(index.keys()), threshold=0.4)
        if matches:
            return matches[0][0]  # Return best match
        return None
    
    async def _read_note(self, title: str) -> ToolResult:
        index = self._load_index()
        
        actual_title = self._find_note(title, index)
        if not actual_title:
            # List available notes to help
            available = list(index.keys())[:5]
            hint = f" Available: {', '.join(available)}" if available else ""
            return ToolResult(success=False, error=f"Note '{title}' not found.{hint}")
        
        filepath = self.notes_dir / index[actual_title]["filename"]
        
        if not filepath.exists():
            return ToolResult(success=False, error=f"Note file missing for '{actual_title}'")
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        return ToolResult(success=True, data={
            "title": actual_title,
            "content": content,
            "tags": index[actual_title].get("tags", []),
            "created_at": index[actual_title].get("created_at"),
            "updated_at": index[actual_title].get("updated_at")
        })
    
    async def _update_note(self, title: str, content: str, append: bool = False) -> ToolResult:
        index = self._load_index()
        
        actual_title = self._find_note(title, index)
        if not actual_title:
            return ToolResult(success=False, error=f"Note '{title}' not found")
        
        filepath = self.notes_dir / index[actual_title]["filename"]
        
        if append:
            with open(filepath, "r", encoding="utf-8") as f:
                existing = f.read()
            content = existing + "\n\n" + content
        # else: content remains as passed
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        index[actual_title]["updated_at"] = datetime.now().isoformat()
        self._save_index(index)
        
        return ToolResult(success=True, data=f"Note '{actual_title}' updated successfully")
    
    async def _delete_note(self, title: str) -> ToolResult:
        index = self._load_index()
        
        actual_title = self._find_note(title, index)
        if not actual_title:
            available = list(index.keys())[:5]
            hint = f" Available: {', '.join(available)}" if available else ""
            return ToolResult(success=False, error=f"Note '{title}' not found.{hint}")
        
        filepath = self.notes_dir / index[actual_title]["filename"]
        
        if filepath.exists():
            filepath.unlink()
        
        del index[actual_title]
        self._save_index(index)
        
        return ToolResult(success=True, data=f"Note '{actual_title}' deleted successfully")
    
    async def _list_notes(self, tags: list = None) -> ToolResult:
        index = self._load_index()
        
        notes = []
        for title, meta in index.items():
            if tags:
                if not any(t in meta.get("tags", []) for t in tags):
                    continue
            notes.append({
                "title": title,
                "tags": meta.get("tags", []),
                "updated_at": meta.get("updated_at")
            })
        
        return ToolResult(success=True, data=notes)
    
    async def _search_notes(self, query: str) -> ToolResult:
        index = self._load_index()
        query_lower = query.lower()
        results = []
        
        for title, meta in index.items():
            filepath = self.notes_dir / meta["filename"]
            if not filepath.exists():
                continue
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            if query_lower in title.lower() or query_lower in content.lower():
                # Get snippet around match
                content_lower = content.lower()
                idx = content_lower.find(query_lower)
                if idx != -1:
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 50)
                    snippet = "..." + content[start:end] + "..."
                else:
                    snippet = content[:100] + "..."
                
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "tags": meta.get("tags", [])
                })
        
        return ToolResult(success=True, data=results)
