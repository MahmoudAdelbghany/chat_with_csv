# Chat with CSV

**Chat with CSV** is a production-ready application that enables natural language interaction with structured data. Users can upload CSV files, ask questions in plain English, and receive answers based on secure, sandboxed Python code execution.

This project has evolved from a simple prototype into a full-stack architecture with decoupled frontend/backend, persistent storage, and secure multi-user support.

<img width="1801" height="892" alt="Screenshot" src="https://github.com/user-attachments/assets/e602ada8-5cc2-4a9f-a1fa-7076b0e9dae5" />

---

## 🚀 Live Demo

- **Frontend**: [https://chat-with-csv-indol.vercel.app](https://chat-with-csv-indol.vercel.app)
- **Backend**: [https://chatwithcsv-production.up.railway.app](https://chatwithcsv-production.up.railway.app/docs)

---

## ✨ Key Features

- **Natural Language Analysis**: Ask questions like "Show me the distribution of age" or "Plot a correlation matrix".
- **Secure Code Execution**: LLM-generated Python code is sanitized via AST parsing to prevent unsafe operations (no network/file access).
- **Streaming Responses**: Real-time feedback with intermediate tool execution steps and token streaming.
- **Persistent History**: Chat sessions are stored in PostgreSQL and can be resumed later.
- **Anonymous User Isolation**: Secure cookie-based authentication ensures users only see their own data without needing a login.
- **Production Ready**: Fully Dockerized, with strict CORS and security policies for cross-domain deployment.

---

## 🛠 Tech Stack

### Frontend
- **React (Vite)**: Modern, fast tooling for building the UI.
- **Axios / Fetch**: For robust API communication.
- **CSS Modules**: Clean, component-scoped styling.

### Backend
- **FastAPI**: High-performance async Python web framework.
- **SQLModel + AsyncPG**: Async database ORM for PostgreSQL.
- **Pandas**: Core data manipulation library.

### Infrastructure
- **PostgreSQL**: Relational database for structured persistence.
- **Docker & Docker Compose**: Containerization for consistent dev/prod environments.
- **Railway & Vercel**: Deployment platforms for backend and frontend respectively.

---

## 🛡 Security Model

Security is a core design principle:

2.  **Code Sandboxing**: We do not blindly execute code.
    - **AST Parsing**: All code is parsed to reject dangerous nodes (`Import`, `Exec`, etc.).
    - **Allowlisting**: Only specific safe libraries (`pandas`, `numpy`, `matplotlib`) are allowed.
    - **Restricted Globals**: Execution runs in a stripped-down global scope.

3.  **Authentication**:
    - **Anonymous Sessions**: Users are identified by a secure, HTTP-only `user_id` cookie.
    - **Cross-Origin Security**: Configured with `SameSite=None` and `Secure=True` to allow safe cross-domain communication between Vercel and Railway.

---

## ⚡ Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (Recommended)

### Quick Start (Docker)

1.  **Clone & Configure**:
    ```bash
    cp .env.example .env
    # Add your OPENAI_API_KEY to .env
    ```

2.  **Run**:
    ```bash
    docker compose up --build
    ```
    - Frontend: `http://localhost:5173`
    - Backend: `http://localhost:8000`

### Manual Setup (No Docker)

**Backend:**
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 📚 Documentation

- [Architecture Overview](ARCHITECTURE.md): Deep dive into system design and data flow.
- [Changelog](CHANGELOG.md): Version history and feature updates.

---

## ⚖️ License

MIT License
