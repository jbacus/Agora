"""
Response aggregation and formatting for the Virtual Debate Panel.
"""
from typing import List

from loguru import logger

from ..data.models import AuthorResponse, DebatePanelResponse, Query


class ResponseAggregator:
    """
    Aggregates and formats responses from multiple authors.

    Formats responses to clearly show contrasts and disagreements
    between authors' philosophical stances.
    """

    def __init__(self):
        """Initialize the response aggregator."""
        logger.info("Initialized ResponseAggregator")

    def aggregate(
        self,
        query: Query,
        author_responses: List[AuthorResponse],
        total_time_ms: float,
        selection_method: str
    ) -> DebatePanelResponse:
        """
        Aggregate author responses into a debate panel response.

        Args:
            query: Original user query
            author_responses: List of responses from selected authors
            total_time_ms: Total time taken for entire operation
            selection_method: Method used for author selection

        Returns:
            Formatted debate panel response
        """
        # Sort responses by relevance score (highest first)
        sorted_responses = sorted(
            author_responses,
            key=lambda r: r.relevance_score,
            reverse=True
        )

        logger.info(
            f"Aggregated {len(sorted_responses)} responses "
            f"(total_time={total_time_ms:.0f}ms)"
        )

        return DebatePanelResponse(
            query=query,
            authors=sorted_responses,
            total_time_ms=total_time_ms,
            selection_method=selection_method
        )

    def format_as_markdown(self, response: DebatePanelResponse) -> str:
        """
        Format debate panel response as markdown.

        Args:
            response: Debate panel response

        Returns:
            Markdown-formatted string
        """
        lines = []

        # Header
        lines.append("# Virtual Debate Panel\n")
        lines.append(f"**Query:** {response.query.text}\n")
        lines.append(
            f"**Panel:** {response.author_count} authors "
            f"({response.selection_method} selection)\n"
        )
        lines.append("---\n")

        # Author responses
        for i, author_resp in enumerate(response.authors, 1):
            lines.append(f"## {i}. {author_resp.author_name}")
            lines.append(f"*Relevance: {author_resp.relevance_score:.2f}*\n")
            lines.append(author_resp.response_text)
            lines.append("\n---\n")

        # Footer
        lines.append(
            f"*Generated in {response.total_time_ms:.0f}ms "
            f"({response.timestamp.strftime('%Y-%m-%d %H:%M:%S')})*"
        )

        return "\n".join(lines)

    def format_as_html(self, response: DebatePanelResponse) -> str:
        """
        Format debate panel response as HTML.

        Args:
            response: Debate panel response

        Returns:
            HTML-formatted string
        """
        html = []

        # Header
        html.append('<div class="debate-panel">')
        html.append('<div class="header">')
        html.append('<h1>Virtual Debate Panel</h1>')
        html.append(f'<p class="query"><strong>Query:</strong> {response.query.text}</p>')
        html.append(
            f'<p class="meta"><strong>Panel:</strong> {response.author_count} authors '
            f'({response.selection_method} selection)</p>'
        )
        html.append('</div>')

        # Author responses
        html.append('<div class="responses">')
        for i, author_resp in enumerate(response.authors, 1):
            html.append(f'<div class="author-response" data-author="{author_resp.author_id}">')
            html.append(f'<h2>{i}. {author_resp.author_name}</h2>')
            html.append(
                f'<p class="relevance">Relevance: '
                f'<span class="score">{author_resp.relevance_score:.2f}</span></p>'
            )

            # Convert paragraphs to HTML
            paragraphs = author_resp.response_text.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    html.append(f'<p>{para.strip()}</p>')

            html.append('</div>')

        html.append('</div>')

        # Footer
        html.append('<div class="footer">')
        html.append(
            f'<p class="meta">Generated in {response.total_time_ms:.0f}ms '
            f'({response.timestamp.strftime("%Y-%m-%d %H:%M:%S")})</p>'
        )
        html.append('</div>')
        html.append('</div>')

        return '\n'.join(html)

    def format_as_plain_text(self, response: DebatePanelResponse) -> str:
        """
        Format debate panel response as plain text.

        Args:
            response: Debate panel response

        Returns:
            Plain text formatted string
        """
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("VIRTUAL DEBATE PANEL")
        lines.append("=" * 80)
        lines.append(f"\nQuery: {response.query.text}\n")
        lines.append(
            f"Panel: {response.author_count} authors "
            f"({response.selection_method} selection)\n"
        )
        lines.append("-" * 80)

        # Author responses
        for i, author_resp in enumerate(response.authors, 1):
            lines.append(f"\n[{i}] {author_resp.author_name.upper()}")
            lines.append(f"Relevance: {author_resp.relevance_score:.2f}\n")
            lines.append(author_resp.response_text)
            lines.append("\n" + "-" * 80)

        # Footer
        lines.append(
            f"\nGenerated in {response.total_time_ms:.0f}ms "
            f"({response.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
        )
        lines.append("=" * 80)

        return "\n".join(lines)

    def extract_key_differences(self, response: DebatePanelResponse) -> List[str]:
        """
        Extract key differences and disagreements between authors (future enhancement).

        This is a placeholder for future AI-powered analysis that would
        identify specific points of disagreement and contrast.

        Args:
            response: Debate panel response

        Returns:
            List of key difference statements
        """
        # TODO: Implement AI-powered difference extraction
        # This would use an LLM to analyze responses and identify:
        # - Direct contradictions
        # - Different perspectives on the same concept
        # - Unique insights from each author
        # - Areas of agreement vs disagreement

        logger.warning("Key difference extraction not yet implemented")
        return [
            f"Multiple perspectives from {response.author_count} authors",
            "See individual responses for detailed viewpoints"
        ]

    def create_comparison_table(self, response: DebatePanelResponse) -> str:
        """
        Create a comparison table highlighting author positions.

        Args:
            response: Debate panel response

        Returns:
            Markdown table comparing author positions
        """
        lines = []

        lines.append("## Author Comparison\n")
        lines.append("| Author | Relevance | Key Position |")
        lines.append("|--------|-----------|--------------|")

        for author_resp in response.authors:
            # Extract first sentence as "key position"
            first_sentence = author_resp.response_text.split('.')[0]
            if len(first_sentence) > 80:
                first_sentence = first_sentence[:77] + "..."

            lines.append(
                f"| {author_resp.author_name} | "
                f"{author_resp.relevance_score:.2f} | "
                f"{first_sentence} |"
            )

        return "\n".join(lines)
