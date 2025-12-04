#!/bin/bash
# Comprehensive Platform Testing Script
# Usage: ./test-platform.sh

set -e

echo "🚀 Starting BugBridge Platform Testing..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print section headers
print_section() {
    echo ""
    echo "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${GREEN}$1${NC}"
    echo "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_section "📋 Checking Prerequisites"

if ! command_exists python3; then
    echo "${RED}❌ Python 3 not found${NC}"
    exit 1
fi
echo "${GREEN}✅ Python 3 found${NC}"

if ! command_exists node; then
    echo "${RED}❌ Node.js not found${NC}"
    exit 1
fi
echo "${GREEN}✅ Node.js found${NC}"

if ! command_exists psql; then
    echo "${YELLOW}⚠️  PostgreSQL client not found (some tests may fail)${NC}"
else
    echo "${GREEN}✅ PostgreSQL client found${NC}"
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate
echo "${GREEN}✅ Virtual environment activated${NC}"

# 1. Backend Tests
print_section "📦 Running Backend Unit Tests"

if [ -d "tests" ] && [ "$(ls -A tests/*.py 2>/dev/null)" ]; then
    echo "Running pytest..."
    pytest tests/ -v --tb=short || {
        echo "${YELLOW}⚠️  Some backend tests failed${NC}"
    }
else
    echo "${YELLOW}⚠️  No backend tests found${NC}"
fi

# 2. Check Backend Dependencies
print_section "🔍 Checking Backend Dependencies"

python3 -c "import bugbridge; print('✅ BugBridge module importable')" || {
    echo "${RED}❌ BugBridge module not importable${NC}"
    echo "Run: pip install -r requirements.txt"
}

# 3. Dashboard Tests
print_section "🎨 Running Dashboard Unit Tests"

if [ -d "dashboard" ]; then
    cd dashboard
    
    if [ -f "package.json" ]; then
        # Check if node_modules exists
        if [ ! -d "node_modules" ]; then
            echo "${YELLOW}⚠️  Installing dashboard dependencies...${NC}"
            npm install
        fi
        
        echo "Running dashboard tests..."
        npm test -- --passWithNoTests || {
            echo "${YELLOW}⚠️  Some dashboard tests failed${NC}"
        }
    else
        echo "${YELLOW}⚠️  Dashboard package.json not found${NC}"
    fi
    
    cd ..
else
    echo "${YELLOW}⚠️  Dashboard directory not found${NC}"
fi

# 4. API Health Check
print_section "🔍 Checking API Health"

API_URL="${API_URL:-http://localhost:8000}"
if curl -f -s "${API_URL}/docs" > /dev/null 2>&1; then
    echo "${GREEN}✅ API server is running at ${API_URL}${NC}"
    echo "   API Docs: ${API_URL}/docs"
else
    echo "${YELLOW}⚠️  API server not running at ${API_URL}${NC}"
    echo "   Start with: uvicorn bugbridge.api.main:app --reload --port 8000"
fi

# 5. Dashboard Health Check
print_section "🔍 Checking Dashboard Health"

DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:3000}"
if curl -f -s "${DASHBOARD_URL}" > /dev/null 2>&1; then
    echo "${GREEN}✅ Dashboard is running at ${DASHBOARD_URL}${NC}"
else
    echo "${YELLOW}⚠️  Dashboard not running at ${DASHBOARD_URL}${NC}"
    echo "   Start with: cd dashboard && npm run dev"
fi

# 6. Database Connection Check
print_section "🗄️  Checking Database Connection"

if command_exists psql; then
    if [ -n "$DATABASE_URL" ]; then
        if psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
            echo "${GREEN}✅ Database connection successful${NC}"
        else
            echo "${YELLOW}⚠️  Database connection failed${NC}"
            echo "   Check DATABASE_URL in .env file"
        fi
    else
        echo "${YELLOW}⚠️  DATABASE_URL not set${NC}"
    fi
fi

# 7. Environment Variables Check
print_section "🔐 Checking Environment Variables"

if [ -f ".env" ]; then
    echo "${GREEN}✅ .env file exists${NC}"
    
    # Check critical variables
    if grep -q "CANNY_API_KEY" .env && ! grep -q "CANNY_API_KEY=$" .env; then
        echo "${GREEN}✅ CANNY_API_KEY is set${NC}"
    else
        echo "${YELLOW}⚠️  CANNY_API_KEY not set${NC}"
    fi
    
    if grep -q "XAI_API_KEY" .env && ! grep -q "XAI_API_KEY=$" .env; then
        echo "${GREEN}✅ XAI_API_KEY is set${NC}"
    else
        echo "${YELLOW}⚠️  XAI_API_KEY not set${NC}"
    fi
    
    if grep -q "DATABASE_URL" .env && ! grep -q "DATABASE_URL=$" .env; then
        echo "${GREEN}✅ DATABASE_URL is set${NC}"
    else
        echo "${YELLOW}⚠️  DATABASE_URL not set${NC}"
    fi
else
    echo "${YELLOW}⚠️  .env file not found${NC}"
    echo "   Copy .env.example to .env and configure"
fi

# Summary
print_section "📊 Testing Summary"

echo "${GREEN}✅ Platform testing complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Review any warnings above"
echo "2. Start services:"
echo "   - Backend: uvicorn bugbridge.api.main:app --reload --port 8000"
echo "   - Dashboard: cd dashboard && npm run dev"
echo "3. See TESTING_GUIDE.md for detailed testing instructions"
echo ""

