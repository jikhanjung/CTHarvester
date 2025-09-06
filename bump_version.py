#!/usr/bin/env python
"""
Version bump utility for CTHarvester
Usage: python bump_version.py [major|minor|patch]
"""

import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

def get_current_version() -> str:
    """Read current version from version.py"""
    version_file = Path("version.py")
    if not version_file.exists():
        raise FileNotFoundError("version.py not found")
    
    content = version_file.read_text()
    match = re.search(r'__version__ = "(.*?)"', content)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version string in version.py")

def update_version_file(new_version: str) -> None:
    """Update version.py with new version"""
    version_file = Path("version.py")
    content = version_file.read_text()
    
    # Update __version__ string
    new_content = re.sub(
        r'__version__ = ".*?"',
        f'__version__ = "{new_version}"',
        content
    )
    
    # Update __version_info__ tuple
    version_parts = new_version.split('.')
    if len(version_parts) == 3:
        new_content = re.sub(
            r'__version_info__ = .*',
            f'__version_info__ = tuple(map(int, __version__.split(\'.\')))',
            new_content
        )
    
    # Create backup
    backup_file = version_file.with_suffix('.py.bak')
    version_file.rename(backup_file)
    
    try:
        # Write new file
        version_file.write_text(new_content)
        print(f"✅ Version updated to {new_version}")
        
        # Remove backup
        backup_file.unlink()
    except Exception as e:
        # Rollback on error
        backup_file.rename(version_file)
        raise e

def bump_version(bump_type: str = 'patch') -> str:
    """
    Increment version based on bump type
    
    Args:
        bump_type: 'major', 'minor', or 'patch'
    
    Returns:
        New version string
    """
    current = get_current_version()
    parts = current.split('.')
    
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current}")
    
    major, minor, patch = map(int, parts)
    
    if bump_type == 'major':
        new_version = f"{major + 1}.0.0"
    elif bump_type == 'minor':
        new_version = f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        new_version = f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")
    
    print(f"Bumping version: {current} → {new_version}")
    return new_version

def create_git_tag(version: str, message: Optional[str] = None) -> None:
    """Create and optionally push git tag"""
    tag_name = f"v{version}"
    
    if message is None:
        message = f"Release version {version}"
    
    try:
        # Check if tag already exists
        result = subprocess.run(
            ['git', 'tag', '-l', tag_name],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print(f"⚠️  Tag {tag_name} already exists")
            return
        
        # Create annotated tag
        subprocess.run(
            ['git', 'tag', '-a', tag_name, '-m', message],
            check=True
        )
        print(f"✅ Git tag created: {tag_name}")
        
        # Ask to push tag
        response = input("Push tag to remote? (y/N): ")
        if response.lower() == 'y':
            subprocess.run(['git', 'push', 'origin', tag_name], check=True)
            print(f"✅ Tag pushed to remote")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create git tag: {e}")

def update_changelog(version: str) -> None:
    """Update or create CHANGELOG.md"""
    changelog_file = Path("CHANGELOG.md")
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    if not changelog_file.exists():
        # Create new changelog
        content = f"""# Changelog

All notable changes to CTHarvester will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [{version}] - {date_str}

### Added
- Initial version with centralized version management

### Changed
- Version information now managed through version.py

### Fixed
- Version consistency across all build artifacts

"""
        changelog_file.write_text(content)
        print("✅ CHANGELOG.md created")
    else:
        # Add new version section
        content = changelog_file.read_text()
        
        # Check if version already exists
        if f"## [{version}]" in content:
            print(f"⚠️  Version {version} already in CHANGELOG.md")
            return
        
        # Create new section
        new_section = f"""
## [{version}] - {date_str}

### Added
- 

### Changed
- 

### Fixed
- 

"""
        # Insert after the header section
        lines = content.split('\n')
        insert_index = 0
        
        # Find where to insert (after the description, before first version)
        for i, line in enumerate(lines):
            if line.startswith('## ['):
                insert_index = i
                break
        
        if insert_index == 0:
            # No existing versions, add after header
            for i, line in enumerate(lines):
                if line.strip() == '' and i > 5:  # Skip initial header lines
                    insert_index = i + 1
                    break
        
        lines.insert(insert_index, new_section)
        new_content = '\n'.join(lines)
        
        changelog_file.write_text(new_content)
        print("✅ CHANGELOG.md updated")
        print("⚠️  Please update the changelog entries before committing")

def check_git_status() -> bool:
    """Check if git working directory is clean"""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            print("⚠️  Warning: You have uncommitted changes")
            response = input("Continue anyway? (y/N): ")
            return response.lower() == 'y'
        return True
    except subprocess.CalledProcessError:
        print("⚠️  Not a git repository or git not available")
        return True

def main():
    """Main execution function"""
    # Parse arguments
    bump_type = sys.argv[1] if len(sys.argv) > 1 else 'patch'
    
    if bump_type in ['-h', '--help']:
        print(__doc__)
        print("\nBump types:")
        print("  major: Increment major version (x.0.0)")
        print("  minor: Increment minor version (0.x.0)")
        print("  patch: Increment patch version (0.0.x)")
        sys.exit(0)
    
    if bump_type not in ['major', 'minor', 'patch']:
        print(f"Error: Invalid bump type '{bump_type}'")
        print("Usage: python bump_version.py [major|minor|patch]")
        sys.exit(1)
    
    try:
        # Check git status
        if not check_git_status():
            print("Aborted")
            sys.exit(1)
        
        # Show current version
        current_version = get_current_version()
        print(f"Current version: {current_version}")
        
        # Bump version
        new_version = bump_version(bump_type)
        
        # Confirm with user
        response = input(f"Update version to {new_version}? (y/N): ")
        if response.lower() != 'y':
            print("Aborted")
            sys.exit(0)
        
        # Update version file
        update_version_file(new_version)
        
        # Update CHANGELOG
        response = input("Update CHANGELOG.md? (y/N): ")
        if response.lower() == 'y':
            update_changelog(new_version)
        
        # Git operations
        response = input("Create git commit? (y/N): ")
        if response.lower() == 'y':
            # Stage files
            subprocess.run(['git', 'add', 'version.py'], check=True)
            
            if Path("CHANGELOG.md").exists():
                subprocess.run(['git', 'add', 'CHANGELOG.md'], check=True)
            
            # Create commit
            commit_message = f"chore: bump version to {new_version}"
            subprocess.run(
                ['git', 'commit', '-m', commit_message],
                check=True
            )
            print(f"✅ Git commit created: {commit_message}")
            
            # Create tag
            response = input("Create git tag? (y/N): ")
            if response.lower() == 'y':
                create_git_tag(new_version)
        
        print(f"\n🎉 Version {new_version} is ready!")
        print("\nNext steps:")
        print("1. Update any changelog entries if needed")
        print("2. Run tests to ensure everything works")
        print("3. Build the application with: pyinstaller CTHarvester.spec")
        
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()