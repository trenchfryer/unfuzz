'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getTeams, createTeam, deleteTeam } from '@/lib/api';
import type { Team, TeamCreate } from '@/lib/types';

export default function TeamsPage() {
  const router = useRouter();
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTeam, setNewTeam] = useState<TeamCreate>({
    name: '',
    sport: '',
    season: '',
  });

  useEffect(() => {
    loadTeams();
  }, []);

  async function loadTeams() {
    try {
      setLoading(true);
      const result = await getTeams();
      setTeams(result.teams);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load teams');
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateTeam(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createTeam(newTeam);
      setNewTeam({ name: '', sport: '', season: '' });
      setShowCreateForm(false);
      await loadTeams();
    } catch (err: any) {
      alert('Failed to create team: ' + err.message);
    }
  }

  async function handleDeleteTeam(teamId: string, teamName: string) {
    if (!confirm(`Delete team "${teamName}"? This will also delete all players.`)) {
      return;
    }

    try {
      await deleteTeam(teamId);
      await loadTeams();
    } catch (err: any) {
      alert('Failed to delete team: ' + err.message);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-12">
            <p className="text-gray-600">Loading teams...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <Link
                href="/app"
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                ← Back to Photos
              </Link>
              <span className="text-gray-300">|</span>
              <Link
                href="/settings"
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                Settings
              </Link>
            </div>
            <h1 className="text-3xl font-bold text-gray-900">Teams & Players</h1>
            <p className="mt-2 text-sm text-gray-600">
              Manage your sports teams and player rosters
            </p>
          </div>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            + Create Team
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Create Team Form */}
        {showCreateForm && (
          <div className="mb-6 bg-white shadow rounded-lg p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Create New Team</h2>
            <form onSubmit={handleCreateTeam} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Team Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newTeam.name}
                    onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., Warriors"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sport
                  </label>
                  <input
                    type="text"
                    value={newTeam.sport || ''}
                    onChange={(e) => setNewTeam({ ...newTeam, sport: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., Basketball"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Season
                  </label>
                  <input
                    type="text"
                    value={newTeam.season || ''}
                    onChange={(e) => setNewTeam({ ...newTeam, season: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., 2024-2025"
                  />
                </div>
              </div>
              <div className="flex space-x-3">
                <button
                  type="submit"
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Create Team
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Teams List */}
        {teams.length === 0 ? (
          <div className="bg-white shadow rounded-lg p-12 text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-2">No teams yet</h3>
            <p className="text-gray-600 mb-6">
              Create your first team to start tracking players and jersey numbers
            </p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              + Create Your First Team
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {teams.map((team) => (
              <div
                key={team.id}
                className="bg-white shadow rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
              >
                {/* Team Logo */}
                {team.logo_url && (
                  <div className="h-32 bg-gray-100 flex items-center justify-center">
                    <img
                      src={team.logo_url}
                      alt={team.name}
                      className="max-h-full max-w-full object-contain p-4"
                    />
                  </div>
                )}

                {/* Team Info */}
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{team.name}</h3>
                  {team.sport && (
                    <p className="text-sm text-gray-600 mb-1">Sport: {team.sport}</p>
                  )}
                  {team.season && (
                    <p className="text-sm text-gray-600 mb-3">Season: {team.season}</p>
                  )}
                  <p className="text-sm text-gray-500 mb-4">
                    {team.player_count || 0} players
                  </p>

                  {/* Actions */}
                  <div className="flex space-x-2">
                    <Link
                      href={`/settings/teams/${team.id}`}
                      className="flex-1 text-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Manage
                    </Link>
                    <button
                      onClick={() => handleDeleteTeam(team.id, team.name)}
                      className="px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
