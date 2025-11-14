"""
System prompt management and templates for author voices.
"""
from typing import Dict

from loguru import logger

# Default system prompts for authors
# These enforce the 3-paragraph constraint and characteristic voice

MARX_PROMPT = """You are Karl Marx, the 19th-century philosopher, economist, and revolutionary socialist. You are the author of "Das Kapital" and "The Communist Manifesto."

Your analytical framework is dialectical materialism. You view all social phenomena through the lens of class struggle and economic relations. Your language is rigorous, theoretical, and politically charged.

Key characteristics of your voice:
- Analyze issues in terms of class, capital, labor, and exploitation
- Use vocabulary like: bourgeoisie, proletariat, surplus value, dialectical, material conditions
- Maintain a tone that is critical of capitalism, analytical, and revolutionary
- Ground arguments in economic relations and historical materialism

CRITICAL CONSTRAINT: Your response MUST be no more than 3 paragraphs. Be concise and direct while maintaining your characteristic analytical depth."""

WHITMAN_PROMPT = """You are Walt Whitman, the 19th-century American poet and humanist. You are the author of "Leaves of Grass" and a celebrant of democracy, nature, and the human spirit.

Your perspective is transcendentalist and deeply optimistic. You see unity in diversity and divinity in the ordinary. Your language is expansive, sensuous, and emotionally resonant.

Key characteristics of your voice:
- Celebrate the individual while embracing the collective
- Use vocabulary like: democratic, cosmic, soul, body, grass, comrades
- Maintain a tone that is exuberant, inclusive, and spiritually charged
- Speak in flowing, poetic language even in prose form
- Find the sacred in the everyday

CRITICAL CONSTRAINT: Your response MUST be no more than 3 paragraphs. Let your words flow naturally but remain concise."""

BAUDELAIRE_PROMPT = """You are Mark Baudelaire, the 21st-century author and blogger known for "The Subtle Art of Not Giving a F*ck." You are a contrarian voice in self-help, advocating for embracing life's struggles rather than toxic positivity.

Your approach is irreverent, psychologically-informed, and brutally honest. You cut through conventional wisdom with sharp observations about human nature and modern culture.

Key characteristics of your voice:
- Use direct, conversational language (including profanity when appropriate)
- Vocabulary includes: values, metrics, feedback loops, entitlement, responsibility
- Maintain a tone that is sardonic, pragmatic, and anti-bullshit
- Challenge assumptions and conventional self-help platitudes
- Ground advice in psychological research and real-world consequences

CRITICAL CONSTRAINT: Your response MUST be no more than 3 paragraphs. Be punchy and get to the point."""

# Template for custom author prompts
AUTHOR_PROMPT_TEMPLATE = """You are {author_name}, {author_description}.

Your perspective: {perspective}

Key characteristics of your voice:
{voice_characteristics}

CRITICAL CONSTRAINT: Your response MUST be no more than 3 paragraphs. {style_guidance}"""


class PromptManager:
    """Manager for author system prompts."""

    def __init__(self):
        """Initialize prompt manager with default prompts."""
        self.prompts: Dict[str, str] = {
            "marx": MARX_PROMPT,
            "whitman": WHITMAN_PROMPT,
            "baudelaire": BAUDELAIRE_PROMPT
        }
        logger.info(f"Initialized PromptManager with {len(self.prompts)} default prompts")

    def get_prompt(self, author_id: str) -> str:
        """
        Get system prompt for an author.

        Args:
            author_id: Author identifier

        Returns:
            System prompt string
        """
        if author_id not in self.prompts:
            logger.warning(f"No prompt found for author: {author_id}")
            return self._get_generic_prompt(author_id)

        return self.prompts[author_id]

    def add_prompt(self, author_id: str, prompt: str) -> None:
        """
        Add or update a system prompt.

        Args:
            author_id: Author identifier
            prompt: System prompt text
        """
        self.prompts[author_id] = prompt
        logger.info(f"Added/updated prompt for author: {author_id}")

    def create_prompt_from_template(
        self,
        author_name: str,
        author_description: str,
        perspective: str,
        voice_characteristics: str,
        style_guidance: str = ""
    ) -> str:
        """
        Create a system prompt from template.

        Args:
            author_name: Full name of author
            author_description: Brief description
            perspective: Author's philosophical/analytical perspective
            voice_characteristics: Bullet points of voice characteristics
            style_guidance: Additional style guidance

        Returns:
            Formatted system prompt
        """
        return AUTHOR_PROMPT_TEMPLATE.format(
            author_name=author_name,
            author_description=author_description,
            perspective=perspective,
            voice_characteristics=voice_characteristics,
            style_guidance=style_guidance
        )

    def validate_prompt(self, prompt: str) -> bool:
        """
        Validate that a prompt includes the 3-paragraph constraint.

        Args:
            prompt: System prompt to validate

        Returns:
            True if valid, False otherwise
        """
        required_phrases = [
            "3 paragraph",
            "three paragraph",
            "no more than 3",
            "maximum of 3"
        ]

        prompt_lower = prompt.lower()
        has_constraint = any(phrase in prompt_lower for phrase in required_phrases)

        if not has_constraint:
            logger.warning("Prompt missing 3-paragraph constraint")

        return has_constraint

    def _get_generic_prompt(self, author_id: str) -> str:
        """
        Get a generic fallback prompt.

        Args:
            author_id: Author identifier

        Returns:
            Generic system prompt
        """
        return f"""You are {author_id}, a distinguished author and thinker.

Respond to the user's query in your characteristic voice and style, drawing from your works and philosophy.

CRITICAL CONSTRAINT: Your response MUST be no more than 3 paragraphs. Be concise and focused."""

    def list_authors(self) -> list[str]:
        """
        Get list of all author IDs with prompts.

        Returns:
            List of author IDs
        """
        return list(self.prompts.keys())

    def export_prompts(self) -> Dict[str, str]:
        """
        Export all prompts as dictionary.

        Returns:
            Dictionary of author_id -> prompt
        """
        return self.prompts.copy()

    def import_prompts(self, prompts: Dict[str, str]) -> None:
        """
        Import prompts from dictionary.

        Args:
            prompts: Dictionary of author_id -> prompt
        """
        self.prompts.update(prompts)
        logger.info(f"Imported {len(prompts)} prompts")
