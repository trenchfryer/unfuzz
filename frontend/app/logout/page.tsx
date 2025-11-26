'use client';

import { useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';

export default function LogoutPage() {
  const router = useRouter();

  useEffect(() => {
    const signOut = async () => {
      const supabase = createClient();

      // Clear all auth data
      await supabase.auth.signOut();

      // Clear all cookies manually
      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });

      // Clear localStorage and sessionStorage
      localStorage.clear();
      sessionStorage.clear();

      // Redirect to login after 1 second
      setTimeout(() => {
        router.push('/auth/login');
      }, 1000);
    };

    signOut();
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
        <p className="mt-4 text-gray-600">Signing out...</p>
      </div>
    </div>
  );
}
