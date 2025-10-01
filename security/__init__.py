"""Security validation and file handling utilities.

This package provides security-focused file validation and path handling to prevent
common security vulnerabilities like path traversal attacks and unauthorized file access.

Created during Phase 4 refactoring as part of the security improvements initiative.

Modules:
    file_validator: Secure file path validation and operations

Key Features:
    - Path traversal attack prevention
    - File type validation
    - Size limit enforcement
    - Secure path joining and listing operations
    - Cross-platform compatibility (Windows, Linux, macOS)

Example:
    >>> from security.file_validator import SecureFileValidator
    >>> validator = SecureFileValidator()
    >>> safe_path = validator.validate_path("/path/to/file.txt")
    >>> files = validator.secure_listdir("/path/to/directory")

Note:
    All file operations in the application should use SecureFileValidator
    to ensure consistent security checks across the codebase.

See Also:
    security.file_validator: Main file validation module
"""
