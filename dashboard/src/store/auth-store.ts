/**
 * Authentication Store
 * 
 * Zustand store for managing authentication state.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  username: string;
  email?: string;
  role: 'admin' | 'viewer';
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (token: string, user: User) => {
        // Store token in localStorage for API client
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', token);
        }
        set({ token, user, isAuthenticated: true });
      },
      logout: () => {
        // Remove token from localStorage
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
        }
        set({ token: null, user: null, isAuthenticated: false });
      },
      updateUser: (user: User) => {
        set({ user });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
