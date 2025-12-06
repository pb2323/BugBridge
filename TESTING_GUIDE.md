# BugBridge Platform Testing Guide

Complete step-by-step guide to test the entire BugBridge platform from setup to end-to-end workflows.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Backend Testing](#backend-testing)
4. [Frontend/Dashboard Testing](#frontenddashboard-testing)
5. [Integration Testing](#integration-testing)
6. [End-to-End Workflow Testing](#end-to-end-workflow-testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Python 3.10+** (for backend)
- **Node.js 18+** and **npm** (for dashboard)
- **PostgreSQL 14+** (database)
- **Git** (version control)

### Required Accounts & API Keys

- **Canny.io Account**: API key and board ID
- **XAI (xAI) API Key**: For LLM operations
- **Jira Instance**: With MCP server configured (or use mock for testing)
- **SMTP Server** (optional): For email notifications

---

## Initial Setup

### Step 1: Clone and Navigate to Project

```bash
cd /Users/puneetbajaj/Desktop/playground/BugBridge
```

### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Set Up PostgreSQL Database

```bash
# Create database
createdb bugbridge

# OR using psql
psql -U postgres
CREATE DATABASE bugbridge;
\q
```

### Step 4: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your configuration
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bugbridge

# Canny.io
CANNY_API_KEY=your_canny_api_key
CANNY_BOARD_ID=your_board_id
CANNY_ADMIN_USER_ID=your_admin_user_id

# XAI
XAI_API_KEY=your_xai_api_key
XAI_MODEL=grok-4-fast-reasoning

# Jira MCP Server
JIRA_MCP_SERVER_URL=http://localhost:8001  # If using local MCP server
JIRA_PROJECT_KEY=PROJ  # Your Jira project key

# API
API_SECRET_KEY=your-secret-key-here-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Email (optional)
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password
EMAIL_FROM_EMAIL=your-email@gmail.com
```

### Step 5: Initialize Database Schema

```bash
# Run database migrations (if using Alembic)
alembic upgrade head

# OR run schema directly
psql -U postgres -d bugbridge -f bugbridge/database/schema.py
```

### Step 6: Set Up Dashboard

```bash
# Navigate to dashboard directory
cd dashboard

# Install dependencies
npm install

# Create environment file
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_PATH=/api
EOF
```

---

## Backend Testing

### Step 1: Run Database Migrations (if needed)

```bash
# Activate virtual environment first
source venv/bin/activate

# Check database connection
python -c "from bugbridge.database.session import get_session; print('Database connected!')"
```

### Step 2: Run Backend Unit Tests

```bash
# Run all backend tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_bug_detection_agent.py -v
pytest tests/test_sentiment_analysis_agent.py -v
pytest tests/test_priority_scoring_agent.py -v
pytest tests/test_jira_creation_integration.py -v
pytest tests/test_reporting_agent.py -v

# Run with coverage
pytest tests/ --cov=bugbridge --cov-report=html
```

### Step 3: Test Backend API Server

```bash
# Start the FastAPI server
uvicorn bugbridge.api.main:app --reload --port 8000

# OR using Python directly
python -m uvicorn bugbridge.api.main:app --reload --port 8000
```

**Verify API is running:**

```bash
# Test health endpoint (if available)
curl http://localhost:8000/api/health

# View API documentation
open http://localhost:8000/docs
```

### Step 4: Test Authentication Endpoints

```bash
# Create a test user first (you may need to do this via database or CLI)
# Then test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Save the token from response
export TOKEN="your-jwt-token-here"

# Test protected endpoint
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Step 5: Test API Endpoints

```bash
# Test feedback endpoint
curl http://localhost:8000/api/feedback \
  -H "Authorization: Bearer $TOKEN"

# Test metrics endpoint
curl http://localhost:8000/api/metrics \
  -H "Authorization: Bearer $TOKEN"

# Test config endpoint
curl http://localhost:8000/api/config \
  -H "Authorization: Bearer $TOKEN"
```

---

## Frontend/Dashboard Testing

### Step 1: Start Dashboard Development Server

```bash
# Navigate to dashboard directory
cd dashboard

# Start Next.js dev server
npm run dev
```

**Verify dashboard is running:**

- Open browser: http://localhost:3000
- You should see the login page

### Step 2: Run Dashboard Unit Tests

```bash
# Run all unit tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

### Step 3: Test Dashboard UI Manually

1. **Login Flow:**
   - Navigate to http://localhost:3000
   - Enter credentials (create test user first if needed)
   - Verify redirect to dashboard

2. **Dashboard Overview:**
   - Check metrics cards are displayed
   - Verify charts are rendering
   - Test auto-refresh functionality

3. **Navigation:**
   - Test all sidebar links
   - Verify page transitions
   - Check responsive design (resize browser)

4. **Feedback Page:**
   - View feedback list
   - Test filtering and search
   - Test pagination
   - View individual feedback details

5. **Settings Page:**
   - Test configuration forms
   - Verify save/cancel functionality
   - Test role-based access (admin only)

6. **Reports Page:**
   - View report list
   - Generate new report
   - View report details
   - Test export functionality

### Step 4: Run Dashboard E2E Tests

```bash
# Make sure dashboard is running first
npm run dev  # In one terminal

# Run E2E tests in another terminal
npm run test:e2e

# Run E2E tests in UI mode (interactive)
npm run test:e2e:ui

# Run E2E tests in headed mode (visible browser)
npm run test:e2e:headed
```

---

## Integration Testing

### Step 1: Test Canny.io Integration

```bash
# Activate virtual environment
source venv/bin/activate

# Test Canny.io connection
python -c "
from bugbridge.integrations.canny import CannyClient
from bugbridge.config import get_settings

settings = get_settings()
client = CannyClient(settings.canny)
posts = client.get_posts(limit=5)
print(f'Found {len(posts)} posts')
"
```

### Step 2: Test XAI Integration

```bash
# Test XAI LLM connection
python -c "
from bugbridge.integrations.xai import get_xai_llm
from bugbridge.config import get_settings

settings = get_settings()
llm = get_xai_llm(settings.xai)
response = llm.invoke('Hello, test message')
print(f'LLM Response: {response.content[:100]}')
"
```

### Step 3: Test Jira MCP Integration

```bash
# If using real MCP server
export REAL_MCP_SERVER=1
pytest tests/test_jira_real_mcp_server.py -v

# OR test with mock
pytest tests/test_mcp_jira_client.py -v
pytest tests/test_jira_tools.py -v
```

### Step 4: Test Full Analysis Pipeline

```bash
# Test the complete analysis workflow
pytest tests/test_analysis_pipeline_integration.py -v

# This tests:
# - Feedback collection
# - Bug detection
# - Sentiment analysis
# - Priority scoring
```

---

## End-to-End Workflow Testing

### Step 1: Start All Services

**Terminal 1 - Backend API:**
```bash
source venv/bin/activate
uvicorn bugbridge.api.main:app --reload --port 8000
```

**Terminal 2 - Dashboard:**
```bash
cd dashboard
npm run dev
```

**Terminal 3 - MCP Server (if using real Jira):**
```bash
# Start your MCP server
# Example: python -m mcp_atlassian.server --port 8001
```

### Step 2: Test Complete Feedback-to-Resolution Flow

#### 2.1: Create Test Feedback in Canny.io

1. Go to your Canny.io board
2. Create a new post (bug report or feature request)
3. Add some comments and votes
4. Note the post ID

#### 2.2: Trigger Feedback Collection

```bash
# Run the feedback collection workflow
python -c "
from bugbridge.workflows.main import execute_main_workflow
from bugbridge.database.session import get_session

# Get a feedback post ID from Canny.io
post_id = 'your-canny-post-id'

# Execute workflow
result = execute_main_workflow(post_id)
print(f'Workflow result: {result}')
"
```

#### 2.3: Verify Analysis Results

```bash
# Check database for analysis results
psql -U postgres -d bugbridge -c "
SELECT 
    fp.id,
    fp.title,
    ar.is_bug,
    ar.sentiment_category,
    ar.priority_score
FROM feedback_posts fp
JOIN analysis_results ar ON fp.id = ar.feedback_post_id
ORDER BY fp.created_at DESC
LIMIT 5;
"
```

#### 2.4: Verify Jira Ticket Creation

```bash
# Check if Jira ticket was created
psql -U postgres -d bugbridge -c "
SELECT 
    jt.id,
    jt.jira_key,
    jt.jira_url,
    jt.status,
    fp.title as feedback_title
FROM jira_tickets jt
JOIN feedback_posts fp ON jt.feedback_post_id = fp.id
ORDER BY jt.created_at DESC
LIMIT 5;
"
```

#### 2.5: Test Monitoring and Notification

```bash
# Manually update Jira ticket status to "Done" (via Jira UI or API)
# Then trigger monitoring workflow

python -c "
from bugbridge.agents.monitoring import MonitoringAgent
from bugbridge.database.session import get_session

# Get a ticket ID
session = next(get_session())
from bugbridge.database.models import JiraTicket
ticket = session.query(JiraTicket).first()

if ticket:
    # Execute monitoring
    # This should detect resolution and trigger notification
    print(f'Monitoring ticket: {ticket.jira_key}')
"
```

### Step 3: Test Report Generation

```bash
# Generate a daily report
python -m bugbridge.cli.report generate-report

# OR via API
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Step 4: Verify Dashboard Integration

1. **Login to Dashboard:**
   - Go to http://localhost:3000
   - Login with test credentials

2. **View Metrics:**
   - Check dashboard overview
   - Verify metrics match database

3. **View Feedback:**
   - Navigate to Feedback page
   - Verify your test feedback appears
   - Check analysis results are displayed

4. **View Jira Tickets:**
   - Navigate to Jira Tickets page
   - Verify created tickets are listed

5. **View Reports:**
   - Navigate to Reports page
   - Verify generated reports appear
   - Test report viewing and export

---

## Automated Testing Script

Create a comprehensive test script:

```bash
#!/bin/bash
# test-platform.sh

set -e

echo "🚀 Starting BugBridge Platform Testing..."

# 1. Backend Tests
echo "📦 Running backend unit tests..."
source venv/bin/activate
pytest tests/ -v --tb=short

# 2. Dashboard Tests
echo "🎨 Running dashboard unit tests..."
cd dashboard
npm test -- --passWithNoTests

# 3. API Health Check
echo "🔍 Checking API health..."
curl -f http://localhost:8000/api/health || echo "⚠️  API not running"

# 4. Dashboard Health Check
echo "🔍 Checking dashboard health..."
curl -f http://localhost:3000 || echo "⚠️  Dashboard not running"

echo "✅ Testing complete!"
```

Make it executable:
```bash
chmod +x test-platform.sh
./test-platform.sh
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Error

```bash
# Check PostgreSQL is running
pg_isready

# Check connection string
psql $DATABASE_URL -c "SELECT 1;"
```

#### 2. API Not Starting

```bash
# Check port 8000 is available
lsof -i :8000

# Check for import errors
python -c "from bugbridge.api.main import app; print('OK')"
```

#### 3. Dashboard Build Errors

```bash
# Clear Next.js cache
cd dashboard
rm -rf .next
npm run build
```

#### 4. Authentication Issues

```bash
# Verify JWT secret is set
echo $API_SECRET_KEY

# Check token format
# Token should be: Bearer <token>
```

#### 5. Canny.io API Errors

```bash
# Test API key
curl https://canny.io/api/v1/posts/list \
  -H "Authorization: Bearer $CANNY_API_KEY"
```

#### 6. XAI API Errors

```bash
# Verify API key is set
echo $XAI_API_KEY

# Test connection
python -c "
from bugbridge.integrations.xai import get_xai_llm
llm = get_xai_llm()
print('XAI connected')
"
```

---

## Testing Checklist

Use this checklist to ensure comprehensive testing:

### Backend
- [x] Database connection working
- [x] All unit tests passing
- [x] API server starts successfully
- [x] Authentication endpoints working
- [x] All API endpoints accessible
- [x] Canny.io integration working
- [x] XAI integration working
- [x] Jira MCP integration working
- [x] Analysis pipeline working
- [x] Report generation working

### Frontend
- [x] Dashboard builds successfully
- [x] All unit tests passing
- [x] Dashboard starts successfully
- [x] Login flow working
- [x] All pages accessible
- [x] API integration working
- [x] Responsive design working
- [x] E2E tests passing

### Integration
- [x] Feedback collection working
- [x] Analysis results stored
- [x] Jira tickets created
- [x] Monitoring working
- [x] Notifications sent
- [x] Reports generated
- [x] Dashboard displays data correctly

### End-to-End
- [x] Complete workflow: Feedback → Analysis → Jira → Resolution → Notification
- [x] Dashboard shows all data
- [x] All features accessible
- [x] No console errors
- [x] Performance acceptable

---

## Next Steps

After successful testing:

1. **Performance Testing:** Load test with multiple feedback items
2. **Security Testing:** Test authentication, authorization, input validation
3. **Error Handling:** Test error scenarios and recovery
4. **Production Deployment:** Deploy to production environment
5. **Monitoring:** Set up logging and monitoring

---

## Support

For issues or questions:
- Check logs: `tail -f logs/bugbridge.log`
- Review documentation: `docs/`
- Check test output for detailed error messages

