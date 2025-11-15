#!/usr/bin/env python3
"""
Agora LibraryThing Text Acquisition - Agentic Architecture
===========================================================

Multi-agent system for acquiring author texts where each author operates
as an autonomous agent with its own search strategy and decision-making.

Key Concepts:
- Each author is an autonomous agent
- Source specialists (Gutenberg, Archive.org, etc.) are expert agents
- Agents run in parallel and share knowledge
- Intelligent strategy selection based on author profile
- Collaborative learning from successes and failures
"""

import argparse
import asyncio
import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import quote_plus
import aiohttp
from aiohttp import ClientSession, ClientTimeout

# Import from the original script
import sys
sys.path.insert(0, str(Path(__file__).parent))
from acquire_from_librarything import (
    Book, AuthorReport, LibraryThingParser
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Era(Enum):
    """Historical eras for author classification"""
    ANCIENT = "ancient"  # Before 500 CE
    MEDIEVAL = "medieval"  # 500-1500 CE
    EARLY_MODERN = "early_modern"  # 1500-1800
    MODERN = "modern"  # 1800-1928
    CONTEMPORARY = "contemporary"  # After 1928


@dataclass
class AuthorProfile:
    """Profile of an author for intelligent strategy selection"""
    name: str
    era: Era
    estimated_death_year: Optional[int] = None
    primary_language: str = "english"
    likely_public_domain: bool = True
    genres: Set[str] = field(default_factory=set)

    @classmethod
    def infer_from_books(cls, author_name: str, books: List[Book]) -> 'AuthorProfile':
        """Infer author profile from their books"""
        # Extract publication dates
        pub_dates = []
        for book in books:
            if book.publication_date:
                # Try to extract year
                match = re.search(r'(\d{4})', book.publication_date)
                if match:
                    year = int(match.group(1))
                    if 0 < year < 2100:  # Sanity check
                        pub_dates.append(year)

        # Determine era and public domain status
        if pub_dates:
            earliest = min(pub_dates)
            latest = max(pub_dates)

            # Estimate death year (assume author was at least 20 when first published)
            estimated_death = latest + 40  # Rough estimate

            # Determine era
            if earliest < 500:
                era = Era.ANCIENT
            elif earliest < 1500:
                era = Era.MEDIEVAL
            elif earliest < 1800:
                era = Era.EARLY_MODERN
            elif latest < 1928:
                era = Era.MODERN
            else:
                era = Era.CONTEMPORARY

            # Public domain check (rough: pre-1928 in US)
            likely_public_domain = latest < 1928

        else:
            # No date info, assume older is safer
            era = Era.MODERN
            estimated_death = None
            likely_public_domain = True

        return cls(
            name=author_name,
            era=era,
            estimated_death_year=estimated_death,
            likely_public_domain=likely_public_domain,
        )


@dataclass
class SearchResult:
    """Result from a source agent search"""
    source: str
    book_id: str
    title: str
    author: str
    url: str
    download_urls: List[str]
    confidence: float  # 0.0-1.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Message between agents"""
    from_agent: str
    to_agent: str
    message_type: str  # "tip", "warning", "request", "response"
    content: Dict


class SharedKnowledgeBase:
    """Knowledge shared across all agents"""

    def __init__(self):
        self.successful_searches: Dict[str, List[SearchResult]] = defaultdict(list)
        self.failed_searches: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.source_performance: Dict[str, Dict] = defaultdict(
            lambda: {"searches": 0, "successes": 0, "downloads": 0, "failures": 0}
        )
        self.best_strategies: Dict[Era, List[str]] = {}
        self.rate_limits: Dict[str, float] = {}  # source -> timestamp when available

    def record_search_success(self, source: str, author_era: Era, result: SearchResult):
        """Record successful search"""
        key = f"{author_era.value}:{source}"
        self.successful_searches[key].append(result)
        self.source_performance[source]["searches"] += 1
        self.source_performance[source]["successes"] += 1

    def record_search_failure(self, source: str, author: str, title: str):
        """Record failed search"""
        key = f"{author}:{source}"
        self.failed_searches[key].append((author, title))
        self.source_performance[source]["searches"] += 1

    def record_download_success(self, source: str):
        """Record successful download"""
        self.source_performance[source]["downloads"] += 1

    def record_download_failure(self, source: str):
        """Record failed download"""
        self.source_performance[source]["failures"] += 1

    def get_recommended_sources(self, profile: AuthorProfile) -> List[str]:
        """Get recommended sources based on profile and history"""
        # Default strategy by era
        defaults = {
            Era.ANCIENT: ["wikisource", "perseus", "gutenberg"],
            Era.MEDIEVAL: ["wikisource", "gutenberg"],
            Era.EARLY_MODERN: ["gutenberg", "wikisource"],
            Era.MODERN: ["gutenberg", "archive"],
            Era.CONTEMPORARY: ["archive", "openlibrary"],
        }

        strategy = defaults.get(profile.era, ["gutenberg", "archive"])

        # Filter out rate-limited sources
        now = time.time()
        available = [
            s for s in strategy
            if s not in self.rate_limits or self.rate_limits[s] < now
        ]

        return available or strategy  # Return all if none available

    def set_rate_limit(self, source: str, duration_seconds: int = 60):
        """Mark a source as rate-limited"""
        self.rate_limits[source] = time.time() + duration_seconds
        logger.warning(f"Source {source} rate-limited for {duration_seconds}s")

    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        return {
            "total_successful_searches": sum(
                len(results) for results in self.successful_searches.values()
            ),
            "total_failed_searches": sum(
                len(failures) for failures in self.failed_searches.values()
            ),
            "source_performance": dict(self.source_performance),
        }


class SourceAgent:
    """Base class for source-specific agents"""

    name: str = "base"
    expertise: List[str] = []

    def __init__(self, knowledge_base: SharedKnowledgeBase):
        self.knowledge = knowledge_base
        self.session: Optional[ClientSession] = None

    async def initialize(self):
        """Initialize async resources"""
        timeout = ClientTimeout(total=30)
        self.session = ClientSession(timeout=timeout)

    async def cleanup(self):
        """Cleanup async resources"""
        if self.session:
            await self.session.close()

    async def search(self, author: str, title: str, profile: AuthorProfile) -> Optional[SearchResult]:
        """Search for a book - to be implemented by subclasses"""
        raise NotImplementedError

    async def download(self, result: SearchResult, output_path: Path) -> bool:
        """Download a book - to be implemented by subclasses"""
        raise NotImplementedError

    def recommend_for(self, profile: AuthorProfile) -> Dict[str, float]:
        """Return recommendation for this author profile"""
        return {"confidence": 0.5, "priority": 5}


class GutenbergAgent(SourceAgent):
    """Agent specialized in Project Gutenberg"""

    name = "gutenberg"
    expertise = ["pre-1928", "english", "classics", "philosophy"]

    GUTENBERG_API = "https://gutendex.com/books"
    GUTENBERG_MIRROR = "https://www.gutenberg.org"

    def __init__(self, knowledge_base: SharedKnowledgeBase):
        super().__init__(knowledge_base)
        self.cache: Dict[str, Optional[SearchResult]] = {}

    def recommend_for(self, profile: AuthorProfile) -> Dict[str, float]:
        """High confidence for pre-1928 authors"""
        if profile.era in [Era.ANCIENT, Era.MEDIEVAL, Era.EARLY_MODERN, Era.MODERN]:
            return {"confidence": 0.9, "priority": 1}
        return {"confidence": 0.2, "priority": 4}

    async def search(self, author: str, title: str, profile: AuthorProfile) -> Optional[SearchResult]:
        """Search Gutenberg catalog"""
        cache_key = f"{author}:{title}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # Try API first
            result = await self._search_api(author, title)
            if result:
                self.cache[cache_key] = result
                self.knowledge.record_search_success(self.name, profile.era, result)
                return result

            # Fallback to manual lookup
            result = self._manual_lookup(author, title)
            if result:
                self.cache[cache_key] = result
                self.knowledge.record_search_success(self.name, profile.era, result)
                return result

            self.knowledge.record_search_failure(self.name, author, title)
            return None

        except Exception as e:
            logger.debug(f"Gutenberg search error for {title}: {e}")
            self.knowledge.record_search_failure(self.name, author, title)
            return None

    async def _search_api(self, author: str, title: str) -> Optional[SearchResult]:
        """Search using Gutendex API"""
        if not self.session:
            return None

        try:
            params = {"search": f"{author} {title}"}
            async with self.session.get(self.GUTENBERG_API, params=params) as resp:
                if resp.status == 403:
                    self.knowledge.set_rate_limit(self.name, 300)
                    return None

                if resp.status != 200:
                    return None

                data = await resp.json()
                if data.get('count', 0) > 0:
                    book = data['results'][0]
                    book_id = str(book['id'])

                    return SearchResult(
                        source=self.name,
                        book_id=book_id,
                        title=book['title'],
                        author=author,
                        url=f"{self.GUTENBERG_MIRROR}/ebooks/{book_id}",
                        download_urls=self._build_download_urls(book_id),
                        confidence=0.8,
                        metadata={"api_result": True}
                    )

        except Exception as e:
            logger.debug(f"API search failed: {e}")

        return None

    def _manual_lookup(self, author: str, title: str) -> Optional[SearchResult]:
        """Manual lookup from known books database"""
        # Same database as original script
        known_books = {
            'karl marx': {'das kapital': 61, 'capital': 61, 'communist manifesto': 61},
            'marx': {'das kapital': 61, 'capital': 61, 'communist manifesto': 61},
            'walt whitman': {'leaves of grass': 1322, 'democratic vistas': 8813},
            'whitman': {'leaves of grass': 1322, 'democratic vistas': 8813},
            'jane austen': {'pride and prejudice': 1342, 'emma': 158, 'sense and sensibility': 161},
            'austen': {'pride and prejudice': 1342, 'emma': 158},
            'homer': {'odyssey': 1727, 'iliad': 6130},
            'marcus aurelius': {'meditations': 2680},
            'aurelius': {'meditations': 2680},
            'plato': {'republic': 1497, 'apology': 1656, 'symposium': 1600},
            'friedrich nietzsche': {'beyond good and evil': 4363, 'thus spoke zarathustra': 1998},
            'nietzsche': {'beyond good and evil': 4363, 'zarathustra': 1998},
        }

        author_norm = author.lower().strip()
        title_norm = title.lower().strip()

        if author_norm in known_books:
            for known_title, gutenberg_id in known_books[author_norm].items():
                if known_title in title_norm or title_norm in known_title:
                    book_id = str(gutenberg_id)
                    return SearchResult(
                        source=self.name,
                        book_id=book_id,
                        title=title,
                        author=author,
                        url=f"{self.GUTENBERG_MIRROR}/ebooks/{book_id}",
                        download_urls=self._build_download_urls(book_id),
                        confidence=0.9,
                        metadata={"manual_lookup": True}
                    )

        return None

    def _build_download_urls(self, book_id: str) -> List[str]:
        """Build list of potential download URLs"""
        return [
            f"{self.GUTENBERG_MIRROR}/files/{book_id}/{book_id}-0.txt",
            f"{self.GUTENBERG_MIRROR}/files/{book_id}/{book_id}.txt",
            f"{self.GUTENBERG_MIRROR}/cache/epub/{book_id}/pg{book_id}.txt",
        ]

    async def download(self, result: SearchResult, output_path: Path) -> bool:
        """Download text from Gutenberg"""
        if not self.session:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)

        for url in result.download_urls:
            try:
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        if len(content) > 100:
                            output_path.write_text(content, encoding='utf-8')
                            logger.info(f"Downloaded: {output_path}")
                            self.knowledge.record_download_success(self.name)
                            return True

            except Exception as e:
                logger.debug(f"Download failed from {url}: {e}")
                continue

        self.knowledge.record_download_failure(self.name)
        return False


