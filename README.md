# Review Response System 🤖💬

An automated, multi-agent AI pipeline for processing customer reviews. Specialized agents (monitor, triage, research, drafter, QA) collaborate via websockets to ingest feedback, gather context, and generate brand-compliant, personalized responses. Includes a real-time React dashboard and FastAPI backend to track the entire review lifecycle.

---

## 🏗️ Architecture Overview

The system is built on a **multi-agent architecture** utilizing the Band.ai platform for secure, stateful WebSocket communication between agents. 

### The Agents
1. **Monitor Agent** 📡: The entry point. It receives webhooks or direct injections, parses the review, extracts basic sentiment, and initiates the pipeline envelope.
2. **Triage Agent** 🚦: Classifies the review (e.g., complaint, compliment, question), determines priority severity, and flags if human intervention is required.
3. **Research Agent** 🔍: Queries the local database (`data/reviews.db`) to look up past customer interactions, booking history, or hotel policies to provide factual context.
4. **Drafting Agent** ✍️: Generates a personalized, empathetic response based on the gathered context, triage classification, and the original review.
5. **QA Agent** ⚖️: Strictly reviews the draft against 10 brand voice and compliance checks (e.g., `addresses_core_complaint`, `no_legal_liability_admission`). It computes a weighted score and can **bounce the draft back to the Drafting Agent** for revision if it hard fails or scores below the threshold.

### The Dashboard
- **Frontend**: A React (Vite) application that visualizes the pipeline. It features a live DAG (Directed Acyclic Graph) view using Server-Sent Events (SSE) to animate reviews as they flow through the agents.
- **Backend Bridge**: A FastAPI application that securely bridges the Band.ai agent webhooks to the frontend dashboard.

---

## 🚀 Installation & Setup

### Prerequisites
- **Python 3.12+**
- **Node.js 18+** & npm
- [uv](https://github.com/astral-sh/uv) (Python package manager)

### 1. Clone & Python Dependencies
```bash
# Clone the repository
git clone git@github.com:resilientbeast/review-response-system.git
cd review-response-system

# Install Python dependencies using uv
uv sync
```

### 2. Frontend Dependencies
```bash
cd dashboard/frontend
npm install
cd ../..
```

### 3. Environment Configuration
Copy the `.env.example` file to create your local `.env`:
```bash
cp .env.example .env
```
Fill in your `BAND_API_KEY`, `OPENAI_API_KEY` (or chosen LLM provider), and any other required secrets.

Next, copy the agent configuration:
```bash
cp agent_config.yaml.example agent_config.yaml
```

### 4. Database Setup
Initialize the local SQLite database used by the Research agent:
```bash
sqlite3 data/reviews.db < migrations/001_initial.sql
```

---

## 🏃‍♂️ Running the System

To see the full pipeline in action, you need to start three separate processes.

**1. Start the Agent Pipeline**
Spins up all the agents (Monitor, Triage, Research, Drafter, QA) and connects them to Band.ai:
```bash
uv run python run_all.py
```

**2. Start the Backend Dashboard Bridge**
Provides the SSE stream to the frontend:
```bash
uv run uvicorn dashboard.bridge:app --port 8001
```

**3. Start the Frontend Dashboard**
Runs the React development server:
```bash
cd dashboard/frontend
npm run dev
```

*(Optional)* If you want to ingest webhooks from external platforms, start the ingestion receiver:
```bash
uv run uvicorn ingestion.receiver:app --port 8000
```

---

## 🧪 Demo & Testing

1. Ensure all three core processes are running.
2. Open your browser and navigate to the React dashboard at `http://localhost:5173`.
3. Click the **"Inject Review"** button on the dashboard.
4. **Watch the magic happen:**
   - The Monitor agent will pick up the payload and pass it to Triage.
   - You'll see the UI animate as the review flows through Research, Drafting, and QA.
   - The QA panel will display the 10 specific boolean checks, calculating a final score.
   - If the Drafter uses corporate speak or fails to address the core complaint, watch the QA agent flag the error and dynamically route it back to the Drafter for a rewrite!
   
## 🗂️ Project Structure

- `/agents`: Contains the Python code and logic for each specialized agent.
- `/dashboard`: Contains the FastAPI bridge (`bridge.py`) and the React frontend (`/frontend`).
- `/shared`: Shared schemas, models, and base agent configurations.
- `/data` & `/migrations`: SQLite database files and SQL migrations.
- `run_all.py`: Orchestration script to run all agents simultaneously.
