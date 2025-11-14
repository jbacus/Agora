#!/usr/bin/env python3
"""
RAG Pipeline Testing Script
Tests the Retrieval-Augmented Generation pipeline with various queries.
"""
import asyncio
import sys
import time
from typing import Dict, List

import yaml
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path
sys.path.insert(0, '.')

from config.settings import settings
from src.data import get_embedding_provider, get_vector_db
from src.data.models import Author, Query, VoiceCharacteristics
from src.processing import get_llm_client, RAGPipeline
from src.routing import SemanticRouter


console = Console()


def load_authors_from_config() -> Dict[str, Author]:
    """Load author profiles from YAML config files."""
    authors = {}
    author_files = ["marx", "whitman", "baudelaire"]

    for author_id in author_files:
        try:
            with open(f"config/authors/{author_id}.yaml", "r") as f:
                data = yaml.safe_load(f)

            authors[author_id] = Author(
                id=author_id,
                name=data["name"],
                expertise_domains=data["expertise_domains"],
                voice_characteristics=VoiceCharacteristics(**data["voice_characteristics"]),
                system_prompt=data["system_prompt"],
                bio=data.get("bio"),
                works=data.get("major_works", [])
            )
            logger.info(f"Loaded author: {data['name']}")
        except Exception as e:
            logger.error(f"Failed to load author {author_id}: {e}")

    return authors


# Test queries categorized by expected author
TEST_QUERIES = {
    'marx': [
        "What is the relationship between labor and capital?",
        "Explain class struggle and its historical significance",
        "How does capitalism exploit workers?",
        "What is the theory of surplus value?",
    ],
    'whitman': [
        "What is the meaning of democracy?",
        "How should we celebrate the individual?",
        "What is the relationship between nature and humanity?",
        "How does poetry connect us to the divine?",
    ],
    'baudelaire': [
        "How do I stop caring what others think?",
        "What makes a good life?",
        "How should I deal with failure and setbacks?",
        "What is the purpose of suffering?",
    ],
    'multi_author': [
        "What is freedom?",
        "How should we live our lives?",
        "What is happiness?",
        "What is the meaning of life?",
    ]
}


async def test_query(
    query: str,
    semantic_router: SemanticRouter,
    rag_pipeline: RAGPipeline,
    authors: Dict[str, Author],
    expected_author: str = None
) -> dict:
    """Test a single query through the RAG pipeline."""

    start_time = time.time()

    # Create Query object
    query_obj = Query(text=query, specified_authors=None)

    # Select authors
    selection_result = semantic_router.select_authors(query_obj)
    selection_time = time.time() - start_time

    # Generate response from first author
    if selection_result.selected_authors:
        response_start = time.time()
        first_author_id = selection_result.selected_authors[0]

        # Get Author object
        author = authors.get(first_author_id)
        if not author:
            logger.error(f"Author not found: {first_author_id}")
            response = None
            response_time = 0
        else:
            # Use the query embedding from selection (already computed)
            query_embedding = selection_result.query_vector

            # Generate response using async method
            response = await rag_pipeline.generate_response_async(
                query=query_obj,
                author=author,
                query_embedding=query_embedding
            )
            response_time = time.time() - response_start
    else:
        response = None
        response_time = 0

    total_time = time.time() - start_time

    # Check if expected author was selected
    correct_selection = None
    if expected_author:
        correct_selection = expected_author in selection_result.selected_authors

    return {
        'query': query,
        'expected_author': expected_author,
        'selection_result': selection_result,
        'correct_selection': correct_selection,
        'response': response,
        'timing': {
            'selection': selection_time,
            'generation': response_time,
            'total': total_time
        }
    }


