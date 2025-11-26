import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';
import { type NextRequest } from 'next/server';

/**
 * OAuth callback route
 * Handles the redirect from Google OAuth and exchanges the code for a session
 */
export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get('code');
  const redirectTo = requestUrl.searchParams.get('redirectTo') || '/app';

  if (code) {
    const supabase = await createClient();

    // Exchange code for session
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      console.error('Error exchanging code for session:', error);
      // Redirect to login with error
      return NextResponse.redirect(
        new URL(`/auth/login?error=${encodeURIComponent(error.message)}`, requestUrl.origin)
      );
    }
  }

  // Redirect to the original destination or /app
  return NextResponse.redirect(new URL(redirectTo, requestUrl.origin));
}
