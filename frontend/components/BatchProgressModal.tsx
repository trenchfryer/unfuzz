'use client';

import { Fragment, useState, useEffect, useRef } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/solid';
import { SparklesIcon, BookmarkIcon } from '@heroicons/react/24/outline';
import { createClient as createSupabaseClient } from '@/lib/supabase/client';

interface BatchProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string | null;
}

interface ProgressData {
  job_id: string;
  status: 'queued' | 'started' | 'processing' | 'finished' | 'failed' | 'error';
  current: number;
  total: number;
  message: string;
  percent: number;
  successful?: number;
  failed?: number;
  duration_seconds?: number;
}

export default function BatchProgressModal({
  isOpen,
  onClose,
  jobId,
}: BatchProgressModalProps) {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!isOpen || !jobId) {
      // Close WebSocket when modal closes
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    // Connect to WebSocket
    const ws = new WebSocket(`ws://localhost:8015/api/v1/batch/ws/enhancement/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected for job:', jobId);
    };

    ws.onmessage = (event) => {
      const data: ProgressData = JSON.parse(event.data);
      console.log('Progress update:', data);
      setProgress(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [isOpen, jobId]);

  const handleSaveToLibrary = async () => {
    if (!jobId) return;

    try {
      setIsSaving(true);

      // Get auth token
      const supabase = createSupabaseClient();
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      if (!token) {
        throw new Error('No authentication token available');
      }

      // Call API to save batch enhanced images to library
      const response = await fetch(
        `http://localhost:8015/api/v1/batch/enhancement/${jobId}/save-to-library`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to save to library');
      }

      const data = await response.json();
      console.log('Saved to library:', data);

      // Show success message and close
      alert(`Successfully saved ${data.saved_count} enhanced images to your library!`);
      onClose();
    } catch (error) {
      console.error('Save to library failed:', error);
      alert('Failed to save to library. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'finished':
        return 'text-green-600';
      case 'failed':
      case 'error':
        return 'text-red-600';
      case 'processing':
      case 'started':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'finished':
        return <CheckCircleIcon className="h-12 w-12 text-green-600" />;
      case 'failed':
      case 'error':
        return <XCircleIcon className="h-12 w-12 text-red-600" />;
      default:
        return (
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent" />
        );
    }
  };

  const isComplete = progress?.status === 'finished' || progress?.status === 'failed';

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={() => {}}>
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
                {/* Icon */}
                <div className="flex justify-center mb-6">
                  {getStatusIcon(progress?.status)}
                </div>

                {/* Title */}
                <Dialog.Title
                  as="h3"
                  className={`text-2xl font-bold text-center mb-2 ${getStatusColor(
                    progress?.status
                  )}`}
                >
                  {progress?.status === 'finished'
                    ? 'Enhancement Complete!'
                    : progress?.status === 'failed'
                    ? 'Enhancement Failed'
                    : 'Enhancing Images...'}
                </Dialog.Title>

                {/* Message */}
                <p className="text-center text-gray-600 mb-6">{progress?.message || 'Connecting...'}</p>

                {/* Progress Bar */}
                {progress && progress.status !== 'finished' && progress.status !== 'failed' && (
                  <div className="mb-6">
                    <div className="flex justify-between text-sm text-gray-600 mb-2">
                      <span>
                        {progress.current} / {progress.total} images
                      </span>
                      <span>{progress.percent.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="h-3 rounded-full bg-gradient-to-r from-blue-600 to-purple-600 transition-all duration-500"
                        style={{ width: `${progress.percent}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Results (shown when complete) */}
                {isComplete && progress && (
                  <div className="space-y-3 mb-6">
                    {progress.status === 'finished' && (
                      <>
                        <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                          <span className="text-sm font-medium text-green-900">Successful</span>
                          <span className="text-lg font-bold text-green-600">
                            {progress.successful || 0}
                          </span>
                        </div>
                        {progress.failed && progress.failed > 0 && (
                          <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                            <span className="text-sm font-medium text-red-900">Failed</span>
                            <span className="text-lg font-bold text-red-600">{progress.failed}</span>
                          </div>
                        )}
                        {progress.duration_seconds && (
                          <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                            <span className="text-sm font-medium text-blue-900">Duration</span>
                            <span className="text-lg font-bold text-blue-600">
                              {progress.duration_seconds.toFixed(1)}s
                            </span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  {isComplete && progress?.status === 'finished' && (
                    <button
                      onClick={handleSaveToLibrary}
                      disabled={isSaving}
                      className="flex-1 px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center justify-center gap-2"
                    >
                      <BookmarkIcon className="h-5 w-5" />
                      {isSaving ? 'Saving...' : 'Save to Library'}
                    </button>
                  )}
                  <button
                    onClick={onClose}
                    disabled={!isComplete}
                    className={`${
                      isComplete ? 'flex-1' : 'w-full'
                    } px-6 py-3 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium`}
                  >
                    {isComplete ? 'Close' : 'Processing...'}
                  </button>
                </div>

                {/* Job ID (for debugging) */}
                {jobId && (
                  <div className="mt-4 text-center">
                    <p className="text-xs text-gray-400">Job ID: {jobId.slice(0, 8)}</p>
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
}
