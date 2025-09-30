#!/usr/bin/env python3
"""Generate release notes from git commits.

This script analyzes git commits between releases and generates structured
release notes following the Keep a Changelog format.

Usage:
    python generate_release_notes.py --tag v1.0.0 --output release_notes.md
    python generate_release_notes.py --from v0.9.0 --to v1.0.0
"""
import argparse
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict

try:
    import git
except ImportError:
    print("Error: gitpython is required. Install with: pip install gitpython")
    sys.exit(1)


# Conventional commit types
COMMIT_TYPES = {
    'feat': ('Added', '✨'),
    'fix': ('Fixed', '🐛'),
    'docs': ('Documentation', '📝'),
    'style': ('Style', '💄'),
    'refactor': ('Changed', '♻️'),
    'perf': ('Performance', '⚡'),
    'test': ('Tests', '✅'),
    'build': ('Build', '🏗️'),
    'ci': ('CI/CD', '👷'),
    'chore': ('Maintenance', '🔧'),
    'revert': ('Reverted', '⏪'),
    'security': ('Security', '🔒'),
}

# Breaking change markers
BREAKING_MARKERS = ['BREAKING CHANGE', 'BREAKING-CHANGE', '!']


def parse_commit_message(message: str) -> Tuple[str, str, str, bool]:
    """Parse conventional commit message.

    Args:
        message: Commit message

    Returns:
        Tuple of (type, scope, description, is_breaking)
    """
    # Check for breaking change
    is_breaking = any(marker in message.upper() for marker in BREAKING_MARKERS[:2])

    # Parse conventional commit format: type(scope)!: description
    pattern = r'^(\w+)(?:\(([^)]+)\))?(!)?:\s*(.+)$'
    match = re.match(pattern, message.split('\n')[0])

    if match:
        commit_type, scope, breaking_marker, description = match.groups()
        if breaking_marker == '!':
            is_breaking = True
        return commit_type, scope or '', description, is_breaking
    else:
        # Non-conventional commit
        return 'other', '', message.split('\n')[0], False


def get_commits_between_tags(repo: git.Repo, from_tag: str, to_tag: str = 'HEAD') -> List[git.Commit]:
    """Get commits between two tags.

    Args:
        repo: Git repository
        from_tag: Starting tag/commit
        to_tag: Ending tag/commit (default: HEAD)

    Returns:
        List of commits
    """
    try:
        if to_tag == 'HEAD':
            commits = list(repo.iter_commits(f'{from_tag}..HEAD'))
        else:
            commits = list(repo.iter_commits(f'{from_tag}..{to_tag}'))
        return commits
    except git.GitCommandError as e:
        print(f"Error getting commits: {e}")
        return []


def find_previous_tag(repo: git.Repo, current_tag: str) -> str:
    """Find the previous tag before current_tag.

    Args:
        repo: Git repository
        current_tag: Current tag

    Returns:
        Previous tag name or None
    """
    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    tag_names = [t.name for t in tags]

    if current_tag in tag_names:
        idx = tag_names.index(current_tag)
        if idx > 0:
            return tag_names[idx - 1]

    # If current_tag not found or is first, return first commit
    return None


def categorize_commits(commits: List[git.Commit]) -> Dict[str, List[Dict]]:
    """Categorize commits by type.

    Args:
        commits: List of commits

    Returns:
        Dictionary mapping categories to commit info
    """
    categories = defaultdict(list)
    breaking_changes = []

    for commit in commits:
        message = commit.message.strip()
        commit_type, scope, description, is_breaking = parse_commit_message(message)

        # Get full commit message body for breaking changes
        body_lines = message.split('\n')[1:]
        body = '\n'.join(line.strip() for line in body_lines if line.strip())

        commit_info = {
            'hash': commit.hexsha[:7],
            'description': description,
            'scope': scope,
            'author': commit.author.name,
            'date': datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d'),
            'body': body
        }

        # Handle breaking changes
        if is_breaking:
            breaking_changes.append(commit_info)

        # Categorize by type
        if commit_type in COMMIT_TYPES:
            category, emoji = COMMIT_TYPES[commit_type]
            categories[category].append(commit_info)
        else:
            categories['Other'].append(commit_info)

    # Add breaking changes as separate category if any
    if breaking_changes:
        categories['⚠️ BREAKING CHANGES'] = breaking_changes

    return dict(categories)


