"""
Image Enhancement Service using Pillow for automated post-processing.
Applies adjustments based on PostProcessingRecommendations from Gemini.
"""
import logging
from typing import Optional
from PIL import Image, ImageEnhance, ImageFilter
import io

from app.models.image import PostProcessingRecommendations

logger = logging.getLogger(__name__)


class ImageEnhancementService:
    """Service for applying automated image enhancements."""

    def enhance_image(
        self,
        image_path: str,
        recommendations: PostProcessingRecommendations,
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Apply post-processing enhancements to an image.

        Args:
            image_path: Path to the input image
            recommendations: PostProcessingRecommendations from analysis
            output_path: Optional path to save enhanced image

        Returns:
            Enhanced image as bytes (JPEG format)
        """
        try:
            # Load image
            img = Image.open(image_path)
            logger.info(f"Loaded image: {img.size}, mode: {img.mode}")

            # Convert to RGB if needed (for consistency)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Apply exposure adjustment (brightness)
            if recommendations.exposure_adjustment is not None and recommendations.exposure_adjustment != 0:
                # Exposure: -2.0 to +2.0 EV -> brightness factor: 0.25 to 4.0
                # Formula: factor = 2^exposure
                factor = 2 ** recommendations.exposure_adjustment
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(factor)
                logger.info(f"Applied exposure adjustment: {recommendations.exposure_adjustment:.2f} EV (factor: {factor:.2f})")

            # Apply contrast adjustment
            if recommendations.contrast_adjustment is not None and recommendations.contrast_adjustment != 0:
                # Contrast: -100 to +100 -> factor: 0.0 to 2.0
                factor = 1.0 + (recommendations.contrast_adjustment / 100.0)
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(factor)
                logger.info(f"Applied contrast adjustment: {recommendations.contrast_adjustment} (factor: {factor:.2f})")

            # Apply saturation adjustment
            if recommendations.saturation_adjustment is not None and recommendations.saturation_adjustment != 0:
                # Saturation: -100 to +100 -> factor: 0.0 to 2.0
                factor = 1.0 + (recommendations.saturation_adjustment / 100.0)
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(factor)
                logger.info(f"Applied saturation adjustment: {recommendations.saturation_adjustment} (factor: {factor:.2f})")

            # Apply vibrance adjustment (similar to saturation but more subtle)
            if recommendations.vibrance_adjustment is not None and recommendations.vibrance_adjustment != 0:
                # Vibrance: softer saturation boost
                factor = 1.0 + (recommendations.vibrance_adjustment / 200.0)  # Half the intensity
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(factor)
                logger.info(f"Applied vibrance adjustment: {recommendations.vibrance_adjustment} (factor: {factor:.2f})")

            # Apply sharpness adjustment
            if recommendations.sharpness_adjustment is not None and recommendations.sharpness_adjustment > 0:
                # Sharpness: 0 to +100 -> factor: 1.0 to 3.0
                factor = 1.0 + (recommendations.sharpness_adjustment / 50.0)
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(factor)
                logger.info(f"Applied sharpness adjustment: {recommendations.sharpness_adjustment} (factor: {factor:.2f})")

            # Apply noise reduction (blur filter)
            if recommendations.noise_reduction is not None and recommendations.noise_reduction > 0:
                # Noise reduction: 0 to 100 -> radius: 0 to 2
                # Only apply if significant noise reduction is needed
                if recommendations.noise_reduction > 30:
                    radius = (recommendations.noise_reduction / 100.0) * 2.0
                    img = img.filter(ImageFilter.GaussianBlur(radius=radius))
                    logger.info(f"Applied noise reduction: {recommendations.noise_reduction} (radius: {radius:.2f})")

            # Note: Highlights, shadows, whites, blacks, temperature, and tint adjustments
            # require more advanced processing (curves, channel manipulation) that would
            # be better handled by a library like OpenCV or rawpy. For now, we handle
            # the basic adjustments that Pillow can do well.

            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95, optimize=True)
            output.seek(0)
            enhanced_bytes = output.read()

            # Optionally save to file
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(enhanced_bytes)
                logger.info(f"Saved enhanced image to: {output_path}")

            logger.info(f"Enhancement completed. Output size: {len(enhanced_bytes)} bytes")
            return enhanced_bytes

        except Exception as e:
            logger.error(f"Error enhancing image: {e}", exc_info=True)
            raise

    def create_preview(
        self,
        image_path: str,
        recommendations: PostProcessingRecommendations,
        max_size: int = 1200
    ) -> bytes:
        """
        Create a preview of the enhanced image with reduced resolution for faster loading.

        Args:
            image_path: Path to the input image
            recommendations: PostProcessingRecommendations from analysis
            max_size: Maximum dimension for preview (default 1200px)

        Returns:
            Enhanced preview image as bytes (JPEG format)
        """
        try:
            # Load and resize for preview
            img = Image.open(image_path)

            # Resize for preview
            if img.width > max_size or img.height > max_size:
                if img.width > img.height:
                    new_width = max_size
                    new_height = int((max_size / img.width) * img.height)
                else:
                    new_height = max_size
                    new_width = int((max_size / img.height) * img.width)

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized preview to {new_width}x{new_height}")

            # Save to temporary path for enhancement
            temp_path = image_path + '.preview.tmp'
            img.save(temp_path, format='JPEG', quality=85)

            # Apply enhancements to preview
            preview_bytes = self.enhance_image(temp_path, recommendations)

            # Clean up temp file
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)

            return preview_bytes

        except Exception as e:
            logger.error(f"Error creating preview: {e}", exc_info=True)
            raise
