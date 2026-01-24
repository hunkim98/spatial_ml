import hashlib
import base64
from typing import Optional


class FileHashChecker:
    """Utility class for computing and comparing file hashes."""

    @staticmethod
    def md5_for_file(filepath: str) -> str:
        """
        Compute MD5 hash of a file.

        Args:
            filepath: Path to the file to hash

        Returns:
            Hexadecimal MD5 hash string
        """
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def gcs_md5_to_hex(gcs_md5_base64: str) -> str:
        """
        Convert GCS base64-encoded MD5 hash to hexadecimal format.

        Args:
            gcs_md5_base64: Base64-encoded MD5 hash from GCS

        Returns:
            Hexadecimal MD5 hash string
        """
        return base64.b64decode(gcs_md5_base64).hex()

    @staticmethod
    def compare_file_with_gcs_hash(local_filepath: str, gcs_md5_base64: Optional[str]) -> bool:
        """
        Compare local file hash with GCS blob hash.

        Args:
            local_filepath: Path to the local file
            gcs_md5_base64: Base64-encoded MD5 hash from GCS (can be None)

        Returns:
            True if hashes match, False otherwise
        """
        if not gcs_md5_base64:
            return False

        local_md5 = FileHashChecker.md5_for_file(local_filepath)
        gcs_md5_hex = FileHashChecker.gcs_md5_to_hex(gcs_md5_base64)

        return local_md5 == gcs_md5_hex