def format_release_notes(
    tag: str,
    date: str,
    categories: Dict[str, List[Dict]],
    repo_url: str = None
) -> str:
    """Format release notes in markdown.

    Args:
        tag: Release tag
        date: Release date
        categories: Categorized commits
        repo_url: Repository URL for linking

    Returns:
        Formatted markdown string
    """
    lines = [
        f"# Release {tag}",
        f"",
        f"**Release Date:** {date}",
        f"",
    ]

    # Priority order for categories
    priority_categories = [
        '⚠️ BREAKING CHANGES',
        'Added',
        'Changed',
        'Fixed',
        'Security',
        'Performance',
        'Documentation',
    ]

    # Add priority categories first
    for category in priority_categories:
        if category in categories:
            lines.extend(_format_category(category, categories[category], repo_url))
            del categories[category]

    # Add remaining categories
    for category, commits in sorted(categories.items()):
        lines.extend(_format_category(category, commits, repo_url))

    return '\n'.join(lines)


def _format_category(category: str, commits: List[Dict], repo_url: str = None) -> List[str]:
    """Format a single category of commits.

    Args:
        category: Category name
        commits: List of commit info dicts
        repo_url: Repository URL

    Returns:
        List of formatted lines
    """
    if not commits:
        return []

    lines = [
        f"## {category}",
        f"",
    ]

    for commit in commits:
        # Format: - Description (scope) [hash]
        scope = f" **({commit['scope']})**" if commit['scope'] else ""
        hash_link = f"[`{commit['hash']}`]({repo_url}/commit/{commit['hash']})" if repo_url else f"`{commit['hash']}`"

        lines.append(f"- {commit['description']}{scope} {hash_link}")

        # Add body for breaking changes
        if category == '⚠️ BREAKING CHANGES' and commit['body']:
            # Extract BREAKING CHANGE description
            for line in commit['body'].split('\n'):
                if 'BREAKING CHANGE:' in line:
                    desc = line.split('BREAKING CHANGE:')[1].strip()
                    lines.append(f"  > {desc}")

    lines.append("")
    return lines


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Generate release notes from git commits'
    )
    parser.add_argument(
        '--tag',
        help='Tag to generate notes for (will compare with previous tag)'
    )
    parser.add_argument(
        '--from',
        dest='from_tag',
        help='Starting tag/commit'
    )
    parser.add_argument(
        '--to',
        dest='to_tag',
        default='HEAD',
        help='Ending tag/commit (default: HEAD)'
    )
    parser.add_argument(
        '--output',
        default='release_notes.md',
        help='Output file (default: release_notes.md)'
    )
    parser.add_argument(
        '--repo-url',
        help='Repository URL for commit links'
    )

    args = parser.parse_args()

    # Open repository
    try:
        repo = git.Repo('.')
    except git.InvalidGitRepositoryError:
        print("Error: Not a git repository")
        return 1

    # Determine tag range
    if args.tag:
        to_tag = args.tag
        from_tag = find_previous_tag(repo, args.tag)
        if not from_tag:
            # Use first commit
            from_tag = list(repo.iter_commits())[-1].hexsha
            print(f"No previous tag found, using first commit: {from_tag[:7]}")
    elif args.from_tag:
        from_tag = args.from_tag
        to_tag = args.to_tag
    else:
        print("Error: Must specify either --tag or --from")
        return 1

    print(f"Generating release notes: {from_tag} -> {to_tag}")

    # Get commits
    commits = get_commits_between_tags(repo, from_tag, to_tag)
    if not commits:
        print("No commits found in range")
        return 1

    print(f"Found {len(commits)} commits")

    # Categorize commits
    categories = categorize_commits(commits)

    # Format release notes
    today = datetime.now().strftime('%Y-%m-%d')
    release_notes = format_release_notes(
        tag=to_tag if to_tag != 'HEAD' else 'Unreleased',
        date=today,
        categories=categories,
        repo_url=args.repo_url
    )

    # Write output
    output_path = Path(args.output)
    output_path.write_text(release_notes, encoding='utf-8')
    print(f"Release notes written to: {output_path}")

    # Print summary
    print("\nSummary:")
    for category, commits_list in categories.items():
        print(f"  {category}: {len(commits_list)} changes")

    return 0


if __name__ == '__main__':
    sys.exit(main())