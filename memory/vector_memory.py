"""
Vector Memory System using OpenAI embeddings
Semantic search, automatic importance scoring, memory consolidation
"""
import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from openai import AsyncOpenAI

from config.settings import settings

# Memory limits
MAX_MEMORIES = 500  # Maximum number of memories to keep
CLEANUP_THRESHOLD = 550  # Trigger cleanup when this many memories
MIN_IMPORTANCE_FOR_OLD = 0.4  # Old memories below this importance get removed
OLD_MEMORY_DAYS = 60  # Memories older than this are considered "old"


class VectorMemory:
    """
    Intelligent memory system with:
    - Semantic search via embeddings
    - Automatic importance scoring
    - Memory decay and consolidation
    - Context-aware retrieval
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.memories_file = settings.MEMORIES_DIR / "vector_memories.json"
        self.embeddings_file = settings.MEMORIES_DIR / "embeddings.npy"
        self.memories: list[dict] = []
        self.embeddings: np.ndarray = np.array([])
        self._load()
    
    def _load(self):
        """Load memories and embeddings from disk"""
        if self.memories_file.exists():
            with open(self.memories_file, "r", encoding="utf-8") as f:
                self.memories = json.load(f)
        
        if self.embeddings_file.exists():
            self.embeddings = np.load(self.embeddings_file)
        elif self.memories:
            # Embeddings missing, will rebuild on next add
            self.embeddings = np.array([])
    
    def _save(self):
        """Save memories and embeddings to disk"""
        with open(self.memories_file, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, indent=2, ensure_ascii=False)
        
        if len(self.embeddings) > 0:
            np.save(self.embeddings_file, self.embeddings)
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector for text"""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return np.array(response.data[0].embedding)
    
    async def add(
        self,
        content: str,
        memory_type: str = "general",
        importance: float = 0.5,
        source: str = "conversation",
        metadata: dict = None
    ) -> dict:
        """Add a new memory with embedding (with deduplication)"""
        embedding = await self._get_embedding(content)
        
        # Deduplication: check if very similar memory exists (>0.9 similarity)
        if len(self.embeddings) > 0:
            similarities = np.dot(self.embeddings, embedding) / (
                np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(embedding)
            )
            max_sim_idx = np.argmax(similarities)
            if similarities[max_sim_idx] > 0.9:
                # Update importance of existing memory instead of adding duplicate
                existing = self.memories[max_sim_idx]
                existing["importance"] = max(existing["importance"], importance)
                existing["access_count"] += 1
                existing["last_accessed"] = datetime.now().isoformat()
                self._save()
                return existing  # Return existing instead of creating new
        
        memory = {
            "id": len(self.memories),
            "content": content,
            "type": memory_type,  # fact, preference, event, task, insight
            "importance": importance,  # 0.0 to 1.0
            "source": source,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0,
            "metadata": metadata or {}
        }
        
        self.memories.append(memory)
        
        if len(self.embeddings) == 0:
            self.embeddings = embedding.reshape(1, -1)
        else:
            self.embeddings = np.vstack([self.embeddings, embedding])
        
        self._save()
        
        # Cleanup if too many memories
        self.cleanup_old_memories()
        
        return memory
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.3,
        memory_types: list[str] = None,
        recency_weight: float = 0.1
    ) -> list[dict]:
        """
        Semantic search with SMART importance scoring:
        - Boost importance when accessed (learn from usage)
        - Decay importance for never-accessed old memories
        - Weight by memory type (facts > events > general)
        """
        if not self.memories or len(self.embeddings) == 0:
            return []
        
        query_embedding = await self._get_embedding(query)
        
        # Cosine similarity
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        results = []
        now = datetime.now()
        
        # Type importance weights (facts are more valuable than general)
        type_weights = {
            "fact": 1.2,
            "preference": 1.15,
            "insight": 1.1,
            "task": 1.0,
            "event": 0.9,
            "general": 0.8
        }
        
        for i, (memory, similarity) in enumerate(zip(self.memories, similarities)):
            if similarity < min_similarity:
                continue
            
            if memory_types and memory["type"] not in memory_types:
                continue
            
            # Calculate recency score (exponential decay over 30 days)
            created = datetime.fromisoformat(memory["created_at"])
            days_old = (now - created).days
            recency_score = np.exp(-days_old / 30)
            
            # Smart importance adjustment
            base_importance = memory["importance"]
            access_boost = min(memory["access_count"] * 0.02, 0.2)  # Max +0.2 from access
            age_decay = 0 if days_old < 14 else min(days_old * 0.001, 0.1)  # Slow decay after 2 weeks
            type_weight = type_weights.get(memory["type"], 1.0)
            
            smart_importance = (base_importance + access_boost - age_decay) * type_weight
            smart_importance = max(0.1, min(1.0, smart_importance))  # Clamp to [0.1, 1.0]
            
            # Combined score
            score = (
                similarity * (1 - recency_weight) +
                recency_score * recency_weight +
                smart_importance * 0.15  # Increased importance weight
            )
            
            results.append({
                **memory,
                "similarity": float(similarity),
                "score": float(score),
                "smart_importance": float(smart_importance)
            })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Update access stats and boost importance for accessed memories
        for result in results[:limit]:
            idx = result["id"]
            self.memories[idx]["last_accessed"] = now.isoformat()
            self.memories[idx]["access_count"] += 1
            # Slight importance boost on access (learn from usage patterns)
            old_importance = self.memories[idx]["importance"]
            self.memories[idx]["importance"] = min(1.0, old_importance + 0.01)
        
        self._save()
        return results[:limit]
    
    async def get_context(self, query: str, max_tokens: int = 1500) -> str:
        """Get formatted context for the agent"""
        memories = await self.search(query, limit=15)
        
        if not memories:
            return ""
        
        # Group by type
        by_type = {}
        for m in memories:
            t = m["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(m)
        
        context_parts = ["# Relevant Memory Context"]
        
        type_labels = {
            "fact": "Known Facts",
            "preference": "User Preferences", 
            "event": "Past Events",
            "task": "Related Tasks",
            "insight": "Insights",
            "general": "General"
        }
        
        char_count = 0
        max_chars = max_tokens * 4  # Rough estimate
        
        for mem_type, mems in by_type.items():
            label = type_labels.get(mem_type, mem_type.title())
            context_parts.append(f"\n## {label}")
            
            for m in mems[:5]:  # Max 5 per type
                line = f"- {m['content']}"
                if char_count + len(line) > max_chars:
                    break
                context_parts.append(line)
                char_count += len(line)
        
        return "\n".join(context_parts)
    
    def cleanup_old_memories(self):
        """
        Remove old, low-importance memories to stay under limits
        Called automatically when memory count exceeds threshold
        """
        if len(self.memories) < CLEANUP_THRESHOLD:
            return
        
        now = datetime.now()
        keep_indices = []
        
        for i, mem in enumerate(self.memories):
            created = datetime.fromisoformat(mem["created_at"])
            days_old = (now - created).days
            
            # Keep if: recent OR high importance OR frequently accessed
            is_recent = days_old < OLD_MEMORY_DAYS
            is_important = mem["importance"] >= MIN_IMPORTANCE_FOR_OLD
            is_accessed = mem["access_count"] >= 3
            
            if is_recent or is_important or is_accessed:
                keep_indices.append(i)
        
        # If still too many, remove oldest low-scoring ones
        if len(keep_indices) > MAX_MEMORIES:
            # Score memories
            scored = []
            for i in keep_indices:
                mem = self.memories[i]
                created = datetime.fromisoformat(mem["created_at"])
                days_old = (now - created).days
                score = mem["importance"] + (mem["access_count"] * 0.1) - (days_old * 0.01)
                scored.append((i, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            keep_indices = [i for i, _ in scored[:MAX_MEMORIES]]
        
        # Rebuild memories and embeddings
        if len(keep_indices) < len(self.memories):
            new_memories = [self.memories[i] for i in sorted(keep_indices)]
            
            # Reassign IDs
            for idx, mem in enumerate(new_memories):
                mem["id"] = idx
            
            # Rebuild embeddings
            if len(self.embeddings) > 0:
                new_embeddings = self.embeddings[sorted(keep_indices)]
                self.embeddings = new_embeddings
            
            self.memories = new_memories
            self._save()
            
            return len(keep_indices)
        
        return len(self.memories)
    
    def get_stats(self) -> dict:
        """Get memory statistics"""
        if not self.memories:
            return {"total_memories": 0, "by_type": {}, "avg_importance": 0}
        
        by_type = {}
        for m in self.memories:
            t = m["type"]
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total_memories": len(self.memories),
            "by_type": by_type,
            "avg_importance": sum(m["importance"] for m in self.memories) / len(self.memories),
            "max_memories": MAX_MEMORIES
        }
