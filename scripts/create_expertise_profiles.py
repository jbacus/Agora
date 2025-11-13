#!/usr/bin/env python3
"""
Create expertise profile vectors for authors based on their domains.
"""
import sys
from pathlib import Path

import yaml
from loguru import logger
from rich.console import Console

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from src.data import Author, VoiceCharacteristics, get_embedding_provider, get_vector_db

console = Console()


def create_expertise_text(author_data: dict) -> str:
    """
    Create a text representation of author's expertise for embedding.

    Args:
        author_data: Author configuration dictionary

    Returns:
        Expertise text for embedding
    """
    expertise_text = f"{author_data['name']} is an expert in: "
    expertise_text += ", ".join(author_data['expertise_domains'])
    expertise_text += ". "

    if 'bio' in author_data:
        expertise_text += author_data['bio']

    return expertise_text


def create_expertise_profiles():
    """Create and store expertise profile vectors for all authors."""
    console.print("\n[bold blue]Creating Expertise Profiles[/bold blue]\n")

    # Initialize services
    console.print("[cyan]Initializing services...[/cyan]")
    vector_db = get_vector_db(**settings.get_vector_db_config())
    vector_db.initialize()
    embedding_provider = get_embedding_provider(**settings.get_embedding_config())
    console.print("[green]✓ Services initialized[/green]\n")

    # Load author configs
    author_files = ["marx", "whitman", "manson"]
    authors = []

    for author_id in author_files:
        config_path = Path(f"config/authors/{author_id}.yaml")

        if not config_path.exists():
            logger.warning(f"Config not found: {config_path}")
            continue

        console.print(f"[cyan]Processing {author_id}...[/cyan]")

        # Load config
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        # Create expertise text
        expertise_text = create_expertise_text(data)
        logger.info(f"Expertise text for {author_id}: {expertise_text[:100]}...")

        # Generate embedding
        expertise_vector = embedding_provider.embed_text(expertise_text)
        logger.info(f"Generated expertise vector (dim={len(expertise_vector)})")

        # Create Author object
        author = Author(
            id=author_id,
            name=data["name"],
            expertise_domains=data["expertise_domains"],
            voice_characteristics=VoiceCharacteristics(**data["voice_characteristics"]),
            system_prompt=data["system_prompt"],
            expertise_vector=expertise_vector,
            bio=data.get("bio"),
            works=data.get("major_works", [])
        )

        authors.append(author)
        console.print(f"[green]✓ Created profile for {data['name']}[/green]")

    # Insert into vector database
    console.print(f"\n[cyan]Inserting {len(authors)} profiles into database...[/cyan]")
    for author in authors:
        vector_db.insert_author_profile(author)

    console.print(f"[green]✓ Inserted {len(authors)} author profiles[/green]\n")

    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold green]Expertise profiles created successfully![/bold green]")
    console.print("=" * 60)
    console.print(f"Authors processed: {len(authors)}")
    console.print(f"Vector dimension: {embedding_provider.dimension}")
    console.print("\nNext step:")
    console.print("  python -m uvicorn src.api.main:app --reload")


if __name__ == "__main__":
    create_expertise_profiles()
