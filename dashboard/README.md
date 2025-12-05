# BugBridge Dashboard

Interactive web dashboard for the BugBridge AI-powered feedback management platform.

## Overview

The BugBridge Dashboard is a modern, responsive web application built with Next.js and React that provides a comprehensive interface for managing customer feedback, monitoring Jira tickets, viewing analytics, and configuring the platform.

## Features

### 🎯 Core Functionality

- **Dashboard Overview**: Real-time metrics with auto-refresh, burning issues tracking, and key performance indicators
- **Feedback Management**: Browse, search, filter, and process customer feedback from Canny.io
- **Jira Integration**: Track Jira tickets, monitor status changes, and view resolution progress
- **Analytics & Metrics**: Visual charts and graphs showing trends, sentiment analysis, and performance metrics
- **Reports**: Generate and view daily reports with AI-powered insights and email delivery
- **Settings**: Configure Canny.io, Jira, XAI, and other platform settings (admin only)

### 🔐 Authentication & Security

- JWT-based authentication with secure token storage
- Role-based access control (Admin and Viewer roles)
- Session persistence across page refreshes
- Protected routes and API endpoints
- Automatic token refresh and logout on expiration

### 📊 Data Visualization

- **Recharts Integration**: Interactive and responsive charts
- **Real-time Updates**: Auto-refresh data at configurable intervals
- **Visual Metrics**: Pie charts, bar charts, line graphs for comprehensive insights
- **Export Capabilities**: Download reports as CSV

### 🎨 User Experience

- Modern, clean UI with Tailwind CSS
- Responsive design for mobile and desktop
- Loading states and error handling
- Toast notifications for user feedback
- Dark mode ready (infrastructure in place)

## Technology Stack

### Core Frameworks

- **Next.js 14+**: React framework with App Router and Server Components
- **TypeScript**: Type-safe JavaScript for robust code
- **React 18**: Latest React features including Suspense and Concurrent Rendering

### State Management & Data Fetching

- **TanStack Query (React Query)**: Powerful data fetching, caching, and synchronization
- **Zustand**: Lightweight state management with persistence
- **Axios**: HTTP client with interceptors for authentication

### UI & Styling

- **Tailwind CSS**: Utility-first CSS framework
- **Heroicons**: Beautiful hand-crafted SVG icons
- **Recharts**: Composable charting library

### Development Tools

- **ESLint**: Code linting and style enforcement
- **Prettier**: Code formatting (optional)
- **TypeScript**: Static type checking

### Testing

- **Jest**: JavaScript testing framework
- **React Testing Library**: Component testing utilities
- **Playwright**: End-to-end testing

## Getting Started

### Prerequisites

- Node.js 18 or higher
- npm or yarn
- BugBridge backend API running (see main README)

### Installation

1. **Navigate to dashboard directory**
   ```bash
   cd dashboard
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.local.example .env.local
   ```

   Update `.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_API_BASE_PATH=/api
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

5. **Access the dashboard**
   - Open browser to `http://localhost:3000`
   - Login with your admin credentials

### Build for Production

```bash
# Build optimized production bundle
npm run build

# Start production server
npm start

# Or export static files
npm run build && npm run export
```

## Project Structure

