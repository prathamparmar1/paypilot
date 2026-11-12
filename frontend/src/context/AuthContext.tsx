"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Business } from "@/types";

const TOKEN_KEY = "paypilot_token";

interface AuthState {
  token: string | null;
  business: Business | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    owner_name: string;
    business_name: string;
    email: string;
    password: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = useCallback(async (t: string) => {
    const me = await api<Business>("/business/me", {}, t);
    setBusiness(me);
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (!saved) {
      setLoading(false);
      return;
    }
    loadProfile(saved)
      .then(() => setToken(saved))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, [loadProfile]);

  const finishAuth = async (t: string) => {
    localStorage.setItem(TOKEN_KEY, t);
    await loadProfile(t);
    setToken(t);
  };

  const login = async (email: string, password: string) => {
    const res = await api<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    await finishAuth(res.access_token);
  };

  const register: AuthState["register"] = async (data) => {
    const res = await api<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    await finishAuth(res.access_token);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setBusiness(null);
  };

  return (
    <AuthContext.Provider value={{ token, business, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}