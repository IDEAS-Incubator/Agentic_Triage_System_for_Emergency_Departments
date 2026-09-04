import json
import os
import textwrap
import uuid
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
import tiktoken  # Add this import for proper token counting

load_dotenv()

CHUNK_SIZE = 750
METADATA_MARK = "---"
KNOWLEDGE_BASE_FOLDER = "./RAG/domain_knowledge"
KNOWLEDGE_BASE_FILE_FORMATS = [".md", ".pdf"]  # Changed to list to support multiple formats

CHUNK_DIR_NAME = "./RAG/chunks"
CHUNK_DIR = Path(CHUNK_DIR_NAME)

# Initialize tokenizer for accurate token counting
tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI's standard tokenizer

# Create chunks directory if it doesn't exist
CHUNK_DIR.mkdir(exist_ok=True)

def gather_knowledge_documents() -> list[str]:
    return [
        f"{directory}/{file}"
        for directory, subdirectory, files in os.walk(KNOWLEDGE_BASE_FOLDER)
        for file in files
        if any(file_format in file for file_format in KNOWLEDGE_BASE_FILE_FORMATS)  # Check for any supported format
    ]


def extract_document_metadata(document_text: str) -> tuple:
    first_mark = document_text.find(METADATA_MARK)
    if first_mark == -1:
        # No metadata found, return empty values and full text
        return "", "", document_text

    metadata_start_index = first_mark + len(METADATA_MARK)
    metadata_end_index = document_text.find(METADATA_MARK, metadata_start_index)

    if metadata_end_index == -1:
        # No closing metadata mark, return empty values and full text
        return "", "", document_text

    metadata = document_text[metadata_start_index:metadata_end_index]
    title = ""
    description = ""

    for line in metadata.split("\n"):
        if "title:" in line:
            title = line.replace("title: ", "").replace('"', "").strip()
        if "description:" in line:
            description = line.replace("description: ", "").replace('"', "").strip()

    return title, description, document_text[metadata_end_index + len(METADATA_MARK):].strip()


def create_chunks_by_tokens(text: str, max_tokens: int) -> list[str]:
    """Create chunks based on token count, not character count."""
    tokens = tokenizer.encode(text)
    chunks = []

    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text)

    return chunks


def create_file_for_each_chunk(
    title: str, description: str, document: str, chunk_index: int, chunk: str
) -> None:
    chunk_id = str(uuid.uuid4())

    # Use Path to create a safe filename
    document_path = Path(document)
    safe_document_name = document_path.with_suffix("").as_posix().replace("/", "_")
    safe_document_name = safe_document_name.replace(chr(92), "_")
    safe_filename = f"{safe_document_name}_index-{chunk_index}.json"

    # Ensure chunks directory exists
    chunks_dir = Path("./RAG/chunks")
    chunks_dir.mkdir(parents=True, exist_ok=True)

    # Full path to the chunk file
    chunk_file_path = chunks_dir / safe_filename

    # Calculate actual token count
    actual_token_count = len(tokenizer.encode(chunk))

    with chunk_file_path.open("w", encoding="utf-8") as chunk_file:
        json.dump(
            {
                "id": chunk_id,
                "title": title,
                "description": description,
                "document": document,
                "chunk_text": chunk,
                "chunk_token_count": actual_token_count,  # Fixed: use actual token count
            },
            chunk_file,
            indent=4,
        )


def read_document_text(document: str) -> str:
    document_path = Path(document)

    if document_path.suffix.lower() == ".pdf":
        reader = PdfReader(document_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return document_path.read_text(encoding="utf-8")


def chunk_documents():
    documents = gather_knowledge_documents()
    for document in documents:
        try:
            document_text = read_document_text(document)
            title, description, remaining_text = extract_document_metadata(document_text)

            # Use fixed-size token-based chunking
            chunks = create_chunks_by_tokens(remaining_text, CHUNK_SIZE)

            for chunk_index, chunk in enumerate(chunks, start=1):
                create_file_for_each_chunk(
                    title, description, document, chunk_index, chunk
                )
        except Exception as e:
            print(f"Error processing {document}: {e}")


if __name__ == "__main__":
    chunk_documents()
