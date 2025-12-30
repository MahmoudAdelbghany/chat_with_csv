# Changelog

All notable changes to this project are documented in this file.

---

## [0.7.0] - Production Deployment & Security - 2025-12-30

### Added
- **Production Infrastructure**: Fully Dockerized backend and frontend.
- **Deployment**: Configured for Railway (backend + DB) and Vercel (frontend).
- **Strict CORS**: Configured allowed origins for production security.
- **Cross-Origin Authentication**: Implemented `SameSite=None` and `Secure=True` cookies to support Vercel-to-Railway communication.

### Fixed
- **Database Schema**: Resolved `UndefinedColumnError` in production by updating schema migrations.
- **CORS Errors**: Fixed `Access-Control-Allow-Origin` wildcard issues with credentials.

---

## [0.6.0] - Multi-User Support - 2025-12-30

### Added
- **Anonymous Sessions**: Implemented `user_id` generation via secure HTTP-only cookies.
- **Data Isolation**: Scoped all database queries (Datasets, Conversations) to the authenticated `user_id`.
- **Database Models**: Updated `Dataset` and `Conversation` tables to include `user_id`.

### Changed
- **API Endpoints**: Injected auth dependencies into all protected routes.
- **Frontend Client**: Updated Axios/Fetch to send credentials with every request.

---

## [0.5.0] - Persistence Layer - 2025-12-29

### Added
- **PostgreSQL Integration**: Replaced in-memory storage with SQLModel + asyncpg.
- **Data Persistence**: Sessions and uploads now survive server restarts.
- **Chat History**: Added ability to view and load past conversations.
- **Sidebar UI**: New sidebar component for session management and history navigation.

---

## [0.4.0] - Frontend Rewrite (React) - 2025-12-29

### Changed
- **Architecture Shift**: Migrated from Streamlit to a decoupled React + Vite frontend.
- **UI/UX**: Implemented a modern, responsive chat interface with Markdown support.
- **State Management**: Moved to client-side state with efficient re-rendering.

### Added
- **File Upload Component**: dedicated drag-and-drop upload area.
- **Streaming Support**: Real-time token streaming from backend to frontend.

---

## [0.3.0] - Backend API (FastAPI) - 2025-12-29

### Changed
- **Framework**: Migrated backend logic from Streamlit to FastAPI.
- **API Design**: Established RESTful endpoints for `/upload`, `/chat`, and `/conversations`.
- **Response Format**: adopted NDJSON for streaming complex agent events (tokens, tool calls, errors).

---

## [0.2.0] - Secure Execution Engine - 2025-12-28

### Added
- **Code Sandbox**: Implemented AST-based validation for LLM-generated Python code.
- **Safety Rules**: Blocked dangerous imports (`os`, `sys`, `subprocess`) and builtins.
- **Context Awareness**: dynamic system prompts based on uploaded CSV schema.

---

## [0.1.0] - Initial Prototype - 2025-12-02

### Added
- **MVP**: Basic Chat with CSV functionality using Streamlit.
- **LLM Integration**: Initial OpenAI integration for generating pandas code.
- **Execution**: Basic `exec()` based code running (replaced in v0.2.0).
