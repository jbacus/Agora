#!/usr/bin/env python3
"""
Preview enhanced expertise profiles before regeneration.
Shows the difference between old and new profile text.
"""
import sys
from pathlib import Path

import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_old_expertise_text(author_data: dict) -> str:
    """Old version - keyword lists."""
    expertise_text = f"{author_data['name']} is an expert in: "
    expertise_text += ", ".join(author_data['expertise_domains'])
    expertise_text += ". "

    if 'bio' in author_data:
        expertise_text += author_data['bio']

    return expertise_text


def create_new_expertise_text(author_data: dict) -> str:
    """New version - semantically rich."""
    # Start with name and natural language domain description
    text = f"{author_data['name']} specializes in "

    # Convert underscores to spaces for better embedding
    domains = [d.replace('_', ' ') for d in author_data['expertise_domains']]
    text += ", ".join(domains) + ". "

    # Add biographical context
    if 'bio' in author_data:
        text += author_data['bio'] + " "

    # Add voice characteristics for richer semantic content
    voice = author_data.get('voice_characteristics', {})
    if 'perspective' in voice:
        text += f"Their perspective is characterized by {voice['perspective']}. "
    if 'vocabulary' in voice:
        text += f"Key concepts include: {voice['vocabulary']}. "

    # Add major works for additional context
    if 'major_works' in author_data and author_data['major_works']:
        works = ", ".join(author_data['major_works'][:3])  # Top 3 works
        text += f"Major works: {works}."

    return text


def preview_profiles():
    """Preview all author profiles."""
    print("\n" + "="*80)
    print("EXPERTISE PROFILE COMPARISON")
    print("="*80)
    print("\nComparing OLD (keyword-based) vs NEW (semantically rich) profiles\n")

    author_files = ["marx", "whitman", "baudelaire"]

    for author_id in author_files:
        config_path = Path(f"config/authors/{author_id}.yaml")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        old_text = create_old_expertise_text(data)
        new_text = create_new_expertise_text(data)

        print(f"\n{'='*80}")
        print(f"{data['name'].upper()}")
        print("="*80)

        print("\nOLD Profile (keyword-based):")
        print("-" * 80)
        print(old_text)
        print("-" * 80)

        print("\nNEW Profile (semantically rich):")
        print("-" * 80)
        print(new_text)
        print("-" * 80)

        # Show length comparison
        old_len = len(old_text.split())
        new_len = len(new_text.split())
        print(f"\nWord count: OLD={old_len}, NEW={new_len} (+{new_len-old_len} words)")

    print("\n" + "=" * 80)
    print("KEY IMPROVEMENTS:")
    print("=" * 80)
    print("  ✓ Natural language domains (labor_theory_of_value → labor theory of value)")
    print("  ✓ Added voice characteristics and perspective")
    print("  ✓ Included major works for context")
    print("  ✓ More semantic overlap with user queries")
    print("\nNext step: python scripts/create_expertise_profiles.py")
    print()


if __name__ == "__main__":
    preview_profiles()
