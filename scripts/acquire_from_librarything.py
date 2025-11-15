#!/usr/bin/env python3
"""
Agora LibraryThing Text Acquisition Script
===========================================

This script processes a LibraryThing export file, searches for books on Project Gutenberg
and other public domain sources, downloads the texts, and prepares them for ingestion
into the Agora author ingest process.

Usage:
    python scripts/acquire_from_librarything.py --input library.tsv
    python scripts/acquire_from_librarything.py --input library.tsv --output-dir data/raw
    python scripts/acquire_from_librarything.py --input library.tsv --author-filter "Marx,Whitman"
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import quote_plus
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Book:
    """Represents a book from LibraryThing export"""
    title: str
    author: str
    author_normalized: str  # Normalized for directory names
    isbn: Optional[str] = None
    publication_date: Optional[str] = None
    gutenberg_id: Optional[str] = None
    gutenberg_url: Optional[str] = None
    downloaded: bool = False
    download_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AuthorReport:
    """Report for a single author's acquisition results"""
    author: str
    author_id: str  # Normalized ID for directory
    total_books: int = 0
    books_found: int = 0
    books_downloaded: int = 0
    books_failed: int = 0
    books: List[Book] = field(default_factory=list)


class GutenbergSearcher:
    """Searches and downloads books from Project Gutenberg"""

    GUTENBERG_API = "https://gutendex.com/books"
    GUTENBERG_MIRROR = "https://www.gutenberg.org"

    def __init__(self):
        self.session = self._create_session()
        self.cache = {}  # Simple in-memory cache

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic"""
        session = requests.Session()
        # Add headers to avoid being blocked
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AgoraBot/1.0; +https://github.com/agora)',
            'Accept': 'application/json',
        })
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def search_book(self, title: str, author: str) -> Optional[Dict]:
        """
        Search for a book on Project Gutenberg using the Gutendex API

        Args:
            title: Book title
            author: Author name

        Returns:
            Dictionary with book info if found, None otherwise
        """
        cache_key = f"{author}:{title}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Try API search first
            result = self._search_with_api(author, title)
            if result:
                self.cache[cache_key] = result
                return result

            # Fallback to manual mapping for common books
            result = self._manual_lookup(author, title)
            if result:
                self.cache[cache_key] = result
                return result

            self.cache[cache_key] = None
            return None

        except Exception as e:
            logger.error(f"Error searching for {title} by {author}: {e}")
            # Try manual lookup as fallback
            result = self._manual_lookup(author, title)
            if result:
                self.cache[cache_key] = result
                return result
            return None

    def _search_with_api(self, author: str, title: str) -> Optional[Dict]:
        """Search using the Gutendex API"""
        try:
            # Search by author and title
            params = {
                'search': f"{author} {title}",
            }

            logger.debug(f"Searching Gutenberg API for: {author} - {title}")
            response = self.session.get(
                self.GUTENBERG_API,
                params=params,
                timeout=10
            )

            # If we get 403, the API might be blocking us
            if response.status_code == 403:
                logger.debug("API returned 403, will try manual lookup")
                return None

            response.raise_for_status()
            data = response.json()

            if data.get('count', 0) > 0:
                # Return the first result
                book = data['results'][0]
                return {
                    'id': book['id'],
                    'title': book['title'],
                    'authors': [a['name'] for a in book.get('authors', [])],
                    'formats': book.get('formats', {}),
                }

            # Try searching by author only if title search failed
            params = {'search': author}
            response = self.session.get(
                self.GUTENBERG_API,
                params=params,
                timeout=10
            )

            if response.status_code == 403:
                return None

            response.raise_for_status()
            data = response.json()

            if data.get('count', 0) > 0:
                # Try to find a title match in the results
                for book in data['results']:
                    book_title = book['title'].lower()
                    search_title = title.lower()

                    # Simple fuzzy matching
                    if (search_title in book_title or
                        book_title in search_title or
                        self._title_similarity(search_title, book_title) > 0.6):
                        return {
                            'id': book['id'],
                            'title': book['title'],
                            'authors': [a['name'] for a in book.get('authors', [])],
                            'formats': book.get('formats', {}),
                        }

            return None

        except Exception as e:
            logger.debug(f"API search failed: {e}")
            return None

    def _manual_lookup(self, author: str, title: str) -> Optional[Dict]:
        """
        Manual lookup for common public domain books
        This is a fallback when the API is unavailable
        """
        # Normalize inputs for matching
        author_norm = author.lower().strip()
        title_norm = title.lower().strip()

        # Common books mapping (author -> title -> gutenberg_id)
        # This is a curated list of popular public domain works
        known_books = {
            'karl marx': {
                'das kapital': 61,
                'capital': 61,
                'communist manifesto': 61,
                'manifesto': 61,
                'wage labour and capital': 8002,
                'wage labor': 8002,
            },
            'marx': {
                'das kapital': 61,
                'capital': 61,
                'communist manifesto': 61,
                'manifesto': 61,
                'wage labour and capital': 8002,
            },
            'walt whitman': {
                'leaves of grass': 1322,
                'democratic vistas': 8813,
                'specimen days': 8892,
            },
            'whitman': {
                'leaves of grass': 1322,
                'democratic vistas': 8813,
                'specimen days': 8892,
            },
            'charles baudelaire': {
                'flowers of evil': 36098,
                'paris spleen': 57346,
            },
            'baudelaire': {
                'flowers of evil': 36098,
                'paris spleen': 57346,
            },
            'jane austen': {
                'pride and prejudice': 1342,
                'emma': 158,
                'sense and sensibility': 161,
                'mansfield park': 141,
                'northanger abbey': 121,
                'persuasion': 105,
            },
            'austen': {
                'pride and prejudice': 1342,
                'emma': 158,
                'sense and sensibility': 161,
            },
            'homer': {
                'odyssey': 1727,
                'iliad': 6130,
            },
            'marcus aurelius': {
                'meditations': 2680,
            },
            'aurelius': {
                'meditations': 2680,
            },
            'plato': {
                'republic': 1497,
                'apology': 1656,
                'symposium': 1600,
            },
            'friedrich nietzsche': {
                'beyond good and evil': 4363,
                'thus spoke zarathustra': 1998,
                'genealogy of morals': 52319,
            },
            'nietzsche': {
                'beyond good and evil': 4363,
                'thus spoke zarathustra': 1998,
                'zarathustra': 1998,
            },
            'niccolò machiavelli': {
                'prince': 1232,
            },
            'machiavelli': {
                'prince': 1232,
            },
            'sun tzu': {
                'art of war': 132,
            },
            'tzu': {
                'art of war': 132,
            },
        }

        # Check if we have this author
        if author_norm in known_books:
            author_books = known_books[author_norm]

            # Try to match the title
            for known_title, gutenberg_id in author_books.items():
                if (known_title in title_norm or
                    title_norm in known_title or
                    self._title_similarity(title_norm, known_title) > 0.7):
                    logger.debug(f"Manual lookup found: {title} -> {gutenberg_id}")
                    return {
                        'id': gutenberg_id,
                        'title': title,
                        'authors': [author],
                        'formats': {},
                    }

        return None

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Simple word-based similarity score"""
        words1 = set(re.findall(r'\w+', title1.lower()))
        words2 = set(re.findall(r'\w+', title2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def download_text(self, gutenberg_id: int, output_path: Path) -> bool:
        """
        Download a book's text from Project Gutenberg

        Args:
            gutenberg_id: The Gutenberg book ID
            output_path: Where to save the file

        Returns:
            True if successful, False otherwise
        """
        # Try wget first (it often works better than requests for Gutenberg)
        if self._download_with_wget(gutenberg_id, output_path):
            return True

        # Fall back to requests-based download
        return self._download_with_requests(gutenberg_id, output_path)

    def _download_with_wget(self, gutenberg_id: int, output_path: Path) -> bool:
        """Try downloading using wget command"""
        import subprocess

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try different URL patterns
        urls = [
            f"{self.GUTENBERG_MIRROR}/files/{gutenberg_id}/{gutenberg_id}-0.txt",
            f"{self.GUTENBERG_MIRROR}/files/{gutenberg_id}/{gutenberg_id}.txt",
            f"{self.GUTENBERG_MIRROR}/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
        ]

        for url in urls:
            try:
                logger.debug(f"Trying wget download from: {url}")
                result = subprocess.run(
                    ['wget', '-q', '-O', str(output_path), url],
                    timeout=30,
                    capture_output=True
                )

                if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 100:
                    logger.info(f"Downloaded: {output_path}")
                    return True
                else:
                    # Clean up failed download
                    if output_path.exists():
                        output_path.unlink()

            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                logger.debug(f"wget download failed: {e}")
                if output_path.exists():
                    output_path.unlink()
                continue

        return False

    def _download_with_requests(self, gutenberg_id: int, output_path: Path) -> bool:
        """Fallback download using requests library"""
        # Try different text format URLs and mirrors
        urls = [
            # Primary Gutenberg.org URLs
            f"{self.GUTENBERG_MIRROR}/files/{gutenberg_id}/{gutenberg_id}-0.txt",
            f"{self.GUTENBERG_MIRROR}/files/{gutenberg_id}/{gutenberg_id}.txt",
            f"{self.GUTENBERG_MIRROR}/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
            f"{self.GUTENBERG_MIRROR}/ebooks/{gutenberg_id}.txt.utf-8",
        ]

        for url in urls:
            try:
                logger.debug(f"Trying requests download from: {url}")
                response = self.session.get(url, timeout=30, allow_redirects=True)

                if response.status_code == 200 and len(response.text) > 100:
                    # Ensure output directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Try to detect encoding and write
                    try:
                        # Most Gutenberg texts are UTF-8
                        output_path.write_text(response.text, encoding='utf-8')
                    except UnicodeDecodeError:
                        # Fallback to writing bytes
                        output_path.write_bytes(response.content)

                    logger.info(f"Downloaded: {output_path}")
                    return True
                elif response.status_code == 200:
                    logger.debug(f"Response too short ({len(response.text)} chars), trying next URL")

            except Exception as e:
                logger.debug(f"Failed to download from {url}: {e}")
                continue

        logger.warning(f"Could not download Gutenberg ID {gutenberg_id} from any source")
        return False


class LibraryThingParser:
    """Parses LibraryThing export files (both JSON and TSV formats)"""

    def parse(self, file_path: Path) -> List[Book]:
        """
        Parse a LibraryThing export file (auto-detects JSON or TSV format)

        Args:
            file_path: Path to the LibraryThing export file

        Returns:
            List of Book objects
        """
        # Detect format by file extension or content
        if file_path.suffix.lower() == '.json':
            return self._parse_json(file_path)
        elif file_path.suffix.lower() in ['.tsv', '.txt']:
            return self._parse_tsv(file_path)
        else:
            # Try to auto-detect by reading first few bytes
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_char = f.read(1)
                    if first_char == '{' or first_char == '[':
                        return self._parse_json(file_path)
                    else:
                        return self._parse_tsv(file_path)
            except Exception:
                logger.warning("Could not auto-detect format, assuming TSV")
                return self._parse_tsv(file_path)

    def _parse_json(self, file_path: Path) -> List[Book]:
        """Parse LibraryThing JSON export format"""
        books = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # JSON format is a dictionary with book IDs as keys
            for book_id, book_data in data.items():
                # Extract title
                title = book_data.get('title', '')
                if not title:
                    continue

                # Extract author (prefer "fl" format: "First Last")
                author = ''
                if 'authors' in book_data and book_data['authors']:
                    # Get first author - handle different data structures
                    first_author = book_data['authors'][0]
                    if isinstance(first_author, dict):
                        # Dictionary format: {"fl": "First Last", "lf": "Last, First"}
                        author = first_author.get('fl', '') or first_author.get('lf', '')
                    elif isinstance(first_author, list):
                        # List format: take first element or join all
                        author = first_author[0] if first_author else ''
                    elif isinstance(first_author, str):
                        # String format: use directly
                        author = first_author
                    else:
                        # Unknown format: convert to string
                        author = str(first_author)
                elif 'primaryauthor' in book_data:
                    author = book_data['primaryauthor']

                if not author:
                    author = 'Unknown Author'

                # Clean author name
                author = self._clean_author_name(author)

                # Extract ISBN
                isbn = None
                if 'originalisbn' in book_data:
                    isbn = book_data['originalisbn']
                elif 'isbn' in book_data:
                    isbn_data = book_data['isbn']
                    if isinstance(isbn_data, dict):
                        # Get first ISBN from dict
                        isbn = next(iter(isbn_data.values()), None)
                    elif isinstance(isbn_data, list):
                        isbn = isbn_data[0] if isbn_data else None
                    else:
                        isbn = str(isbn_data)

                # Extract publication date
                pub_date = book_data.get('date', '')

                book = Book(
                    title=title.strip(),
                    author=author.strip(),
                    author_normalized=self._normalize_author_name(author),
                    isbn=isbn.strip() if isbn else None,
                    publication_date=pub_date.strip() if pub_date else None,
                )

                books.append(book)

        except Exception as e:
            logger.error(f"Error parsing LibraryThing JSON file: {e}")
            raise

        logger.info(f"Parsed {len(books)} books from LibraryThing JSON export")
        return books

    def _parse_tsv(self, file_path: Path) -> List[Book]:
        """Parse LibraryThing TSV export format"""
        books = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # LibraryThing exports are tab-delimited
                reader = csv.DictReader(f, delimiter='\t')

                for row in reader:
                    # Extract author (prefer "AUTHOR (first, last)" format)
                    author = (
                        row.get('AUTHOR (first, last)', '') or
                        row.get('AUTHOR (last, first)', '') or
                        row.get('Author', '') or
                        'Unknown Author'
                    )

                    # Clean author name
                    author = self._clean_author_name(author)

                    # Extract title
                    title = row.get('TITLE', '') or row.get('Title', '')

                    if not title:
                        continue

                    # Extract other fields
                    isbn = row.get('ISBNs', '') or row.get('ISBN', '')
                    pub_date = row.get('PUBLICATION DATE', '') or row.get('Publication Date', '')

                    book = Book(
                        title=title.strip(),
                        author=author.strip(),
                        author_normalized=self._normalize_author_name(author),
                        isbn=isbn.strip() if isbn else None,
                        publication_date=pub_date.strip() if pub_date else None,
                    )

                    books.append(book)

        except Exception as e:
            logger.error(f"Error parsing LibraryThing TSV file: {e}")
            raise

        logger.info(f"Parsed {len(books)} books from LibraryThing TSV export")
        return books

    def _clean_author_name(self, author: str) -> str:
        """Clean author name by removing extra info in parentheses, dates, etc."""
        # Remove anything in parentheses
        author = re.sub(r'\([^)]*\)', '', author)
        # Remove dates like "1818-1883"
        author = re.sub(r'\d{4}-\d{4}', '', author)
        # Remove extra whitespace
        author = ' '.join(author.split())
        return author.strip()

    def _normalize_author_name(self, author: str) -> str:
        """
        Normalize author name for use as directory name

        Examples:
            "Karl Marx" -> "marx"
            "Walt Whitman" -> "whitman"
            "Charles Baudelaire" -> "baudelaire"
        """
        # Take the last name (assuming Western naming convention)
        parts = author.strip().split()
        if not parts:
            return "unknown"

        # Use last name
        last_name = parts[-1]

        # Convert to lowercase, remove special characters
        normalized = re.sub(r'[^a-z0-9]', '', last_name.lower())

        return normalized if normalized else "unknown"


class TextAcquisitionPipeline:
    """Main pipeline for acquiring texts from LibraryThing export"""

    def __init__(self, output_dir: Path = Path("data/raw")):
        self.output_dir = output_dir
        self.searcher = GutenbergSearcher()
        self.parser = LibraryThingParser()
        self.reports: Dict[str, AuthorReport] = {}

    def process(
        self,
        input_file: Path,
        author_filter: Optional[Set[str]] = None,
        max_books_per_author: Optional[int] = None,
    ) -> Dict[str, AuthorReport]:
        """
        Process a LibraryThing export file

        Args:
            input_file: Path to LibraryThing TSV export
            author_filter: Optional set of author names to filter by
            max_books_per_author: Optional limit on books per author

        Returns:
            Dictionary mapping author IDs to AuthorReport objects
        """
        logger.info(f"Processing LibraryThing export: {input_file}")

        # Parse the export file
        books = self.parser.parse(input_file)

        # Group by author
        books_by_author = defaultdict(list)
        for book in books:
            books_by_author[book.author_normalized].append(book)

        # Filter authors if requested
        if author_filter:
            author_filter_normalized = {
                self.parser._normalize_author_name(a) for a in author_filter
            }
            books_by_author = {
                k: v for k, v in books_by_author.items()
                if k in author_filter_normalized
            }

        logger.info(f"Found {len(books_by_author)} unique authors")

        # Process each author
        for author_id, author_books in books_by_author.items():
            logger.info(f"\nProcessing author: {author_books[0].author} ({author_id})")

            # Limit books if requested
            if max_books_per_author:
                author_books = author_books[:max_books_per_author]

            report = self._process_author(author_id, author_books)
            self.reports[author_id] = report

        return self.reports

    def _process_author(self, author_id: str, books: List[Book]) -> AuthorReport:
        """Process all books for a single author"""
        report = AuthorReport(
            author=books[0].author,
            author_id=author_id,
            total_books=len(books),
            books=books,
        )

        # Create author directory
        author_dir = self.output_dir / author_id
        author_dir.mkdir(parents=True, exist_ok=True)

        for book in books:
            logger.info(f"  Searching: {book.title}")

            # Search for the book on Gutenberg
            result = self.searcher.search_book(book.title, book.author)

            if result:
                book.gutenberg_id = str(result['id'])
                book.gutenberg_url = f"https://www.gutenberg.org/ebooks/{result['id']}"
                report.books_found += 1

                logger.info(f"    Found: Gutenberg ID {book.gutenberg_id}")

                # Create filename from title
                filename = self._create_filename(book.title)
                output_path = author_dir / filename

                # Download the text
                if self.searcher.download_text(result['id'], output_path):
                    book.downloaded = True
                    book.download_path = str(output_path)
                    report.books_downloaded += 1
                    logger.info(f"    Downloaded to: {output_path}")
                else:
                    book.error = "Download failed"
                    report.books_failed += 1
                    logger.warning(f"    Failed to download")

                # Rate limiting - be nice to Gutenberg
                time.sleep(1)
            else:
                book.error = "Not found on Gutenberg"
                report.books_failed += 1
                logger.info(f"    Not found on Gutenberg")

        return report

    def _create_filename(self, title: str) -> str:
        """
        Create a safe filename from a book title

        Example: "Das Kapital, Vol. 1" -> "das_kapital_vol_1.txt"
        """
        # Remove special characters, convert to lowercase
        filename = re.sub(r'[^\w\s-]', '', title.lower())
        # Replace spaces and dashes with underscores
        filename = re.sub(r'[-\s]+', '_', filename)
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        # Limit length
        filename = filename[:100]
        # Add extension
        return f"{filename}.txt"

    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """
        Generate a report of acquisition results

        Args:
            output_file: Optional path to save the report

        Returns:
            Report as a string
        """
        report_lines = [
            "=" * 80,
            "Agora LibraryThing Text Acquisition Report",
            "=" * 80,
            "",
        ]

        # Summary statistics
        total_authors = len(self.reports)
        total_books = sum(r.total_books for r in self.reports.values())
        total_found = sum(r.books_found for r in self.reports.values())
        total_downloaded = sum(r.books_downloaded for r in self.reports.values())
        total_failed = sum(r.books_failed for r in self.reports.values())

        report_lines.extend([
            "SUMMARY",
            "-" * 80,
            f"Total authors processed: {total_authors}",
            f"Total books in library: {total_books}",
            f"Books found on Gutenberg: {total_found} ({total_found/total_books*100:.1f}%)" if total_books > 0 else "Books found: 0",
            f"Books downloaded: {total_downloaded} ({total_downloaded/total_books*100:.1f}%)" if total_books > 0 else "Books downloaded: 0",
            f"Books failed: {total_failed}",
            "",
        ])

        # Authors with texts found
        authors_with_texts = [r for r in self.reports.values() if r.books_downloaded > 0]
        authors_without_texts = [r for r in self.reports.values() if r.books_downloaded == 0]

        if authors_with_texts:
            report_lines.extend([
                "AUTHORS WITH TEXTS DISCOVERED",
                "-" * 80,
            ])

            for report in sorted(authors_with_texts, key=lambda r: r.author):
                report_lines.append(
                    f"✓ {report.author} ({report.author_id}): "
                    f"{report.books_downloaded}/{report.total_books} books downloaded"
                )

                # List downloaded books
                for book in report.books:
                    if book.downloaded:
                        report_lines.append(f"    - {book.title}")

            report_lines.append("")

        if authors_without_texts:
            report_lines.extend([
                "AUTHORS WITHOUT TEXTS DISCOVERED",
                "-" * 80,
            ])

            for report in sorted(authors_without_texts, key=lambda r: r.author):
                report_lines.append(
                    f"✗ {report.author} ({report.author_id}): "
                    f"0/{report.total_books} books found"
                )

            report_lines.append("")

        # Next steps
        report_lines.extend([
            "NEXT STEPS",
            "-" * 80,
            "1. Clean the downloaded texts:",
            "   python scripts/clean_texts.py",
            "",
            "2. Create author YAML configs in config/authors/ for each author",
            "",
            "3. Ingest each author's texts:",
        ])

        for report in sorted(authors_with_texts, key=lambda r: r.author_id):
            report_lines.append(
                f"   python scripts/ingest_author.py --author {report.author_id}"
            )

        report_lines.extend([
            "",
            "4. Create expertise profiles:",
            "   python scripts/create_expertise_profiles.py",
            "",
            "=" * 80,
        ])

        report_text = "\n".join(report_lines)

        # Save to file if requested
        if output_file:
            output_file.write_text(report_text, encoding='utf-8')
            logger.info(f"Report saved to: {output_file}")

        return report_text

    def save_json_report(self, output_file: Path):
        """Save detailed report as JSON"""
        data = {
            'summary': {
                'total_authors': len(self.reports),
                'total_books': sum(r.total_books for r in self.reports.values()),
                'books_found': sum(r.books_found for r in self.reports.values()),
                'books_downloaded': sum(r.books_downloaded for r in self.reports.values()),
                'books_failed': sum(r.books_failed for r in self.reports.values()),
            },
            'authors': {
                author_id: {
                    'author': report.author,
                    'author_id': report.author_id,
                    'total_books': report.total_books,
                    'books_found': report.books_found,
                    'books_downloaded': report.books_downloaded,
                    'books_failed': report.books_failed,
                    'books': [
                        {
                            'title': book.title,
                            'gutenberg_id': book.gutenberg_id,
                            'gutenberg_url': book.gutenberg_url,
                            'downloaded': book.downloaded,
                            'download_path': book.download_path,
                            'error': book.error,
                        }
                        for book in report.books
                    ]
                }
                for author_id, report in self.reports.items()
            }
        }

        output_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
        logger.info(f"JSON report saved to: {output_file}")

    def generate_download_script(self, output_file: Path):
        """
        Generate a shell script for manual downloading
        Useful when automated downloads fail due to network/access issues
        """
        script_lines = [
            "#!/bin/bash",
            "# ============================================",
            "# Agora LibraryThing Text Download Script",
            "# Generated automatically - downloads texts from Project Gutenberg",
            "# ============================================",
            "",
            "set -e",
            "",
            "echo \"📚 Starting Text Download\"",
            "echo \"============================================\"",
            "echo \"\"",
            "",
        ]

        # Add downloads for each author
        for author_id, report in sorted(self.reports.items()):
            if report.books_found == 0:
                continue

            script_lines.extend([
                f"# ============================================",
                f"# {report.author} ({author_id})",
                f"# ============================================",
                f"echo \"📖 Downloading texts for {report.author}...\"",
                f"mkdir -p {self.output_dir}/{author_id}",
                "",
            ])

            for book in report.books:
                if not book.gutenberg_id:
                    continue

                filename = self._create_filename(book.title)
                output_path = f"{self.output_dir}/{author_id}/{filename}"

                # Try multiple URL patterns
                script_lines.extend([
                    f"# {book.title}",
                    f"if [ ! -f \"{output_path}\" ]; then",
                    f"    echo \"  Downloading: {book.title}...\"",
                    f"    wget -q --show-progress \\",
                    f"        https://www.gutenberg.org/files/{book.gutenberg_id}/{book.gutenberg_id}-0.txt \\",
                    f"        -O \"{output_path}\" 2>/dev/null || \\",
                    f"    wget -q --show-progress \\",
                    f"        https://www.gutenberg.org/files/{book.gutenberg_id}/{book.gutenberg_id}.txt \\",
                    f"        -O \"{output_path}\" 2>/dev/null || \\",
                    f"    wget -q --show-progress \\",
                    f"        https://www.gutenberg.org/cache/epub/{book.gutenberg_id}/pg{book.gutenberg_id}.txt \\",
                    f"        -O \"{output_path}\" 2>/dev/null || \\",
                    f"    echo \"    ⚠️  Failed to download {book.title}\"",
                    f"    ",
                    f"    if [ -f \"{output_path}\" ] && [ $(wc -c < \"{output_path}\") -gt 100 ]; then",
                    f"        echo \"    ✅ Downloaded: {book.title}\"",
                    f"    else",
                    f"        rm -f \"{output_path}\"",
                    f"    fi",
                    f"else",
                    f"    echo \"  ✅ {book.title} already exists\"",
                    f"fi",
                    "",
                ])

            script_lines.append("")

        # Add summary
        script_lines.extend([
            "# ============================================",
            "# Summary",
            "# ============================================",
            "echo \"\"",
            "echo \"============================================\"",
            "echo \"✅ Download Script Complete\"",
            "echo \"============================================\"",
            "echo \"\"",
            "echo \"Next steps:\"",
            "echo \"  1. Review downloaded files in data/raw/\"",
            "echo \"  2. Clean texts: python scripts/clean_texts.py\"",
            "echo \"  3. Create author YAML configs in config/authors/\"",
            "echo \"  4. Ingest authors: python scripts/ingest_author.py --author <author_id>\"",
            "echo \"\"",
        ])

        script_text = "\n".join(script_lines)
        output_file.write_text(script_text, encoding='utf-8')
        output_file.chmod(0o755)  # Make executable
        logger.info(f"Download script saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Acquire texts from LibraryThing export for Agora ingest'
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Path to LibraryThing TSV export file'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/raw'),
        help='Output directory for downloaded texts (default: data/raw)'
    )
    parser.add_argument(
        '--author-filter',
        type=str,
        help='Comma-separated list of authors to process (e.g., "Marx,Whitman")'
    )
    parser.add_argument(
        '--max-books-per-author',
        type=int,
        help='Maximum number of books to process per author'
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=Path('acquisition_report.txt'),
        help='Output path for text report (default: acquisition_report.txt)'
    )
    parser.add_argument(
        '--json-report',
        type=Path,
        default=Path('acquisition_report.json'),
        help='Output path for JSON report (default: acquisition_report.json)'
    )
    parser.add_argument(
        '--download-script',
        type=Path,
        default=Path('download_texts.sh'),
        help='Output path for download shell script (default: download_texts.sh)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse author filter
    author_filter = None
    if args.author_filter:
        author_filter = set(a.strip() for a in args.author_filter.split(','))

    # Run the pipeline
    pipeline = TextAcquisitionPipeline(output_dir=args.output_dir)

    try:
        pipeline.process(
            input_file=args.input,
            author_filter=author_filter,
            max_books_per_author=args.max_books_per_author,
        )

        # Generate reports
        report_text = pipeline.generate_report(output_file=args.report)
        print("\n" + report_text)

        pipeline.save_json_report(args.json_report)

        # Generate download script for manual downloading
        pipeline.generate_download_script(args.download_script)

        print(f"\n📝 Generated download script: {args.download_script}")
        print(f"   Run it with: ./{args.download_script}")

        logger.info("\n✅ Acquisition complete!")

    except Exception as e:
        logger.error(f"Error during acquisition: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
