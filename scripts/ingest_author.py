#!/usr/bin/env python3
"""
Ingest author texts: chunk, embed, and store in vector database.
"""
import argparse
import sys
from pathlib import Path
from typing import List

import tiktoken
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.data import TextChunk, get_embedding_provider, get_vector_db

console = Console()


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
    encoding_name: str = "cl100k_base"
) -> List[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in tokens
        overlap: Overlap between chunks in tokens
        encoding_name: Tokenizer encoding name

    Returns:
        List of text chunks
    """
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)

    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)

        start += chunk_size - overlap

    return chunks


def load_text_files(author_dir: Path) -> List[tuple[str, str]]:
    """
    Load all text files from author directory.

    Args:
        author_dir: Directory containing author texts

    Returns:
        List of (filename, content) tuples
    """
    files = []
    for file_path in author_dir.glob("*.txt"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            files.append((file_path.stem, content))
            logger.info(f"Loaded: {file_path.name} ({len(content)} chars)")
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")

    return files


def ingest_author(author_id: str, input_dir: Path):
    """
    Ingest all texts for an author.

    Args:
        author_id: Author identifier (e.g., 'marx')
        input_dir: Directory containing author texts
    """
    console.print(f"\n[bold blue]Ingesting author: {author_id}[/bold blue]\n")

    # Check if input directory exists
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        console.print(f"[red]✗ Directory not found: {input_dir}[/red]")
        console.print("\nPlease create the directory and add .txt files:")
        console.print(f"  mkdir -p {input_dir}")
        console.print(f"  # Add text files to {input_dir}")
        return

    # Load text files
    console.print("[cyan]Loading text files...[/cyan]")
    files = load_text_files(input_dir)

    if not files:
        logger.error(f"No .txt files found in {input_dir}")
        console.print(f"[red]✗ No .txt files found in {input_dir}[/red]")
        return

    console.print(f"[green]✓ Loaded {len(files)} files[/green]\n")

    # Initialize services
    console.print("[cyan]Initializing services...[/cyan]")
    vector_db = get_vector_db(**settings.get_vector_db_config())
    vector_db.initialize()
    embedding_provider = get_embedding_provider(**settings.get_embedding_config())
    console.print("[green]✓ Services initialized[/green]\n")

    # Process each file
    all_chunks = []
    console.print("[cyan]Chunking texts...[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            f"Processing files for {author_id}",
            total=len(files)
        )

        for filename, content in files:
            progress.update(task, description=f"Processing: {filename}")

            # Chunk text
            chunks = chunk_text(
                content,
                chunk_size=settings.chunk_size,
                overlap=settings.chunk_overlap
            )

            logger.info(f"{filename}: {len(chunks)} chunks")

            # Create TextChunk objects
            for i, chunk_content in enumerate(chunks):
                chunk_id = f"{author_id}_{filename}_{i}"
                text_chunk = TextChunk(
                    id=chunk_id,
                    author_id=author_id,
                    text=chunk_content,
                    metadata={
                        "book": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }
                )
                all_chunks.append(text_chunk)

            progress.update(task, advance=1)

    console.print(f"\n[green]✓ Created {len(all_chunks)} chunks[/green]\n")

    # Generate embeddings
    console.print("[cyan]Generating embeddings...[/cyan]")
    texts = [chunk.text for chunk in all_chunks]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task(
            "Embedding chunks",
            total=len(texts)
        )

        # Process in batches to show progress
        batch_size = 50
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = embedding_provider.embed_batch(batch)
            embeddings.extend(batch_embeddings)
            progress.update(task, advance=len(batch))

        for chunk, embedding in zip(all_chunks, embeddings):
            chunk.embedding = embedding

    console.print(f"[green]✓ Generated {len(embeddings)} embeddings[/green]\n")

    # Insert into vector database
    console.print("[cyan]Inserting into vector database...[/cyan]")
    vector_db.insert_chunks(all_chunks)
    console.print(f"[green]✓ Inserted {len(all_chunks)} chunks[/green]\n")

    # Summary
    console.print("\n" + "=" * 60)
    console.print(f"[bold green]Ingestion complete for {author_id}![/bold green]")
    console.print("=" * 60)
    console.print(f"Files processed: {len(files)}")
    console.print(f"Total chunks: {len(all_chunks)}")
    console.print(f"Embedding dimension: {embedding_provider.dimension}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest author texts into vector database"
    )
    parser.add_argument(
        "--author",
        required=True,
        help="Author ID (e.g., 'marx', 'whitman', 'baudelaire')"
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Input directory (default: data/raw/<author>/)"
    )

    args = parser.parse_args()

    # Determine input directory
    if args.input:
        input_dir = args.input
    else:
        input_dir = Path(settings.data_raw_dir) / args.author

    ingest_author(args.author, input_dir)


if __name__ == "__main__":
    main()