class InternetArchiveAgent(SourceAgent):
    """Agent for Internet Archive (stub implementation)"""

    name = "archive"
    expertise = ["all_eras", "scanned_books", "rare"]

    def recommend_for(self, profile: AuthorProfile) -> Dict[str, float]:
        """Moderate confidence for all eras"""
        return {"confidence": 0.6, "priority": 2}

    async def search(self, author: str, title: str, profile: AuthorProfile) -> Optional[SearchResult]:
        """Search Internet Archive - stub for now"""
        logger.debug(f"Archive search for {title} by {author} (not yet implemented)")
        return None

    async def download(self, result: SearchResult, output_path: Path) -> bool:
        """Download from Archive - stub for now"""
        return False


class WikisourceAgent(SourceAgent):
    """Agent for Wikisource (stub implementation)"""

    name = "wikisource"
    expertise = ["ancient", "foreign_language", "scholarly"]

    def recommend_for(self, profile: AuthorProfile) -> Dict[str, float]:
        """High confidence for ancient/medieval works"""
        if profile.era in [Era.ANCIENT, Era.MEDIEVAL]:
            return {"confidence": 0.85, "priority": 1}
        return {"confidence": 0.4, "priority": 3}

    async def search(self, author: str, title: str, profile: AuthorProfile) -> Optional[SearchResult]:
        """Search Wikisource - stub for now"""
        logger.debug(f"Wikisource search for {title} by {author} (not yet implemented)")
        return None

    async def download(self, result: SearchResult, output_path: Path) -> bool:
        """Download from Wikisource - stub for now"""
        return False


