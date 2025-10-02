#!/bin/bash
# Setup script for Next Improvements Plan
# Creates necessary infrastructure for Phases 1-4

set -e

echo "=================================================="
echo "CTHarvester - Next Improvements Setup"
echo "=================================================="
echo ""

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install additional dependencies
echo ""
echo "Installing additional dependencies..."
echo "---------------------------------------------------"

pip install --upgrade pip

# Phase 1: Type checking
pip install mypy types-PyYAML types-Pillow

# Phase 2: Testing tools
pip install pytest-benchmark pytest-timeout

# Phase 4: Advanced testing
pip install hypothesis mutmut pytest-snapshot

echo "✓ Dependencies installed"

# Create directory structure
echo ""
echo "Creating directory structure..."
echo "---------------------------------------------------"

mkdir -p tests/integration
mkdir -p tests/property
mkdir -p tests/snapshots
mkdir -p tests/benchmarks
mkdir -p scripts/profiling
mkdir -p performance_data

echo "✓ Directories created"

# Create baseline performance metrics
echo ""
echo "Collecting baseline metrics..."
echo "---------------------------------------------------"

python -c "
import json
import time

baseline = {
    'timestamp': time.time(),
    'version': '0.2.3',
    'metrics': {
        'thumbnail_generation': {
            'images_per_second': 0,
            'memory_mb': 0
        },
        'type_hints': {
            'coverage_percent': 46.7
        },
        'tests': {
            'total': 603,
            'coverage_percent': 60.0
        }
    }
}

with open('performance_data/baseline.json', 'w') as f:
    json.dump(baseline, f, indent=2)

print('✓ Baseline metrics saved to performance_data/baseline.json')
"

# Create .mutmut-config
echo ""
echo "Creating mutation testing config..."
echo "---------------------------------------------------"

cat > .mutmut-config.py << 'EOF'
def pre_mutation(context):
    """Skip test files and build directories"""
    skip_patterns = ['test_', 'build/', 'dist/', '.venv/', '__pycache__/']
    if any(pattern in context.filename for pattern in skip_patterns):
        context.skip = True
EOF

echo "✓ Created .mutmut-config.py"

# Update pyproject.toml with new tools
echo ""
echo "Updating pyproject.toml..."
echo "---------------------------------------------------"

python << 'PYTHON_SCRIPT'
import sys
from pathlib import Path

pyproject_path = Path('pyproject.toml')
content = pyproject_path.read_text()

# Add hypothesis config if not present
if '[tool.hypothesis]' not in content:
    hypothesis_config = '''
# Hypothesis (property-based testing) configuration
[tool.hypothesis]
max_examples = 100
derandomize = true
deadline = 500  # milliseconds
'''
    content += hypothesis_config

# Add pytest-benchmark config if not present
if '[tool.pytest.ini_options]' in content and 'benchmark' not in content:
    # Find the markers section and add benchmark marker
    import re
    markers_pattern = r'(markers = \[)(.*?)(\])'
    def add_benchmark_marker(match):
        markers = match.group(2)
        if 'benchmark' not in markers:
            markers += ',\n    "benchmark: marks tests as benchmarks"'
        return match.group(1) + markers + match.group(3)

    content = re.sub(markers_pattern, add_benchmark_marker, content, flags=re.DOTALL)

pyproject_path.write_text(content)
print('✓ Updated pyproject.toml')
PYTHON_SCRIPT

# Create template files for each phase
echo ""
echo "Creating template test files..."
echo "---------------------------------------------------"

# Phase 2: Integration test template
cat > tests/integration/test_thumbnail_complete_workflow.py << 'EOF'
"""
Integration tests for complete thumbnail workflow

Part of Phase 2: Integration Tests Expansion
"""

import pytest


@pytest.mark.integration
@pytest.mark.slow
class TestThumbnailCompleteWorkflow:
    """Complete thumbnail workflow integration tests"""

    def test_full_workflow_with_real_data(self):
        """Test complete workflow with real dataset"""
        # TODO: Implement
        pytest.skip("Template - to be implemented in Phase 2")

    def test_rust_fallback_scenario(self):
        """Test Rust failure and Python fallback"""
        # TODO: Implement
        pytest.skip("Template - to be implemented in Phase 2")

    def test_large_dataset_handling(self):
        """Test with 1000+ images"""
        # TODO: Implement
        pytest.skip("Template - to be implemented in Phase 2")
EOF

# Phase 4: Property-based test template
cat > tests/property/test_image_properties.py << 'EOF'
"""
Property-based tests for image processing

Part of Phase 4: Advanced Testing Patterns
"""

import pytest
from hypothesis import given, strategies as st


@pytest.mark.property
class TestImageProperties:
    """Property-based tests using Hypothesis"""

    @given(
        width=st.integers(min_value=1, max_value=4096),
        height=st.integers(min_value=1, max_value=4096)
    )
    def test_downsample_preserves_aspect_ratio(self, width, height):
        """Property: Downsampling preserves aspect ratio"""
        # TODO: Implement
        pytest.skip("Template - to be implemented in Phase 4")
EOF

echo "✓ Created template test files"

# Create profiling script template
cat > scripts/profiling/profile_performance.py << 'EOF'
#!/usr/bin/env python3
"""
Performance profiling script

Part of Phase 3: Performance Profiling Automation
"""

import cProfile
import pstats
import sys
from pathlib import Path


def profile_thumbnail_generation():
    """Profile thumbnail generation"""
    # TODO: Implement
    print("Template - to be implemented in Phase 3")


if __name__ == '__main__':
    profile_thumbnail_generation()
EOF

chmod +x scripts/profiling/profile_performance.py

echo "✓ Created profiling script template"

# Print summary
echo ""
echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "📦 Installed packages:"
echo "  - mypy (type checking)"
echo "  - hypothesis (property-based testing)"
echo "  - mutmut (mutation testing)"
echo "  - pytest-benchmark (performance testing)"
echo "  - pytest-snapshot (snapshot testing)"
echo ""
echo "📁 Created directories:"
echo "  - tests/integration/"
echo "  - tests/property/"
echo "  - tests/snapshots/"
echo "  - tests/benchmarks/"
echo "  - scripts/profiling/"
echo "  - performance_data/"
echo ""
echo "📄 Created files:"
echo "  - .mutmut-config.py"
echo "  - performance_data/baseline.json"
echo "  - Template test files"
echo ""
echo "🚀 Next steps:"
echo "  1. Review: devlog/20251002_068_next_improvements_plan.md"
echo "  2. Start Phase 1: Add type hints to core modules"
echo "  3. Run: mypy core/ utils/ --config-file pyproject.toml"
echo ""
echo "To track progress, see the implementation plan:"
echo "  cat devlog/20251002_068_next_improvements_plan.md"
echo ""
