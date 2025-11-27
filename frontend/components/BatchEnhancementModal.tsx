'use client';

import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, SparklesIcon } from '@heroicons/react/24/outline';

type PresetName = 'auto' | 'instagram' | 'story' | 'facebook' | 'snapchat' | 'print' | 'professional' | 'vibrant';

interface Preset {
  name: PresetName;
  display_name: string;
  description: string;
  aspect_ratio: string;
  icon: string;
}

interface BatchEnhancementModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedImageCount: number;
  onStartEnhancement: (preset: PresetName) => void;
}

const PRESETS: Preset[] = [
  {
    name: 'auto',
    display_name: 'Auto (AI Recommendations)',
    description: 'Smart AI adjustments with no preset modifiers',
    aspect_ratio: 'Original',
    icon: '🤖'
  },
  {
    name: 'instagram',
    display_name: 'Instagram Feed',
    description: 'Square crop (1:1) with vibrant colors',
    aspect_ratio: '1:1',
    icon: '📷'
  },
  {
    name: 'story',
    display_name: 'Stories & Reels',
    description: 'Vertical (9:16) for Instagram, TikTok',
    aspect_ratio: '9:16',
    icon: '📱'
  },
  {
    name: 'facebook',
    display_name: 'Facebook Feed',
    description: 'Vertical (4:5) optimized for mobile',
    aspect_ratio: '4:5',
    icon: '👍'
  },
  {
    name: 'snapchat',
    display_name: 'Snapchat',
    description: 'Vertical (9:16) with high impact colors',
    aspect_ratio: '9:16',
    icon: '👻'
  },
  {
    name: 'print',
    display_name: 'Print Quality',
    description: 'Maximum quality with natural colors',
    aspect_ratio: 'Original',
    icon: '🖨️'
  },
  {
    name: 'professional',
    display_name: 'Professional',
    description: 'Natural, balanced look',
    aspect_ratio: 'Original',
    icon: '💼'
  },
  {
    name: 'vibrant',
    display_name: 'Vibrant',
    description: 'Eye-catching colors for maximum impact',
    aspect_ratio: 'Original',
    icon: '🌈'
  }
];

export default function BatchEnhancementModal({
  isOpen,
  onClose,
  selectedImageCount,
  onStartEnhancement,
}: BatchEnhancementModalProps) {
  const [selectedPreset, setSelectedPreset] = useState<PresetName>('professional');

  const handleStart = () => {
    onStartEnhancement(selectedPreset);
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
          <div className="fixed inset-0 bg-black/30" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                      <SparklesIcon className="h-6 w-6 text-purple-600" />
                    </div>
                    <div>
                      <Dialog.Title as="h3" className="text-xl font-bold text-gray-900">
                        Enhance & Save to Library
                      </Dialog.Title>
                      <p className="text-sm text-gray-500 mt-1">
                        {selectedImageCount} {selectedImageCount === 1 ? 'image' : 'images'} selected
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                {/* Preset Selection */}
                <div className="mb-6 space-y-4">
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">
                      Choose Enhancement Preset
                    </h4>
                    <div className="grid grid-cols-2 gap-2 max-h-80 overflow-y-auto">
                      {PRESETS.map((preset) => (
                        <button
                          key={preset.name}
                          onClick={() => setSelectedPreset(preset.name)}
                          className={`
                            p-3 rounded-lg border-2 text-left transition-all
                            ${selectedPreset === preset.name
                              ? 'border-purple-500 bg-purple-50 shadow-md'
                              : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                            }
                          `}
                        >
                          <div className="flex items-start gap-2">
                            <span className="text-2xl">{preset.icon}</span>
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm font-semibold truncate ${
                                selectedPreset === preset.name ? 'text-purple-900' : 'text-gray-900'
                              }`}>
                                {preset.display_name}
                              </p>
                              <p className="text-xs text-gray-600 line-clamp-2 mt-0.5">
                                {preset.description}
                              </p>
                              <p className={`text-xs font-medium mt-1 ${
                                selectedPreset === preset.name ? 'text-purple-700' : 'text-gray-500'
                              }`}>
                                {preset.aspect_ratio}
                              </p>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <p className="text-xs text-blue-900">
                      <strong>✨ AI Enhancement:</strong> Automatically applies optimal adjustments
                      (exposure, contrast, sharpness) + preset optimizations for your target platform.
                    </p>
                  </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={onClose}
                    className="px-5 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleStart}
                    className="px-5 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium flex items-center gap-2"
                  >
                    <SparklesIcon className="h-5 w-5" />
                    Enhance & Save
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
