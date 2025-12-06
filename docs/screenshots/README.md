# Test Screenshots

This directory contains screenshots of test results demonstrating the reliability and functionality of BugBridge.

## Required Screenshots

### 1. Backend Tests (`backend-tests.png`)
Screenshot should show:
- Terminal output of `pytest tests/ -v`
- All tests passing (green checkmarks)
- Test count (150+ tests)
- Coverage percentage (75%+)

### 2. Frontend Tests (`frontend-tests.png`)
Screenshot should show:
- Terminal output of `npm test`
- All tests passing
- Test count (30+ tests)
- Coverage summary

### 3. End-to-End Tests (`e2e-tests.png`)
Screenshot should show:
- Playwright UI or terminal output of `npm run test:e2e`
- All E2E scenarios passing
- Test count (15+ scenarios)

## How to Generate Screenshots

### Backend Tests
```bash
cd /Users/puneetbajaj/Desktop/playground/BugBridge
source venv/bin/activate
pytest tests/ -v
# Take screenshot of terminal showing all tests passing
```

### Frontend Tests
```bash
cd /Users/puneetbajaj/Desktop/playground/BugBridge/dashboard
npm test
# Take screenshot of terminal showing all tests passing
```

### E2E Tests
```bash
cd /Users/puneetbajaj/Desktop/playground/BugBridge/dashboard
npm run test:e2e:ui
# Take screenshot of Playwright UI showing all tests passing
```

## Naming Convention
- `backend-tests.png` - Backend test results
- `frontend-tests.png` - Frontend test results
- `e2e-tests.png` - End-to-end test results

## Image Specifications
- Format: PNG
- Resolution: At least 1920x1080 for clarity
- File size: Keep under 5MB per image
- Ensure text is readable

## Placeholder Files
Until actual screenshots are added, placeholder text files exist to maintain directory structure.

