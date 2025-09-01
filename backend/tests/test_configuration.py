"""
Tests for configuration validation and critical settings
"""

import os
import sys

import pytest

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import Config, config


class TestConfiguration:
    """Test suite for configuration validation"""

    def test_default_config_values(self):
        """Test that default configuration has expected values"""
        # Check critical settings
        assert hasattr(config, "ANTHROPIC_API_KEY")
        assert hasattr(config, "ANTHROPIC_MODEL")
        assert hasattr(config, "EMBEDDING_MODEL")
        assert hasattr(config, "CHUNK_SIZE")
        assert hasattr(config, "CHUNK_OVERLAP")
        assert hasattr(config, "MAX_RESULTS")
        assert hasattr(config, "MAX_HISTORY")
        assert hasattr(config, "CHROMA_PATH")

        # Check types
        assert isinstance(config.CHUNK_SIZE, int)
        assert isinstance(config.CHUNK_OVERLAP, int)
        assert isinstance(config.MAX_RESULTS, int)
        assert isinstance(config.MAX_HISTORY, int)

        # Check reasonable values
        assert config.CHUNK_SIZE > 0
        assert config.CHUNK_OVERLAP >= 0
        assert config.CHUNK_OVERLAP < config.CHUNK_SIZE
        assert config.MAX_HISTORY >= 0

    def test_critical_max_results_bug(self):
        """Test for the critical MAX_RESULTS=0 bug that causes query failures"""
        # This is the bug we suspect is causing query failures
        if config.MAX_RESULTS == 0:
            pytest.fail(
                f"CRITICAL BUG DETECTED: MAX_RESULTS is set to {config.MAX_RESULTS}. "
                "This will cause vector searches to return no results, leading to query failures. "
                "MAX_RESULTS should be set to a positive integer (recommended: 5-10)."
            )

        # MAX_RESULTS should be positive for searches to work
        assert (
            config.MAX_RESULTS > 0
        ), "MAX_RESULTS must be positive for searches to return results"

    def test_anthropic_model_format(self):
        """Test that Anthropic model string is in expected format"""
        model = config.ANTHROPIC_MODEL
        assert isinstance(model, str)
        assert len(model) > 0

        # Should be a valid Claude model identifier
        # Common formats: claude-3-sonnet-20241022, claude-3-haiku-20240307, etc.
        assert (
            "claude" in model.lower()
        ), f"Model '{model}' doesn't appear to be a Claude model"

    def test_embedding_model_format(self):
        """Test that embedding model is a valid SentenceTransformer model"""
        embedding_model = config.EMBEDDING_MODEL
        assert isinstance(embedding_model, str)
        assert len(embedding_model) > 0

        # Common embedding models have specific formats
        valid_prefixes = [
            "all-MiniLM",
            "all-mpnet",
            "sentence-transformers",
            "distilbert",
        ]
        is_valid_format = any(prefix in embedding_model for prefix in valid_prefixes)

        if not is_valid_format:
            # Could be a custom model, so we'll just warn
            print(
                f"Warning: Embedding model '{embedding_model}' doesn't match common patterns"
            )

    def test_chunk_settings_logic(self):
        """Test that chunk size and overlap settings make logical sense"""
        assert (
            config.CHUNK_SIZE > config.CHUNK_OVERLAP
        ), "Chunk overlap should be smaller than chunk size"

        # Reasonable bounds
        assert config.CHUNK_SIZE >= 100, "Chunk size seems too small (< 100 characters)"
        assert (
            config.CHUNK_SIZE <= 2000
        ), "Chunk size seems too large (> 2000 characters)"
        assert (
            config.CHUNK_OVERLAP <= config.CHUNK_SIZE * 0.5
        ), "Chunk overlap should not exceed 50% of chunk size"

    def test_path_settings(self):
        """Test that path settings are valid"""
        chroma_path = config.CHROMA_PATH
        assert isinstance(chroma_path, str)
        assert len(chroma_path) > 0

        # Path should be relative or absolute
        assert not chroma_path.startswith(" "), "Path should not start with space"
        assert not chroma_path.endswith(" "), "Path should not end with space"

    def test_api_key_presence(self):
        """Test API key configuration (without revealing the actual key)"""
        api_key = config.ANTHROPIC_API_KEY
        assert isinstance(api_key, str)

        if len(api_key) == 0:
            pytest.fail(
                "CONFIGURATION ERROR: ANTHROPIC_API_KEY is empty. "
                "This will cause all AI generation requests to fail. "
                "Please set ANTHROPIC_API_KEY in your .env file."
            )

        # Basic format check (Anthropic keys typically start with 'sk-')
        if not api_key.startswith("sk-") and not api_key.startswith("test-"):
            print(
                f"Warning: API key doesn't start with expected prefix 'sk-' (got: '{api_key[:10]}...')"
            )

    def test_custom_config_creation(self):
        """Test creating custom config objects"""
        custom_config = Config()

        # Should have all expected attributes
        expected_attrs = [
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_MODEL",
            "EMBEDDING_MODEL",
            "CHUNK_SIZE",
            "CHUNK_OVERLAP",
            "MAX_RESULTS",
            "MAX_HISTORY",
            "CHROMA_PATH",
        ]

        for attr in expected_attrs:
            assert hasattr(custom_config, attr), f"Missing attribute: {attr}"

    def test_environment_variable_loading(self):
        """Test that Config properly loads environment variables from the actual environment"""
        import os

        # Test that the actual config loaded the real environment variables correctly
        # ANTHROPIC_API_KEY should be loaded from environment and be non-empty
        assert (
            len(config.ANTHROPIC_API_KEY) > 0
        ), "ANTHROPIC_API_KEY should be loaded from environment"
        assert isinstance(
            config.ANTHROPIC_API_KEY, str
        ), "ANTHROPIC_API_KEY should be a string"

        # Should match what's actually in the environment
        env_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        assert (
            config.ANTHROPIC_API_KEY == env_api_key
        ), "Config should load ANTHROPIC_API_KEY from environment"

        # ANTHROPIC_MODEL should be loaded (either from env or default)
        assert len(config.ANTHROPIC_MODEL) > 0, "ANTHROPIC_MODEL should be set"
        assert isinstance(
            config.ANTHROPIC_MODEL, str
        ), "ANTHROPIC_MODEL should be a string"
        assert config.ANTHROPIC_MODEL.startswith(
            "claude"
        ), "ANTHROPIC_MODEL should be a Claude model"

        # Should use env value if set, otherwise default
        env_model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        assert (
            config.ANTHROPIC_MODEL == env_model
        ), "Config should load ANTHROPIC_MODEL from environment or use default"

        # EMBEDDING_MODEL should be set (either from env or default)
        assert len(config.EMBEDDING_MODEL) > 0, "EMBEDDING_MODEL should be set"
        assert isinstance(
            config.EMBEDDING_MODEL, str
        ), "EMBEDDING_MODEL should be a string"

    def test_config_values_for_production_readiness(self):
        """Test that config values are suitable for production"""
        # MAX_RESULTS should be reasonable (not too high to avoid excessive API costs)
        assert (
            config.MAX_RESULTS <= 20
        ), f"MAX_RESULTS ({config.MAX_RESULTS}) is very high and could cause expensive API calls"

        # MAX_HISTORY should be reasonable
        assert (
            config.MAX_HISTORY <= 10
        ), f"MAX_HISTORY ({config.MAX_HISTORY}) is very high and could cause long context windows"

        # Chunk settings should be optimized for the embedding model
        if "MiniLM" in config.EMBEDDING_MODEL:
            # MiniLM models typically work well with 256-512 token chunks
            # Roughly 200-400 characters per 100 tokens
            assert (
                200 <= config.CHUNK_SIZE <= 1200
            ), "Chunk size may not be optimal for MiniLM embedding model"


if __name__ == "__main__":
    pytest.main([__file__])
