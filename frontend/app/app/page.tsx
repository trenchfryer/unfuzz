'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { PhotoIcon, CloudArrowUpIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { uploadImagesBatch, analyzeImage } from '@/lib/api';
import type { ImageData, UploadProgress } from '@/lib/types';
import ImageGallery from '@/components/ImageGallery';

export default function AppPage() {
  const [images, setImages] = useState<ImageData[]>([]);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<'upload' | 'analyze' | 'review'>('upload');

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setIsUploading(true);
    setCurrentPhase('upload');

    // Initialize progress tracking
    const progressItems: UploadProgress[] = acceptedFiles.map((file) => ({
      filename: file.name,
      progress: 0,
      status: 'uploading',
    }));
    setUploadProgress(progressItems);

    try {
      // Upload images
      console.log('Uploading', acceptedFiles.length, 'files...');
      const uploadedImages = await uploadImagesBatch(acceptedFiles);

      console.log('✅ Upload completed, received', uploadedImages.length, 'images');

      // Verify we got images back
      if (!uploadedImages || uploadedImages.length === 0) {
        throw new Error('No images returned from upload');
      }

      // Update progress to completed
      setUploadProgress((prev) =>
        prev.map((item) => ({
          ...item,
          progress: 100,
          status: 'completed',
        }))
      );

      console.log('🎯 Setting images in state:', uploadedImages);
      uploadedImages.forEach((img, idx) => {
        console.log(`  Image ${idx + 1}:`, {
          id: img.id,
          filename: img.filename,
          thumbnail_path: img.thumbnail_path,
          file_path: img.file_path
        });
      });

      // Set images and clear upload state
      setImages(uploadedImages);
      setIsUploading(false);

      // Clear upload progress after a short delay
      setTimeout(() => {
        setUploadProgress([]);
      }, 1000);

      // Automatically start analysis
      console.log('🚀 Starting analysis in 500ms...');
      setTimeout(() => {
        startAnalysis(uploadedImages);
      }, 500);
    } catch (error) {
      console.error('❌ Upload failed:', error);
      alert(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);

      setUploadProgress((prev) =>
        prev.map((item) => ({
          ...item,
          status: 'failed',
          error: error instanceof Error ? error.message : 'Upload failed',
        }))
      );
      setIsUploading(false);
    }
  }, []);

  const startAnalysis = async (imagesToAnalyze: ImageData[]) => {
    console.log('📊 Starting analysis for', imagesToAnalyze.length, 'images');
    setIsAnalyzing(true);
    setCurrentPhase('analyze');

    // Mark all images as analyzing
    setImages((prevImages) =>
      prevImages.map((img) => ({
        ...img,
        analysis_status: 'analyzing' as const,
      }))
    );

    // OPTIMIZATION 3: Process images in parallel (3x-5x faster for multiple images)
    const concurrencyLimit = 3; // Process 3 images at a time to avoid overwhelming the API

    for (let i = 0; i < imagesToAnalyze.length; i += concurrencyLimit) {
      const batch = imagesToAnalyze.slice(i, i + concurrencyLimit);

      // Process batch in parallel
      await Promise.all(
        batch.map(async (image, batchIndex) => {
          try {
            const globalIndex = i + batchIndex + 1;
            console.log(`🔍 Analyzing image ${globalIndex}/${imagesToAnalyze.length}: ${image.filename}`);

            const analysisResult = await analyzeImage(image.id);

            console.log(`✅ Analysis complete for ${image.filename}`);

            // Update image with analysis results
            setImages((prevImages) =>
              prevImages.map((img) =>
                img.id === image.id
                  ? {
                      ...img,
                      analysis: analysisResult.analysis,
                      metadata: analysisResult.metadata,
                      analysis_status: 'completed',
                    }
                  : img
              )
            );
          } catch (error) {
            console.error(`❌ Failed to analyze ${image.filename}:`, error);

            setImages((prevImages) =>
              prevImages.map((img) =>
                img.id === image.id
                  ? {
                      ...img,
                      analysis_status: 'failed',
                    }
                  : img
              )
            );
          }
        })
      );
    }

    console.log('🎉 All analyses complete, moving to review phase');
    setIsAnalyzing(false);
    setCurrentPhase('review');
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.heic', '.cr2', '.nef', '.arw', '.dng'],
    },
    multiple: true,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-50 shadow-sm">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PhotoIcon className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              UnFuzz
            </span>
          </div>

          <div className="flex items-center gap-4">
            {images.length > 0 && (
              <div className="text-sm text-gray-600">
                {images.filter((img) => img.analysis_status === 'completed').length} /{' '}
                {images.length} analyzed
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Upload Phase */}
        {currentPhase === 'upload' && images.length === 0 && (
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold mb-4">Start Culling Your Photos</h1>
              <p className="text-xl text-gray-600">
                Upload your images and let AI analyze them in minutes
              </p>
            </div>

            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-xl p-16 text-center cursor-pointer
                transition-all duration-200
                ${
                  isDragActive
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                }
              `}
            >
              <input {...getInputProps()} />

              <div className="flex flex-col items-center gap-4">
                <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center">
                  <CloudArrowUpIcon className="h-10 w-10 text-blue-600" />
                </div>

                {isDragActive ? (
                  <p className="text-xl font-semibold text-blue-600">Drop your photos here</p>
                ) : (
                  <>
                    <p className="text-xl font-semibold">Drag & drop your photos</p>
                    <p className="text-gray-600">or click to browse</p>
                  </>
                )}

                <p className="text-sm text-gray-500 mt-4">
                  Supports JPEG, PNG, HEIC, and RAW formats (CR2, NEF, ARW, DNG)
                </p>
              </div>
            </div>

            {/* Upload Progress */}
            {uploadProgress.length > 0 && (
              <div className="mt-8 space-y-2">
                <h3 className="font-semibold mb-4">Uploading...</h3>
                {uploadProgress.map((item, index) => (
                  <div key={index} className="flex items-center gap-4 p-3 bg-white rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium truncate">{item.filename}</span>
                        <span className="text-sm text-gray-500">{item.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            item.status === 'failed' ? 'bg-red-500' : 'bg-blue-600'
                          }`}
                          style={{ width: `${item.progress}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Analysis Phase */}
        {currentPhase === 'analyze' && (
          <div className="max-w-2xl mx-auto text-center py-16">
            <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-6 animate-pulse">
              <SparklesIcon className="h-10 w-10 text-purple-600" />
            </div>
            <h2 className="text-3xl font-bold mb-4">Analyzing Your Photos</h2>
            <p className="text-xl text-gray-600 mb-8">
              AI is evaluating {images.length} images across 30+ quality factors...
            </p>

            <div className="text-left max-w-md mx-auto">
              {images.map((image, index) => (
                <div
                  key={image.id}
                  className="flex items-center gap-3 p-3 mb-2 bg-white rounded-lg"
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      image.analysis_status === 'completed'
                        ? 'bg-green-500'
                        : image.analysis_status === 'analyzing'
                        ? 'bg-blue-500 animate-pulse'
                        : 'bg-gray-300'
                    }`}
                  />
                  <span className="text-sm truncate flex-1">{image.filename}</span>
                  {image.analysis_status === 'completed' && (
                    <span className="text-xs text-green-600 font-medium">✓</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Review Phase */}
        {currentPhase === 'review' && images.length > 0 && (
          <div>
            <div className="mb-8">
              <h2 className="text-3xl font-bold mb-2">Review Your Photos</h2>
              <p className="text-gray-600">
                AI has analyzed your images. Review the selections and make adjustments.
              </p>
            </div>

            <ImageGallery images={images} onImagesChange={setImages} />

            {/* Add new photos button */}
            <div className="mt-8 text-center">
              <div {...getRootProps()} className="inline-block">
                <input {...getInputProps()} />
                <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                  Add More Photos
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
