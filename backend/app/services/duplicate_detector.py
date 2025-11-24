import imagehash
from PIL import Image
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects duplicate and similar images using perceptual hashing.
    Uses both dHash and pHash for robust duplicate detection.
    """

    def __init__(self, similarity_threshold: int = 10):
        """
        Initialize duplicate detector.

        Args:
            similarity_threshold: Hamming distance threshold for duplicates.
                                 Lower = more strict (default 10 = 96% similarity)
        """
        self.similarity_threshold = similarity_threshold

    def compute_hashes(self, image_path: str) -> Tuple[str, str]:
        """
        Compute perceptual hashes for an image.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (dhash, phash) as hex strings
        """
        try:
            img = Image.open(image_path)

            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Compute hashes
            dhash = imagehash.dhash(img)
            phash = imagehash.phash(img)

            return str(dhash), str(phash)

        except Exception as e:
            logger.error(f"Error computing hashes for {image_path}: {e}")
            raise

    def calculate_similarity(
        self,
        hash1: str,
        hash2: str,
        hash_type: str = "dhash"
    ) -> int:
        """
        Calculate Hamming distance between two hashes.

        Args:
            hash1: First hash (hex string)
            hash2: Second hash (hex string)
            hash_type: Type of hash ('dhash' or 'phash')

        Returns:
            Hamming distance (0 = identical, higher = more different)
        """
        try:
            if hash_type == "dhash":
                h1 = imagehash.hex_to_hash(hash1)
                h2 = imagehash.hex_to_hash(hash2)
            else:  # phash
                h1 = imagehash.hex_to_hash(hash1)
                h2 = imagehash.hex_to_hash(hash2)

            return h1 - h2  # Hamming distance

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 999  # Return high value on error

    def are_duplicates(
        self,
        image_path1: str,
        image_path2: str,
        use_both_hashes: bool = True
    ) -> bool:
        """
        Check if two images are duplicates or nearly identical.

        Args:
            image_path1: Path to first image
            image_path2: Path to second image
            use_both_hashes: If True, require both dhash and phash to match

        Returns:
            True if images are considered duplicates
        """
        try:
            dhash1, phash1 = self.compute_hashes(image_path1)
            dhash2, phash2 = self.compute_hashes(image_path2)

            dhash_distance = self.calculate_similarity(dhash1, dhash2, "dhash")
            phash_distance = self.calculate_similarity(phash1, phash2, "phash")

            if use_both_hashes:
                # Both hashes must indicate similarity
                return (
                    dhash_distance <= self.similarity_threshold and
                    phash_distance <= self.similarity_threshold
                )
            else:
                # Either hash indicating similarity is enough
                return (
                    dhash_distance <= self.similarity_threshold or
                    phash_distance <= self.similarity_threshold
                )

        except Exception as e:
            logger.error(f"Error comparing images: {e}")
            return False

    def find_duplicate_groups(
        self,
        image_data: List[Dict[str, str]]
    ) -> List[List[int]]:
        """
        Find groups of duplicate images from a list.

        Args:
            image_data: List of dicts with 'id', 'dhash', 'phash' keys

        Returns:
            List of lists, where each inner list contains indices of duplicate images
        """
        groups = []
        processed = set()

        for i, img1 in enumerate(image_data):
            if i in processed:
                continue

            # Start new group
            group = [i]
            processed.add(i)

            # Find all duplicates of this image
            for j, img2 in enumerate(image_data[i + 1:], start=i + 1):
                if j in processed:
                    continue

                # Compare hashes
                dhash_dist = self.calculate_similarity(
                    img1['dhash'],
                    img2['dhash'],
                    "dhash"
                )
                phash_dist = self.calculate_similarity(
                    img1['phash'],
                    img2['phash'],
                    "phash"
                )

                # If similar by both hashes, add to group
                if (dhash_dist <= self.similarity_threshold and
                    phash_dist <= self.similarity_threshold):
                    group.append(j)
                    processed.add(j)

            # Only add groups with more than 1 image
            if len(group) > 1:
                groups.append(group)

        return groups

    def find_burst_sequences(
        self,
        image_data: List[Dict],
        time_threshold_seconds: int = 5
    ) -> List[List[int]]:
        """
        Find burst sequences based on capture time proximity.

        Args:
            image_data: List of dicts with 'id', 'capture_time', 'dhash', 'phash'
            time_threshold_seconds: Max seconds between shots in a burst

        Returns:
            List of lists containing indices of images in burst sequences
        """
        from datetime import timedelta

        # Sort by capture time
        sorted_data = sorted(
            enumerate(image_data),
            key=lambda x: x[1].get('capture_time', '')
        )

        sequences = []
        current_sequence = []

        for i, (idx, img) in enumerate(sorted_data):
            if not img.get('capture_time'):
                continue

            if not current_sequence:
                current_sequence.append(idx)
                continue

            # Get previous image in sequence
            prev_idx = current_sequence[-1]
            prev_img = image_data[prev_idx]

            # Calculate time difference
            time_diff = (
                img['capture_time'] - prev_img['capture_time']
            ).total_seconds()

            # Check if within burst threshold
            if time_diff <= time_threshold_seconds:
                # Also check if images are similar (burst photos should be)
                dhash_dist = self.calculate_similarity(
                    img['dhash'],
                    prev_img['dhash'],
                    "dhash"
                )

                # More lenient threshold for bursts (allow 30 Hamming distance)
                if dhash_dist <= 30:
                    current_sequence.append(idx)
                else:
                    # Time is close but images are different - new sequence
                    if len(current_sequence) > 1:
                        sequences.append(current_sequence)
                    current_sequence = [idx]
            else:
                # Time gap too large - save sequence and start new
                if len(current_sequence) > 1:
                    sequences.append(current_sequence)
                current_sequence = [idx]

        # Add final sequence
        if len(current_sequence) > 1:
            sequences.append(current_sequence)

        return sequences

    def select_best_from_group(
        self,
        image_data: List[Dict],
        group_indices: List[int]
    ) -> int:
        """
        Select the best image from a duplicate group based on scores.

        Args:
            image_data: List of all image data dicts
            group_indices: Indices of images in the duplicate group

        Returns:
            Index of the best image in the group
        """
        best_idx = group_indices[0]
        best_score = image_data[best_idx].get('overall_score', 0)

        for idx in group_indices[1:]:
            score = image_data[idx].get('overall_score', 0)
            if score > best_score:
                best_score = score
                best_idx = idx

        return best_idx
