'use client';

import { XMarkIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import type { ImageData } from '@/lib/types';

interface ImageDetailModalProps {
  image: ImageData;
  onClose: () => void;
  onToggleSelection: () => void;
}

export default function ImageDetailModal({ image, onClose, onToggleSelection }: ImageDetailModalProps) {
  const { analysis, metadata } = image;

  if (!analysis) {
    return null;
  }

  const factorCategories = [
    {
      name: 'Technical Quality',
      factors: [
        { name: 'Sharpness', score: analysis.factor_scores.sharpness },
        { name: 'Exposure', score: analysis.factor_scores.exposure },
        { name: 'Color Accuracy', score: analysis.factor_scores.color_accuracy },
        { name: 'Noise/Grain', score: analysis.factor_scores.noise_grain },
        { name: 'Dynamic Range', score: analysis.factor_scores.dynamic_range },
      ],
    },
    {
      name: 'Composition',
      factors: [
        { name: 'Rule of Thirds', score: analysis.factor_scores.rule_of_thirds },
        { name: 'Subject Placement', score: analysis.factor_scores.subject_placement },
        { name: 'Framing', score: analysis.factor_scores.framing },
        { name: 'Leading Lines', score: analysis.factor_scores.leading_lines },
        { name: 'Balance', score: analysis.factor_scores.balance },
        { name: 'Depth', score: analysis.factor_scores.depth },
        { name: 'Negative Space', score: analysis.factor_scores.negative_space },
        { name: 'Perspective', score: analysis.factor_scores.perspective },
      ],
    },
    {
      name: 'Subject Quality',
      factors: [
        { name: 'Facial Detection', score: analysis.factor_scores.facial_detection },
        { name: 'Eye Status', score: analysis.factor_scores.eye_status },
        { name: 'Facial Expression', score: analysis.factor_scores.facial_expression },
        { name: 'Body Language', score: analysis.factor_scores.body_language },
        { name: 'Subject Attention', score: analysis.factor_scores.subject_attention },
        { name: 'Group Dynamics', score: analysis.factor_scores.group_dynamics },
        { name: 'Motion Blur', score: analysis.factor_scores.motion_blur },
        { name: 'Subject Lighting', score: analysis.factor_scores.subject_lighting },
        { name: 'Skin Tones', score: analysis.factor_scores.skin_tones },
        { name: 'Subject Framing', score: analysis.factor_scores.subject_framing },
      ],
    },
    {
      name: 'Artistic Quality',
      factors: [
        { name: 'Lighting Quality', score: analysis.factor_scores.lighting_quality },
        { name: 'Color Harmony', score: analysis.factor_scores.color_harmony },
        { name: 'Emotional Impact', score: analysis.factor_scores.emotional_impact },
        { name: 'Uniqueness', score: analysis.factor_scores.uniqueness },
        { name: 'Professional Polish', score: analysis.factor_scores.professional_polish },
      ],
    },
  ];

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-blue-600 bg-blue-100';
    if (score >= 40) return 'text-yellow-600 bg-yellow-100';
    if (score >= 20) return 'text-orange-600 bg-orange-100';
    return 'text-red-600 bg-red-100';
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-blue-500';
    if (score >= 40) return 'bg-yellow-500';
    if (score >= 20) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between z-10">
          <div className="flex-1">
            <h2 className="text-xl font-bold truncate">{image.filename}</h2>
            <div className="flex items-center gap-4 mt-2">
              <span
                className={`px-3 py-1 rounded-full text-sm font-bold ${
                  analysis.quality_tier === 'excellent'
                    ? 'bg-green-500 text-white'
                    : analysis.quality_tier === 'good'
                    ? 'bg-blue-500 text-white'
                    : analysis.quality_tier === 'acceptable'
                    ? 'bg-yellow-500 text-white'
                    : analysis.quality_tier === 'poor'
                    ? 'bg-orange-500 text-white'
                    : 'bg-red-500 text-white'
                }`}
              >
                {analysis.quality_tier.toUpperCase()} - {analysis.overall_score.toFixed(0)}/100
              </span>

              {analysis.subject_analysis.has_people && (
                <span className="text-sm text-gray-600">
                  {analysis.subject_analysis.faces_detected} face(s) •{' '}
                  {analysis.subject_analysis.eyes_status}
                </span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-6 p-6">
          {/* Image Preview */}
          <div>
            <img
              src={image.file_path}
              alt={image.filename}
              className="w-full rounded-lg shadow-lg"
            />

            {/* AI Summary */}
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-semibold mb-2">AI Summary</h3>
              <p className="text-sm text-gray-700">{analysis.ai_summary}</p>
            </div>

            {/* Issues & Recommendations */}
            {analysis.detected_issues.length > 0 && (
              <div className="mt-4 p-4 bg-yellow-50 rounded-lg">
                <h3 className="font-semibold mb-2 text-yellow-900">Detected Issues</h3>
                <ul className="text-sm text-yellow-800 space-y-1">
                  {analysis.detected_issues.map((issue, idx) => (
                    <li key={idx}>• {issue}</li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.recommendations.length > 0 && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg">
                <h3 className="font-semibold mb-2 text-green-900">Recommendations</h3>
                <ul className="text-sm text-green-800 space-y-1">
                  {analysis.recommendations.map((rec, idx) => (
                    <li key={idx}>• {rec}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* EXIF Data */}
            {metadata && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold mb-2">Camera Settings</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {metadata.camera_make && (
                  <div>
                    <span className="text-gray-600">Camera:</span>{' '}
                    <span className="font-medium">
                      {metadata.camera_make} {metadata.camera_model}
                    </span>
                  </div>
                )}
                {metadata.lens_model && (
                  <div>
                    <span className="text-gray-600">Lens:</span>{' '}
                    <span className="font-medium">{metadata.lens_model}</span>
                  </div>
                )}
                {metadata.focal_length && (
                  <div>
                    <span className="text-gray-600">Focal Length:</span>{' '}
                    <span className="font-medium">{metadata.focal_length}mm</span>
                  </div>
                )}
                {metadata.aperture && (
                  <div>
                    <span className="text-gray-600">Aperture:</span>{' '}
                    <span className="font-medium">f/{metadata.aperture}</span>
                  </div>
                )}
                {metadata.shutter_speed && (
                  <div>
                    <span className="text-gray-600">Shutter:</span>{' '}
                    <span className="font-medium">{metadata.shutter_speed}</span>
                  </div>
                )}
                {metadata.iso && (
                  <div>
                    <span className="text-gray-600">ISO:</span>{' '}
                    <span className="font-medium">{metadata.iso}</span>
                  </div>
                )}
              </div>
              </div>
            )}

            {/* Selection Button */}
            <button
              onClick={onToggleSelection}
              className={`w-full mt-4 py-3 rounded-lg font-semibold transition-colors ${
                image.user_selected
                  ? 'bg-purple-600 text-white hover:bg-purple-700'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {image.user_selected ? (
                <>
                  <CheckCircleIcon className="inline h-5 w-5 mr-2" />
                  Selected for Export
                </>
              ) : (
                'Select for Export'
              )}
            </button>
          </div>

          {/* Quality Factors */}
          <div className="space-y-6">
            <h3 className="text-lg font-bold">Quality Analysis Breakdown</h3>

            {factorCategories.map((category, idx) => (
              <div key={idx} className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-semibold mb-3">{category.name}</h4>
                <div className="space-y-2">
                  {category.factors.map((factor, fidx) => (
                    <div key={fidx}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-gray-700">{factor.name}</span>
                        <span className={`text-sm font-bold px-2 py-0.5 rounded ${getScoreColor(factor.score)}`}>
                          {factor.score.toFixed(0)}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${getScoreBarColor(factor.score)}`}
                          style={{ width: `${factor.score}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
