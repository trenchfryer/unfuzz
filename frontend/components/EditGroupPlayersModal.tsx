'use client';

import { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, PencilIcon, UserGroupIcon } from '@heroicons/react/24/outline';

interface PlayerData {
  jersey_number: string;
  player_name: string;
}

interface EditGroupPlayersModalProps {
  isOpen: boolean;
  onClose: () => void;
  detectedPlayers: Array<{number: string; confidence: number; player_name?: string}>;
  onSave: (players: PlayerData[]) => Promise<void>;
}

export default function EditGroupPlayersModal({
  isOpen,
  onClose,
  detectedPlayers,
  onSave,
}: EditGroupPlayersModalProps) {
  const [players, setPlayers] = useState<PlayerData[]>(
    detectedPlayers.map(p => ({
      jersey_number: p.number,
      player_name: p.player_name || ''
    }))
  );
  const [saving, setSaving] = useState(false);

  const handlePlayerChange = (index: number, field: 'jersey_number' | 'player_name', value: string) => {
    const newPlayers = [...players];
    newPlayers[index][field] = value;
    setPlayers(newPlayers);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(players);
      onClose();
    } catch (error) {
      console.error('Failed to save group players:', error);
      alert('Failed to save changes. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-lg bg-white p-6 shadow-xl transition-all">
                <div className="flex items-center justify-between mb-4">
                  <Dialog.Title className="text-lg font-semibold flex items-center gap-2">
                    <UserGroupIcon className="h-5 w-5 text-green-600" />
                    Edit Group Players
                  </Dialog.Title>
                  <button
                    onClick={onClose}
                    className="p-1 hover:bg-gray-100 rounded transition-colors"
                  >
                    <XMarkIcon className="h-5 w-5 text-gray-500" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                    <p className="text-xs text-green-800">
                      <strong>Group Photo:</strong> Edit each player's jersey number and name below.
                    </p>
                  </div>

                  {players.map((player, index) => (
                    <div key={index} className="p-3 border border-gray-200 rounded-lg space-y-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700">Player {index + 1}</span>
                        {detectedPlayers[index]?.confidence && (
                          <span className="text-xs text-gray-500">
                            {Math.round(detectedPlayers[index].confidence * 100)}% confidence
                          </span>
                        )}
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Jersey Number
                        </label>
                        <input
                          type="text"
                          value={player.jersey_number}
                          onChange={(e) => handlePlayerChange(index, 'jersey_number', e.target.value)}
                          placeholder="e.g., 23"
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Player Name
                        </label>
                        <input
                          type="text"
                          value={player.player_name}
                          onChange={(e) => handlePlayerChange(index, 'player_name', e.target.value)}
                          placeholder="e.g., John Smith"
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>
                    </div>
                  ))}

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <p className="text-xs text-blue-800">
                      Manual corrections will override AI-detected values. Leave blank to use AI detection.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={onClose}
                    disabled={saving}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save All Players'}
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
