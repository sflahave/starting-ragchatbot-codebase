# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
- **Quick start**: `./run.sh` - Starts the FastAPI server on port 8000
- **Manual start**: `cd backend && uv run uvicorn app:app --reload --port 8000`
- **Install dependencies**: `uv sync`

### Code Quality & Formatting
- **Format code**: `scripts/format.sh` - Auto-formats code with black and organizes imports with isort
- **Lint code**: `scripts/lint.sh` - Runs flake8 linting checks
- **Quality check**: `scripts/quality-check.sh` - Runs full quality suite (formatting, linting, tests)
- **Manual commands**:
  - `uv run black .` - Format code with black
  - `uv run isort .` - Organize imports
  - `uv run flake8 .` - Run linting checks

### Environment Setup
- Create `.env` file with `ANTHROPIC_API_KEY=your_key_here`
- Uses Python 3.13+ with uv package manager
- Code formatting: black (line length 88), isort for import organization
- Linting: flake8 with black-compatible settings

## Architecture Overview

This is a full-stack RAG (Retrieval-Augmented Generation) system for querying course materials.

### Core Components

**Backend (`/backend/`)**:
- `app.py` - FastAPI application with `/api/query` and `/api/courses` endpoints
- `rag_system.py` - Main orchestrator that coordinates all components
- `vector_store.py` - ChromaDB integration for semantic search and embeddings
- `document_processor.py` - Processes course documents into chunks
- `ai_generator.py` - Anthropic Claude integration for response generation
- `session_manager.py` - Manages conversation history and sessions
- `search_tools.py` - Tool management system for search capabilities
- `models.py` - Data models for Course, Lesson, and CourseChunk
- `config.py` - Configuration management

**Frontend (`/frontend/`)**:
- Static files (HTML/CSS/JS) served by FastAPI
- `index.html` - Main web interface
- `script.js` - Frontend logic for API interactions
- `style.css` - Application styling

### Data Flow

1. Documents in `/docs/` are processed into chunks on startup
2. Course content and metadata stored in ChromaDB vector database
3. User queries trigger semantic search against vector store
4. Retrieved context is sent to Claude AI for response generation
5. Session manager tracks conversation history across queries

### Key Features

- **RAG Pipeline**: Document processing → Vector storage → Semantic retrieval → AI generation
- **Session Management**: Maintains conversation context across queries
- **Tool System**: Extensible search tools architecture
- **Course Analytics**: Tracks course statistics and titles
- **Auto-loading**: Processes documents from `/docs/` folder on startup

The application runs as a single FastAPI server that serves both the API and static frontend files.