class AuthorAgent:
    """Autonomous agent representing an author's acquisition task"""

    def __init__(
        self,
        author_name: str,
        author_id: str,
        books: List[Book],
        profile: AuthorProfile,
        source_agents: List[SourceAgent],
        knowledge: SharedKnowledgeBase,
        output_dir: Path
    ):
        self.name = author_name
        self.author_id = author_id
        self.books = books
        self.profile = profile
        self.source_agents = source_agents
        self.knowledge = knowledge
        self.output_dir = output_dir

        # Agent state
        self.findings: List[SearchResult] = []
        self.downloads: List[Book] = []
        self.failures: List[Book] = []
        self.strategy: List[str] = []
        self.messages: List[AgentMessage] = []

    def _determine_strategy(self) -> List[str]:
        """Determine search strategy based on profile and knowledge"""
        # Get knowledge-based recommendations
        recommended = self.knowledge.get_recommended_sources(self.profile)

        # Rank source agents by their confidence for this profile
        rankings = []
        for agent in self.source_agents:
            rec = agent.recommend_for(self.profile)
            rankings.append((agent.name, rec['confidence'], rec['priority']))

        # Sort by confidence (desc) then priority (asc)
        rankings.sort(key=lambda x: (-x[1], x[2]))

        # Combine with knowledge base recommendations
        strategy = []
        for source_name, _, _ in rankings:
            if source_name in recommended:
                strategy.append(source_name)

        # Add others that weren't recommended but might work
        for source_name, _, _ in rankings:
            if source_name not in strategy:
                strategy.append(source_name)

        return strategy

    async def acquire_works(self) -> AuthorReport:
        """Main autonomous acquisition loop"""
        logger.info(f"Agent {self.name} starting acquisition with strategy: {self.strategy}")

        # Determine strategy
        self.strategy = self._determine_strategy()

        # Check if likely not public domain
        if not self.profile.likely_public_domain:
            logger.warning(
                f"Agent {self.name}: Works likely NOT public domain "
                f"(era: {self.profile.era.value})"
            )
            # Still try, but with low expectations

        # Search for each book
        for book in self.books:
            result = await self._intelligent_search(book)
            if result:
                # Try to download
                success = await self._download_book(result, book)
                if success:
                    self.downloads.append(book)
                else:
                    self.failures.append(book)
            else:
                self.failures.append(book)

        return self._generate_report()

    async def _intelligent_search(self, book: Book) -> Optional[SearchResult]:
        """Search using strategy, adapting as needed"""
        for source_name in self.strategy:
            # Find the source agent
            agent = next((a for a in self.source_agents if a.name == source_name), None)
            if not agent:
                continue

            logger.debug(f"Agent {self.name}: Trying {source_name} for {book.title}")

            result = await agent.search(book.author, book.title, self.profile)

            if result and self._is_good_match(result, book):
                logger.info(
                    f"Agent {self.name}: Found {book.title} on {source_name} "
                    f"(confidence: {result.confidence:.2f})"
                )
                self.findings.append(result)
                return result

        logger.info(f"Agent {self.name}: Could not find {book.title} on any source")
        return None

    def _is_good_match(self, result: SearchResult, book: Book) -> bool:
        """Assess if search result is a good match"""
        # Could add more sophisticated matching here
        # For now, trust the source agent's confidence
        return result.confidence > 0.5

    async def _download_book(self, result: SearchResult, book: Book) -> bool:
        """Download and verify a book"""
        # Find source agent
        agent = next((a for a in self.source_agents if a.name == result.source), None)
        if not agent:
            return False

        # Create filename
        filename = self._create_filename(book.title)
        output_path = self.output_dir / self.author_id / filename

        # Download
        success = await agent.download(result, output_path)

        if success:
            book.downloaded = True
            book.download_path = str(output_path)
            book.gutenberg_id = result.book_id
            book.gutenberg_url = result.url
            logger.info(f"Agent {self.name}: Successfully downloaded {book.title}")
        else:
            book.error = f"Download failed from {result.source}"
            logger.warning(f"Agent {self.name}: Failed to download {book.title}")

        return success

    def _create_filename(self, title: str) -> str:
        """Create safe filename from title"""
        filename = re.sub(r'[^\w\s-]', '', title.lower())
        filename = re.sub(r'[-\s]+', '_', filename)
        filename = filename.strip('_')
        filename = filename[:100]
        return f"{filename}.txt"

    def _generate_report(self) -> AuthorReport:
        """Generate report of this agent's work"""
        return AuthorReport(
            author=self.name,
            author_id=self.author_id,
            total_books=len(self.books),
            books_found=len(self.findings),
            books_downloaded=len(self.downloads),
            books_failed=len(self.failures),
            books=self.books,
        )


