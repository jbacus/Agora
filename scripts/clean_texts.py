#!/usr/bin/env python3
"""
Text Cleaning and Preprocessing Script
Removes Project Gutenberg boilerplate and cleans up texts for ingestion.
"""
import re
from pathlib import Path
from typing import Optional

from loguru import logger


def clean_gutenberg_text(text: str) -> str:
    """Remove Project Gutenberg boilerplate and clean text."""

    # Remove header (everything before "*** START OF" marker)
    start_patterns = [
        r'\*\*\* START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*',
        r'\*{3,}\s*START OF.*?\*{3,}',
    ]

    for pattern in start_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            text = text[match.end():]
            logger.info(f"Removed header ({match.end()} characters)")
            break

    # Remove footer (everything after "*** END OF" marker)
    end_patterns = [
        r'\*\*\* END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*',
        r'\*{3,}\s*END OF.*?\*{3,}',
    ]

    for pattern in end_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            text = text[:match.start()]
            logger.info(f"Removed footer (kept {len(text)} characters)")
            break

    # Remove multiple blank lines (more than 2)
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    # Remove excessive whitespace
    text = re.sub(r'[ \t]+', ' ', text)

    # Fix common encoding issues
    replacements = {
        ''': "'",
        ''': "'",
        '"': '"',
        '"': '"',
        '—': '--',
        '–': '-',
        '…': '...',
        '\r\n': '\n',
        '\r': '\n',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Trim whitespace
    text = text.strip()

    return text


def clean_author_texts(author_dir: Path, force: bool = False) -> int:
    """
    Clean all texts for an author.

    Args:
        author_dir: Directory containing author's raw texts
        force: If True, re-clean even if already cleaned

    Returns:
        Number of files cleaned
    """
    if not author_dir.exists():
        logger.warning(f"Directory not found: {author_dir}")
        return 0

    txt_files = list(author_dir.glob('*.txt'))
    if not txt_files:
        logger.warning(f"No .txt files found in {author_dir}")
        return 0

    logger.info(f"Cleaning {len(txt_files)} files in {author_dir.name}/")

    cleaned_count = 0

    for txt_file in txt_files:
        # Check if already cleaned (heuristic: no Project Gutenberg markers)
        if not force:
            content = txt_file.read_text(encoding='utf-8', errors='ignore')
            if 'PROJECT GUTENBERG' not in content.upper():
                logger.info(f"  ✓ {txt_file.name} (already cleaned)")
                cleaned_count += 1
                continue

        logger.info(f"  Cleaning {txt_file.name}...")

        # Read original text
        try:
            text = txt_file.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"  ✗ Error reading {txt_file.name}: {e}")
            continue

        original_size = len(text)

        # Clean text
        cleaned = clean_gutenberg_text(text)
        cleaned_size = len(cleaned)

        # Write back
        try:
            txt_file.write_text(cleaned, encoding='utf-8')
            reduction = ((original_size - cleaned_size) / original_size * 100)
            logger.info(f"  ✓ {txt_file.name} ({original_size:,} → {cleaned_size:,} chars, {reduction:.1f}% reduction)")
            cleaned_count += 1
        except Exception as e:
            logger.error(f"  ✗ Error writing {txt_file.name}: {e}")

    return cleaned_count


def validate_texts(author_dir: Path) -> dict:
    """
    Validate cleaned texts.

    Returns:
        Dictionary with validation results
    """
    results = {
        'total_files': 0,
        'total_chars': 0,
        'total_words': 0,
        'files': []
    }

    for txt_file in author_dir.glob('*.txt'):
        text = txt_file.read_text(encoding='utf-8')

        file_info = {
            'name': txt_file.name,
            'size_chars': len(text),
            'size_words': len(text.split()),
            'size_kb': len(text.encode('utf-8')) / 1024,
            'has_gutenberg_markers': 'PROJECT GUTENBERG' in text.upper(),
            'encoding_issues': len(re.findall(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', text))
        }

        results['files'].append(file_info)
        results['total_files'] += 1
        results['total_chars'] += file_info['size_chars']
        results['total_words'] += file_info['size_words']

    return results


def main():
    """Main entry point."""
    import sys

    # Configure logging
    logger.remove()
    logger.add(sys.stderr, format="<level>{message}</level>", level="INFO")

    logger.info("📚 Agora Text Cleaning")
    logger.info("=" * 60)
    logger.info("")

    # Clean all authors
    authors = ['marx', 'whitman', 'baudelaire']
    data_dir = Path('data/raw')

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        logger.info("Run ./scripts/acquire_texts.sh first")
        return 1

    total_cleaned = 0

    for author in authors:
        author_dir = data_dir / author
        if author_dir.exists():
            count = clean_author_texts(author_dir)
            total_cleaned += count
            logger.info("")
        else:
            logger.warning(f"Author directory not found: {author_dir}")
            logger.info("")

    # Validation
    logger.info("=" * 60)
    logger.info("📊 Validation Results")
    logger.info("=" * 60)
    logger.info("")

    for author in authors:
        author_dir = data_dir / author
        if not author_dir.exists():
            continue

        results = validate_texts(author_dir)

        logger.info(f"{author.upper()}:")
        logger.info(f"  Files: {results['total_files']}")
        logger.info(f"  Total characters: {results['total_chars']:,}")
        logger.info(f"  Total words: {results['total_words']:,}")
        logger.info(f"  Estimated chunks: ~{results['total_words'] // 400}")
        logger.info("")

        for file_info in results['files']:
            status = "✓" if not file_info['has_gutenberg_markers'] else "⚠"
            logger.info(f"  {status} {file_info['name']}: {file_info['size_words']:,} words ({file_info['size_kb']:.1f} KB)")

        logger.info("")

    logger.info("=" * 60)
    logger.info(f"✅ Cleaned {total_cleaned} files")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📝 Next steps:")
    logger.info("  1. Review cleaned texts in data/raw/")
    logger.info("  2. Set up .env file with GEMINI_API_KEY")
    logger.info("  3. Run: python scripts/init_database.py")
    logger.info("  4. Run: python scripts/ingest_author.py --author [author]")
    logger.info("")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
