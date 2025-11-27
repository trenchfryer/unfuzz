'use client';

import { Fragment, useState, useRef, useEffect } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ArrowDownTrayIcon, BookmarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { SparklesIcon, CheckCircleIcon } from '@heroicons/react/24/solid';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';
import { motion, AnimatePresence } from 'framer-motion';
import type { ImageData } from '@/lib/types';
import { downloadEnhancedImage, saveEnhancedImageToLibrary } from '@/lib/api';

interface ModernEnhancementModalProps {
  isOpen: boolean;
  onClose: () => void;
  image: ImageData;
}

interface Adjustments {
  brightness: number;
  contrast: number;
  saturation: number;
  vibrance: number;
  sharpness: number;
  exposure: number;
}

const PRESETS = {
  ai: { brightness: 100, contrast: 100, saturation: 100, vibrance: 0, sharpness: 0, exposure: 0 }, // Placeholder, set dynamically
  none: { brightness: 100, contrast: 100, saturation: 100, vibrance: 0, sharpness: 0, exposure: 0 },
  vivid: { brightness: 105, contrast: 110, saturation: 120, vibrance: 15, sharpness: 10, exposure: 0.1 },
  natural: { brightness: 102, contrast: 105, saturation: 95, vibrance: 5, sharpness: 5, exposure: 0.05 },
  dramatic: { brightness: 95, contrast: 130, saturation: 110, vibrance: 20, sharpness: 15, exposure: -0.1 },
  soft: { brightness: 108, contrast: 90, saturation: 95, vibrance: 0, sharpness: 0, exposure: 0.15 },
};

