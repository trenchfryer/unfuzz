'use client';

import { useState } from 'react';
import { CheckCircleIcon, XCircleIcon, StarIcon } from '@heroicons/react/24/solid';
import { StarIcon as StarOutlineIcon, SparklesIcon, QueueListIcon, EyeSlashIcon, TrashIcon, CheckIcon, XMarkIcon, PlusCircleIcon } from '@heroicons/react/24/outline';
import type { ImageData } from '@/lib/types';
import ImageDetailModal from './ImageDetailModal';
import EnhancementPreviewModal from './EnhancementPreviewModal';
import BatchEnhancementModal from './BatchEnhancementModal';
import BatchProgressModal from './BatchProgressModal';
import DuplicateStack, { DuplicateGroup } from './DuplicateStack';
import { updateImagePlayerOverride, updateGroupPhotoData, deleteImage } from '@/lib/api';

interface ImageGalleryProps {
  images: ImageData[];
  onImagesChange: (images: ImageData[]) => void;
}

export default function ImageGallery({ images, onImagesChange }: ImageGalleryProps) {
  const [filter, setFilter] = useState<'all' | 'excellent' | 'good' | 'acceptable' | 'poor' | 'reject'>('all');
  const [selectedImage, setSelectedImage] = useState<ImageData | null>(null);
  const [enhancementImage, setEnhancementImage] = useState<ImageData | null>(null);
  const [sortBy, setSortBy] = useState<'score' | 'time' | 'name'>('score');

  // Inline editing state
  const [editingField, setEditingField] = useState<{
    imageId: string;
    field: 'jersey' | 'name' | 'group' | 'group_jersey' | 'group_name';
    playerIndex?: number;
  } | null>(null);
  const [editValue, setEditValue] = useState('');

  // Batch enhancement state
  const [batchMode, setBatchMode] = useState(false);
  const [batchSelectedIds, setBatchSelectedIds] = useState<Set<string>>(new Set());
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  // Batch delete state
  const [deleteMode, setDeleteMode] = useState(false);
  const [deleteSelectedIds, setDeleteSelectedIds] = useState<Set<string>>(new Set());
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteAction, setDeleteAction] = useState<'selected' | 'duplicates' | 'all' | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Duplicate detection state
  const [hideDuplicates, setHideDuplicates] = useState(false);

  // Filter by quality tier
  const filteredImages = images.filter((img) => {
    if (filter === 'all') return true;
    return img.analysis?.quality_tier === filter;
  });

  // Filter out duplicates if hide duplicates is enabled
  const duplicateFilteredImages = hideDuplicates
    ? filteredImages.filter((img) => !img.is_duplicate)
    : filteredImages;

  // Sort images
  const sortedImages = [...duplicateFilteredImages].sort((a, b) => {
    if (sortBy === 'score') {
      return (b.analysis?.overall_score || 0) - (a.analysis?.overall_score || 0);
    } else if (sortBy === 'time') {
      return new Date(b.metadata?.capture_time || '').getTime() - new Date(a.metadata?.capture_time || '').getTime();
    } else {
      return a.filename.localeCompare(b.filename);
    }
  });

  // Group images by duplicate_group_id
  const groupedImages: Array<{ type: 'single' | 'group'; image: ImageData; group?: DuplicateGroup }> = [];
  const processedGroups = new Set<string>();

  for (const img of sortedImages) {
    if (img.duplicate_group_id && !processedGroups.has(img.duplicate_group_id)) {
      // This image is part of a duplicate group
      processedGroups.add(img.duplicate_group_id);

      // Find all images in this group (from the full filtered list, not just sorted)
      const groupImages = duplicateFilteredImages.filter(
        (i) => i.duplicate_group_id === img.duplicate_group_id
      ).sort((a, b) => (b.analysis?.overall_score || 0) - (a.analysis?.overall_score || 0));

      if (groupImages.length > 1) {
        // Find the best image (the one marked as not duplicate)
        const bestImage = groupImages.find((i) => !i.is_duplicate) || groupImages[0];

        groupedImages.push({
          type: 'group',
          image: bestImage,
          group: {
            id: img.duplicate_group_id,
            count: groupImages.length,
            images: groupImages,
            best_image_id: bestImage.id,
          },
        });
      } else {
        // Only one image in group (shouldn't happen, but handle gracefully)
        groupedImages.push({ type: 'single', image: img });
      }
    } else if (!img.duplicate_group_id) {
      // Standalone image, not part of any duplicate group
      groupedImages.push({ type: 'single', image: img });
    }
    // Skip if already processed as part of a group
  };

  const toggleSelection = (imageId: string) => {
    onImagesChange(
      images.map((img) =>
        img.id === imageId ? { ...img, user_selected: !img.user_selected } : img
      )
    );
  };

  const handleSavePlayerOverride = async (image: ImageData, jerseyNumber: string, playerName: string) => {
    try {
      // Get all images in the same duplicate group (if any)
      const imagesToUpdate = image.duplicate_group_id
        ? images.filter(img => img.duplicate_group_id === image.duplicate_group_id)
        : [image];

      // Update backend for all images in the group
      await Promise.all(
        imagesToUpdate.map(img => updateImagePlayerOverride(img.id, playerName, jerseyNumber))
      );

      // Update local state for all images in the group
      onImagesChange(
        images.map((img) => {
          const shouldUpdate = imagesToUpdate.some(updateImg => updateImg.id === img.id);
          return shouldUpdate
            ? {
                ...img,
                player_name_override: playerName || undefined,
                jersey_number_override: jerseyNumber || undefined,
              }
            : img;
        })
      );
    } catch (error) {
      console.error('Failed to save player override:', error);
      throw error;
    }
  };

  // Inline editing handlers
  const startInlineEdit = (imageId: string, field: 'jersey' | 'name' | 'group', currentValue: string, playerIndex?: number) => {
    setEditingField({ imageId, field, playerIndex });
    setEditValue(currentValue);
  };

  const cancelInlineEdit = () => {
    setEditingField(null);
    setEditValue('');
  };

  const saveInlineEdit = async (image: ImageData) => {
    if (!editingField) return;

    try {
      if (editingField.field === 'jersey') {
        // Save jersey number
        await handleSavePlayerOverride(image, editValue, image.player_name_override || image.player_name || '');
      } else if (editingField.field === 'name') {
        // Save player name
        await handleSavePlayerOverride(
          image,
          image.jersey_number_override || image.detected_jersey_number || '',
          editValue
        );
      }
      cancelInlineEdit();
    } catch (error) {
      console.error('Failed to save inline edit:', error);
    }
  };

  const removeGroupPlayer = (image: ImageData, playerIndex: number) => {
    if (!image.detected_jersey_numbers || !image.player_names) return;

    const updatedJerseyNumbers = image.detected_jersey_numbers.filter((_, i) => i !== playerIndex);
    const updatedPlayerNames = image.player_names.filter((_, i) => i !== playerIndex);

    onImagesChange(
      images.map((img) =>
        img.id === image.id
          ? {
              ...img,
              detected_jersey_numbers: updatedJerseyNumbers,
              player_names: updatedPlayerNames,
            }
          : img
      )
    );
  };

  const updateGroupPlayerName = async (image: ImageData, playerIndex: number, newName: string) => {
    if (!image.detected_jersey_numbers || !image.player_names) return;

    try {
      const updatedJerseyNumbers = [...image.detected_jersey_numbers];
      updatedJerseyNumbers[playerIndex] = {
        ...updatedJerseyNumbers[playerIndex],
        player_name: newName
      };

      const updatedPlayerNames = [...image.player_names];
      updatedPlayerNames[playerIndex] = newName;

      // Save to backend
      await updateGroupPhotoData(
        image.id,
        updatedJerseyNumbers,
        updatedPlayerNames
      );

      // Update local state
      onImagesChange(
        images.map((img) =>
          img.id === image.id
            ? {
                ...img,
                detected_jersey_numbers: updatedJerseyNumbers,
                player_names: updatedPlayerNames,
              }
            : img
        )
      );

      cancelInlineEdit();
    } catch (error) {
      console.error('Failed to update group player name:', error);
    }
  };

  const updateGroupPlayerJersey = async (image: ImageData, playerIndex: number, newJersey: string) => {
    if (!image.detected_jersey_numbers) return;

    try {
      console.log('🔍 Original detected_jersey_numbers:', image.detected_jersey_numbers);
      console.log('🔍 Type of each element:', image.detected_jersey_numbers.map((item, i) => `[${i}]: ${typeof item}`));

      const updatedJerseyNumbers = [...image.detected_jersey_numbers];
      updatedJerseyNumbers[playerIndex] = {
        ...updatedJerseyNumbers[playerIndex],
        number: newJersey
      };

      console.log('🔍 Updated jersey numbers to send:', updatedJerseyNumbers);
      console.log('🔍 Type of each updated element:', updatedJerseyNumbers.map((item, i) => `[${i}]: ${typeof item}`));

      // Save to backend
      await updateGroupPhotoData(
        image.id,
        updatedJerseyNumbers,
        image.player_names
      );

      // Update local state
      onImagesChange(
        images.map((img) =>
          img.id === image.id
            ? {
                ...img,
                detected_jersey_numbers: updatedJerseyNumbers,
              }
            : img
        )
      );

      cancelInlineEdit();
    } catch (error) {
      console.error('Failed to update group player jersey:', error);
    }
  };

  const addGroupPlayer = (image: ImageData) => {
    const updatedJerseyNumbers = [
      ...(image.detected_jersey_numbers || []),
      { number: '', confidence: 1.0, player_name: '' }
    ];
    const updatedPlayerNames = [...(image.player_names || []), ''];

    onImagesChange(
      images.map((img) =>
        img.id === image.id
          ? {
              ...img,
              detected_jersey_numbers: updatedJerseyNumbers,
              player_names: updatedPlayerNames,
              is_group_photo: true,
            }
          : img
      )
    );

    // Start editing the newly added player's name
    startInlineEdit(image.id, 'group_name', '', updatedPlayerNames.length - 1);
  };

  // Batch mode handlers
  const toggleBatchMode = () => {
    setBatchMode(!batchMode);
    setBatchSelectedIds(new Set()); // Clear selection when toggling
  };

  const toggleBatchSelection = (imageId: string) => {
    const newSet = new Set(batchSelectedIds);
    if (newSet.has(imageId)) {
      newSet.delete(imageId);
    } else {
      newSet.add(imageId);
    }
    setBatchSelectedIds(newSet);
  };

  const selectAllFiltered = () => {
    const allIds = new Set(sortedImages.map(img => img.id));
    setBatchSelectedIds(allIds);
  };

  const clearBatchSelection = () => {
    setBatchSelectedIds(new Set());
  };

  const handleStartBatchEnhancement = async () => {
    if (batchSelectedIds.size === 0) return;

    try {
      setShowBatchModal(false);

      // Call backend API to start batch enhancement with auto preset (AI recommendations only)
      const response = await fetch('http://localhost:8015/api/v1/batch/enhancement', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_ids: Array.from(batchSelectedIds),
          preset: 'auto', // Auto preset - uses AI recommendations without preset modifiers
          user_id: 'test_user', // TODO: Replace with actual user ID from auth
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start batch enhancement');
      }

      const data = await response.json();
      setCurrentJobId(data.job_id);
      setShowProgressModal(true);

      console.log('Batch enhancement started:', data);
    } catch (error) {
      console.error('Failed to start batch enhancement:', error);
      alert('Failed to start batch enhancement. Please try again.');
    }
  };

  const handleProgressModalClose = () => {
    setShowProgressModal(false);
    setCurrentJobId(null);
    // Optionally clear selection after completion
    setBatchSelectedIds(new Set());
  };

  // Delete mode handlers
  const toggleDeleteMode = () => {
    setDeleteMode(!deleteMode);
    setDeleteSelectedIds(new Set()); // Clear selection when toggling
  };

  const toggleDeleteSelection = (imageId: string) => {
    const newSet = new Set(deleteSelectedIds);
    if (newSet.has(imageId)) {
      newSet.delete(imageId);
    } else {
      newSet.add(imageId);
    }
    setDeleteSelectedIds(newSet);
  };

  const selectAllForDelete = () => {
    const allIds = new Set(sortedImages.map(img => img.id));
    setDeleteSelectedIds(allIds);
  };

  const clearDeleteSelection = () => {
    setDeleteSelectedIds(new Set());
  };

  const handleDeleteSingle = async (imageId: string) => {
    if (!confirm('Delete this image? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteImage(imageId);
      // Remove from local state
      onImagesChange(images.filter(img => img.id !== imageId));
    } catch (error) {
      console.error('Failed to delete image:', error);
      alert('Failed to delete image. Please try again.');
    }
  };

  const handleDeleteConfirm = async () => {
    setShowDeleteConfirm(false);
    setIsDeleting(true);

    try {
      let idsToDelete: string[] = [];

      if (deleteAction === 'selected') {
        idsToDelete = Array.from(deleteSelectedIds);
      } else if (deleteAction === 'duplicates') {
        // Only delete orphaned duplicates (not part of any group)
        idsToDelete = images.filter(img => img.is_duplicate && !img.duplicate_group_id).map(img => img.id);
      } else if (deleteAction === 'all') {
        idsToDelete = images.map(img => img.id);
      }

      // Delete all selected images
      await Promise.all(idsToDelete.map(id => deleteImage(id)));

      // Update local state
      onImagesChange(images.filter(img => !idsToDelete.includes(img.id)));

      // Reset state
      setDeleteSelectedIds(new Set());
      setDeleteMode(false);
      setDeleteAction(null);

      alert(`Successfully deleted ${idsToDelete.length} image(s)`);
    } catch (error) {
      console.error('Failed to delete images:', error);
      alert('Failed to delete some images. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const initiateDelete = (action: 'selected' | 'duplicates' | 'all') => {
    setDeleteAction(action);
    setShowDeleteConfirm(true);
  };

  const getQualityColor = (tier?: string) => {
    switch (tier) {
      case 'excellent':
        return 'border-green-500 bg-green-50';
      case 'good':
        return 'border-blue-500 bg-blue-50';
      case 'acceptable':
        return 'border-yellow-500 bg-yellow-50';
      case 'poor':
        return 'border-orange-500 bg-orange-50';
      case 'reject':
        return 'border-red-500 bg-red-50';
      default:
        return 'border-gray-300';
    }
  };

  const getQualityBadge = (tier?: string) => {
    const colors = {
      excellent: 'bg-green-500 text-white',
      good: 'bg-blue-500 text-white',
      acceptable: 'bg-yellow-500 text-white',
      poor: 'bg-orange-500 text-white',
      reject: 'bg-red-500 text-white',
    };

    return colors[tier as keyof typeof colors] || 'bg-gray-500 text-white';
  };

  const stats = {
    total: images.length,
    excellent: images.filter((img) => img.analysis?.quality_tier === 'excellent').length,
    good: images.filter((img) => img.analysis?.quality_tier === 'good').length,
    acceptable: images.filter((img) => img.analysis?.quality_tier === 'acceptable').length,
    poor: images.filter((img) => img.analysis?.quality_tier === 'poor').length,
    reject: images.filter((img) => img.analysis?.quality_tier === 'reject').length,
    selected: images.filter((img) => img.user_selected).length,
  };

  return (
    <div>
      {/* Stats Bar */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-7 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-600">Total</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{stats.excellent}</div>
            <div className="text-sm text-gray-600">Excellent</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{stats.good}</div>
            <div className="text-sm text-gray-600">Good</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">{stats.acceptable}</div>
            <div className="text-sm text-gray-600">Acceptable</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{stats.poor}</div>
            <div className="text-sm text-gray-600">Poor</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{stats.reject}</div>
            <div className="text-sm text-gray-600">Reject</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{stats.selected}</div>
            <div className="text-sm text-gray-600">Selected</div>
          </div>
        </div>
      </div>

      {/* Filters and Sort */}
      <div className="flex flex-col gap-4 mb-6">
        {/* Top Row: Quality Filters */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === 'all' ? 'bg-gray-900 text-white' : 'bg-white text-gray-700 border'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('excellent')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === 'excellent' ? 'bg-green-600 text-white' : 'bg-white text-gray-700 border'
            }`}
          >
            Excellent
          </button>
          <button
            onClick={() => setFilter('good')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === 'good' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border'
            }`}
          >
            Good
          </button>
          <button
            onClick={() => setFilter('acceptable')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              filter === 'acceptable' ? 'bg-yellow-600 text-white' : 'bg-white text-gray-700 border'
            }`}
          >
            Acceptable
          </button>

          {/* Duplicate Toggle */}
          <button
            onClick={() => setHideDuplicates(!hideDuplicates)}
            className={`px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 ${
              hideDuplicates ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border'
            }`}
            title={hideDuplicates ? 'Show all images including duplicates' : 'Hide duplicate images, show only best from each group'}
          >
            <EyeSlashIcon className="h-4 w-4" />
            <span className="hidden sm:inline">Hide Duplicates</span>
          </button>

          {/* Sort Dropdown */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-4 py-2 border rounded-lg text-sm ml-auto"
          >
            <option value="score">Sort by Score</option>
            <option value="time">Sort by Time</option>
            <option value="name">Sort by Name</option>
          </select>
        </div>

        {/* Batch Enhancement Bar - Prominent and Sticky-Ready */}
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-200 rounded-xl p-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center">
                <SparklesIcon className="h-5 w-5 text-white" />
              </div>
              <div>
                <h3 className="font-bold text-gray-900">Batch Enhancement</h3>
                <p className="text-sm text-gray-600">
                  {batchMode
                    ? `${batchSelectedIds.size} image${batchSelectedIds.size !== 1 ? 's' : ''} selected`
                    : 'Select multiple images to enhance and save to library'
                  }
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              {!batchMode ? (
                <button
                  onClick={toggleBatchMode}
                  className="w-full sm:w-auto px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold flex items-center justify-center gap-2 shadow-lg"
                >
                  <QueueListIcon className="h-5 w-5" />
                  Start Batch Mode
                </button>
              ) : (
                <>
                  {batchSelectedIds.size === 0 ? (
                    <>
                      <button
                        onClick={selectAllFiltered}
                        className="flex-1 sm:flex-none px-4 py-2 bg-white text-purple-600 border-2 border-purple-600 rounded-lg hover:bg-purple-50 transition-colors font-medium"
                      >
                        Select All ({sortedImages.length})
                      </button>
                      <button
                        onClick={toggleBatchMode}
                        className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => setShowBatchModal(true)}
                        className="flex-1 sm:flex-none px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold flex items-center justify-center gap-2 shadow-lg"
                      >
                        <SparklesIcon className="h-5 w-5" />
                        Enhance {batchSelectedIds.size} Image{batchSelectedIds.size !== 1 ? 's' : ''}
                      </button>
                      <button
                        onClick={clearBatchSelection}
                        className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Clear
                      </button>
                      <button
                        onClick={toggleBatchMode}
                        className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Exit
                      </button>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Workspace Cleanup - Compact Design */}
        <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <TrashIcon className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">
                {deleteMode
                  ? `${deleteSelectedIds.size} selected`
                  : 'Cleanup Workspace'
                }
              </span>
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap">
              {!deleteMode ? (
                <>
                  <button
                    onClick={toggleDeleteMode}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                  >
                    <TrashIcon className="h-3.5 w-3.5" />
                    Select to Delete
                  </button>
                  {!hideDuplicates && images.filter(img => img.is_duplicate && !img.duplicate_group_id).length > 0 && (
                    <button
                      onClick={() => initiateDelete('duplicates')}
                      className="px-3 py-1.5 text-xs font-medium bg-orange-600 text-white rounded hover:bg-orange-700 transition-colors"
                      title={`Delete ${images.filter(img => img.is_duplicate && !img.duplicate_group_id).length} orphaned duplicate images`}
                    >
                      Delete Orphaned Duplicates ({images.filter(img => img.is_duplicate && !img.duplicate_group_id).length})
                    </button>
                  )}
                  <button
                    onClick={() => initiateDelete('all')}
                    className="px-3 py-1.5 text-xs font-medium text-red-600 bg-white border border-red-300 rounded hover:bg-red-50 transition-colors"
                  >
                    Clear All
                  </button>
                </>
              ) : (
                <>
                  {deleteSelectedIds.size === 0 ? (
                    <>
                      <button
                        onClick={selectAllForDelete}
                        className="px-3 py-1.5 text-xs font-medium text-red-600 bg-white border border-red-300 rounded hover:bg-red-50 transition-colors"
                      >
                        Select All ({sortedImages.length})
                      </button>
                      <button
                        onClick={toggleDeleteMode}
                        className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => initiateDelete('selected')}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                      >
                        <TrashIcon className="h-3.5 w-3.5" />
                        Delete ({deleteSelectedIds.size})
                      </button>
                      <button
                        onClick={clearDeleteSelection}
                        className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                      >
                        Clear
                      </button>
                      <button
                        onClick={toggleDeleteMode}
                        className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                <TrashIcon className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-gray-900">Confirm Deletion</h3>
                <p className="text-sm text-gray-600">This action cannot be undone</p>
              </div>
            </div>

            <div className="mb-6">
              {deleteAction === 'selected' && (
                <p className="text-gray-700">
                  Are you sure you want to delete <strong>{deleteSelectedIds.size}</strong> selected image{deleteSelectedIds.size !== 1 ? 's' : ''}?
                </p>
              )}
              {deleteAction === 'duplicates' && (
                <p className="text-gray-700">
                  Are you sure you want to delete <strong>{images.filter(img => img.is_duplicate && !img.duplicate_group_id).length}</strong> orphaned duplicate image{images.filter(img => img.is_duplicate && !img.duplicate_group_id).length !== 1 ? 's' : ''}? These are duplicates that are not part of any group.
                </p>
              )}
              {deleteAction === 'all' && (
                <p className="text-gray-700">
                  Are you sure you want to <strong>clear your entire workspace</strong> ({images.length} images)? All unanalyzed images and unsaved work will be lost.
                </p>
              )}
            </div>

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteAction(null);
                }}
                disabled={isDeleting}
                className="px-5 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="px-5 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium flex items-center gap-2 disabled:opacity-50"
              >
                {isDeleting ? (
                  <>Deleting...</>
                ) : (
                  <>
                    <TrashIcon className="h-5 w-5" />
                    Delete
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Image Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {groupedImages.map((item, index) =>
          item.type === 'group' && item.group ? (
            // Render duplicate stack
            <DuplicateStack
              key={item.group.id}
              group={item.group}
              onImageClick={(image) => setSelectedImage(image)}
              onSelectBest={(imageId) => {
                // Update the is_duplicate flags when a new best image is selected
                onImagesChange(
                  images.map((img) => {
                    if (img.duplicate_group_id === item.group!.id) {
                      return { ...img, is_duplicate: img.id !== imageId };
                    }
                    return img;
                  })
                );
              }}
              getQualityColor={getQualityColor}
              getQualityBadge={getQualityBadge}
            />
          ) : (
            // Render single image
            <div
              key={item.image.id}
              className={`relative group rounded-lg border-2 overflow-hidden cursor-pointer transition-all hover:shadow-lg ${getQualityColor(
                item.image.analysis?.quality_tier
              )} ${item.image.user_selected ? 'ring-4 ring-purple-500' : ''} ${
                batchMode && batchSelectedIds.has(item.image.id) ? 'ring-4 ring-purple-600' : ''
              } ${deleteMode && deleteSelectedIds.has(item.image.id) ? 'ring-4 ring-red-600' : ''}`}
              onClick={() => {
                if (batchMode) {
                  toggleBatchSelection(item.image.id);
                } else if (deleteMode) {
                  toggleDeleteSelection(item.image.id);
                } else {
                  setSelectedImage(item.image);
                }
              }}
            >
              {/* Original single image rendering - keep existing code */}
              {/* Thumbnail */}
              <div className="aspect-square bg-gray-200 relative overflow-hidden">
                <img
                  src={item.image.thumbnail_path || item.image.file_path}
                  alt={item.image.filename}
                  className="w-full h-full object-cover absolute inset-0"
                  style={{
                    zIndex: 1
                  }}
                />

                {/* Quality Badge */}
                {item.image.analysis && !batchMode && !deleteMode && (
                  <div className="absolute top-2 left-2" style={{ zIndex: 10 }}>
                    <span
                      className={`px-2 py-1 rounded text-xs font-bold ${getQualityBadge(
                        item.image.analysis.quality_tier
                      )}`}
                    >
                      {item.image.analysis.overall_score.toFixed(0)}
                    </span>
                  </div>
                )}

                {/* Batch Mode Checkbox */}
                {batchMode && (
                  <div className="absolute top-2 left-2" style={{ zIndex: 10 }}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                      batchSelectedIds.has(item.image.id) ? 'bg-purple-600' : 'bg-white border-2 border-gray-300'
                    }`}>
                      {batchSelectedIds.has(item.image.id) && (
                        <CheckCircleIcon className="h-5 w-5 text-white" />
                      )}
                    </div>
                  </div>
                )}

                {/* Delete Mode Checkbox */}
                {deleteMode && (
                  <div className="absolute top-2 left-2" style={{ zIndex: 10 }}>
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                      deleteSelectedIds.has(item.image.id) ? 'bg-red-600' : 'bg-white border-2 border-gray-300'
                    }`}>
                      {deleteSelectedIds.has(item.image.id) && (
                        <CheckCircleIcon className="h-5 w-5 text-white" />
                      )}
                    </div>
                  </div>
                )}

                {/* Quick Delete Button - Shows on hover when not in any mode */}
                {!batchMode && !deleteMode && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSingle(item.image.id);
                    }}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-red-600 hover:bg-red-700 text-white p-2 rounded-full shadow-lg"
                    style={{ zIndex: 10 }}
                    title="Delete this image"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                )}

                {/* Selected Badge */}
                {item.image.user_selected && !batchMode && (
                  <div className="absolute top-2 right-2" style={{ zIndex: 10 }}>
                    <CheckCircleIcon className="h-6 w-6 text-purple-600 bg-white rounded-full" />
                  </div>
                )}

                {/* Enhance Button - Shows on hover if post-processing available (not in delete mode) */}
                {!deleteMode && item.image.analysis?.post_processing?.can_auto_fix && (
                  <div
                    className="absolute inset-0 bg-black/0 group-hover:bg-black/60 transition-all flex items-center justify-center"
                    style={{ zIndex: 5 }}
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEnhancementImage(item.image);
                      }}
                      className="opacity-0 group-hover:opacity-100 transition-opacity px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium flex items-center gap-2 shadow-lg"
                    >
                      <SparklesIcon className="h-5 w-5" />
                      Enhance
                    </button>
                  </div>
                )}
              </div>

              {/* Image Info */}
              <div className="p-2 bg-white">
                <p className="text-xs font-medium truncate">{item.image.filename}</p>
                {item.image.analysis && (
                  <>
                    <p className="text-xs text-gray-500 mt-1">
                      {item.image.analysis.quality_tier.charAt(0).toUpperCase() +
                        item.image.analysis.quality_tier.slice(1)}
                    </p>
                    {/* Player Identification - Inline Editing */}
                    {(item.image.detected_jersey_number || item.image.jersey_number_override || item.image.player_name_override || item.image.player_names?.length) && (
                      <div className="mt-1">
                        {item.image.is_group_photo && item.image.player_names && item.image.player_names.length > 0 ? (
                          <div className="space-y-1">
                            <div className="flex items-center justify-between">
                              <div className="text-xs font-bold text-green-600">GROUP ({item.image.player_names.length}):</div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  addGroupPlayer(item.image);
                                }}
                                className="text-xs text-green-600 hover:text-green-800 flex items-center gap-0.5"
                                title="Add player"
                              >
                                <PlusCircleIcon className="h-3 w-3" />
                                Add
                              </button>
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {item.image.detected_jersey_numbers && item.image.detected_jersey_numbers.map((jerseyData, idx) => {
                                const playerName = item.image.player_names?.[idx] || '';
                                const jerseyNumber = jerseyData.number || '';

                                return (
                                  <div
                                    key={idx}
                                    className="inline-flex items-center gap-1 bg-blue-100 rounded px-1.5 py-0.5 group/chip"
                                  >
                                    {/* Jersey Number */}
                                    {editingField?.imageId === item.image.id && editingField?.field === 'group_jersey' && editingField?.playerIndex === idx ? (
                                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                        <input
                                          autoFocus
                                          type="text"
                                          value={editValue}
                                          onChange={(e) => setEditValue(e.target.value)}
                                          onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                              updateGroupPlayerJersey(item.image, idx, editValue);
                                            } else if (e.key === 'Escape') {
                                              cancelInlineEdit();
                                            }
                                          }}
                                          className="text-xs font-bold bg-white border border-blue-300 rounded px-1 py-0 w-10 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                          placeholder="#"
                                        />
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            updateGroupPlayerJersey(item.image, idx, editValue);
                                          }}
                                          className="text-green-600 hover:text-green-800"
                                          title="Save"
                                        >
                                          <CheckIcon className="h-3 w-3" />
                                        </button>
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            cancelInlineEdit();
                                          }}
                                          className="text-red-600 hover:text-red-800"
                                          title="Cancel"
                                        >
                                          <XMarkIcon className="h-3 w-3" />
                                        </button>
                                      </div>
                                    ) : (
                                      <span
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          startInlineEdit(item.image.id, 'group_jersey', jerseyNumber, idx);
                                        }}
                                        className="text-xs font-bold text-blue-700 cursor-pointer hover:underline"
                                        title="Click to edit jersey"
                                      >
                                        #{jerseyNumber || '?'}
                                      </span>
                                    )}

                                    {/* Player Name */}
                                    {editingField?.imageId === item.image.id && editingField?.field === 'group_name' && editingField?.playerIndex === idx ? (
                                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                        <input
                                          autoFocus
                                          type="text"
                                          value={editValue}
                                          onChange={(e) => setEditValue(e.target.value)}
                                          onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                              updateGroupPlayerName(item.image, idx, editValue);
                                            } else if (e.key === 'Escape') {
                                              cancelInlineEdit();
                                            }
                                          }}
                                          className="text-xs bg-white border border-blue-300 rounded px-1 py-0 w-24 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                          placeholder="Name"
                                        />
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            updateGroupPlayerName(item.image, idx, editValue);
                                          }}
                                          className="text-green-600 hover:text-green-800"
                                          title="Save"
                                        >
                                          <CheckIcon className="h-3 w-3" />
                                        </button>
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            cancelInlineEdit();
                                          }}
                                          className="text-red-600 hover:text-red-800"
                                          title="Cancel"
                                        >
                                          <XMarkIcon className="h-3 w-3" />
                                        </button>
                                      </div>
                                    ) : (
                                      <span
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          startInlineEdit(item.image.id, 'group_name', playerName, idx);
                                        }}
                                        className="text-xs text-blue-800 cursor-pointer hover:underline"
                                        title="Click to edit name"
                                      >
                                        {playerName || 'Unnamed'}
                                      </span>
                                    )}

                                    {/* Remove Button */}
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        removeGroupPlayer(item.image, idx);
                                      }}
                                      className="opacity-0 group-hover/chip:opacity-100 text-red-600 hover:text-red-800"
                                      title="Remove player"
                                    >
                                      <XCircleIcon className="h-3 w-3" />
                                    </button>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 flex-wrap">
                            {/* Jersey Number - Inline Editable */}
                            {editingField?.imageId === item.image.id && editingField?.field === 'jersey' ? (
                              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                <input
                                  autoFocus
                                  type="text"
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      saveInlineEdit(item.image);
                                    } else if (e.key === 'Escape') {
                                      cancelInlineEdit();
                                    }
                                  }}
                                  className="text-xs font-bold bg-white border border-blue-300 rounded px-1 py-0.5 w-12 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                  placeholder="#"
                                />
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    saveInlineEdit(item.image);
                                  }}
                                  className="text-green-600 hover:text-green-800"
                                  title="Save"
                                >
                                  <CheckIcon className="h-3 w-3" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    cancelInlineEdit();
                                  }}
                                  className="text-red-600 hover:text-red-800"
                                  title="Cancel"
                                >
                                  <XMarkIcon className="h-3 w-3" />
                                </button>
                              </div>
                            ) : (
                              <span
                                onClick={(e) => {
                                  e.stopPropagation();
                                  startInlineEdit(
                                    item.image.id,
                                    'jersey',
                                    item.image.jersey_number_override || item.image.detected_jersey_number || ''
                                  );
                                }}
                                className="text-xs font-bold text-blue-600 cursor-pointer hover:underline px-1 py-0.5 rounded hover:bg-blue-50"
                                title="Click to edit jersey number"
                              >
                                #{item.image.jersey_number_override || item.image.detected_jersey_number}
                              </span>
                            )}

                            {/* Player Name - Inline Editable */}
                            {editingField?.imageId === item.image.id && editingField?.field === 'name' ? (
                              <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                                <input
                                  autoFocus
                                  type="text"
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      saveInlineEdit(item.image);
                                    } else if (e.key === 'Escape') {
                                      cancelInlineEdit();
                                    }
                                  }}
                                  className="text-xs bg-white border border-blue-300 rounded px-2 py-0.5 w-28 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                  placeholder="Player name"
                                />
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    saveInlineEdit(item.image);
                                  }}
                                  className="text-green-600 hover:text-green-800"
                                  title="Save"
                                >
                                  <CheckIcon className="h-3 w-3" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    cancelInlineEdit();
                                  }}
                                  className="text-red-600 hover:text-red-800"
                                  title="Cancel"
                                >
                                  <XMarkIcon className="h-3 w-3" />
                                </button>
                              </div>
                            ) : (
                              (item.image.player_name_override || item.image.player_name) ? (
                                <span
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    startInlineEdit(
                                      item.image.id,
                                      'name',
                                      item.image.player_name_override || item.image.player_name || ''
                                    );
                                  }}
                                  className={`text-xs break-words cursor-pointer hover:underline px-1 py-0.5 rounded hover:bg-blue-50 ${item.image.player_name_override ? 'text-purple-800 font-semibold' : 'text-blue-800'}`}
                                  title="Click to edit player name"
                                >
                                  {item.image.player_name_override || item.image.player_name}
                                </span>
                              ) : (
                                <span
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    startInlineEdit(item.image.id, 'name', '');
                                  }}
                                  className="text-xs text-gray-400 cursor-pointer hover:text-blue-600 hover:underline italic"
                                  title="Click to add player name"
                                >
                                  + Add name
                                </span>
                              )
                            )}

                            {item.image.player_confidence && !item.image.player_name_override && !editingField && (
                              <span className="text-xs text-gray-400">
                                ({Math.round(item.image.player_confidence * 100)}%)
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )
        )}
      </div>


      {/* Detail Modal */}
      {selectedImage && (
        <ImageDetailModal
          image={selectedImage}
          onClose={() => setSelectedImage(null)}
          onToggleSelection={() => toggleSelection(selectedImage.id)}
        />
      )}

      {/* Enhancement Preview Modal */}
      {enhancementImage && (
        <EnhancementPreviewModal
          isOpen={true}
          image={enhancementImage}
          onClose={() => setEnhancementImage(null)}
        />
      )}

      {/* Batch Enhancement Modal */}
      <BatchEnhancementModal
        isOpen={showBatchModal}
        onClose={() => setShowBatchModal(false)}
        selectedImageCount={batchSelectedIds.size}
        onStartEnhancement={handleStartBatchEnhancement}
      />

      {/* Batch Progress Modal */}
      <BatchProgressModal
        isOpen={showProgressModal}
        onClose={handleProgressModalClose}
        jobId={currentJobId}
      />
    </div>
  );
}
