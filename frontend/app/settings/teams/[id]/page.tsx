'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  getTeam,
  updateTeam,
  uploadTeamLogo,
  deleteTeamLogo,
  getTeamPlayers,
  createPlayer,
  updatePlayer,
  deletePlayer,
  bulkCreatePlayers,
} from '@/lib/api';
import type { Team, TeamUpdate, Player, PlayerCreate, PlayerUpdate } from '@/lib/types';

export default function TeamDetailPage() {
  const params = useParams();
  const router = useRouter();
  const teamId = params.id as string;

  const [team, setTeam] = useState<Team | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Team editing state
  const [editingTeam, setEditingTeam] = useState(false);
  const [teamForm, setTeamForm] = useState<TeamUpdate>({});

  // Batch player creation state
  const [showAddPlayer, setShowAddPlayer] = useState(false);
  const [pendingPlayers, setPendingPlayers] = useState<Omit<PlayerCreate, 'team_id'>[]>([]);
  const [editingPlayer, setEditingPlayer] = useState<string | null>(null);
  const [newPlayer, setNewPlayer] = useState<Omit<PlayerCreate, 'team_id'>>({
    jersey_number: '',
    first_name: '',
    last_name: '',
    position: '',
    grade_year: '',
  });

  useEffect(() => {
    loadTeamData();
  }, [teamId]);

  async function loadTeamData() {
    try {
      setLoading(true);
      const [teamData, playersData] = await Promise.all([
        getTeam(teamId),
        getTeamPlayers(teamId),
      ]);
      setTeam(teamData);
      setPlayers(playersData.players);
      setTeamForm({
        name: teamData.name,
        sport: teamData.sport,
        season: teamData.season,
        primary_color: teamData.primary_color,
        secondary_color: teamData.secondary_color,
        notes: teamData.notes,
      });
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load team');
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdateTeam(e: React.FormEvent) {
    e.preventDefault();
    try {
      await updateTeam(teamId, teamForm);
      await loadTeamData();
      setEditingTeam(false);
    } catch (err: any) {
      alert('Failed to update team: ' + err.message);
    }
  }

  async function handleLogoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      await uploadTeamLogo(teamId, file);
      await loadTeamData();
    } catch (err: any) {
      alert('Failed to upload logo: ' + err.message);
    }
  }

  async function handleDeleteLogo() {
    if (!confirm('Delete team logo?')) return;

    try {
      await deleteTeamLogo(teamId);
      await loadTeamData();
    } catch (err: any) {
      alert('Failed to delete logo: ' + err.message);
    }
  }

  function handleAddPlayerToPending(e: React.FormEvent) {
    e.preventDefault();

    // Check for duplicate jersey numbers in pending list
    const isDuplicate = pendingPlayers.some(p => p.jersey_number === newPlayer.jersey_number);
    if (isDuplicate) {
      alert(`Jersey #${newPlayer.jersey_number} is already in your pending list`);
      return;
    }

    // Add to pending list
    setPendingPlayers([...pendingPlayers, { ...newPlayer }]);

    // Reset form
    setNewPlayer({
      jersey_number: '',
      first_name: '',
      last_name: '',
      position: '',
      grade_year: '',
    });
  }

  function handleRemovePendingPlayer(index: number) {
    setPendingPlayers(pendingPlayers.filter((_, i) => i !== index));
  }

  async function handleSaveAllPlayers() {
    if (pendingPlayers.length === 0) return;

    try {
      setSaving(true);
      await bulkCreatePlayers(teamId, pendingPlayers);
      setPendingPlayers([]);
      setShowAddPlayer(false);
      await loadTeamData();
      alert(`Successfully added ${pendingPlayers.length} player(s)!`);
    } catch (err: any) {
      alert('Failed to save players: ' + err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdatePlayer(playerId: string, update: PlayerUpdate) {
    try {
      await updatePlayer(playerId, update);
      await loadTeamData();
      setEditingPlayer(null);
    } catch (err: any) {
      alert('Failed to update player: ' + err.message);
    }
  }

  async function handleDeletePlayer(playerId: string, playerName: string) {
    if (!confirm(`Delete player "${playerName}"?`)) return;

    try {
      await deletePlayer(playerId);
      await loadTeamData();
    } catch (err: any) {
      alert('Failed to delete player: ' + err.message);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-12">
            <p className="text-gray-600">Loading team...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-12">
            <p className="text-red-600">{error || 'Team not found'}</p>
            <Link href="/settings/teams" className="text-blue-600 hover:text-blue-800 mt-4 inline-block">
              ← Back to Teams
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <Link
              href="/app"
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              ← Back to Photos
            </Link>
            <span className="text-gray-300">|</span>
            <Link
              href="/settings/teams"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              All Teams
            </Link>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">{team.name}</h1>
          <p className="mt-2 text-sm text-gray-600">
            {team.sport && `${team.sport}`}
            {team.season && ` • ${team.season}`}
          </p>
        </div>

        {/* Team Details Card */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex justify-between items-start mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Team Details</h2>
            <button
              onClick={() => setEditingTeam(!editingTeam)}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              {editingTeam ? 'Cancel' : 'Edit'}
            </button>
          </div>

          {editingTeam ? (
            <form onSubmit={handleUpdateTeam} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Team Name
                  </label>
                  <input
                    type="text"
                    value={teamForm.name || ''}
                    onChange={(e) => setTeamForm({ ...teamForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sport
                  </label>
                  <input
                    type="text"
                    value={teamForm.sport || ''}
                    onChange={(e) => setTeamForm({ ...teamForm, sport: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Season
                  </label>
                  <input
                    type="text"
                    value={teamForm.season || ''}
                    onChange={(e) => setTeamForm({ ...teamForm, season: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Primary Color
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="color"
                      value={teamForm.primary_color || '#000000'}
                      onChange={(e) => setTeamForm({ ...teamForm, primary_color: e.target.value })}
                      className="h-10 w-20 border border-gray-300 rounded-md"
                    />
                    <input
                      type="text"
                      value={teamForm.primary_color || ''}
                      onChange={(e) => setTeamForm({ ...teamForm, primary_color: e.target.value })}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      placeholder="#000000"
                    />
                  </div>
                </div>
              </div>
              <div className="flex space-x-3">
                <button
                  type="submit"
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
                >
                  Save Changes
                </button>
                <button
                  type="button"
                  onClick={() => setEditingTeam(false)}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center space-x-4">
                {team.logo_url && (
                  <div className="w-24 h-24 bg-gray-100 rounded-lg flex items-center justify-center p-2">
                    <img src={team.logo_url} alt="Team logo" className="max-w-full max-h-full object-contain" />
                  </div>
                )}
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Team Logo
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleLogoUpload}
                      className="text-sm text-gray-600"
                    />
                    {team.logo_url && (
                      <button
                        onClick={handleDeleteLogo}
                        className="text-sm text-red-600 hover:text-red-800"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Players Roster Card */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-gray-900">
              Player Roster ({players.length})
            </h2>
            <button
              onClick={() => setShowAddPlayer(!showAddPlayer)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
            >
              + Add Player
            </button>
          </div>

          {/* Add Player Form */}
          {showAddPlayer && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-900 mb-3">Add Players to Roster</h3>

              {/* Player Entry Form */}
              <form onSubmit={handleAddPlayerToPending}>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Jersey # *
                    </label>
                    <input
                      type="text"
                      required
                      value={newPlayer.jersey_number}
                      onChange={(e) => setNewPlayer({ ...newPlayer, jersey_number: e.target.value })}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md"
                      placeholder="23"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      First Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={newPlayer.first_name}
                      onChange={(e) => setNewPlayer({ ...newPlayer, first_name: e.target.value })}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Last Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={newPlayer.last_name}
                      onChange={(e) => setNewPlayer({ ...newPlayer, last_name: e.target.value })}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Position
                    </label>
                    <input
                      type="text"
                      value={newPlayer.position || ''}
                      onChange={(e) => setNewPlayer({ ...newPlayer, position: e.target.value })}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Grade/Year
                    </label>
                    <input
                      type="text"
                      value={newPlayer.grade_year || ''}
                      onChange={(e) => setNewPlayer({ ...newPlayer, grade_year: e.target.value })}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md"
                    />
                  </div>
                </div>
                <div className="flex space-x-2 mt-3">
                  <button
                    type="submit"
                    className="px-3 py-1 text-sm border border-transparent font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                  >
                    + Add to List
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowAddPlayer(false);
                      setPendingPlayers([]);
                    }}
                    className="px-3 py-1 text-sm border border-gray-300 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </form>

              {/* Pending Players List */}
              {pendingPlayers.length > 0 && (
                <div className="mt-4 border-t pt-4">
                  <div className="flex justify-between items-center mb-2">
                    <h4 className="text-sm font-medium text-gray-700">
                      Players to Add ({pendingPlayers.length})
                    </h4>
                    <button
                      onClick={handleSaveAllPlayers}
                      disabled={saving}
                      className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {saving ? 'Saving...' : `Save All ${pendingPlayers.length} Player(s)`}
                    </button>
                  </div>
                  <div className="bg-white rounded border divide-y">
                    {pendingPlayers.map((player, index) => (
                      <div key={index} className="flex items-center justify-between px-3 py-2">
                        <div className="flex items-center space-x-4 text-sm">
                          <span className="font-medium text-gray-900 w-8">#{player.jersey_number}</span>
                          <span className="text-gray-700">{player.first_name} {player.last_name}</span>
                          {player.position && <span className="text-gray-500">{player.position}</span>}
                          {player.grade_year && <span className="text-gray-500">{player.grade_year}</span>}
                        </div>
                        <button
                          onClick={() => handleRemovePendingPlayer(index)}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Players Table */}
          {players.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-600">No players added yet</p>
              <button
                onClick={() => setShowAddPlayer(true)}
                className="mt-4 text-blue-600 hover:text-blue-800"
              >
                Add your first player
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      #
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Position
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Grade/Year
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {players.sort((a, b) => parseInt(a.jersey_number) - parseInt(b.jersey_number)).map((player) => (
                    <tr key={player.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
                        {player.jersey_number}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                        {player.first_name} {player.last_name}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {player.position || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        {player.grade_year || '-'}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleDeletePlayer(player.id, `${player.first_name} ${player.last_name}`)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
