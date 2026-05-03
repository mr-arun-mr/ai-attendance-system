import React, { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";

interface AuthUser {
  user_id: number;
  full_name: string;
  is_admin: boolean;
  access_token: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  login: (data: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const stored = localStorage.getItem("auth");
    return stored ? JSON.parse(stored) : null;
  });

  const login = (data: AuthUser) => {
    localStorage.setItem("auth", JSON.stringify(data));
    setUser(data);
  };

  const logout = () => {
    localStorage.removeItem("auth");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
