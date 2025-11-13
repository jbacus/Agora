"""
LLM client integration for multiple providers (Gemini, OpenAI, Anthropic).
"""
from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI not available")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available")

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic not available")


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ) -> str:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def generate_streaming(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ):
        """Generate a streaming response from the LLM."""
        pass


class GeminiClient(LLMClient):
    """Google Gemini LLM client."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini client.

        Args:
            api_key: Google API key
            model: Model name
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Generative AI not installed")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name = model
        logger.info(f"Initialized Gemini client with model: {model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ) -> str:
        """Generate a response from Gemini."""
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\nUser Query: {user_prompt}"

        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )

        return response.text

    def generate_streaming(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ):
        """Generate a streaming response from Gemini."""
        full_prompt = f"{system_prompt}\n\nUser Query: {user_prompt}"

        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            ),
            stream=True
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text


class OpenAIClient(LLMClient):
    """OpenAI LLM client."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI not installed")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Initialized OpenAI client with model: {model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ) -> str:
        """Generate a response from OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )

        return response.choices[0].message.content

    def generate_streaming(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ):
        """Generate a streaming response from OpenAI."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicClient(LLMClient):
    """Anthropic Claude LLM client."""

    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model name
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic not installed")

        self.client = Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"Initialized Anthropic client with model: {model}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ) -> str:
        """Generate a response from Claude."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.content[0].text

    def generate_streaming(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ):
        """Generate a streaming response from Claude."""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        ) as stream:
            for text in stream.text_stream:
                yield text


def get_llm_client(
    provider: str,
    **kwargs
) -> LLMClient:
    """
    Factory function to get the appropriate LLM client.

    Args:
        provider: Provider name ('gemini', 'openai', 'anthropic')
        **kwargs: Additional arguments for the client constructor

    Returns:
        LLMClient instance
    """
    if provider == "gemini":
        return GeminiClient(**kwargs)
    elif provider == "openai":
        return OpenAIClient(**kwargs)
    elif provider == "anthropic":
        return AnthropicClient(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