class AgenticOrchestrator:
    """Orchestrates the multi-agent acquisition system"""

    def __init__(
        self,
        output_dir: Path = Path("data/raw"),
        max_concurrent_agents: int = 10
    ):
        self.output_dir = output_dir
        self.max_concurrent_agents = max_concurrent_agents
        self.knowledge = SharedKnowledgeBase()
        self.source_agents: List[SourceAgent] = []
        self.author_agents: List[AuthorAgent] = []
        self.reports: Dict[str, AuthorReport] = {}

    async def initialize(self):
        """Initialize all agents"""
        # Create source agents
        self.source_agents = [
            GutenbergAgent(self.knowledge),
            InternetArchiveAgent(self.knowledge),
            WikisourceAgent(self.knowledge),
        ]

        # Initialize async resources for source agents
        for agent in self.source_agents:
            await agent.initialize()

        logger.info(
            f"Initialized {len(self.source_agents)} source agents: "
            f"{[a.name for a in self.source_agents]}"
        )

    async def cleanup(self):
        """Cleanup all agents"""
        for agent in self.source_agents:
            await agent.cleanup()

    def create_author_agents(self, books_by_author: Dict[str, List[Book]]):
        """Create author agents from parsed library data"""
        for author_id, books in books_by_author.items():
            if not books:
                continue

            author_name = books[0].author

            # Build author profile
            profile = AuthorProfile.infer_from_books(author_name, books)

            # Create agent
            agent = AuthorAgent(
                author_name=author_name,
                author_id=author_id,
                books=books,
                profile=profile,
                source_agents=self.source_agents,
                knowledge=self.knowledge,
                output_dir=self.output_dir
            )

            self.author_agents.append(agent)

            logger.info(
                f"Created agent for {author_name} ({author_id}): "
                f"{len(books)} books, era: {profile.era.value}, "
                f"public domain: {profile.likely_public_domain}"
            )

    async def orchestrate(self) -> Dict[str, AuthorReport]:
        """Run all author agents with coordination"""
        logger.info(
            f"Starting orchestration of {len(self.author_agents)} author agents "
            f"(max {self.max_concurrent_agents} concurrent)"
        )

        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_agents)

        async def run_with_semaphore(agent: AuthorAgent):
            async with semaphore:
                return await agent.acquire_works()

        # Run all agents in parallel (but limited by semaphore)
        start_time = time.time()
        results = await asyncio.gather(*[
            run_with_semaphore(agent)
            for agent in self.author_agents
        ])
        duration = time.time() - start_time

        # Collect reports
        for agent, report in zip(self.author_agents, results):
            self.reports[agent.author_id] = report

        # Log summary
        total_books = sum(r.total_books for r in results)
        total_found = sum(r.books_found for r in results)
        total_downloaded = sum(r.books_downloaded for r in results)

        logger.info(
            f"Orchestration complete in {duration:.1f}s: "
            f"{total_downloaded}/{total_books} books acquired "
            f"({total_found} found on sources)"
        )

        # Log knowledge base stats
        stats = self.knowledge.get_stats()
        logger.info(f"Knowledge base: {stats}")

        return self.reports


