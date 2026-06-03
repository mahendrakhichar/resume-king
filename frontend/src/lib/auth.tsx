import React from "react";
import * as ClerkReal from "@clerk/clerk-react";

export const isClerkConfigured = () => {
  const key = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || "";
  return key && key !== "your_clerk_publishable_key" && !key.includes("mock") && key !== "";
};

// 1. ClerkProvider Wrapper
export function ClerkProvider({ children, publishableKey, ...props }: any) {
  if (isClerkConfigured()) {
    return (
      <ClerkReal.ClerkProvider publishableKey={publishableKey} {...props}>
        {children}
      </ClerkReal.ClerkProvider>
    );
  }
  return <>{children}</>;
}

// 2. SignedIn Wrapper
export function SignedIn({ children }: { children: React.ReactNode }) {
  if (isClerkConfigured()) {
    return <ClerkReal.SignedIn>{children}</ClerkReal.SignedIn>;
  }
  return <>{children}</>;
}

// 3. SignedOut Wrapper
export function SignedOut({ children }: { children: React.ReactNode }) {
  if (isClerkConfigured()) {
    return <ClerkReal.SignedOut>{children}</ClerkReal.SignedOut>;
  }
  return null; // Always signed in in mock mode
}

// 4. SignInButton Wrapper
export function SignInButton({ children, ...props }: any) {
  if (isClerkConfigured()) {
    return <ClerkReal.SignInButton {...props}>{children}</ClerkReal.SignInButton>;
  }
  
  const navigateToDashboard = () => {
    window.location.href = "/dashboard";
  };

  return (
    <span onClick={navigateToDashboard} className="cursor-pointer">
      {children}
    </span>
  );
}

// 5. UserButton Wrapper
export function UserButton(props: any) {
  if (isClerkConfigured()) {
    return <ClerkReal.UserButton {...props} />;
  }

  return (
    <div className="flex items-center gap-3">
      <img
        src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150"
        alt="Mock User"
        className="w-9 h-9 rounded-full border border-purple-500/30 object-cover"
      />
      <button
        onClick={() => {
          window.location.href = "/";
        }}
        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition-colors"
      >
        Sign Out
      </button>
    </div>
  );
}

// 6. useAuth Wrapper
export function useAuth() {
  if (isClerkConfigured()) {
    return ClerkReal.useAuth();
  }
  return {
    isLoaded: true,
    isSignedIn: true,
    userId: "user_mock_123456",
    orgId: null,
    orgRole: null,
    orgSlug: null,
    actor: null,
    signOut: async () => {
      window.location.href = "/";
    },
    getToken: async () => "mock_token_123456",
  };
}

// 7. RedirectToSignIn Wrapper
export function RedirectToSignIn() {
  if (isClerkConfigured()) {
    return <ClerkReal.RedirectToSignIn />;
  }
  window.location.href = "/dashboard";
  return null;
}
