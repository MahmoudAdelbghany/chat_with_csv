# Architecture Overview

This document describes the high-level architecture of **Chat with CSV**, focusing on system boundaries, data flow, and design decisions.

---

## System Overview

Chat with CSV is a full-stack LLM-powered application that allows users to upload CSV files and interact with them using natural language.

The system is composed of four major layers:

1. **Frontend**: React (Vite) application hosted on Vercel.
2. **Backend API**: FastAPI service hosted on Railway.
3. **Agent & Execution Layer**: Sandboxed Python execution engine.
4. **Persistence Layer**: PostgreSQL database and local filesystem.

Each layer is designed to be loosely coupled and stateless where possible.

---

## High-Level Data Flow

```mermaid
graph TD
    User[Browser (React)] -->|HTTPS / Secure Cookies| API[FastAPI Backend]
    API -->|Async Persistance| DB[(PostgreSQL)]
    API -->|File Access| FS[Filesystem]
    API -->|Prompt & Context| LLM[LLM Agent]
    LLM -->|Generated Code| Sandbox[Execution Sandbox]
    Sandbox -->|Results| LLM
    LLM -->|Streaming Response| User
```

---

## Frontend Architecture

**Technology**
- **Framework**: React (Vite)
- **State Management**: React Hooks (minimal state)
- **Networking**: Axios / Fetch API
- **Auth**: Cookie-based session handling

**Key Responsibilities**
- **File Upload**: Direct upload to backend with progress tracking.
- **Chat Interface**: Rendering streaming NDJSON responses for real-time feedback.
- **Session Management**: Handling session switching and history viewing via sidebar.
- **Security**: Using `credentials: include` to support secure cross-origin cookies.

**Key Design Decisions**
- **Stateless UI**: The frontend does not persist chat state locally; it relies on the backend as the source of truth.
- **Strict CORS Support**: Configured to send `withCredentials: true` to handle secure `SameSite=None` cookies from the backend.

---

## Backend API Architecture

**Technology**
- **Framework**: FastAPI
- **Database ORM**: SQLModel + asyncpg
- **Concurrency**: Fully async/await architecture

**Responsibilities**
- **Authentication**: Anonymous user identification via HTTP-only secure cookies.
- **Session Management**: Reconstructing agent state per request from the database.
- **Streaming**: Delivering LLM tokens and tool execution status in real-time via NDJSON.

**Stateless Design**
The backend does not keep long-lived in-memory chat state.
For every request:
1.  **Identify User**: Validate `user_id` from the secure cookie.
2.  **Load Context**: Fetch conversation history and dataset metadata from PostgreSQL.
3.  **Reconstruct Agent**: Initialize the CSV Agent with the dataset context.
4.  **Execute & Reply**: Run the agent lifecycle and stream results back.

---

## Persistence Layer

### Database (PostgreSQL)

**Schema Entities**
- **Dataset**: Metadata about uploaded files (`filename`, `path`, `owner`).
- **Conversation**: Chat session metadata (`title`, `created_at`).
- **Message**: Individual chat entries (`role`, `content`, `timestamp`).

**Relationships**
- **User Scope**: All entities are scoped by a `user_id` string index to ensure isolation.
- **Ownership**: Users own Datasets; Datasets have multiple Conversations.

**(Production Note)**: Tables are automatically created using `SQLModel.metadata.create_all` on startup.

### File Storage

- **Storage**: Uploaded CSVs are stored on the local container filesystem under `/uploads`.
- **References**: Database stores file paths, allowing efficiently reloading dataframes into memory when needed.

---

## Agent & Execution Layer

### Agent Design

- **Stateless Reconstruction**: The agent is initialized fresh for each turn, preventing memory leaks and state drift.
- **Dynamic System Prompts**: Prompts are generated based on the CSV schema (column names, types) of the active dataset.

### Secure Code Execution

LLM-generated Python code is **never executed directly** in the main process.

**Safety Mechanisms**:
- **AST Parsing**: Code is parsed into an Abstract Syntax Tree before execution.
- **Import Allowlist**: Only safe modules (e.g., `pandas`, `numpy`, `matplotlib`) are permitted.
- **Builtin Blocks**: Dangerous functions like `open()`, `exec()`, `eval()`, and network calls are blocked.
- **Verification**: If code violates safety rules, execution is rejected before running.

---

## Authentication & Security Model

### Anonymous Sessions
- **No Sign-up**: Users are identified implicitly via a generated UUID.
- **Transport**: The UUID is stored in a `user_id` cookie.

### Cross-Origin Security (Vercel <-> Railway)
To support the split deployment architecture:
- **CORS**: Backend allows specific origins (Vercel frontend) with `allow_credentials=True`.
- **Cookie Attributes**:
  - `SameSite=None`: Allows cookies to be sent in cross-site requests.
  - `Secure=True`: Requires HTTPS (essential for `SameSite=None`).
  - `HttpOnly`: Prevents client-side scripts from accessing the cookie.

---

## Scalability Considerations

- **Horizontal Scaling**: The stateless backend design allows running multiple replicas.
- **Database**: PostgreSQL handles concurrent load efficiently using async drivers.
- **Optimizations**: Streaming responses keep connection overhead low and improve perceived latency.
