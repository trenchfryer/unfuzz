'use client';

import { Fragment, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ArrowDownTrayIcon, BookmarkIcon } from '@heroicons/react/24/outline';
import { SparklesIcon, CheckCircleIcon } from '@heroicons/react/24/solid';
import type { ImageData, PostProcessingRecommendations } from '@/lib/types';
import { getEnhancementPreviewUrl, downloadEnhancedImage, saveEnhancedImageToLibrary, getEnhancementDownloadUrl } from '@/lib/api';

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
  const [isSavingOriginal, setIsSavingOriginal] = useState(false);
  const [isSavingEnhanced, setIsSavingEnhanced] = useState(false);
  const [savedOriginal, setSavedOriginal] = useState(false);
  const [savedEnhanced, setSavedEnhanced] = useState(false);
  const [previewLoaded, setPreviewLoaded] = useState(false);

  const postProcessing = image.analysis?.post_processing;
  const previewUrl = getEnhancementPreviewUrl(image.id);
  const enhancedUrl = getEnhancementDownloadUrl(image.id);

  const handleDownloadEnhanced = async () => {
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

  const handleDownloadOriginal = () => {
    const link = document.createElement('a');
    link.href = image.file_path;
    link.download = image.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleSaveOriginalToLibrary = async () => {
    setIsSavingOriginal(true);
    try {
      await saveEnhancedImageToLibrary({
        original_image_id: image.id,
        team_id: image.team_id,
        player_id: image.player_id,
        title: image.filename.replace(/\.[^/.]+$/, '') + ' (Original)',
        save_original: true,
      });
      setSavedOriginal(true);
      setTimeout(() => {
        setSavedOriginal(false);
      }, 3000);
    } catch (error) {
      console.error('Error saving original to library:', error);
      alert('Failed to save to library. Please try again.');
    } finally {
      setIsSavingOriginal(false);
    }
  };

  const handleSaveEnhancedToLibrary = async () => {
    setIsSavingEnhanced(true);
    try {
      await saveEnhancedImageToLibrary({
        original_image_id: image.id,
        team_id: image.team_id,
        player_id: image.player_id,
        player_name_override: image.player_name,
        jersey_number_override: image.detected_jersey_number,
        title: image.filename.replace(/\.[^/.]+$/, ''),
        post_processing: image.analysis?.post_processing,
      });
      setSavedEnhanced(true);
      setTimeout(() => {
        setSavedEnhanced(false);
      }, 3000);
    } catch (error) {
      console.error('Error saving enhanced to library:', error);
      alert('Failed to save to library. Please try again.');
    } finally {
      setIsSavingEnhanced(false);
    }
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
                    <div className="relative bg-gray-800 rounded-lg overflow-hidden aspect-[4/3] mb-3">
                      <img
                        src={image.file_path}
                        alt="Original"
                        className="w-full h-full object-contain"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={handleDownloadOriginal}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors text-sm"
                      >
                        <ArrowDownTrayIcon className="h-4 w-4" />
                        Download
                      </button>
                      <button
                        onClick={handleSaveOriginalToLibrary}
                        disabled={isSavingOriginal || savedOriginal}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                      >
                        {savedOriginal ? (
                          <>
                            <CheckCircleIcon className="h-4 w-4" />
                            Saved
                          </>
                        ) : (
                          <>
                            <BookmarkIcon className="h-4 w-4" />
                            {isSavingOriginal ? 'Saving...' : 'Save'}
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Enhanced Image */}
                  <div>
                    <div className="text-sm font-medium text-purple-400 mb-2 flex items-center gap-2">
                      <SparklesIcon className="h-4 w-4" />
                      Enhanced
                    </div>
                    <div className="relative bg-gray-800 rounded-lg overflow-hidden aspect-[4/3] mb-3">
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
                    <div className="flex gap-2">
                      <button
                        onClick={handleDownloadEnhanced}
                        disabled={isDownloading}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                      >
                        <ArrowDownTrayIcon className="h-4 w-4" />
                        {isDownloading ? 'Downloading...' : 'Download'}
                      </button>
                      <button
                        onClick={handleSaveEnhancedToLibrary}
                        disabled={isSavingEnhanced || savedEnhanced}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                      >
                        {savedEnhanced ? (
                          <>
                            <CheckCircleIcon className="h-4 w-4" />
                            Saved
                          </>
                        ) : (
                          <>
                            <BookmarkIcon className="h-4 w-4" />
                            {isSavingEnhanced ? 'Saving...' : 'Save'}
                          </>
                        )}
                      </button>
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
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {savedOriginal && (
                      <div className="flex items-center gap-2 text-green-400 text-sm font-medium">
                        <CheckCircleIcon className="h-5 w-5" />
                        Original saved to library!
                      </div>
                    )}
                    {savedEnhanced && (
                      <div className="flex items-center gap-2 text-green-400 text-sm font-medium">
                        <CheckCircleIcon className="h-5 w-5" />
                        Enhanced saved to library!
                      </div>
                    )}
                  </div>
                  <button
                    onClick={onClose}
                    className="px-6 py-2 text-gray-300 hover:text-white transition-colors"
                  >
                    Close
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
