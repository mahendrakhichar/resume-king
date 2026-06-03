"""Vector storage service utilizing ChromaDB for storing and matching resumes/job descriptions."""

import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class VectorService:
    """Handles ChromaDB semantic vector operations for resume indexing and job matching."""

    _client: Optional[chromadb.PersistentClient] = None
    _resume_collection = None

    @classmethod
    def get_client(cls) -> chromadb.PersistentClient:
        """Initialize and return the persistent ChromaDB client."""
        if cls._client:
            return cls._client

        # Ensure persist directory exists
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB client at: {settings.chroma_persist_dir}")
        cls._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        
        # Initialize default resume collection
        cls._resume_collection = cls._client.get_or_create_collection(
            name="resume_chunks",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity for text matching
        )
        return cls._client

    @classmethod
    def get_resume_collection(cls):
        """Get the default resume collection, ensuring client is initialized."""
        if not cls._resume_collection:
            cls.get_client()
        return cls._resume_collection

    @classmethod
    async def index_resume(cls, resume_id: str, user_id: str, parsed_data: Dict[str, Any], raw_text: str):
        """
        Index a resume into ChromaDB.
        Splits skills, experience bullets, and projects into chunks for precise matching.
        """
        collection = cls.get_resume_collection()
        
        ids = []
        documents = []
        metadatas = []

        # 1. Index skills as a single unit
        skills = parsed_data.get("skills", [])
        if skills:
            skills_text = "Skills: " + ", ".join(skills)
            ids.append(f"{resume_id}_skills")
            documents.append(skills_text)
            metadatas.append({"resume_id": resume_id, "user_id": user_id, "type": "skills"})

        # 2. Index experience bullets
        experience = parsed_data.get("experience", [])
        for i, exp in enumerate(experience):
            company = exp.get("company", "Unknown")
            title = exp.get("title", "Unknown")
            bullets = exp.get("bullets", [])
            for j, bullet in enumerate(bullets):
                exp_text = f"Work Experience at {company} as {title}: {bullet}"
                ids.append(f"{resume_id}_exp_{i}_{j}")
                documents.append(exp_text)
                metadatas.append({
                    "resume_id": resume_id,
                    "user_id": user_id,
                    "type": "experience",
                    "company": company,
                    "title": title
                })

        # 3. Index projects
        projects = parsed_data.get("projects", [])
        for i, proj in enumerate(projects):
            name = proj.get("name", "Unknown")
            bullets = proj.get("bullets", [])
            for j, bullet in enumerate(bullets):
                proj_text = f"Project {name}: {bullet}"
                ids.append(f"{resume_id}_proj_{i}_{j}")
                documents.append(proj_text)
                metadatas.append({
                    "resume_id": resume_id,
                    "user_id": user_id,
                    "type": "project",
                    "project_name": name
                })

        # If resume is entirely plain text without structured parser output, index chunks
        if not ids and raw_text:
            chunks = cls._chunk_text(raw_text, chunk_size=500, chunk_overlap=100)
            for i, chunk in enumerate(chunks):
                ids.append(f"{resume_id}_chunk_{i}")
                documents.append(chunk)
                metadatas.append({"resume_id": resume_id, "user_id": user_id, "type": "raw_chunk"})

        if documents:
            # ChromaDB handles default embeddings under the hood using SentenceTransformers (all-MiniLM-L6-v2)
            # which is completely free, local, and requires zero external API costs.
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Indexed resume {resume_id} into ChromaDB with {len(documents)} vectors.")

    @classmethod
    async def match_job_to_resumes(cls, user_id: str, job_description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB with a Job Description to find the most relevant resume fragments for a specific user.
        """
        collection = cls.get_resume_collection()
        
        # Query ChromaDB, filtering for this specific user's indexed data
        results = collection.query(
            query_texts=[job_description],
            n_results=limit,
            where={"user_id": user_id}
        )

        matches = []
        if not results or not results.get("documents"):
            return matches

        docs = results["documents"][0]
        metadata_list = results["metadatas"][0]
        distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

        for i in range(len(docs)):
            matches.append({
                "document": docs[i],
                "metadata": metadata_list[i],
                "score": 1.0 - distances[i]  # Cosine distance to similarity score
            })
            
        logger.info(f"Found {len(matches)} vector matches for query.")
        return matches

    @classmethod
    async def delete_resume_vectors(cls, resume_id: str):
        """Delete all vector embeddings associated with a resume."""
        collection = cls.get_resume_collection()
        collection.delete(where={"resume_id": resume_id})
        logger.info(f"Deleted vectors for resume {resume_id}")

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Simple helper to split raw text into overlapping chunks."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks
