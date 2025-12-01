# BugBridge

**Automated Feedback-to-Resolution Loop for Enterprise Teams**

BugBridge is an AI-powered feedback management platform that automates the entire feedback lifecycle—from collection and analysis to resolution and customer notification. It bridges the gap between customer feedback portals (like Canny.io) and development tracking systems (like Jira), ensuring no critical issue falls through the cracks and every customer feels heard.

---

## Overview

BugBridge transforms raw customer feedback into actionable development tasks using intelligent AI agents built on LangGraph and LangChain frameworks. The platform:

1. **Collects** feedback from Canny.io automatically
2. **Analyzes** feedback using AI agents to detect bugs, analyze sentiment, and prioritize issues
3. **Creates** Jira tickets automatically with context and priority
4. **Monitors** Jira ticket status and resolution
5. **Notifies** customers when their issues are resolved
6. **Reports** daily summaries and analytics
7. **Visualizes** data through an intuitive and interactive web dashboard

### Key Features

- 🤖 **AI-Powered Analysis**: Intelligent bug detection, sentiment analysis, and priority scoring using XAI (Grok models)
- 🔄 **End-to-End Automation**: Complete workflow from feedback collection to customer notification
- 📊 **Intelligent Prioritization**: Multi-factor priority scoring based on engagement, sentiment, and business impact
- 🔗 **Seamless Integrations**: Native Canny.io and Jira integrations via MCP server
- 📈 **Daily Reporting**: Comprehensive analytics and insights
- 🎨 **Interactive Dashboard**: Intuitive web dashboard with real-time metrics, visualizations, and configuration management

---

## Project Status

🚧 **In Development** - Platform implementation in progress

### Completed

- ✅ Product Requirements Document (PRD)
- ✅ Detailed implementation task breakdown
- ✅ Platform positioning and strategy documentation
- ✅ Canny.io API reference documentation
- ✅ MCP-atlassian server integration (Jira/Confluence)

### In Progress

- 🔨 Project setup and foundation
- 🔨 AI agent system architecture
- 🔨 Feedback collection module
- 🔨 Dashboard development (frontend & API)

---

## Technology Stack

### Core Frameworks

- **LangGraph**: Agent workflow orchestration and state management
- **LangChain**: LLM integration, tooling, and prompt management
- **XAI (xAI) API**: LLM operations using Grok models (grok-beta or grok-2)

### Language & Runtime

- **Python 3.10+**: Backend implementation language
- **TypeScript/JavaScript**: Frontend dashboard implementation
- **asyncio**: For asynchronous operations

### Data Storage

- **PostgreSQL**: Persistent storage for feedback, analysis results, and workflow state
- **Redis**: Caching and temporary state (optional)

### Integrations

- **Canny.io REST API**: Feedback collection and notifications
- **MCP (Model Context Protocol)**: Jira integration via existing mcp-atlassian server

### Backend API

- **FastAPI**: Modern Python web framework for REST API
- **JWT / OAuth2**: Authentication and authorization

### Frontend (Dashboard)

- **React**: UI framework for interactive dashboard
- **Next.js**: React framework with SSR and API routes (optional)
- **Tailwind CSS**: Utility-first CSS framework for responsive design
- **Chart.js / Recharts**: Interactive data visualization library
- **React Query / TanStack Query**: Data fetching and caching

### Key Libraries

- `pydantic`: Data validation and structured outputs
- `httpx`: Async HTTP client
- `sqlalchemy`: ORM for database operations
- `asyncpg`: Async PostgreSQL driver
- `apscheduler`: Task scheduling for reports

---

## Project Structure

```
BugBridge/
├── bugbridge/                    # Main application (to be created)
│   ├── agents/                   # AI agents implementation
│   │   ├── collection.py        # Feedback Collection Agent
│   │   ├── bug_detection.py     # Bug Detection Agent
│   │   ├── sentiment.py         # Sentiment Analysis Agent
│   │   ├── priority.py          # Priority Scoring Agent
│   │   ├── jira_creation.py     # Jira Creation Agent
│   │   ├── monitoring.py        # Monitoring Agent
│   │   ├── notification.py      # Notification Agent
│   │   └── reporting.py         # Reporting Agent
│   ├── models/                   # Pydantic data models
│   ├── database/                 # Database models and schema
│   ├── integrations/             # External API integrations
│   │   ├── canny.py             # Canny.io API client
│   │   ├── xai.py               # XAI API wrapper
│   │   └── mcp_jira.py          # MCP Jira client
│   ├── workflows/                # LangGraph workflows
│   │   ├── main.py              # Main feedback processing workflow
│   │   └── reporting.py         # Daily report generation workflow
│   ├── api/                      # REST API for dashboard
│   │   ├── routes/              # API route handlers
│   │   ├── middleware/          # Authentication and other middleware
│   │   └── models/              # API request/response models
│   ├── tools/                    # LangChain tools
│   └── utils/                    # Utility functions
├── dashboard/                    # Frontend dashboard (React/Next.js)
│   ├── src/                      # Source code
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   └── services/            # API service functions
│   └── package.json             # Frontend dependencies
├── mcp-atlassian/                # MCP server for Jira/Confluence integration
├── tasks/                        # Project documentation
│   ├── prd-bugbridge-platform.md    # Product Requirements Document
│   └── tasks-bugbridge-platform.md  # Implementation task breakdown
├── tests/                        # Test suite (to be created)
├── POSITIONING.md                # Platform positioning and strategy
├── CANNY_API_REFERENCE.md        # Canny.io API documentation
└── README.md                     # This file
```

---

## Documentation

### Planning & Requirements

- **[Product Requirements Document (PRD)](tasks/prd-bugbridge-platform.md)** - Comprehensive technical specifications, architecture design, and implementation details
- **[Implementation Tasks](tasks/tasks-bugbridge-platform.md)** - Detailed task breakdown with 160+ sub-tasks organized into 11 phases

### Strategy & Positioning

- **[POSITIONING.md](POSITIONING.md)** - Platform positioning, market analysis, value proposition, and go-to-market strategy
- **[CANNY_API_REFERENCE.md](CANNY_API_REFERENCE.md)** - Complete Canny.io API reference with endpoints, examples, and usage

### Architecture

- **LangGraph Workflows**: Agent orchestration and state management
- **LangChain Integration**: LLM operations and tooling
- **AI Agents**: Specialized agents for each processing step
- **Database Schema**: PostgreSQL schema for persistent storage

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL database
- Canny.io API key
- XAI API key
- Jira access (via MCP server)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/pb2323/BugBridge.git
   cd BugBridge
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Set up database**
   ```bash
   # Run database migrations
   # (Migration scripts to be created)
   ```

6. **Run the application**
   ```bash
   python -m bugbridge.main
   ```

### Environment Variables

See `.env.example` for required configuration:

```env
# Canny.io Configuration
CANNY_API_KEY=your_api_key
CANNY_SUBDOMAIN=bugbridge.canny.io
CANNY_BOARD_ID=board_id
CANNY_SYNC_INTERVAL=3600

# Jira MCP Configuration
JIRA_MCP_SERVER_URL=http://localhost:8000
JIRA_PROJECT_KEY=PROJ
JIRA_RESOLUTION_STATUSES=Done,Resolved,Fixed

# XAI Configuration
XAI__API_KEY=your_xai_api_key
XAI__MODEL=grok-4-fast-reasoning
XAI__TEMPERATURE=0.0
XAI__MAX_OUTPUT_TOKENS=2048

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/bugbridge
```

---

## Implementation Phases

The platform implementation is organized into 6 phases (see [PRD](tasks/prd-bugbridge-platform.md) for details):

1. **Phase 1: Foundation** (Weeks 1-2)
   - Project setup with LangGraph and LangChain
   - Data models and database schema
   - Feedback Collection Agent

2. **Phase 2: Analysis Agents** (Weeks 3-4)
   - Bug Detection Agent
   - Sentiment Analysis Agent
   - Priority Scoring Agent

3. **Phase 3: Jira Integration** (Weeks 5-6)
   - MCP client setup
   - Jira Creation Agent

