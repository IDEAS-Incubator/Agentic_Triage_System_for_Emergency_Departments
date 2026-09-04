Project Overview

This repository contains code to build a RAG (Retrieval-Augmented Generation) system from scratch using local models powered by Ollama with LLaMA model.

The system retrieves relevant content from domain_knowledge folder. <br>
System can uses a local LLM to answer user queries with RAG system. <br>


## 🛠️ Setup

### 1. Clone the repository:
```bash
git clone https://github.com/IDEAS-Incubator/Agentic_Triage_System_for_Emergency_Departments
cd RAG
```

### 2. Create and activate conda environment:
```bash
conda create -n Agentic_Triage_System_for_Emergency_Departments python=3.12
conda activate Agentic_Triage_System_for_Emergency_Departments
```

### 3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 4. Install Ollama and required models:
```bash
# Install Ollama (follow instructions for your OS)
# For Windows:
winget install ollama

# Pull required models
ollama pull nomic-embed-text
ollama pull llama3.2:latest
```

### 5. Configure environment variables:

```bash
copy .env.example .env
```


## 📦 Running the Project

### 1. Chunk the data
Split the GitLab Handbook into smaller chunks:
```bash
python chunk.py
```

### 2. Generate embeddings
Create embeddings using the local embedding model:
```bash
python embeddings.py
```

### 3. Ask your question!
Run the RAG pipeline:
```bash
python rag.py "who is ceo"
```


