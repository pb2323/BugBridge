# Testing Guide for BugBridge Dashboard

This document provides guidance on running and writing tests for the BugBridge dashboard.

## Testing Stack

- **Jest**: Unit and integration testing framework
- **React Testing Library**: React component testing utilities
- **Playwright**: End-to-end (E2E) testing framework

## Running Tests

### Unit Tests

Run all unit tests:
```bash
npm test
```

Run tests in watch mode:
```bash
npm run test:watch
```

Run tests with coverage:
```bash
npm run test:coverage
```

### E2E Tests

Run all E2E tests:
```bash
npm run test:e2e
```

Run E2E tests in UI mode (interactive):
```bash
npm run test:e2e:ui
```

Run E2E tests in headed mode (visible browser):
```bash
npm run test:e2e:headed
```

## Test Structure

### Unit Tests

Unit tests are located in `src/__tests__/` and mirror the source code structure:

```
src/__tests__/
├── components/
│   ├── auth/
│   └── common/
├── hooks/
├── lib/
└── services/
    └── api/
```

### E2E Tests

E2E tests are located in the `e2e/` directory:

```
e2e/
├── auth.spec.ts          # Authentication flow tests
├── dashboard.spec.ts     # Dashboard feature tests
└── responsive.spec.ts    # Responsive design tests
```

## Writing Tests

### Unit Tests for Components

Example:
```typescript
import { render, screen } from '@testing-library/react';
import { MyComponent } from '../MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

### Unit Tests for Hooks

Example:
```typescript
import { renderHook } from '@testing-library/react';
import { useMyHook } from '../useMyHook';

describe('useMyHook', () => {
  it('should return expected value', () => {
    const { result } = renderHook(() => useMyHook());
    expect(result.current.value).toBe('expected');
  });
});
```

### E2E Tests

Example:
```typescript
import { test, expect } from '@playwright/test';

test('should navigate to dashboard', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL('/dashboard');
});
```

## Mocking

### API Mocks

Use `jest.mock()` to mock API services:

```typescript
jest.mock('../../services/api/auth');
const mockAuthApi = authApi as jest.Mocked<typeof authApi>;
```

### Router Mocks

Next.js router is automatically mocked in `jest.setup.js`. The mock provides:
- `useRouter()` hook
- `usePathname()` hook
- `useSearchParams()` hook

### localStorage Mocks

localStorage is automatically mocked in `jest.setup.js`. Use it in tests:

```typescript
localStorage.setItem('auth_token', 'test-token');
```

## E2E Test Best Practices

1. **Mock API Responses**: Use Playwright's `page.route()` to mock API responses
2. **Set Up Authentication**: Use `page.addInitScript()` to set authentication state
3. **Wait for Elements**: Use `page.waitForSelector()` or `expect().toBeVisible()` with timeout
4. **Clean Up**: Tests should clean up after themselves (handled automatically by Playwright)

## Coverage Goals

- **Unit Tests**: Aim for >80% code coverage
- **E2E Tests**: Cover all critical user flows
- **Integration Tests**: Test API service layer

## CI/CD Integration

Tests are configured to run in CI environments. The Playwright configuration includes:
- Retry logic for flaky tests
- Screenshot capture on failure
- Trace collection for debugging

## Troubleshooting

### Tests failing in CI but passing locally
- Check timeouts (increase if needed)
- Verify API mocks are properly set up
- Check environment variables

### E2E tests timing out
- Increase timeout in test configuration
- Check that dev server is running
- Verify API mocks are responding correctly

### Jest tests not finding modules
- Check `jest.config.js` moduleNameMapper
- Verify `tsconfig.json` paths configuration
- Ensure files are in the correct location

