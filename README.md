<div align="center">

# 👑 ResumeForge AI (Resume King)
### Autonomous Multi-Agent Resume Tailoring & ATS Optimization Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Agentic_Workflow-LangGraph-FF6F00)](https://langchain-ai.github.io/langgraph/)
[![OpenRouter](https://img.shields.io/badge/LLM_Gateway-OpenRouter-6366F1)](https://openrouter.ai/)

<p align="center">
  Transform your resume with an ensemble of AI agents debating, optimizing, and tailoring your experience directly against job descriptions in real-time.
</p>

</div>

---

## 🌟 Highlights & Features

* 🤖 **Multi-Agent Orchestration**: Powered by **LangGraph**, specialized autonomous agents collaborate in a structured state machine:
  * **JD Analyzer**: Deconstructs requirements, required skills, and hidden preferences.
  * **ATS Matcher**: Computes real-time keyword coverage and semantic vector alignment.
  * **Resume Rewriter**: Rewrites bullet points using strong action verbs and quantified impact.
  * **Hiring Debate**: Simulates recruiter vs. hiring manager debate to stress-test your profile.
  * **Interview Prep Agent**: Generates targeted technical and behavioral interview preparation guides.
* ⚡ **Multi-Tier LLM Routing**: Built on top of **OpenRouter** with dynamic task-based model selection (Qwen Coder, Gemma, LLaMA 3.3, MiniMax) and automatic multi-provider fallback.
* 📊 **Interactive ATS Score Gauge & Diff Viewer**: Visually inspect side-by-side changes and track ATS score improvements in real-time.
* 🔄 **Live Progress Streaming**: Real-time agent status updates streamed over WebSockets.
* 🛡️ **Plug-and-Play Authentication**: Integrated Clerk authentication with zero-config local development mock mode.

---

## 🏗️ Architecture Overview

```
                      ┌─────────────────────────┐
                      │    Web Client (React)   │
                      │  Tailwind + TypeScript  │
                      └────────────┬────────────┘
                                   │ HTTP / WebSocket
                      ┌────────────▼────────────┐
                      │    FastAPI Application  │
                      │  Auth, Routes, Services │
                      └────────────┬────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
         ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
         │ PostgreSQL  │    │  ChromaDB   │    │  LangGraph  │
         │ (SQLAlchemy)│    │(VectorStore)│    │ Multi-Agent │
         └─────────────┘    └─────────────┘    └──────┬──────┘
                                                      │
                                               ┌──────▼──────┐
                                               │ OpenRouter  │
                                               │ LLM Gateway │
                                               └─────────────┘
```

---

## 🚀 Quickstart Guide

### Prerequisites
* **Node.js** >= 18.x
* **Python** >= 3.10
* **PostgreSQL** (Local instance or free cloud database like [Neon](https://neon.tech))

---

### 1. Clone the Repository

```bash
git clone https://github.com/mahendrakhichar/resume-king.git
cd resume-king
```

---

### 2. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # macOS/Linux:
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows (PowerShell):
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to add your `OPENROUTER_API_KEY` and `DATABASE_URL`.*
5. Start the backend development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   *The API and interactive Swagger docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs).*

---

### 3. Frontend Setup (React + Vite)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. *(Optional)* Configure frontend environment variables:
   ```bash
   cp .env.example .env
   ```
4. Start the frontend development server:
   ```bash
   npm run dev
   ```
   *The application will be live at [http://localhost:5173](http://localhost:5173).*

---

## 📁 Repository Structure

```
resume-king/
├── backend/                  # FastAPI Application
│   ├── agents/               # LangGraph AI Agents (ATS, Rewriter, Debate, etc.)
│   ├── api/                  # FastAPI Route Handlers & Endpoints
│   ├── config/               # Pydantic Settings & Environment Loaders
│   ├── db/                   # Async SQLAlchemy Session & Database Base
│   ├── models/               # SQLAlchemy Database Models
│   ├── parsers/              # PDF & Text Resume Parsing Engines
│   ├── schemas/              # Pydantic Request & Response Schemas
│   ├── services/             # LLM Service, Vector Service & Auth Service
│   ├── utils/                # File Handlers, Logging, and Helpers
│   ├── workflows/            # LangGraph Workflow Nodes & State Definitions
│   └── main.py               # Application Entrypoint
├── frontend/                 # React 19 + Vite + TypeScript Application
│   ├── public/               # Static Assets & Icons
│   └── src/
│       ├── components/       # UI Components (Agents, Resume, Review, Layout)
│       ├── hooks/            # Custom Hooks (WebSockets, State)
│       ├── lib/              # API Client & Auth Wrappers
│       ├── pages/            # Page Views (Dashboard, Session, History)
│       ├── stores/           # Zustand State Stores
│       └── types/            # TypeScript Type Definitions
├── .github/                  # Issue & PR Templates
├── CONTRIBUTING.md           # Contribution Guidelines
├── CODE_OF_CONDUCT.md        # Contributor Code of Conduct
├── SECURITY.md               # Security Policy
└── LICENSE                   # MIT License
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Please check out [CONTRIBUTING.md](CONTRIBUTING.md) to learn how to get started, run tests, and submit pull requests.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 🔒 Security

If you discover any security issues or vulnerabilities, please review our [SECURITY.md](SECURITY.md) policy for responsible disclosure.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/mahendrakhichar">Mahendra Khichar</a> and contributors.
</p>
