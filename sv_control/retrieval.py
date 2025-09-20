from chromadb import PersistentClient
from pathlib import Path
from pydantic import BaseModel
import os

class Retriever(BaseModel):
    chroma_dir: str = ".chroma"

    def client(self):
        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)
        return PersistentClient(path=self.chroma_dir)
