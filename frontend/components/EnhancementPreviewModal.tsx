'use client';

import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ArrowDownTrayIcon, CloudArrowUpIcon } from '@heroicons/react/24/outline';
import { SparklesIcon } from '@heroicons/react/24/solid';
import type { ImageData, PostProcessingRecommendations } from '@/lib/types';
import { getEnhancementPreviewUrl, downloadEnhancedImage } from '@/lib/api';

interface EnhancementPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  image: ImageData;
}

export default function EnhancementPreviewModal({
  isOpen,
  onClose,
  image,
}: EnhancementPreviewModalProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [previewLoaded, setPreviewLoaded] = useState(false);

  const postProcessing = image.analysis?.post_processing;
  const previewUrl = getEnhancementPreviewUrl(image.id);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const filename = image.filename.replace(/\.[^/.]+$/, '_enhanced.jpg');
      await downloadEnhancedImage(image.id, filename);
    } catch (error) {
      console.error('Error downloading enhanced image:', error);
      alert('Failed to download enhanced image. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleSaveToGoogleDrive = () => {
    // Placeholder for Google Drive integration
    alert('Google Drive integration coming soon!');
  };

  const getAdjustmentLabel = (value: number | undefined, suffix: string = '') => {
    if (value === undefined || value === null || value === 0) return null;
    const sign = value > 0 ? '+' : '';
    return `${sign}${value}${suffix}`;
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
          <div className="fixed inset-0 bg-black/75" />
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
              <Dialog.Panel className="w-full max-w-7xl transform overflow-hidden rounded-2xl bg-gray-900 p-6 shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <SparklesIcon className="h-6 w-6 text-purple-400" />
                    <Dialog.Title className="text-2xl font-bold text-white">
                      Enhancement Preview
                    </Dialog.Title>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                {/* Before/After Comparison */}
                <div className="grid grid-cols-2 gap-6 mb-6">
                  {/* Original Image */}
                  <div>
                    <div className="text-sm font-medium text-gray-400 mb-2">Original</div>
                    <div className="relative bg-gray-800 rounded-lg overflow-hidden aspect-[4/3]">
                      <img
                        src={image.file_path}
                        alt="Original"
                        className="w-full h-full object-contain"
                      />
                    </div>
                  </div>

                  {/* Enhanced Image */}
                  <div>
                    <div className="text-sm font-medium text-purple-400 mb-2 flex items-center gap-2">
                      <SparklesIcon className="h-4 w-4" />
                      Enhanced
                    </div>
                    <div className="relative bg-gray-800 rounded-lg overflow-hidden aspect-[4/3]">
                      {!previewLoaded && (
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                        </div>
                      )}
                      <img
                        src={previewUrl}
                        alt="Enhanced"
                        className="w-full h-full object-contain"
                        onLoad={() => setPreviewLoaded(true)}
                      />
                    </div>
                  </div>
                </div>

                {/* Adjustments Applied */}
                {postProcessing && (
                  <div className="mb-6 p-4 bg-gray-800 rounded-lg">
                    <h3 className="text-sm font-semibold text-gray-300 mb-3">Adjustments Applied:</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {getAdjustmentLabel(postProcessing.exposure_adjustment, ' EV') && (
                        <div className="text-sm">
                          <span className="text-gray-400">Exposure:</span>{' '}
                          <span className="text-white font-medium">
                            {getAdjustmentLabel(postProcessing.exposure_adjustment, ' EV')}
                          </span>
                        </div>
                      )}
                      {getAdjustmentLabel(postProcessing.contrast_adjustment) && (
                        <div className="text-sm">
                          <span className="text-gray-400">Contrast:</span>{' '}
                          <span className="text-white font-medium">
                            {getAdjustmentLabel(postProcessing.contrast_adjustment)}
                          </span>
                        </div>
                      )}
                      {getAdjustmentLabel(postProcessing.saturation_adjustment) && (
                        <div className="text-sm">
                          <span className="text-gray-400">Saturation:</span>{' '}
                          <span className="text-white font-medium">
                            {getAdjustmentLabel(postProcessing.saturation_adjustment)}
                          </span>
                        </div>
                      )}
                      {getAdjustmentLabel(postProcessing.vibrance_adjustment) && (
                        <div className="text-sm">
                          <span className="text-gray-400">Vibrance:</span>{' '}
                          <span className="text-white font-medium">
                            {getAdjustmentLabel(postProcessing.vibrance_adjustment)}
                          </span>
                        </div>
                      )}
                      {getAdjustmentLabel(postProcessing.sharpness_adjustment) && (
                        <div className="text-sm">
                          <span className="text-gray-400">Sharpness:</span>{' '}
                          <span className="text-white font-medium">
                            {getAdjustmentLabel(postProcessing.sharpness_adjustment)}
                          </span>
                        </div>
                      )}
                      {postProcessing.noise_reduction && postProcessing.noise_reduction > 0 && (
                        <div className="text-sm">
                          <span className="text-gray-400">Noise Reduction:</span>{' '}
                          <span className="text-white font-medium">
                            {postProcessing.noise_reduction}%
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveToGoogleDrive}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <CloudArrowUpIcon className="h-5 w-5" />
                    Save to Google Drive
                  </button>
                  <button
                    onClick={handleDownload}
                    disabled={isDownloading}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ArrowDownTrayIcon className="h-5 w-5" />
                    {isDownloading ? 'Downloading...' : 'Download Enhanced'}
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
