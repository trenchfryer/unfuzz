import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';
import { type NextRequest } from 'next/server';

/**
 * Logout route - clears the session and redirects to home
 */
export async function GET(request: NextRequest) {
  const supabase = await createClient();

  // Sign out the user
  await supabase.auth.signOut();

  // Redirect to home page
  return NextResponse.redirect(new URL('/', request.url));
}
