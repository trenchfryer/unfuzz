'use client';

import { useState } from 'react';
import { CheckCircleIcon, XCircleIcon, StarIcon } from '@heroicons/react/24/solid';
import { StarIcon as StarOutlineIcon, SparklesIcon, PencilIcon } from '@heroicons/react/24/outline';
import type { ImageData } from '@/lib/types';
import ImageDetailModal from './ImageDetailModal';
import EnhancementPreviewModal from './EnhancementPreviewModal';
import EditPlayerModal from './EditPlayerModal';
import { updateImagePlayerOverride } from '@/lib/api';

interface ImageGalleryProps {
  images: ImageData[];
  onImagesChange: (images: ImageData[]) => void;
}

export default function ImageGallery({ images, onImagesChange }: ImageGalleryProps) {
  const [filter, setFilter] = useState<'all' | 'excellent' | 'good' | 'acceptable' | 'poor' | 'reject'>('all');
  const [selectedImage, setSelectedImage] = useState<ImageData | null>(null);
  const [enhancementImage, setEnhancementImage] = useState<ImageData | null>(null);
  const [editPlayerImage, setEditPlayerImage] = useState<ImageData | null>(null);
  const [sortBy, setSortBy] = useState<'score' | 'time' | 'name'>('score');

  const filteredImages = images.filter((img) => {
    if (filter === 'all') return true;
    return img.analysis?.quality_tier === filter;
  });

  const sortedImages = [...filteredImages].sort((a, b) => {
    if (sortBy === 'score') {
      return (b.analysis?.overall_score || 0) - (a.analysis?.overall_score || 0);
    } else if (sortBy === 'time') {
      return new Date(b.metadata.capture_time || '').getTime() - new Date(a.metadata.capture_time || '').getTime();
    } else {
      return a.filename.localeCompare(b.filename);
    }
  });

  const toggleSelection = (imageId: string) => {
    onImagesChange(
      images.map((img) =>
        img.id === imageId ? { ...img, user_selected: !img.user_selected } : img
      )
    );
  };

  const handleSavePlayerOverride = async (jerseyNumber: string, playerName: string) => {
    if (!editPlayerImage) return;

    try {
      // Update backend
      await updateImagePlayerOverride(editPlayerImage.id, playerName, jerseyNumber);

      // Update local state
      onImagesChange(
        images.map((img) =>
          img.id === editPlayerImage.id
            ? {
                ...img,
                player_name_override: playerName || undefined,
                jersey_number_override: jerseyNumber || undefined,
              }
            : img
        )
      );

      setEditPlayerImage(null);
    } catch (error) {
      console.error('Failed to save player override:', error);
      throw error;
    }
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
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex gap-2">
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
        </div>

        <div className="flex gap-2 ml-auto">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-4 py-2 border rounded-lg text-sm"
          >
            <option value="score">Sort by Score</option>
            <option value="time">Sort by Time</option>
            <option value="name">Sort by Name</option>
          </select>
        </div>
      </div>

      {/* Image Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {sortedImages.map((image) => (
          <div
            key={image.id}
            className={`relative group rounded-lg border-2 overflow-hidden cursor-pointer transition-all hover:shadow-lg ${getQualityColor(
              image.analysis?.quality_tier
            )} ${image.user_selected ? 'ring-4 ring-purple-500' : ''}`}
            onClick={() => setSelectedImage(image)}
          >
            {/* Thumbnail */}
            <div className="aspect-square bg-gray-200 relative overflow-hidden">
              <img
                src={image.thumbnail_path || image.file_path}
                alt={image.filename}
                className="w-full h-full object-cover absolute inset-0"
                style={{
                  zIndex: 1
                }}
              />

              {/* Quality Badge */}
              {image.analysis && (
                <div className="absolute top-2 left-2" style={{ zIndex: 10 }}>
                  <span
                    className={`px-2 py-1 rounded text-xs font-bold ${getQualityBadge(
                      image.analysis.quality_tier
                    )}`}
                  >
                    {image.analysis.overall_score.toFixed(0)}
                  </span>
                </div>
              )}

              {/* Selected Badge */}
              {image.user_selected && (
                <div className="absolute top-2 right-2" style={{ zIndex: 10 }}>
                  <CheckCircleIcon className="h-6 w-6 text-purple-600 bg-white rounded-full" />
                </div>
              )}

              {/* Enhance Button - Shows on hover if post-processing available */}
              {image.analysis?.post_processing?.can_auto_fix && (
                <div
                  className="absolute inset-0 bg-black/0 group-hover:bg-black/60 transition-all flex items-center justify-center"
                  style={{ zIndex: 5 }}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setEnhancementImage(image);
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
              <p className="text-xs font-medium truncate">{image.filename}</p>
              {image.analysis && (
                <>
                  <p className="text-xs text-gray-500 mt-1">
                    {image.analysis.quality_tier.charAt(0).toUpperCase() +
                      image.analysis.quality_tier.slice(1)}
                  </p>
                  {/* Player Identification */}
                  {(image.detected_jersey_number || image.jersey_number_override || image.player_name_override || image.player_names?.length) && (
                    <div className="mt-1 flex items-center gap-1">
                      {image.is_group_photo && image.player_names && image.player_names.length > 0 ? (
                        <>
                          <span className="text-xs font-bold text-green-600">GROUP:</span>
                          <span className="text-xs text-blue-800 truncate">
                            {image.player_names.join(', ')}
                          </span>
                        </>
                      ) : (
                        <>
                          <span className="text-xs font-bold text-blue-600">
                            #{image.jersey_number_override || image.detected_jersey_number}
                          </span>
                          {(image.player_name_override || image.player_name) && (
                            <span className={`text-xs truncate ${image.player_name_override ? 'text-purple-800 font-semibold' : 'text-blue-800'}`}>
                              {image.player_name_override || image.player_name}
                            </span>
                          )}
                          {image.player_confidence && !image.player_name_override && (
                            <span className="text-xs text-gray-400">
                              ({Math.round(image.player_confidence * 100)}%)
                            </span>
                          )}
                        </>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditPlayerImage(image);
                        }}
                        className="ml-auto p-0.5 hover:bg-blue-100 rounded transition-colors"
                        title="Edit player info"
                      >
                        <PencilIcon className="h-3 w-3 text-blue-600" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Export Button */}
      {stats.selected > 0 && (
        <div className="fixed bottom-8 right-8">
          <button className="px-6 py-4 bg-purple-600 text-white rounded-full shadow-lg hover:bg-purple-700 transition-colors text-lg font-semibold">
            Export {stats.selected} Selected Photos
          </button>
        </div>
      )}

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

      {/* Edit Player Modal */}
      {editPlayerImage && (
        <EditPlayerModal
          isOpen={true}
          onClose={() => setEditPlayerImage(null)}
          currentJerseyNumber={editPlayerImage.jersey_number_override || editPlayerImage.detected_jersey_number}
          currentPlayerName={editPlayerImage.player_name_override || editPlayerImage.player_name}
          onSave={handleSavePlayerOverride}
        />
      )}
    </div>
  );
}
