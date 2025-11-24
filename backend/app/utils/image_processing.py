from PIL import Image, ExifTags
import piexif
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Utilities for image processing and EXIF extraction."""

    @staticmethod
    def _convert_exif_value_to_string(value: Any) -> Optional[str]:
        """
        Convert EXIF value to string format.

        Args:
            value: EXIF value (can be IFDRational, tuple, int, float, or string)

        Returns:
            String representation or None
        """
        if value is None:
            return None

        # Handle IFDRational objects (fractions like 1/125)
        if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
            # For fractions, calculate decimal value
            if value.denominator == 0:
                return None
            decimal_value = value.numerator / value.denominator
            # Format nicely (e.g., "1/125" for shutter speed)
            if decimal_value == 0:
                return "0"
            elif decimal_value < 1:
                return f"1/{int(1/decimal_value)}"
            else:
                return f"{decimal_value:.2f}".rstrip('0').rstrip('.')

        # Handle tuples (like focal length (24, 1) = 24mm)
        if isinstance(value, tuple):
            if len(value) == 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                if value[1] == 0:
                    return None
                result = value[0] / value[1]
                if result == 0:
                    return "0"
                return f"{result:.2f}".rstrip('0').rstrip('.')
            else:
                return str(value)

        # Handle numbers
        if isinstance(value, (int, float)):
            return str(value)

        # Handle bytes (some EXIF fields are bytes)
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8', errors='ignore').strip()
            except:
                return None

        # Already a string or other type
        return str(value) if value else None

    @staticmethod
    def extract_exif_data(image_path: str) -> Dict[str, Any]:
        """
        Extract EXIF data from an image.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary containing EXIF data
        """
        exif_data = {}

        try:
            img = Image.open(image_path)

            # Get basic image info
            exif_data['width'] = img.width
            exif_data['height'] = img.height
            exif_data['format'] = img.format
            exif_data['mode'] = img.mode

            # Extract EXIF if available
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()

                # Convert all EXIF values to JSON-serializable types
                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    # Convert to string to ensure JSON serializability
                    serializable_value = ImageProcessor._convert_exif_value_to_string(value)
                    if serializable_value is not None:
                        exif_data[tag] = serializable_value

                # Extract commonly used fields and convert to appropriate types
                # Strings
                exif_data['camera_make'] = ImageProcessor._convert_exif_value_to_string(exif_data.get('Make', None))
                exif_data['camera_model'] = ImageProcessor._convert_exif_value_to_string(exif_data.get('Model', None))
                exif_data['lens_model'] = ImageProcessor._convert_exif_value_to_string(exif_data.get('LensModel', None))
                exif_data['shutter_speed'] = ImageProcessor._convert_exif_value_to_string(exif_data.get('ExposureTime', None))

                # Floats - focal_length
                focal_length_raw = exif_data.get('FocalLength', None)
                if focal_length_raw is not None:
                    try:
                        if hasattr(focal_length_raw, 'numerator') and hasattr(focal_length_raw, 'denominator'):
                            exif_data['focal_length'] = float(focal_length_raw.numerator) / float(focal_length_raw.denominator) if focal_length_raw.denominator != 0 else None
                        elif isinstance(focal_length_raw, tuple) and len(focal_length_raw) == 2:
                            exif_data['focal_length'] = float(focal_length_raw[0]) / float(focal_length_raw[1]) if focal_length_raw[1] != 0 else None
                        else:
                            exif_data['focal_length'] = float(focal_length_raw)
                    except (ValueError, TypeError):
                        exif_data['focal_length'] = None
                else:
                    exif_data['focal_length'] = None

                # Floats - aperture
                aperture_raw = exif_data.get('FNumber', None)
                if aperture_raw is not None:
                    try:
                        if hasattr(aperture_raw, 'numerator') and hasattr(aperture_raw, 'denominator'):
                            exif_data['aperture'] = float(aperture_raw.numerator) / float(aperture_raw.denominator) if aperture_raw.denominator != 0 else None
                        elif isinstance(aperture_raw, tuple) and len(aperture_raw) == 2:
                            exif_data['aperture'] = float(aperture_raw[0]) / float(aperture_raw[1]) if aperture_raw[1] != 0 else None
                        else:
                            exif_data['aperture'] = float(aperture_raw)
                    except (ValueError, TypeError):
                        exif_data['aperture'] = None
                else:
                    exif_data['aperture'] = None

                # Integer - ISO
                iso_raw = exif_data.get('ISOSpeedRatings', None)
                if iso_raw is not None:
                    try:
                        exif_data['iso'] = int(iso_raw)
                    except (ValueError, TypeError):
                        exif_data['iso'] = None
                else:
                    exif_data['iso'] = None

                # Parse datetime
                datetime_str = exif_data.get('DateTime', None)
                if datetime_str:
                    try:
                        exif_data['capture_time'] = datetime.strptime(
                            datetime_str,
                            '%Y:%m:%d %H:%M:%S'
                        )
                    except:
                        exif_data['capture_time'] = None

        except Exception as e:
            logger.warning(f"Could not extract EXIF from {image_path}: {e}")

        return exif_data

    @staticmethod
    def create_thumbnail(
        image_path: str,
        output_path: str,
        size: Tuple[int, int] = (400, 400)
    ) -> str:
        """
        Create a thumbnail of an image.

        Args:
            image_path: Path to source image
            output_path: Path for thumbnail output
            size: Tuple of (width, height) for thumbnail

        Returns:
            Path to created thumbnail
        """
        try:
            img = Image.open(image_path)

            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Create thumbnail preserving aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # Save thumbnail
            img.save(output_path, "JPEG", quality=85, optimize=True)

            logger.info(f"Created thumbnail: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error creating thumbnail for {image_path}: {e}")
            raise

    @staticmethod
    def get_image_dimensions(image_path: str) -> Tuple[int, int]:
        """
        Get image dimensions without loading full image.

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (width, height)
        """
        try:
            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            logger.error(f"Error getting dimensions for {image_path}: {e}")
            return (0, 0)

    @staticmethod
    def validate_image(image_path: str) -> bool:
        """
        Validate that a file is a valid image.

        Args:
            image_path: Path to image file

        Returns:
            True if valid image, False otherwise
        """
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception as e:
            logger.error(f"Invalid image {image_path}: {e}")
            return False

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes
        """
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error getting file size for {file_path}: {e}")
            return 0

    @staticmethod
    def is_raw_format(filename: str) -> bool:
        """
        Check if file is a RAW format.

        Args:
            filename: Name of the file

        Returns:
            True if RAW format, False otherwise
        """
        raw_extensions = [
            '.cr2', '.cr3',  # Canon
            '.nef', '.nrw',  # Nikon
            '.arw', '.srf', '.sr2',  # Sony
            '.orf',  # Olympus
            '.rw2',  # Panasonic
            '.dng',  # Adobe
            '.raf',  # Fujifilm
            '.pef',  # Pentax
            '.x3f',  # Sigma
            '.erf',  # Epson
            '.mrw',  # Minolta
        ]

        ext = os.path.splitext(filename.lower())[1]
        return ext in raw_extensions

    @staticmethod
    def convert_raw_to_jpeg(raw_path: str, output_path: str) -> str:
        """
        Convert RAW image to JPEG for processing.
        Note: Requires rawpy library for advanced RAW processing.

        Args:
            raw_path: Path to RAW image
            output_path: Path for JPEG output

        Returns:
            Path to converted JPEG
        """
        try:
            # Try using rawpy if available
            try:
                import rawpy

                with rawpy.imread(raw_path) as raw:
                    rgb = raw.postprocess()
                    img = Image.fromarray(rgb)
                    img.save(output_path, "JPEG", quality=95)

            except ImportError:
                # Fallback to PIL (may not work for all RAW formats)
                logger.warning("rawpy not installed, using PIL for RAW conversion")
                img = Image.open(raw_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(output_path, "JPEG", quality=95)

            logger.info(f"Converted RAW to JPEG: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error converting RAW image {raw_path}: {e}")
            raise
