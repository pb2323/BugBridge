# BugBridge Dashboard

Interactive dashboard for the BugBridge feedback management platform.

## Technology Stack

- **Next.js 14+**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **TanStack Query**: Data fetching and caching
- **Zustand**: State management
- **Recharts**: Data visualization
- **Axios**: HTTP client

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
# Install dependencies
npm install
```

### Environment Variables

Copy `.env.local.example` to `.env.local` and configure:

```bash
cp .env.local.example .env.local
```

Update the following variables:
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)
- `NEXT_PUBLIC_API_BASE_PATH`: API base path (default: /api)

### Development

```bash
# Start development server
npm run dev
```

The dashboard will be available at http://localhost:3000

### Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Project Structure

```
dashboard/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── dashboard/         # Dashboard pages
│   │   ├── login/             # Authentication pages
│   │   └── layout.tsx         # Root layout
│   ├── components/            # React components (to be created)
│   ├── lib/                   # Utility libraries
│   │   ├── api-client.ts     # Axios client configuration
│   │   └── query-client.ts   # React Query configuration
│   ├── services/              # API service functions
│   │   └── api/              # API endpoint services
│   └── store/                # State management
│       └── auth-store.ts     # Authentication store
├── public/                    # Static assets
├── .env.local.example         # Environment variables template
└── package.json              # Dependencies
```

## Features

- ✅ Next.js 14 with App Router
- ✅ TypeScript configuration
- ✅ Tailwind CSS setup
- ✅ React Query for data fetching
- ✅ Zustand for state management
- ✅ API client with authentication
- ✅ Service layer for API endpoints

## Testing

The dashboard includes comprehensive testing infrastructure:

- **Unit Tests**: Jest + React Testing Library for component and hook testing
- **Integration Tests**: API service layer testing
- **E2E Tests**: Playwright for end-to-end testing

### Running Tests

```bash
# Unit tests
npm test

# Unit tests with coverage
npm run test:coverage

# E2E tests
npm run test:e2e

# E2E tests in UI mode
npm run test:e2e:ui
```

See [TESTING.md](./TESTING.md) for detailed testing documentation.

## Next Steps

All dashboard tasks (10.1-10.9) are complete! The dashboard is fully functional with:
- ✅ Complete UI implementation
- ✅ Backend API integration
- ✅ Authentication & authorization
- ✅ Comprehensive test coverage
