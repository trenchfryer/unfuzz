'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { UserCircleIcon, Cog6ToothIcon, ArrowRightOnRectangleIcon, PhotoIcon } from '@heroicons/react/24/outline';
import { createClient } from '@/lib/supabase/client';

export default function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    // Get current user
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setUserEmail(user.email || null);
      }
    };
    getUser();

    // Close menu when clicking outside
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [supabase]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/');
  };

  if (!userEmail) {
    return null;
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <UserCircleIcon className="h-6 w-6 text-gray-600" />
        <span className="text-sm font-medium text-gray-700">{userEmail}</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          <button
            onClick={() => {
              router.push('/library');
              setIsOpen(false);
            }}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <PhotoIcon className="h-5 w-5 text-gray-500" />
            <span>My Library</span>
          </button>

          <button
            onClick={() => {
              router.push('/settings/teams');
              setIsOpen(false);
            }}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Cog6ToothIcon className="h-5 w-5 text-gray-500" />
            <span>Teams & Settings</span>
          </button>

          <div className="border-t border-gray-200 my-1" />

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            <ArrowRightOnRectangleIcon className="h-5 w-5" />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </div>
  );
}