async def main_async(args):
    """Async main function"""
    # Parse library
    parser = LibraryThingParser()
    books = parser.parse(args.input)

    # Group by author
    books_by_author = defaultdict(list)
    for book in books:
        books_by_author[book.author_normalized].append(book)

    # Apply filters
    if args.author_filter:
        author_filter_normalized = {
            parser._normalize_author_name(a)
            for a in args.author_filter.split(',')
        }
        books_by_author = {
            k: v for k, v in books_by_author.items()
            if k in author_filter_normalized
        }

    if args.max_books_per_author:
        for author_id in books_by_author:
            books_by_author[author_id] = books_by_author[author_id][:args.max_books_per_author]

    # Create orchestrator
    orchestrator = AgenticOrchestrator(
        output_dir=args.output_dir,
        max_concurrent_agents=args.max_concurrent
    )

    try:
        # Initialize
        await orchestrator.initialize()

        # Create author agents
        orchestrator.create_author_agents(books_by_author)

        # Run orchestration
        reports = await orchestrator.orchestrate()

        # Generate outputs (reuse from original script)
        from acquire_from_librarything import TextAcquisitionPipeline

        # Create a temporary pipeline just for report generation
        pipeline = TextAcquisitionPipeline(output_dir=args.output_dir)
        pipeline.reports = reports

        # Generate reports
        report_text = pipeline.generate_report(output_file=args.report)
        print("\n" + report_text)

        pipeline.save_json_report(args.json_report)
        pipeline.generate_download_script(args.download_script)

        print(f"\n📝 Generated download script: {args.download_script}")
        print(f"   Run it with: ./{args.download_script}")

        # Print agent-specific insights
        print("\n" + "="*80)
        print("AGENTIC INSIGHTS")
        print("="*80)
        stats = orchestrator.knowledge.get_stats()
        print(f"Total searches: {stats['total_successful_searches'] + stats['total_failed_searches']}")
        print(f"Successful: {stats['total_successful_searches']}")
        print(f"Failed: {stats['total_failed_searches']}")
        print("\nSource Performance:")
        for source, perf in stats['source_performance'].items():
            success_rate = perf['successes'] / perf['searches'] * 100 if perf['searches'] > 0 else 0
            print(f"  {source}: {perf['successes']}/{perf['searches']} searches "
                  f"({success_rate:.1f}%), {perf['downloads']} downloads")

        logger.info("\n✅ Agentic acquisition complete!")

    finally:
        await orchestrator.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description='Agentic text acquisition from LibraryThing export'
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Path to LibraryThing export file (JSON or TSV)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/raw'),
        help='Output directory for downloaded texts'
    )
    parser.add_argument(
        '--author-filter',
        type=str,
        help='Comma-separated list of authors to process'
    )
    parser.add_argument(
        '--max-books-per-author',
        type=int,
        help='Maximum number of books per author'
    )
    parser.add_argument(
        '--max-concurrent',
        type=int,
        default=10,
        help='Maximum concurrent author agents (default: 10)'
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=Path('acquisition_report.txt'),
        help='Output path for text report'
    )
    parser.add_argument(
        '--json-report',
        type=Path,
        default=Path('acquisition_report.json'),
        help='Output path for JSON report'
    )
    parser.add_argument(
        '--download-script',
        type=Path,
        default=Path('download_texts.sh'),
        help='Output path for download shell script'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run async main
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during acquisition: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
