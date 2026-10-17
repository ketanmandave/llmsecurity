import { render, waitFor } from '@testing-library/react';
import { StrictMode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EmployeeWorkspacePage from './EmployeeWorkspacePage';
import { useAuth } from '../contexts/AuthContext';
import api from '../utils/api';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('../utils/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('EmployeeWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      value: vi.fn(),
      writable: true,
    });

    vi.mocked(useAuth).mockReturnValue({
      user: { id: 'user-1', email: 'employee@company.com', role_name: 'Employee' },
      logout: vi.fn(),
      loading: false,
      login: vi.fn(),
      register: vi.fn(),
    } as any);

    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url === '/workspace/conversations') {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: { messages: [] } });
    });
  });

  it('loads conversations once on initial mount for an authenticated user', async () => {
    render(
      <StrictMode>
        <EmployeeWorkspacePage />
      </StrictMode>,
    );

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/workspace/conversations');
    });

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledTimes(1);
    });
  });
});