```
dashboard/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── dashboard/               # Dashboard overview page
│   │   ├── feedback/                # Feedback management pages
│   │   │   └── [id]/               # Individual feedback detail
│   │   ├── jira-tickets/           # Jira tickets page
│   │   ├── metrics/                # Analytics page
│   │   ├── reports/                # Reports pages
│   │   │   └── [id]/               # Individual report viewer
│   │   ├── settings/               # Settings page (admin only)
│   │   ├── login/                  # Login page
│   │   ├── layout.tsx              # Root layout with providers
│   │   ├── page.tsx                # Home page (redirects)
│   │   ├── providers.tsx           # React Query and auth providers
│   │   └── globals.css             # Global styles
│   ├── components/                  # React components
│   │   ├── layout/                 # Layout components
│   │   │   ├── DashboardLayout.tsx # Main dashboard layout
│   │   │   ├── Header.tsx          # Header with navigation
│   │   │   └── Sidebar.tsx         # Sidebar navigation
│   │   ├── auth/                   # Authentication components
│   │   │   ├── LoginForm.tsx       # Login form
│   │   │   └── ProtectedRoute.tsx  # Route protection wrapper
│   │   ├── feedback/               # Feedback components
│   │   │   ├── FeedbackTable.tsx   # Feedback list table
│   │   │   └── FeedbackDetail.tsx  # Feedback detail view
│   │   ├── jira/                   # Jira components
│   │   │   └── JiraTicketsTable.tsx# Jira tickets table
│   │   ├── metrics/                # Metrics components
│   │   │   ├── MetricsOverview.tsx # Metrics cards
│   │   │   ├── BugsVsFeaturesChart.tsx
│   │   │   ├── SentimentChart.tsx
│   │   │   └── PriorityScoreChart.tsx
│   │   ├── reports/                # Report components
│   │   │   ├── ReportViewer.tsx    # Report display
│   │   │   ├── ReportMetricsCharts.tsx # Visual charts
│   │   │   └── ReportList.tsx      # Reports listing
│   │   └── common/                 # Shared components
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── LoadingSpinner.tsx
│   │       └── ErrorBoundary.tsx
│   ├── hooks/                      # Custom React hooks
│   │   ├── useAuth.ts             # Authentication hook
│   │   ├── useFeedback.ts         # Feedback data hook
│   │   ├── useJiraTickets.ts      # Jira tickets hook
│   │   ├── useMetrics.ts          # Metrics hook
│   │   ├── useReports.ts          # Reports hook
│   │   └── useSessionRestore.ts   # Session restoration hook
│   ├── services/                   # API service layer
│   │   └── api/
│   │       ├── auth.ts            # Authentication API
│   │       ├── feedback.ts        # Feedback API
│   │       ├── jira.ts            # Jira API
│   │       ├── metrics.ts         # Metrics API
│   │       ├── reports.ts         # Reports API
│   │       └── config.ts          # Config API
│   ├── store/                      # State management
│   │   └── auth-store.ts          # Zustand auth store
│   ├── lib/                        # Utility libraries
│   │   ├── api-client.ts          # Axios instance configuration
│   │   ├── query-client.ts        # React Query configuration
│   │   ├── jira-utils.ts          # Jira URL utilities
│   │   └── canny-utils.ts         # Canny URL utilities
│   ├── types/                      # TypeScript type definitions
│   │   └── index.ts               # Shared types
│   └── middleware.ts               # Next.js middleware (auth)
├── public/                         # Static assets
├── __tests__/                      # Test files (mirrors src structure)
├── .env.local.example              # Environment variables template
├── next.config.ts                  # Next.js configuration
├── tailwind.config.ts              # Tailwind CSS configuration
├── tsconfig.json                   # TypeScript configuration
├── jest.config.js                  # Jest configuration
├── playwright.config.ts            # Playwright configuration
└── package.json                    # Dependencies and scripts
```

## Available Scripts

```bash
# Development
npm run dev              # Start development server (http://localhost:3000)

# Build
npm run build            # Build for production
npm start                # Start production server

# Testing
npm test                 # Run unit tests
npm run test:watch       # Run tests in watch mode
npm run test:coverage    # Run tests with coverage report
npm run test:e2e         # Run E2E tests
npm run test:e2e:ui      # Run E2E tests with UI

# Linting
npm run lint             # Run ESLint
npm run lint:fix         # Fix ESLint issues

# Type Checking
npm run type-check       # Run TypeScript compiler check
```

## Dashboard Pages

### 1. Dashboard Overview (`/dashboard`)
- Real-time metrics cards (new issues, bugs, resolved tickets, Jira tickets)
- Bugs vs features pie chart
- Sentiment distribution bar chart
- Jira ticket status chart
- Burning issues table with high-priority items
- Auto-refresh every 30 seconds

### 2. Feedback Tab (`/feedback`)
- Comprehensive feedback listing with pagination
- Search by title
- Filter by status, sentiment, bug/feature
- Sort by date, priority, votes
- Individual feedback processing
- Refresh from Canny.io button
- Direct links to Canny.io posts
- Priority score and sentiment indicators

### 3. Jira Tickets Tab (`/jira-tickets`)
- Jira ticket listing with real-time status
- Filter by status, priority, resolution
- Sort by creation date, resolution date
- Direct links to Jira tickets and original Canny posts
- Refresh button to sync from Jira
- Assignee tracking
- Resolution date tracking

### 4. Metrics/Analytics Tab (`/metrics`)
- Comprehensive analytics dashboard
- Time series charts for trends
- Bugs vs features distribution
- Sentiment analysis over time
- Priority score distribution
- Performance metrics (response time, resolution time)
- Customizable date ranges

### 5. Reports Tab (`/reports`)
- Generated reports library
- Visual metrics overview with charts:
  - Key metrics cards
  - Bugs vs features pie chart
  - Sentiment distribution
  - Ticket status breakdown
  - Performance metrics
- Filter by date range, report type
- Export to CSV
- Generate new reports on-demand
- Email delivery confirmation
- AI-generated summaries and insights

