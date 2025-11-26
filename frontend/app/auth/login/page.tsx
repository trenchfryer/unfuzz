'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/contexts/AuthContext';

export default function LoginPage() {
  const { signInWithGoogle, signOut, user, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const redirectTo = searchParams.get('redirectTo') || '/';

  useEffect(() => {
    // If user is already logged in, redirect (unless we're signing out)
    if (user && !loading && !isSigningOut) {
      router.push(redirectTo);
    }
  }, [user, loading, router, redirectTo, isSigningOut]);

  const handleGoogleSignIn = async () => {
    try {
      setIsSigningIn(true);
      setError(null);
      await signInWithGoogle();
    } catch (err: any) {
      console.error('Sign in error:', err);
      setError(err.message || 'Failed to sign in with Google');
      setIsSigningIn(false);
    }
  };

  const handleSignOut = async () => {
    try {
      setIsSigningOut(true);
      setError(null);
      await signOut();
      // Stay on login page after signing out
      setIsSigningOut(false);
    } catch (err: any) {
      console.error('Sign out error:', err);
      setError(err.message || 'Failed to sign out');
      setIsSigningOut(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="text-center">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              UnFuzz
            </h1>
            <p className="text-sm text-gray-600 mb-8">
              AI-Powered Photo Culling & Team Player Recognition
            </p>

            <div className="space-y-4">
              {user ? (
                <>
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-800 mb-3">
                      You are currently signed in as <strong>{user.email}</strong>
                    </p>
                    <button
                      onClick={handleSignOut}
                      disabled={isSigningOut}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isSigningOut ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          <span>Signing out...</span>
                        </>
                      ) : (
                        <span>Sign Out</span>
                      )}
                    </button>
                  </div>
                </>
              ) : (
                <button
                  onClick={handleGoogleSignIn}
                  disabled={isSigningIn}
                  className="w-full flex items-center justify-center gap-3 px-6 py-3 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSigningIn ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-700"></div>
                      <span>Signing in...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" viewBox="0 0 24 24">
                        <path
                          fill="currentColor"
                          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                        />
                        <path
                          fill="currentColor"
                          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        />
                        <path
                          fill="currentColor"
                          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                        />
                        <path
                          fill="currentColor"
                          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                        />
                      </svg>
                      <span>Continue with Google</span>
                    </>
                  )}
                </button>
              )}

              {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  {error}
                </div>
              )}
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-gray-200">
            <p className="text-xs text-center text-gray-500">
              By signing in, you agree to our Terms of Service and Privacy Policy
            </p>
          </div>
        </div>

        <div className="text-center text-sm text-gray-600">
          <p className="mb-2">Features:</p>
          <ul className="space-y-1 text-xs">
            <li>✨ AI-powered image quality analysis</li>
            <li>👥 Team player recognition by jersey number</li>
            <li>📸 Smart photo culling and sorting</li>
            <li>🤝 Collaborate with team members</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
