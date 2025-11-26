'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function SettingsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('teams');

  const tabs = [
    { id: 'teams', name: 'Teams & Players', href: '/settings/teams' },
    { id: 'profile', name: 'Profile', href: '/settings/profile' },
    { id: 'billing', name: 'Billing', href: '/settings/billing' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage your account, teams, and preferences
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <Link
                key={tab.id}
                href={tab.href}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.name}
              </Link>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="text-center py-12">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Welcome to Settings
            </h2>
            <p className="text-gray-600 mb-6">
              Select a tab above to manage your settings
            </p>
            <Link
              href="/settings/teams"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Manage Teams & Players
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