export default function ModernEnhancementModal({
  isOpen,
  onClose,
  image,
}: ModernEnhancementModalProps) {
  const [adjustments, setAdjustments] = useState<Adjustments>(PRESETS.none);
  const [selectedPreset, setSelectedPreset] = useState<keyof typeof PRESETS>('ai');
  const [aiRecommendations, setAiRecommendations] = useState<Adjustments | null>(null);
  const [showBeforeAfter, setShowBeforeAfter] = useState(true);
  const [beforeAfterPosition, setBeforeAfterPosition] = useState(50);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingOriginal, setIsSavingOriginal] = useState(false);
  const [saved, setSaved] = useState(false);
  const [savedOriginal, setSavedOriginal] = useState(false);
  const [activeTab, setActiveTab] = useState<'adjust' | 'filters'>('filters');
  const [showCameraSettings, setShowCameraSettings] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  const cameraSettings = image.analysis?.camera_settings;
  const postProcessing = image.analysis?.post_processing;

  // Load AI recommendations as DEFAULT starting point
  useEffect(() => {
    if (image.analysis?.post_processing) {
      const pp = image.analysis.post_processing;

      console.log('🔍 AI Post-processing recommendations:', pp);

      // Convert AI recommendations to CSS filter percentages
      // Exposure adjustment is in EV: 1 EV = double brightness
      // Formula: 100% + (EV * 40) gives reasonable results
      // e.g., 0.5 EV = 120%, -0.5 EV = 80%
      const aiAdjustments = {
        brightness: 100 + (pp.exposure_adjustment || 0) * 40,
        // Contrast/saturation are already -100 to +100, map to CSS percentage
        contrast: 100 + (pp.contrast_adjustment || 0),
        saturation: 100 + (pp.saturation_adjustment || 0),
        // Note: CSS doesn't support vibrance/sharpness, these are for backend only
        vibrance: pp.vibrance_adjustment || 0,
        sharpness: pp.sharpness_adjustment || 0,
        exposure: pp.exposure_adjustment || 0,
      };

      console.log('✨ AI adjustments converted to CSS:', aiAdjustments);

      // Store AI recommendations
      setAiRecommendations(aiAdjustments);

      // Set AI adjustments as DEFAULT
      setAdjustments(aiAdjustments);
      setSelectedPreset('ai');

      // Update the AI preset dynamically
      PRESETS.ai = aiAdjustments;
    } else {
      console.log('⚠️ No AI recommendations found, using None preset');
      // No AI recommendations, default to none
      setSelectedPreset('none');
    }
  }, [image]);

  const applyPreset = (preset: keyof typeof PRESETS) => {
    setAdjustments(PRESETS[preset]);
    setSelectedPreset(preset);
  };

  const handleAdjustmentChange = (key: keyof Adjustments, value: number) => {
    setAdjustments(prev => ({ ...prev, [key]: value }));
    setSelectedPreset('none'); // Custom adjustment
  };

  const resetToOriginal = () => {
    setAdjustments(PRESETS.none);
    setSelectedPreset('none');
  };

  // Generate CSS filter string for instant preview
  const getFilterStyle = () => {
    const { brightness, contrast, saturation } = adjustments;
    return `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%)`;
  };

  const handleSaveEnhanced = async () => {
    setIsSaving(true);
    try {
      // Convert CSS adjustments BACK to backend parameters
      // These formulas MUST match the conversion in useEffect!
      const postProcessing = {
        // brightness: 100 + (ev * 40) => ev = (brightness - 100) / 40
        exposure_adjustment: (adjustments.brightness - 100) / 40,
        // contrast/saturation: 100 + value => value = (contrast - 100)
        contrast_adjustment: (adjustments.contrast - 100),
        saturation_adjustment: (adjustments.saturation - 100),
        vibrance_adjustment: adjustments.vibrance,
        sharpness_adjustment: adjustments.sharpness,
        can_auto_fix: false,
      };

      console.log('💾 Saving with backend parameters:', postProcessing);

      await saveEnhancedImageToLibrary({
        original_image_id: image.id,
        team_id: image.team_id,
        player_id: image.player_id,
        player_name_override: image.player_name,
        jersey_number_override: image.detected_jersey_number,
        title: image.filename.replace(/\.[^/.]+$/, ''),
        post_processing: postProcessing,
      });

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Error saving enhanced image:', error);
      alert('Failed to save. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveOriginal = async () => {
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
      setTimeout(() => setSavedOriginal(false), 3000);
    } catch (error) {
      console.error('Error saving original:', error);
      alert('Failed to save original. Please try again.');
    } finally {
      setIsSavingOriginal(false);
    }
  };

  const handleDownload = async () => {
    try {
      const filename = image.filename.replace(/\.[^/.]+$/, '_enhanced.jpg');
      await downloadEnhancedImage(image.id, filename);
    } catch (error) {
      console.error('Error downloading:', error);
      alert('Failed to download. Please try again.');
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
          <div className="fixed inset-0 bg-black/90" />
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
              <Dialog.Panel className="w-full max-w-7xl transform overflow-hidden rounded-3xl bg-gray-900 shadow-2xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                      <SparklesIcon className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <Dialog.Title className="text-xl font-bold text-white">
                        Enhance Image
                      </Dialog.Title>
                      <p className="text-xs text-gray-400">Instant AI-powered adjustments</p>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-gray-400 hover:text-white transition-colors p-2 hover:bg-gray-800 rounded-full"
                  >
                    <XMarkIcon className="h-6 w-6" />
                  </button>
                </div>

                <div className="flex flex-col lg:flex-row">
                  {/* Preview Area */}
                  <div className="flex-1 p-6 bg-black/50">
                    {/* Before/After Toggle */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setShowBeforeAfter(!showBeforeAfter)}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                            showBeforeAfter
                              ? 'bg-purple-600 text-white'
                              : 'bg-gray-800 text-gray-400 hover:text-white'
                          }`}
                        >
                          Before/After
                        </button>
                        <button
                          onClick={resetToOriginal}
                          className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-800 text-gray-400 hover:text-white transition-colors flex items-center gap-2"
                        >
                          <ArrowPathIcon className="h-4 w-4" />
                          Reset
                        </button>
                      </div>
                      {selectedPreset !== 'none' && (
                        <motion.div
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="text-sm text-purple-400 font-medium"
                        >
                          {selectedPreset.charAt(0).toUpperCase() + selectedPreset.slice(1)} preset
                        </motion.div>
                      )}
                    </div>

                    {/* Image Preview with Before/After */}
                    <div className="relative rounded-2xl overflow-hidden bg-gray-900 aspect-[4/3]">
                      {showBeforeAfter ? (
                        <div className="relative w-full h-full">
                          {/* After (Enhanced) */}
                          <div className="absolute inset-0">
                            <img
                              src={image.file_path}
                              alt="Enhanced"
                              className="w-full h-full object-contain transition-all duration-300"
                              style={{ filter: getFilterStyle() }}
                            />
                          </div>
                          {/* Before (Original) with clip mask */}
                          <div
                            className="absolute inset-0 overflow-hidden"
                            style={{ clipPath: `inset(0 ${100 - beforeAfterPosition}% 0 0)` }}
                          >
                            <img
                              src={image.file_path}
                              alt="Original"
                              className="w-full h-full object-contain"
                            />
                          </div>
                          {/* Slider handle */}
                          <div
                            className="absolute top-0 bottom-0 w-1 bg-white shadow-2xl cursor-ew-resize z-10"
                            style={{ left: `${beforeAfterPosition}%` }}
                            onMouseDown={(e) => {
                              const container = e.currentTarget.parentElement;
                              if (!container) return;

                              const handleMove = (moveEvent: MouseEvent) => {
                                const rect = container.getBoundingClientRect();
                                const x = moveEvent.clientX - rect.left;
                                const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
                                setBeforeAfterPosition(percentage);
                              };

                              const handleUp = () => {
                                document.removeEventListener('mousemove', handleMove);
                                document.removeEventListener('mouseup', handleUp);
                              };

                              document.addEventListener('mousemove', handleMove);
                              document.addEventListener('mouseup', handleUp);
                            }}
                          >
                            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center">
                              <div className="w-3 h-3 border-2 border-gray-900 rounded-full" />
                            </div>
                          </div>
                          {/* Labels */}
                          <div className="absolute top-4 left-4 px-3 py-1.5 bg-black/70 text-white text-xs font-semibold rounded-full">
                            Before
                          </div>
                          <div className="absolute top-4 right-4 px-3 py-1.5 bg-black/70 text-white text-xs font-semibold rounded-full">
                            After
                          </div>
                        </div>
                      ) : (
                        <img
                          src={image.file_path}
                          alt="Enhanced"
                          className="w-full h-full object-contain transition-all duration-300"
                          style={{ filter: getFilterStyle() }}
                        />
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="space-y-3 mt-6">
                      {/* Enhanced Image Actions */}
                      <div className="flex gap-3">
                        <button
                          onClick={handleDownload}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gray-800 text-white rounded-xl hover:bg-gray-700 transition-all font-medium text-sm"
                        >
                          <ArrowDownTrayIcon className="h-4 w-4" />
                          Download Enhanced
                        </button>
                        <button
                          onClick={handleSaveEnhanced}
                          disabled={isSaving || saved}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                        >
                          {saved ? (
                            <>
                              <CheckCircleIcon className="h-4 w-4" />
                              Saved Enhanced
                            </>
                          ) : (
                            <>
                              <BookmarkIcon className="h-4 w-4" />
                              {isSaving ? 'Saving...' : 'Save Enhanced'}
                            </>
                          )}
                        </button>
                      </div>

                      {/* Original Image Actions */}
                      <div className="flex gap-3">
                        <button
                          onClick={handleDownloadOriginal}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-800/50 text-gray-300 rounded-lg hover:bg-gray-800 hover:text-white transition-all text-xs"
                        >
                          <ArrowDownTrayIcon className="h-3.5 w-3.5" />
                          Download Original
                        </button>
                        <button
                          onClick={handleSaveOriginal}
                          disabled={isSavingOriginal || savedOriginal}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-800/50 text-gray-300 rounded-lg hover:bg-gray-800 hover:text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed text-xs"
                        >
                          {savedOriginal ? (
                            <>
                              <CheckCircleIcon className="h-3.5 w-3.5" />
                              Saved Original
                            </>
                          ) : (
                            <>
                              <BookmarkIcon className="h-3.5 w-3.5" />
                              {isSavingOriginal ? 'Saving...' : 'Save Original'}
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    {/* AI Insights & Camera Settings */}
                    {(cameraSettings || postProcessing) && (
                      <div className="mt-6">
                        <button
                          onClick={() => setShowCameraSettings(!showCameraSettings)}
                          className="w-full flex items-center justify-between px-4 py-3 bg-blue-900/20 border border-blue-700/30 rounded-xl text-blue-300 hover:bg-blue-900/30 transition-all"
                        >
                          <span className="flex items-center gap-2 text-sm font-medium">
                            <SparklesIcon className="h-4 w-4" />
                            AI Insights & Camera Settings
                          </span>
                          <svg
                            className={`h-4 w-4 transition-transform ${showCameraSettings ? 'rotate-180' : ''}`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>

                        <AnimatePresence>
                          {showCameraSettings && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="mt-3 p-4 bg-blue-900/10 border border-blue-700/20 rounded-xl space-y-4">
                                {/* AI Adjustments Applied */}
                                {postProcessing && (
                                  <div>
                                    <h4 className="text-xs font-semibold text-blue-300 mb-2">AI Adjustments Applied:</h4>
                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                      {getAdjustmentLabel(postProcessing.exposure_adjustment, ' EV') && (
                                        <div className="text-gray-300">
                                          <span className="text-gray-400">Exposure:</span>{' '}
                                          <span className="text-white font-medium">
                                            {getAdjustmentLabel(postProcessing.exposure_adjustment, ' EV')}
                                          </span>
                                        </div>
                                      )}
                                      {getAdjustmentLabel(postProcessing.contrast_adjustment) && (
                                        <div className="text-gray-300">
                                          <span className="text-gray-400">Contrast:</span>{' '}
                                          <span className="text-white font-medium">
                                            {getAdjustmentLabel(postProcessing.contrast_adjustment)}
                                          </span>
                                        </div>
                                      )}
                                      {getAdjustmentLabel(postProcessing.saturation_adjustment) && (
                                        <div className="text-gray-300">
                                          <span className="text-gray-400">Saturation:</span>{' '}
                                          <span className="text-white font-medium">
                                            {getAdjustmentLabel(postProcessing.saturation_adjustment)}
                                          </span>
                                        </div>
                                      )}
                                      {getAdjustmentLabel(postProcessing.vibrance_adjustment) && (
                                        <div className="text-gray-300">
                                          <span className="text-gray-400">Vibrance:</span>{' '}
                                          <span className="text-white font-medium">
                                            {getAdjustmentLabel(postProcessing.vibrance_adjustment)}
                                          </span>
                                        </div>
                                      )}
                                      {getAdjustmentLabel(postProcessing.sharpness_adjustment) && (
                                        <div className="text-gray-300">
                                          <span className="text-gray-400">Sharpness:</span>{' '}
                                          <span className="text-white font-medium">
                                            {getAdjustmentLabel(postProcessing.sharpness_adjustment)}
                                          </span>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {/* Camera Settings Recommendations */}
                                {cameraSettings && (
                                  <div>
                                    <h4 className="text-xs font-semibold text-blue-300 mb-2">Camera Settings Recommendations:</h4>
                                    <div className="space-y-1.5 text-xs">
                                      {cameraSettings.iso_recommendation && (
                                        <div className="text-gray-300">
                                          <span className="text-gray-400">ISO:</span>{' '}
                                          <span className="text-white">{cameraSettings.iso_recommendation}</span>
                                        </div>
                                      )}
                                      {cameraSettings.aperture_recommendation && (
                                        <div className="text-gray-300">
                                          <span className="text-gray-400">Aperture:</span>{' '}
                                          <span className="text-white">{cameraSettings.aperture_recommendation}</span>
                                        </div>
                                      )}
                                      {cameraSettings.shutter_speed_recommendation && (
                                        <div className="text-gray-300">
                                          <span className="text-gray-400">Shutter Speed:</span>{' '}
                                          <span className="text-white">{cameraSettings.shutter_speed_recommendation}</span>
                                        </div>
                                      )}
                                      {cameraSettings.general_tips && cameraSettings.general_tips.length > 0 && (
                                        <div className="mt-2 pt-2 border-t border-blue-700/20">
                                          <p className="text-blue-300 font-semibold mb-1">Tips:</p>
                                          <ul className="space-y-0.5 text-gray-300">
                                            {cameraSettings.general_tips.map((tip: string, idx: number) => (
                                              <li key={idx}>• {tip}</li>
                                            ))}
                                          </ul>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )}
                  </div>

                  {/* Controls Area */}
                  <div className="w-full lg:w-96 bg-gray-900/50 p-6 border-l border-gray-800 overflow-y-auto max-h-[80vh]">
                    {/* Tabs */}
                    <div className="flex gap-2 mb-6">
                      <button
                        onClick={() => setActiveTab('filters')}
                        className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          activeTab === 'filters'
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                      >
                        Quick Filters
                      </button>
                      <button
                        onClick={() => setActiveTab('adjust')}
                        className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          activeTab === 'adjust'
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-800 text-gray-400 hover:text-white'
                        }`}
                      >
                        Adjust
                      </button>
                    </div>

                    <AnimatePresence mode="wait">
                      {activeTab === 'filters' && (
                        <motion.div
                          key="filters"
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 20 }}
                          className="space-y-3"
                        >
                          {(Object.keys(PRESETS) as Array<keyof typeof PRESETS>).map((preset) => (
                            <button
                              key={preset}
                              onClick={() => applyPreset(preset)}
                              className={`w-full flex items-center gap-3 p-4 rounded-xl transition-all ${
                                selectedPreset === preset
                                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/50'
                                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                              }`}
                            >
                              <div className="w-16 h-16 rounded-lg overflow-hidden bg-gray-900">
                                <img
                                  src={image.file_path}
                                  alt={preset}
                                  className="w-full h-full object-cover"
                                  style={{
                                    filter: `brightness(${PRESETS[preset].brightness}%) contrast(${PRESETS[preset].contrast}%) saturate(${PRESETS[preset].saturation}%)`,
                                  }}
                                />
                              </div>
                              <div className="flex-1 text-left">
                                <div className="font-semibold flex items-center gap-2">
                                  {preset === 'ai' && (
                                    <>
                                      <SparklesIcon className="h-4 w-4" />
                                      AI Recommended
                                    </>
                                  )}
                                  {preset !== 'ai' && <span className="capitalize">{preset}</span>}
                                </div>
                                <div className="text-xs opacity-75">
                                  {preset === 'ai' && 'AI-powered enhancements'}
                                  {preset === 'none' && 'No adjustments'}
                                  {preset === 'vivid' && 'Vibrant & punchy'}
                                  {preset === 'natural' && 'Subtle enhancement'}
                                  {preset === 'dramatic' && 'High contrast'}
                                  {preset === 'soft' && 'Light & airy'}
                                </div>
                              </div>
                            </button>
                          ))}
                        </motion.div>
                      )}

                      {activeTab === 'adjust' && (
                        <motion.div
                          key="adjust"
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 20 }}
                          className="space-y-6"
                        >
                          {/* Brightness */}
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <label className="text-sm font-medium text-white">Brightness</label>
                              <span className="text-xs font-mono text-purple-400">{adjustments.brightness}%</span>
                            </div>
                            <Slider
                              min={50}
                              max={150}
                              value={adjustments.brightness}
                              onChange={(value) => handleAdjustmentChange('brightness', value as number)}
                              trackStyle={{ backgroundColor: '#9333ea', height: 6 }}
                              railStyle={{ backgroundColor: '#374151', height: 6 }}
                              handleStyle={{
                                borderColor: '#9333ea',
                                backgroundColor: '#fff',
                                width: 20,
                                height: 20,
                                marginTop: -7,
                                boxShadow: '0 0 0 4px rgba(147, 51, 234, 0.2)',
                              }}
                            />
                          </div>

                          {/* Contrast */}
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <label className="text-sm font-medium text-white">Contrast</label>
                              <span className="text-xs font-mono text-purple-400">{adjustments.contrast}%</span>
                            </div>
                            <Slider
                              min={50}
                              max={150}
                              value={adjustments.contrast}
                              onChange={(value) => handleAdjustmentChange('contrast', value as number)}
                              trackStyle={{ backgroundColor: '#9333ea', height: 6 }}
                              railStyle={{ backgroundColor: '#374151', height: 6 }}
                              handleStyle={{
                                borderColor: '#9333ea',
                                backgroundColor: '#fff',
                                width: 20,
                                height: 20,
                                marginTop: -7,
                                boxShadow: '0 0 0 4px rgba(147, 51, 234, 0.2)',
                              }}
                            />
                          </div>

                          {/* Saturation */}
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <label className="text-sm font-medium text-white">Saturation</label>
                              <span className="text-xs font-mono text-purple-400">{adjustments.saturation}%</span>
                            </div>
                            <Slider
                              min={0}
                              max={200}
                              value={adjustments.saturation}
                              onChange={(value) => handleAdjustmentChange('saturation', value as number)}
                              trackStyle={{ backgroundColor: '#9333ea', height: 6 }}
                              railStyle={{ backgroundColor: '#374151', height: 6 }}
                              handleStyle={{
                                borderColor: '#9333ea',
                                backgroundColor: '#fff',
                                width: 20,
                                height: 20,
                                marginTop: -7,
                                boxShadow: '0 0 0 4px rgba(147, 51, 234, 0.2)',
                              }}
                            />
                          </div>

                          {/* Vibrance */}
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <label className="text-sm font-medium text-white">Vibrance</label>
                              <span className="text-xs font-mono text-purple-400">{adjustments.vibrance}</span>
                            </div>
                            <Slider
                              min={-50}
                              max={50}
                              value={adjustments.vibrance}
                              onChange={(value) => handleAdjustmentChange('vibrance', value as number)}
                              trackStyle={{ backgroundColor: '#9333ea', height: 6 }}
                              railStyle={{ backgroundColor: '#374151', height: 6 }}
                              handleStyle={{
                                borderColor: '#9333ea',
                                backgroundColor: '#fff',
                                width: 20,
                                height: 20,
                                marginTop: -7,
                                boxShadow: '0 0 0 4px rgba(147, 51, 234, 0.2)',
                              }}
                            />
                          </div>

                          {/* Sharpness */}
                          <div>
                            <div className="flex items-center justify-between mb-3">
                              <label className="text-sm font-medium text-white">Sharpness</label>
                              <span className="text-xs font-mono text-purple-400">{adjustments.sharpness}</span>
                            </div>
                            <Slider
                              min={0}
                              max={100}
                              value={adjustments.sharpness}
                              onChange={(value) => handleAdjustmentChange('sharpness', value as number)}
                              trackStyle={{ backgroundColor: '#9333ea', height: 6 }}
                              railStyle={{ backgroundColor: '#374151', height: 6 }}
                              handleStyle={{
                                borderColor: '#9333ea',
                                backgroundColor: '#fff',
                                width: 20,
                                height: 20,
                                marginTop: -7,
                                boxShadow: '0 0 0 4px rgba(147, 51, 234, 0.2)',
                              }}
                            />
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