### 6. Settings Tab (`/settings`) - Admin Only
- Canny.io configuration
- Jira MCP server settings
- XAI API configuration
- Database settings
- Priority scoring weights
- Reporting schedule and recipients
- Agent configuration

## Key Features Explained

### Authentication Flow

1. User enters credentials on `/login`
2. Backend validates and returns JWT token
3. Token stored in Zustand store (persisted to localStorage)
4. API client automatically adds token to all requests
5. Session restored on page refresh via `useSessionRestore` hook
6. Automatic logout on token expiration

### Data Fetching Strategy

- **React Query**: Handles all API calls with intelligent caching
- **Auto-refresh**: Key metrics refresh every 30 seconds
- **Optimistic Updates**: UI updates immediately, syncs in background
- **Error Handling**: Graceful error displays with retry options
- **Loading States**: Skeleton loaders and spinners during data fetch

### Responsive Design

- Mobile-first approach with Tailwind CSS
- Collapsible sidebar on small screens
- Responsive tables with horizontal scroll
- Touch-friendly buttons and controls
- Optimized for tablets and desktop

## Testing

### Unit Tests

Located in `src/__tests__/`, mirroring source structure:

```bash
# Run all unit tests
npm test

# Run specific test file
npm test -- useAuth.test.tsx

# Run with coverage
npm run test:coverage
```

Example test locations:
- `src/__tests__/components/` - Component tests
- `src/__tests__/hooks/` - Custom hook tests
- `src/__tests__/services/` - API service tests
- `src/__tests__/lib/` - Utility tests

### E2E Tests

Playwright tests in `e2e/`:

```bash
# Run E2E tests
npm run test:e2e

# Run with UI (debugging)
npm run test:e2e:ui

# Run specific test file
npx playwright test e2e/dashboard.spec.ts
```

See [TESTING.md](./TESTING.md) for comprehensive testing documentation.

## Environment Variables

### Required Variables

```env
# Backend API URL (required)
NEXT_PUBLIC_API_URL=http://localhost:8000

# API base path (optional, defaults to /api)
NEXT_PUBLIC_API_BASE_PATH=/api
```

### Optional Variables

```env
# Enable debug logging (optional)
NEXT_PUBLIC_DEBUG=false

# API request timeout in ms (optional)
NEXT_PUBLIC_API_TIMEOUT=30000
```

## Customization

### Theming

Tailwind configuration in `tailwind.config.ts`:

```typescript
// Customize colors, fonts, spacing, etc.
theme: {
  extend: {
    colors: {
      primary: {...},
      secondary: {...},
    },
  },
}
```

### API Configuration

Modify `src/lib/api-client.ts` for:
- Request/response interceptors
- Error handling
- Timeout settings
- Base URL configuration

### Query Configuration

Modify `src/lib/query-client.ts` for:
- Default cache time
- Retry logic
- Refetch settings
- Global error handling

## Troubleshooting

### Issue: "Cannot connect to backend"

**Solution**:
1. Verify backend is running on port 8000
2. Check `NEXT_PUBLIC_API_URL` in `.env.local`
3. Check browser console for CORS errors
4. Verify backend CORS settings include frontend URL

### Issue: "Session not persisting"

**Solution**:
1. Check browser localStorage for 'auth-storage'
2. Verify JWT token is valid
3. Check token expiration time
4. Clear browser cache and localStorage
5. Restart development server

### Issue: "Charts not displaying"

**Solution**:
1. Check if data is being fetched (Network tab)
2. Verify data format matches expected structure
3. Check console for JavaScript errors
4. Ensure Recharts is properly installed

### Issue: "TypeScript errors"

**Solution**:
```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Run type check
npm run type-check
```

## Performance Optimization

### Implemented Optimizations

- **Code Splitting**: Automatic route-based code splitting via Next.js
- **Image Optimization**: Next.js Image component for optimized images
- **Static Generation**: Pre-rendered pages where possible
- **Lazy Loading**: Components loaded on-demand
- **Memoization**: React.memo for expensive components
- **Query Caching**: React Query caches API responses

### Monitoring

Use Next.js built-in analytics:

```bash
# Analyze bundle size
npm run build
# Review output for chunk sizes
```

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
```

### Other Platforms

Build static export for any hosting:

```bash
npm run build
# Deploy contents of .next/standalone or out/
```

Supported platforms:
- Netlify
- AWS Amplify
- Google Cloud Run
- Docker container
- Traditional web server

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Run tests: `npm test && npm run test:e2e`
6. Submit a pull request

## License

[To be determined]

## Support

- **Main Repository**: https://github.com/pb2323/BugBridge
- **Issues**: https://github.com/pb2323/BugBridge/issues
- **Main README**: [../README.md](../README.md)

---

**Last Updated**: December 2025
