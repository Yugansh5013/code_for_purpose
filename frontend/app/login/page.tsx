"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

// ── Mock Credential Database ──────────────────────────────
const CREDENTIALS: Record<string, { password: string; role: string; label: string; icon: string; color: string; region: string | null }> = {
  "ceo@auraretail.co.uk": {
    password: "ceo123",
    role: "ceo",
    label: "CEO — Full Access",
    icon: "verified_user",
    color: "#c5a000",
    region: null,
  },
  "north@auraretail.co.uk": {
    password: "north123",
    role: "north_manager",
    label: "North Region Manager",
    icon: "shield_person",
    color: "#4488cc",
    region: "North",
  },
  "south@auraretail.co.uk": {
    password: "south123",
    role: "south_manager",
    label: "South Region Manager",
    icon: "shield_person",
    color: "#426565",
    region: "South",
  },
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showHint, setShowHint] = useState(false);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const user = CREDENTIALS[email.toLowerCase().trim()];
    if (!user) {
      setError("Invalid credentials. Use one of the demo accounts below.");
      return;
    }
    if (user.password !== password) {
      setError("Incorrect password. Check the demo credentials.");
      return;
    }

    setLoading(true);

    // Store auth context in localStorage
    localStorage.setItem(
      "omnidata_user",
      JSON.stringify({
        email: email.toLowerCase().trim(),
        role: user.role,
        label: user.label,
        region: user.region,
      })
    );

    setTimeout(() => {
      router.push("/dashboard");
    }, 600);
  };

  const quickLogin = (emailVal: string, passwordVal: string) => {
    setEmail(emailVal);
    setPassword(passwordVal);
    // Auto-submit after a brief animation
    setTimeout(() => {
      const user = CREDENTIALS[emailVal];
      if (user) {
        setLoading(true);
        localStorage.setItem(
          "omnidata_user",
          JSON.stringify({
            email: emailVal,
            role: user.role,
            label: user.label,
            region: user.region,
          })
        );
        setTimeout(() => router.push("/dashboard"), 600);
      }
    }, 200);
  };

  return (
    <div className="bg-background text-on-surface min-h-screen flex flex-col login-gradient fade-slide-in">
      {/* TopAppBar */}
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center py-5 px-6 md:px-16 bg-transparent">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="material-symbols-outlined text-primary text-2xl group-hover:scale-110 transition-transform">bubble_chart</span>
          <h1 className="font-headline font-extrabold tracking-tight text-2xl text-on-surface">OmniData</h1>
        </Link>
      </header>

      {/* Main Content */}
      <main className="flex-grow flex items-center justify-center px-6 pt-20 pb-10 relative">
        <div className="w-full max-w-md relative group z-10">

          {/* Decorative Background */}
          <div className="absolute -top-16 -left-16 w-48 h-48 bg-primary-container opacity-40 rounded-full blur-[80px] pointer-events-none" />
          <div className="absolute -bottom-16 -right-16 w-56 h-56 bg-tertiary-container opacity-40 rounded-full blur-[80px] pointer-events-none" />

          {/* Login Card */}
          <div className="relative glass-panel p-8 md:p-10 rounded-2xl shadow-[0px_40px_80px_rgba(45,52,53,0.08)] border border-outline-variant/10 hover:shadow-[0px_50px_100px_rgba(45,52,53,0.1)] transition-shadow duration-500">
            <div className="mb-6 text-center">
              <h2 className="text-2xl md:text-3xl font-headline font-extrabold text-on-surface tracking-tight mb-1.5">Welcome Back</h2>
              <p className="text-on-surface-variant font-medium text-sm">Sign in to your data intelligence dashboard</p>
            </div>

            {/* Error message */}
            {error && (
              <div className="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-semibold flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">error</span>
                {error}
              </div>
            )}

            <form className="space-y-5" onSubmit={handleLogin}>
              {/* Email Field */}
              <div className="space-y-1.5">
                <label className="block font-semibold uppercase tracking-widest text-on-surface-variant text-[10px] ml-1" htmlFor="username">Email</label>
                <input
                  className="w-full bg-surface-container-low border-none rounded-xl py-3.5 px-5 text-sm text-on-surface placeholder:text-outline focus:ring-4 focus:ring-primary/20 focus:bg-surface-container-lowest transition-all duration-300 shadow-inner"
                  id="username"
                  name="username"
                  placeholder="name@auraretail.co.uk"
                  type="text"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              {/* Password Field */}
              <div className="space-y-1.5">
                <div className="flex justify-between items-center ml-1">
                  <label className="block font-semibold uppercase tracking-widest text-on-surface-variant text-[10px]" htmlFor="password">Password</label>
                </div>
                <input
                  className="w-full bg-surface-container-low border-none rounded-xl py-3.5 px-5 text-sm text-on-surface placeholder:text-outline focus:ring-4 focus:ring-primary/20 focus:bg-surface-container-lowest transition-all duration-300 shadow-inner"
                  id="password"
                  name="password"
                  placeholder="••••••••"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              {/* Sign In Button */}
              <button
                className={`w-full mt-2 bg-gradient-to-r from-primary to-primary-container text-on-primary py-4 rounded-xl font-headline font-extrabold text-base shadow-lg hover:shadow-primary/30 hover:scale-[1.02] active:scale-[0.99] transition-all duration-300 flex items-center justify-center gap-2 group ${loading ? 'opacity-70 pointer-events-none' : ''}`}
                type="submit"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined text-lg animate-spin">progress_activity</span>
                    Authenticating…
                  </>
                ) : (
                  <>
                    Sign In to Dashboard
                    <span className="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">arrow_forward</span>
                  </>
                )}
              </button>
            </form>

            {/* Demo Credentials Section */}
            <div className="mt-6">
              <div className="relative flex items-center justify-center mb-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-surface-container-highest" />
                </div>
                <button
                  onClick={() => setShowHint(!showHint)}
                  className="relative bg-surface-container-lowest px-4 text-[10px] font-semibold text-outline uppercase tracking-widest hover:text-primary transition-colors cursor-pointer flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-xs">passkey</span>
                  Demo Accounts
                  <span className={`material-symbols-outlined text-xs transition-transform ${showHint ? 'rotate-180' : ''}`}>expand_more</span>
                </button>
              </div>

              {showHint && (
                <div className="space-y-2 fade-slide-in">
                  {Object.entries(CREDENTIALS).map(([emailKey, cred]) => (
                    <button
                      key={emailKey}
                      onClick={() => quickLogin(emailKey, cred.password)}
                      className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-container-low border border-transparent hover:border-outline-variant/20 hover:bg-surface-container transition-all duration-200 group text-left"
                    >
                      <span
                        className="material-symbols-outlined text-xl"
                        style={{ color: cred.color }}
                      >
                        {cred.icon}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold text-on-surface">{cred.label}</div>
                        <div className="text-[10px] text-on-surface-variant font-mono truncate">{emailKey} / {cred.password}</div>
                      </div>
                      <span
                        className="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                        style={{ background: `${cred.color}18`, color: cred.color }}
                      >
                        {cred.region ? `${cred.region} Only` : "Full Access"}
                      </span>
                      <span className="material-symbols-outlined text-sm text-on-surface-variant group-hover:text-primary transition-colors">arrow_forward</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Info */}
            <p className="mt-5 text-center text-[10px] font-medium text-on-surface-variant/60">
              Enterprise RBAC demo — each login has different data access permissions
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full flex flex-col md:flex-row justify-between items-center px-6 md:px-16 py-10 bg-transparent text-xs tracking-wide text-on-surface-variant font-medium">
        <div className="mb-4 md:mb-0">© 2024 OmniData Analytics. All rights reserved. Built for scale.</div>
        <nav className="flex gap-6 md:gap-10">
          <Link className="hover:text-primary transition-colors" href="#">Privacy Policy</Link>
          <Link className="hover:text-primary transition-colors" href="#">Terms of Service</Link>
          <Link className="hover:text-primary transition-colors" href="#">System Status</Link>
          <Link className="hover:text-primary transition-colors" href="#">Help Center</Link>
        </nav>
      </footer>
    </div>
  );
}
