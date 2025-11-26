"""
Color extraction service for team logos.
Extracts dominant colors from logo images for jersey detection.
"""

import logging
from typing import List, Tuple
from PIL import Image
import numpy as np
from collections import Counter

logger = logging.getLogger(__name__)


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color code."""
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])


def get_dominant_colors(image_path: str, num_colors: int = 3, resize_width: int = 150) -> List[str]:
    """
    Extract dominant colors from an image.

    Args:
        image_path: Path to the image file
        num_colors: Number of dominant colors to extract (default: 3)
        resize_width: Width to resize image for faster processing

    Returns:
        List of hex color codes for dominant colors
    """
    try:
        # Load and resize image for faster processing
        img = Image.open(image_path)

        # Convert to RGB if necessary (handle RGBA, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize to speed up processing
        aspect_ratio = img.height / img.width
        new_height = int(resize_width * aspect_ratio)
        img = img.resize((resize_width, new_height), Image.Resampling.LANCZOS)

        # Convert to numpy array
        img_array = np.array(img)

        # Reshape to list of pixels
        pixels = img_array.reshape(-1, 3)

        # Remove very dark (near black) and very light (near white) pixels
        # These are often backgrounds or artifacts
        mask = (
            (pixels[:, 0] > 20) & (pixels[:, 0] < 235) &
            (pixels[:, 1] > 20) & (pixels[:, 1] < 235) &
            (pixels[:, 2] > 20) & (pixels[:, 2] < 235)
        )
        filtered_pixels = pixels[mask]

        if len(filtered_pixels) == 0:
            # If all pixels were filtered, use original
            filtered_pixels = pixels

        # Quantize colors to reduce similar shades
        # Round to nearest 15 to group similar colors
        quantized = (filtered_pixels // 15) * 15

        # Convert to tuples for counting
        pixel_tuples = [tuple(pixel) for pixel in quantized]

        # Count occurrences
        color_counts = Counter(pixel_tuples)

        # Get most common colors
        dominant_colors = color_counts.most_common(num_colors)

        # Convert to hex
        hex_colors = [rgb_to_hex(color) for color, count in dominant_colors]

        logger.info(f"Extracted {len(hex_colors)} dominant colors from {image_path}: {hex_colors}")

        return hex_colors

    except Exception as e:
        logger.error(f"Error extracting colors from {image_path}: {e}", exc_info=True)
        return []


def extract_team_colors(logo_path: str) -> dict:
    """
    Extract team colors from a logo image.

    Returns:
        Dictionary with primary_color, secondary_color, tertiary_color
    """
    colors = get_dominant_colors(logo_path, num_colors=3)

    result = {
        "primary_color": colors[0] if len(colors) > 0 else None,
        "secondary_color": colors[1] if len(colors) > 1 else None,
        "tertiary_color": colors[2] if len(colors) > 2 else None,
    }

    logger.info(f"Team colors extracted: {result}")
    return result
