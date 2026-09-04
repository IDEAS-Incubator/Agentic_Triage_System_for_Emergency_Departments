import json
import os
import time
from typing import List

from anyio import Path
from dotenv import load_dotenv
from ollama import Client

load_dotenv()

CHUNK_SIZE = 750
METADATA_MARK = "---"
KNOWLEDGE_BASE_FOLDER = "./RAG/domain_knowledge"
KNOWLEDGE_BASE_FILE_FORMATS = [".md", ".pdf"]  # Changed to list to support multiple formats

CHUNK_DIR_NAME = "./RAG/chunks"
CHUNK_DIR = Path(CHUNK_DIR_NAME)

ollama_client = Client(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))


def gather_chunk_files() -> list[str]:
    return [
        f"{directory}/{file}"
        for directory, subdirectory, files in os.walk(CHUNK_DIR_NAME)
        for file in files
        if ".json" in file
    ]


chunk_files = gather_chunk_files()

for index, chunk_file in enumerate(chunk_files, start=1):
    chunk_data = json.load(open(chunk_file))

    with open(chunk_file, "w") as c:
        response = ollama_client.embeddings(
            model=os.environ.get("EMBEDDING_MODEL", "nomic-embed-text"),
            prompt=chunk_data["chunk_text"],
        )

        chunk_data["embeddings"] = response["embedding"]
        json.dump(chunk_data, c, indent=4)

    time.sleep(0.1)
    print(f"Processed chunks -> {index}/{len(chunk_files)}")
