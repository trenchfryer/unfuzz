'use client';

import { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, PencilIcon } from '@heroicons/react/24/outline';

interface EditPlayerModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentJerseyNumber?: string;
  currentPlayerName?: string;
  onSave: (jerseyNumber: string, playerName: string) => Promise<void>;
}

export default function EditPlayerModal({
  isOpen,
  onClose,
  currentJerseyNumber,
  currentPlayerName,
  onSave,
}: EditPlayerModalProps) {
  const [jerseyNumber, setJerseyNumber] = useState(currentJerseyNumber || '');
  const [playerName, setPlayerName] = useState(currentPlayerName || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(jerseyNumber, playerName);
      onClose();
    } catch (error) {
      console.error('Failed to save player override:', error);
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
                    <PencilIcon className="h-5 w-5 text-blue-600" />
                    Edit Player Info
                  </Dialog.Title>
                  <button
                    onClick={onClose}
                    className="p-1 hover:bg-gray-100 rounded transition-colors"
                  >
                    <XMarkIcon className="h-5 w-5 text-gray-500" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Jersey Number
                    </label>
                    <input
                      type="text"
                      value={jerseyNumber}
                      onChange={(e) => setJerseyNumber(e.target.value)}
                      placeholder="e.g., 23"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Player Name
                    </label>
                    <input
                      type="text"
                      value={playerName}
                      onChange={(e) => setPlayerName(e.target.value)}
                      placeholder="e.g., John Smith"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

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
                    {saving ? 'Saving...' : 'Save Changes'}
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
