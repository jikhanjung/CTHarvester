def pre_mutation(context):
    """Skip test files and build directories"""
    skip_patterns = ["test_", "build/", "dist/", ".venv/", "__pycache__/"]
    if any(pattern in context.filename for pattern in skip_patterns):
        context.skip = True
