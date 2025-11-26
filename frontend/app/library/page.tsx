'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
// Using regular img tags for user-uploaded images from local backend
import {
  PhotoIcon,
  ArrowDownTrayIcon,
  ShareIcon,
  TrashIcon,
  FunnelIcon,
  Squares2X2Icon,
  ListBulletIcon,
  MagnifyingGlassIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { getLibraryImages, incrementDownloadCount, getTeams } from '@/lib/api';
import UserMenu from '@/components/UserMenu';

interface EnhancedImage {
  id: string;
  original_image_id: string;
  team_id?: string;
  player_id?: string;
  enhanced_url: string;
  thumbnail_url?: string;
  player_name_override?: string;
  jersey_number_override?: string;
  title?: string;
  description?: string;
  tags?: string[];
  download_count: number;
  created_at: string;
}

interface Team {
  id: string;
  name: string;
  sport: string;
}

export default function LibraryPage() {
  const router = useRouter();
  const [images, setImages] = useState<EnhancedImage[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [shareImageId, setShareImageId] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<EnhancedImage | null>(null);

  // Helper function to get full image URL (handles both local and Supabase URLs)
  const getImageUrl = (url: string): string => {
    if (!url) return '';
    // If URL is already absolute (starts with http/https), return as-is
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    // Otherwise, prepend the API URL for local files
    return `${process.env.NEXT_PUBLIC_API_URL}${url}`;
  };

  useEffect(() => {
    loadLibrary();
    loadTeams();
  }, [selectedTeam]);

  const loadLibrary = async () => {
    try {
      setLoading(true);
      const filters: any = {};
      if (selectedTeam) {
        filters.team_id = selectedTeam;
      }
      const data = await getLibraryImages(filters);
      setImages(data);
    } catch (error) {
      console.error('Error loading library:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTeams = async () => {
    try {
      const data = await getTeams();
      setTeams(data.teams || []);
    } catch (error) {
      console.error('Error loading teams:', error);
      setTeams([]);
    }
  };

  const handleDownload = async (image: EnhancedImage) => {
    try {
      // Increment download count
      await incrementDownloadCount(image.id);

      // Fetch the image as a blob
      const response = await fetch(getImageUrl(image.enhanced_url));
      const blob = await response.blob();

      // Create object URL from blob
      const url = window.URL.createObjectURL(blob);

      // Create download link
      const link = document.createElement('a');
      link.href = url;
      link.download = `enhanced_${image.player_name_override || 'photo'}_${new Date(image.created_at).toLocaleDateString().replace(/\//g, '-')}.jpg`;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      // Refresh to show updated download count
      loadLibrary();
    } catch (error) {
      console.error('Error downloading image:', error);
      alert('Failed to download image. Please try again.');
    }
  };

  const handleShare = (image: EnhancedImage, platform: string) => {
    const imageUrl = `${window.location.origin}${image.enhanced_url}`;
    const text = `Check out this photo ${image.player_name_override ? `of ${image.player_name_override}` : ''}`;

    let shareUrl = '';
    switch (platform) {
      case 'twitter':
        shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(imageUrl)}`;
        break;
      case 'facebook':
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(imageUrl)}`;
        break;
      case 'copy':
        navigator.clipboard.writeText(imageUrl);
        setShareImageId(null);
        alert('Link copied to clipboard!');
        return;
    }

    if (shareUrl) {
      window.open(shareUrl, '_blank', 'width=600,height=400');
      setShareImageId(null);
    }
  };

  const filteredImages = images.filter(image => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      image.player_name_override?.toLowerCase().includes(query) ||
      image.title?.toLowerCase().includes(query) ||
      image.description?.toLowerCase().includes(query) ||
      image.tags?.some(tag => tag.toLowerCase().includes(query))
    );
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/app')}
                className="text-sm text-gray-600 hover:text-gray-900"
              >
                ← Back to Upload
              </button>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <PhotoIcon className="h-7 w-7 text-blue-600" />
                My Library
              </h1>
            </div>
            <UserMenu />
          </div>

          {/* Toolbar */}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="flex-1 min-w-[200px] relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by player, title, tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Filters Button */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-colors ${
                showFilters || selectedTeam
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <FunnelIcon className="h-5 w-5" />
              Filters
              {selectedTeam && (
                <span className="bg-blue-600 text-white text-xs px-2 py-0.5 rounded-full">1</span>
              )}
            </button>

            {/* View Mode */}
            <div className="flex gap-1 border border-gray-300 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded ${
                  viewMode === 'grid' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Squares2X2Icon className="h-5 w-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded ${
                  viewMode === 'list' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <ListBulletIcon className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Filters Panel */}
          {showFilters && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-gray-900">Filter by Team</h3>
                {selectedTeam && (
                  <button
                    onClick={() => setSelectedTeam('')}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear filters
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <button
                  onClick={() => setSelectedTeam('')}
                  className={`px-4 py-2 rounded-lg border transition-colors ${
                    !selectedTeam
                      ? 'bg-blue-100 border-blue-300 text-blue-700'
                      : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  All Teams
                </button>
                {teams.map(team => (
                  <button
                    key={team.id}
                    onClick={() => setSelectedTeam(team.id)}
                    className={`px-4 py-2 rounded-lg border transition-colors ${
                      selectedTeam === team.id
                        ? 'bg-blue-100 border-blue-300 text-blue-700'
                        : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {team.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : filteredImages.length === 0 ? (
          <div className="text-center py-12">
            <PhotoIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No enhanced images</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchQuery
                ? 'No images match your search'
                : 'Save enhanced images from the upload page to see them here'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => router.push('/app')}
                className="mt-4 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
              >
                Upload & Enhance Photos
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="mb-4 text-sm text-gray-600">
              {filteredImages.length} {filteredImages.length === 1 ? 'image' : 'images'}
            </div>

            {viewMode === 'grid' ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredImages.map(image => (
                  <div key={image.id} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
                    <div
                      className="relative aspect-[3/2] bg-gray-100 cursor-pointer hover:opacity-95 transition-opacity"
                      onClick={() => setPreviewImage(image)}
                    >
                      <img
                        src={getImageUrl(image.enhanced_url)}
                        alt={image.title || 'Enhanced photo'}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="p-4">
                      {image.player_name_override && (
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-semibold text-gray-900">{image.player_name_override}</span>
                          {image.jersey_number_override && (
                            <span className="text-sm text-gray-600">#{image.jersey_number_override}</span>
                          )}
                        </div>
                      )}
                      {image.title && (
                        <p className="text-sm text-gray-700 mb-2">{image.title}</p>
                      )}
                      {image.tags && image.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-3">
                          {image.tags.map((tag, idx) => (
                            <span key={idx} className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
                        <span>{new Date(image.created_at).toLocaleDateString()}</span>
                        <span>{image.download_count} downloads</span>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleDownload(image)}
                          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                        >
                          <ArrowDownTrayIcon className="h-4 w-4" />
                          Download
                        </button>
                        <div className="relative">
                          <button
                            onClick={() => setShareImageId(shareImageId === image.id ? null : image.id)}
                            className="px-3 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            <ShareIcon className="h-4 w-4" />
                          </button>
                          {shareImageId === image.id && (
                            <div className="absolute bottom-full right-0 mb-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
                              <div
                                onClick={() => handleShare(image, 'twitter')}
                                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 cursor-pointer"
                              >
                                Share on Twitter
                              </div>
                              <div
                                onClick={() => handleShare(image, 'facebook')}
                                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 cursor-pointer"
                              >
                                Share on Facebook
                              </div>
                              <div
                                onClick={() => handleShare(image, 'copy')}
                                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 cursor-pointer"
                              >
                                Copy Link
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {filteredImages.map(image => (
                  <div key={image.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 flex gap-4 hover:shadow-md transition-shadow">
                    <div
                      className="w-32 h-32 flex-shrink-0 bg-gray-100 rounded overflow-hidden cursor-pointer hover:opacity-95 transition-opacity"
                      onClick={() => setPreviewImage(image)}
                    >
                      <img
                        src={getImageUrl(image.enhanced_url)}
                        alt={image.title || 'Enhanced photo'}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          {image.player_name_override && (
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-gray-900">{image.player_name_override}</span>
                              {image.jersey_number_override && (
                                <span className="text-sm text-gray-600">#{image.jersey_number_override}</span>
                              )}
                            </div>
                          )}
                          {image.title && (
                            <p className="text-sm text-gray-700 mb-2">{image.title}</p>
                          )}
                          {image.description && (
                            <p className="text-sm text-gray-600 mb-2">{image.description}</p>
                          )}
                          {image.tags && image.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mb-2">
                              {image.tags.map((tag, idx) => (
                                <span key={idx} className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                          <div className="flex items-center gap-4 text-xs text-gray-500">
                            <span>{new Date(image.created_at).toLocaleDateString()}</span>
                            <span>{image.download_count} downloads</span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleDownload(image)}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                          >
                            <ArrowDownTrayIcon className="h-4 w-4" />
                            Download
                          </button>
                          <div className="relative">
                            <button
                              onClick={() => setShareImageId(shareImageId === image.id ? null : image.id)}
                              className="px-3 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                              <ShareIcon className="h-4 w-4" />
                            </button>
                            {shareImageId === image.id && (
                              <div className="absolute top-full right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10">
                                <div
                                  onClick={() => handleShare(image, 'twitter')}
                                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 cursor-pointer"
                                >
                                  Share on Twitter
                                </div>
                                <div
                                  onClick={() => handleShare(image, 'facebook')}
                                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 cursor-pointer"
                                >
                                  Share on Facebook
                                </div>
                                <div
                                  onClick={() => handleShare(image, 'copy')}
                                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 cursor-pointer"
                                >
                                  Copy Link
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </main>

      {/* Image Preview Modal */}
      {previewImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
          onClick={() => setPreviewImage(null)}
        >
          <div className="relative max-w-7xl max-h-full">
            {/* Close button */}
            <button
              onClick={() => setPreviewImage(null)}
              className="absolute top-4 right-4 bg-white text-gray-800 rounded-full p-2 hover:bg-gray-100 transition-colors z-10"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>

            {/* Image */}
            <img
              src={getImageUrl(previewImage.enhanced_url)}
              alt={previewImage.title || 'Enhanced photo'}
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />

            {/* Image info overlay */}
            <div
              className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-6 rounded-b-lg"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-white">
                {previewImage.player_name_override && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xl font-semibold">{previewImage.player_name_override}</span>
                    {previewImage.jersey_number_override && (
                      <span className="text-lg opacity-90">#{previewImage.jersey_number_override}</span>
                    )}
                  </div>
                )}
                {previewImage.title && (
                  <p className="text-sm opacity-90 mb-2">{previewImage.title}</p>
                )}
                <div className="flex items-center gap-4 text-xs opacity-75">
                  <span>{new Date(previewImage.created_at).toLocaleDateString()}</span>
                  <span>•</span>
                  <span>{previewImage.download_count} downloads</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
