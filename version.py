"""
CTHarvester Version Information
Single Source of Truth for version management
"""
import semver

__version__ = "0.2.3-alpha.2"

# semver 라이브러리를 사용해 안전하게 파싱
_ver = semver.VersionInfo.parse(__version__)
__version_info__ = (_ver.major, _ver.minor, _ver.patch)