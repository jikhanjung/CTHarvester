"""
파일 시스템 보안 유틸리티
Directory traversal 공격 방지
"""
import os
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileSecurityError(Exception):
    """파일 보안 관련 예외"""
    pass


class SecureFileValidator:
    """파일 경로 검증 클래스"""

    # 허용된 파일 확장자
    ALLOWED_EXTENSIONS = {'.bmp', '.jpg', '.jpeg', '.png', '.tif', '.tiff'}

    # 금지된 문자/패턴
    FORBIDDEN_PATTERNS = [
        r'\.\.',        # 상위 디렉토리 참조
        r'^/',          # 절대 경로
        r'^\\',         # Windows 절대 경로
        r'[<>:"|?*]',   # Windows 금지 문자
        r'\x00',        # Null 바이트
    ]

    @staticmethod
    def validate_filename(filename: str) -> str:
        """
        파일명 검증 (디렉토리 순회 방지)

        Args:
            filename: 검증할 파일명

        Returns:
            검증된 파일명 (basename만)

        Raises:
            FileSecurityError: 검증 실패 시
        """
        if not filename:
            raise FileSecurityError("Filename is empty")

        # 금지된 패턴 체크
        for pattern in SecureFileValidator.FORBIDDEN_PATTERNS:
            if re.search(pattern, filename):
                raise FileSecurityError(
                    f"Filename contains forbidden pattern: {filename}"
                )

        # basename만 추출 (디렉토리 부분 제거)
        safe_name = os.path.basename(filename)

        if safe_name != filename:
            logger.warning(
                f"Filename contained directory path: {filename} -> {safe_name}"
            )

        return safe_name

    @staticmethod
    def validate_extension(filename: str) -> bool:
        """파일 확장자 검증"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in SecureFileValidator.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_path(file_path: str, base_dir: str) -> str:
        """
        파일 경로 검증 (base_dir 내부인지 확인)

        Args:
            file_path: 검증할 파일 경로
            base_dir: 허용된 기본 디렉토리

        Returns:
            정규화된 절대 경로

        Raises:
            FileSecurityError: base_dir 외부 경로일 경우
        """
        # 절대 경로로 변환 및 정규화
        abs_base = os.path.abspath(base_dir)
        abs_file = os.path.abspath(file_path)

        # 공통 경로 확인
        try:
            common_path = os.path.commonpath([abs_base, abs_file])
        except ValueError:
            # Windows에서 다른 드라이브인 경우
            raise FileSecurityError(
                f"Path is on different drive: {file_path} "
                f"(base: {base_dir})"
            )

        if common_path != abs_base:
            raise FileSecurityError(
                f"Path is outside base directory: {file_path} "
                f"(base: {base_dir})"
            )

        return abs_file

    @staticmethod
    def safe_join(base_dir: str, *paths: str) -> str:
        """
        안전한 경로 결합 (os.path.join의 안전한 버전)

        Args:
            base_dir: 기본 디렉토리
            *paths: 결합할 경로 구성요소들

        Returns:
            안전하게 결합된 경로

        Raises:
            FileSecurityError: 검증 실패 시
        """
        # 각 구성요소 검증
        validated_parts = []
        for part in paths:
            validated_parts.append(
                SecureFileValidator.validate_filename(part)
            )

        # 경로 결합
        joined = os.path.join(base_dir, *validated_parts)

        # 최종 검증
        return SecureFileValidator.validate_path(joined, base_dir)

    @staticmethod
    def secure_listdir(directory: str, extensions: Optional[set] = None) -> list:
        """
        안전한 디렉토리 목록 조회

        Args:
            directory: 조회할 디렉토리
            extensions: 허용할 확장자 집합 (None이면 기본값)

        Returns:
            검증된 파일 목록 (basename만)
        """
        if not os.path.isdir(directory):
            raise FileSecurityError(f"Not a directory: {directory}")

        if extensions is None:
            extensions = SecureFileValidator.ALLOWED_EXTENSIONS

        safe_files = []
        try:
            for item in os.listdir(directory):
                try:
                    # 파일명 검증
                    safe_name = SecureFileValidator.validate_filename(item)

                    # 전체 경로 검증
                    full_path = SecureFileValidator.safe_join(directory, safe_name)

                    # 파일인지 확인하고 확장자 검증
                    if os.path.isfile(full_path):
                        ext = os.path.splitext(safe_name)[1].lower()
                        if ext in extensions:
                            safe_files.append(safe_name)
                        else:
                            logger.debug(f"Skipping non-image file: {safe_name}")

                except FileSecurityError as e:
                    logger.warning(f"Skipping invalid file: {item} ({e})")
                    continue

        except OSError as e:
            logger.error(f"Failed to list directory {directory}: {e}")
            raise FileSecurityError(f"Directory access failed: {e}") from e

        return sorted(safe_files)

    @staticmethod
    def validate_no_symlink(file_path: str) -> str:
        """심볼릭 링크가 아닌지 확인"""
        if os.path.islink(file_path):
            raise FileSecurityError(f"Symbolic links not allowed: {file_path}")
        return file_path


# 편의를 위한 단축 함수들
def safe_open_image(file_path: str, base_dir: str):
    """
    안전하게 이미지 파일 열기

    Args:
        file_path: 이미지 파일 경로
        base_dir: 기본 디렉토리

    Returns:
        PIL Image 객체

    Raises:
        FileSecurityError: 보안 검증 실패
    """
    from PIL import Image

    # 경로 검증
    validated_path = SecureFileValidator.validate_path(file_path, base_dir)

    # 심볼릭 링크 체크
    SecureFileValidator.validate_no_symlink(validated_path)

    # 확장자 검증
    if not SecureFileValidator.validate_extension(validated_path):
        raise FileSecurityError(f"Invalid file extension: {validated_path}")

    # 이미지 열기
    return Image.open(validated_path)