4. **Phase 4: Monitoring & Notifications** (Weeks 7-8)
   - Monitoring Agent
   - Notification Agent

5. **Phase 5: Reporting** (Week 9)
   - Reporting Agent
   - Daily report generation

6. **Phase 6: Dashboard Development** (Weeks 10-11)
   - Backend REST API setup (FastAPI)
   - Frontend dashboard development (React)
   - Authentication and authorization
   - Interactive visualizations and metrics
   - Configuration management interface

7. **Phase 7: Production Readiness** (Weeks 12-14)
   - Error handling and resilience
   - Performance optimization
   - Testing and QA (including dashboard E2E tests)
   - Deployment preparation
   - Dashboard deployment and hosting

---

## Architecture Overview

### Agent-Based System

BugBridge uses specialized AI agents orchestrated by LangGraph:

1. **Feedback Collection Agent**: Collects feedback from Canny.io
2. **Bug Detection Agent**: Identifies bugs vs. feature requests
3. **Sentiment Analysis Agent**: Analyzes emotional tone and urgency
4. **Priority Scoring Agent**: Calculates priority scores (1-100)
5. **Jira Creation Agent**: Creates Jira tickets automatically
6. **Monitoring Agent**: Monitors Jira ticket status
7. **Notification Agent**: Notifies customers when issues are resolved
8. **Reporting Agent**: Generates daily summary reports

### Workflow

```
Feedback Collection → Bug Detection → Sentiment Analysis → 
Priority Scoring → Jira Creation → Monitoring → Notification
```

Each agent makes autonomous decisions using AI (XAI/Grok models) with deterministic behavior through structured outputs.

---

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_agents.py

# Run with coverage
pytest --cov=bugbridge tests/
```

### Testing with Real MCP Server

To test the Jira Creation Agent with a real MCP server (not mocked):

1. **Start the MCP server**:
   ```bash
   cd mcp-atlassian
   python -m mcp_atlassian --transport streamable-http --port 9000 --path /mcp -vv
   ```

2. **Verify server is accessible**:
   ```bash
   python scripts/verify_mcp_server.py
   ```

3. **Run real MCP server tests**:
   ```bash
   REAL_MCP_SERVER=true pytest tests/test_jira_real_mcp_server.py -v
   # Or use the provided script
   ./scripts/test_real_mcp_server.sh
   ```

See [docs/testing-with-real-mcp-server.md](docs/testing-with-real-mcp-server.md) for detailed instructions.

### Code Style

Follow PEP 8 style guidelines. Use `black` for formatting and `flake8` for linting.

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines (to be created).

---

## API Integration Status

### Canny.io API ✅

All CRUD operations verified and working:
- ✅ **READ**: boards, users, posts, categories, tags, comments, votes
- ✅ **CREATE**: users, tags, posts
- ✅ **UPDATE**: users, posts
- ✅ **DELETE**: users, posts
- ✅ **STATUS**: Mark posts as fixed (complete)

See [CANNY_API_REFERENCE.md](CANNY_API_REFERENCE.md) for complete documentation.

### Jira MCP Server ✅

MCP-atlassian server integration tested and working:
- ✅ **CREATE**: Create issues
- ✅ **READ**: Get projects, get issues, get transitions
- ✅ **UPDATE**: Update issues, add comments
- ✅ **STATUS**: Transition issues (status changes)

MCP server configured in `mcp-atlassian/` directory.

---

## License

[To be determined]

---

## Contact & Support

- **Repository**: https://github.com/pb2323/BugBridge
- **Issues**: https://github.com/pb2323/BugBridge/issues

---

## Roadmap

- [ ] Complete Phase 1: Foundation
- [ ] Complete Phase 2: Analysis Agents
- [ ] Complete Phase 3: Jira Integration
- [ ] Complete Phase 4: Monitoring & Notifications
- [ ] Complete Phase 5: Reporting
- [ ] Complete Phase 6: Dashboard Development
- [ ] Complete Phase 7: Production Readiness
- [ ] Beta testing with select customers
- [ ] Public launch

---

**Last Updated**: November 2025