async def run_tests():
    """Run all RAG pipeline tests."""

    console.print("\n[bold blue]🧪 RAG Pipeline Testing[/bold blue]")
    console.print("=" * 60)
    console.print()

    # Initialize services
    console.print("[yellow]Initializing services...[/yellow]")

    try:
        # Load authors
        authors = load_authors_from_config()
        console.print(f"[green]✓ Loaded {len(authors)} author profiles[/green]")

        vector_db = get_vector_db(**settings.get_vector_db_config())
        vector_db.initialize()

        embedding_provider = get_embedding_provider(**settings.get_embedding_config())
        llm_client = get_llm_client(**settings.get_llm_config())

        semantic_router = SemanticRouter(
            vector_db=vector_db,
            embedding_provider=embedding_provider,
            relevance_threshold=settings.relevance_threshold,
            min_authors=settings.min_authors,
            max_authors=settings.max_authors,
            fallback_to_top=settings.fallback_to_top_authors
        )

        rag_pipeline = RAGPipeline(
            vector_db=vector_db,
            embedding_provider=embedding_provider,
            llm_client=llm_client,
            top_k_chunks=settings.top_k_chunks,
            max_response_tokens=settings.max_response_tokens,
            temperature=settings.llm_temperature
        )

        console.print("[green]✓ Services initialized[/green]\n")

    except Exception as e:
        console.print(f"[red]✗ Failed to initialize services: {e}[/red]")
        return 1

    # Run tests
    all_results = []
    correct_selections = 0
    total_with_expected = 0

    for category, queries in TEST_QUERIES.items():
        expected_author = category if category != 'multi_author' else None

        console.print(f"\n[bold]{category.upper()} Queries:[/bold]")
        console.print("-" * 60)

        for query in queries:
            console.print(f"\n[cyan]Q: {query}[/cyan]")

            try:
                result = await test_query(query, semantic_router, rag_pipeline, authors, expected_author)
                all_results.append(result)

                # Display selected authors
                if result['selection_result'].selected_authors:
                    author_ids = result['selection_result'].selected_authors
                    scores = result['selection_result'].similarity_scores
                    author_info = [f"{aid} ({scores.get(aid, 0):.2f})" for aid in author_ids]
                    console.print(f"[yellow]Selected:[/yellow] {', '.join(author_info)}")

                    # Check correctness
                    if expected_author:
                        total_with_expected += 1
                        if result['correct_selection']:
                            console.print("[green]✓ Correct selection[/green]")
                            correct_selections += 1
                        else:
                            console.print(f"[red]✗ Expected {expected_author}[/red]")
                else:
                    console.print("[red]✗ No authors selected[/red]")

                # Display response preview
                if result['response']:
                    response_preview = result['response'].response_text[:150] + "..."
                    console.print(f"[dim]{response_preview}[/dim]")

                # Display timing
                timing = result['timing']
                console.print(f"[dim]Timing: {timing['total']:.2f}s (selection: {timing['selection']:.2f}s, generation: {timing['generation']:.2f}s)[/dim]")

            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")
                logger.exception(f"Query failed: {query}")

    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold blue]📊 Test Summary[/bold blue]")
    console.print("=" * 60 + "\n")

    # Selection accuracy
    if total_with_expected > 0:
        accuracy = (correct_selections / total_with_expected) * 100
        console.print(f"Selection Accuracy: {correct_selections}/{total_with_expected} ({accuracy:.1f}%)")

    # Timing statistics
    all_timings = [r['timing']['total'] for r in all_results if r['timing']['total'] > 0]
    if all_timings:
        avg_time = sum(all_timings) / len(all_timings)
        max_time = max(all_timings)
        min_time = min(all_timings)

        console.print(f"Average response time: {avg_time:.2f}s")
        console.print(f"Min/Max: {min_time:.2f}s / {max_time:.2f}s")

    # Response rate
    responses_generated = sum(1 for r in all_results if r['response'] is not None)
    console.print(f"Responses generated: {responses_generated}/{len(all_results)}")

    console.print()

    # Detailed results table
    table = Table(title="Detailed Results")
    table.add_column("Query", style="cyan", no_wrap=False, max_width=40)
    table.add_column("Expected", style="yellow")
    table.add_column("Selected", style="green")
    table.add_column("✓", style="bold")
    table.add_column("Time (s)", justify="right")

    for result in all_results:
        query_short = result['query'][:40] + "..." if len(result['query']) > 40 else result['query']
        expected = result['expected_author'] or "-"
        selected = ", ".join(result['selection_result'].selected_authors) if result['selection_result'].selected_authors else "None"

        if result['correct_selection'] is True:
            check = "✓"
        elif result['correct_selection'] is False:
            check = "✗"
        else:
            check = "-"

        time_str = f"{result['timing']['total']:.2f}"

        table.add_row(query_short, expected, selected, check, time_str)

    console.print(table)
    console.print()

    # Success criteria
    console.print("[bold]Success Criteria:[/bold]")

    criteria = [
        ("Selection accuracy > 90%", accuracy > 90 if total_with_expected > 0 else False),
        ("Average response time < 5s", avg_time < 5 if all_timings else False),
        ("All queries got responses", responses_generated == len(all_results)),
    ]

    for criterion, passed in criteria:
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"  {status} {criterion}")

    console.print()

    # Overall result
    all_passed = all(passed for _, passed in criteria)
    if all_passed:
        console.print("[bold green]✅ All tests passed! RAG pipeline is working correctly.[/bold green]")
        return 0
    else:
        console.print("[bold yellow]⚠️  Some tests failed. Review results above.[/bold yellow]")
        return 1


def main():
    """Main entry point."""

    # Check if data is ingested
    try:
        vector_db = get_vector_db(**settings.get_vector_db_config())
        vector_db.initialize()

        # Try to get a collection (assumes author-based collections)
        # This is a simple check - adjust based on your actual setup
        console.print("[dim]Checking for ingested data...[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Error checking data: {e}[/red]")
        console.print("\n[yellow]Make sure you've ingested data first:[/yellow]")
        console.print("  1. python scripts/acquire_texts.sh")
        console.print("  2. python scripts/clean_texts.py")
        console.print("  3. python scripts/ingest_author.py --author marx")
        console.print("  4. python scripts/ingest_author.py --author whitman")
        console.print("  5. python scripts/ingest_author.py --author baudelaire")
        console.print()
        return 1

    # Run async tests
    try:
        return asyncio.run(run_tests())
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n[red]✗ Test execution failed: {e}[/red]")
        logger.exception("Test execution failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
