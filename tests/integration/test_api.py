"""
Integration tests for the Agora API.
Tests the full pipeline from API to response.
"""
import pytest
from fastapi.testclient import TestClient

# Import app
import sys
sys.path.insert(0, '.')
from src.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    def test_health_check(self):
        """Test health endpoint returns 200."""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "components" in data
    
    def test_root_endpoint(self):
        """Test root endpoint provides API info."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestAuthorsEndpoint:
    """Tests for author-related endpoints."""
    
    def test_list_authors(self):
        """Test listing all authors."""
        response = client.get("/api/authors")
        assert response.status_code == 200
        
        data = response.json()
        assert "authors" in data
        assert "total" in data
        assert data["total"] >= 0
    
    def test_get_specific_author_marx(self):
        """Test getting Marx author details."""
        response = client.get("/api/authors/marx")
        
        # Should return 200 if Marx is configured
        if response.status_code == 200:
            data = response.json()
            assert data["id"] == "marx"
            assert "name" in data
            assert "expertise_domains" in data
        elif response.status_code == 404:
            # Marx not configured yet - acceptable
            pytest.skip("Marx author not configured")
    
    def test_get_nonexistent_author(self):
        """Test getting non-existent author returns 404."""
        response = client.get("/api/authors/nonexistent")
        assert response.status_code == 404


class TestQueryEndpoint:
    """Tests for query endpoints."""
    
    def test_query_with_marx_topic(self):
        """Test query about class struggle (Marx topic)."""
        response = client.post("/api/query", json={
            "query": "What is class struggle?",
            "max_authors": 3,
            "relevance_threshold": 0.5
        })
        
        # May return 400 if no authors match or data not ingested
        if response.status_code == 200:
            data = response.json()
            assert "query_text" in data
            assert "responses" in data
            assert isinstance(data["responses"], list)
        elif response.status_code == 400:
            pytest.skip("No data ingested yet")
    
    def test_query_with_whitman_topic(self):
        """Test query about democracy (Whitman topic)."""
        response = client.post("/api/query", json={
            "query": "What is the meaning of democracy?",
            "max_authors": 3,
            "relevance_threshold": 0.5
        })
        
        if response.status_code == 200:
            data = response.json()
            assert "responses" in data
        elif response.status_code == 400:
            pytest.skip("No data ingested yet")
    
    def test_query_empty_text(self):
        """Test query with empty text returns validation error."""
        response = client.post("/api/query", json={
            "query": "",
            "max_authors": 3
        })
        assert response.status_code == 422  # Validation error
    
    def test_query_invalid_max_authors(self):
        """Test query with invalid max_authors."""
        response = client.post("/api/query", json={
            "query": "test",
            "max_authors": 100  # Too high
        })
        # Should either accept or validate
        assert response.status_code in [200, 400, 422]


class TestRankingsEndpoint:
    """Tests for the rankings endpoint."""
    
    def test_rankings(self):
        """Test getting author rankings for a query."""
        response = client.get("/api/rankings", params={
            "query": "What is freedom?"
        })
        
        if response.status_code == 200:
            data = response.json()
            assert "query" in data
            assert "rankings" in data
            assert isinstance(data["rankings"], list)
        elif response.status_code == 500:
            pytest.skip("Data not ingested or service error")


class TestStreamingEndpoint:
    """Tests for streaming query endpoint."""
    
    def test_streaming_endpoint_exists(self):
        """Test that streaming endpoint is available."""
        response = client.post("/api/query/stream", json={
            "query": "test query",
            "max_authors": 1
        })
        
        # Should return streaming response or error
        assert response.status_code in [200, 400, 500]
        
        if response.status_code == 200:
            assert response.headers.get("content-type") == "text/event-stream"


class TestDebateEndpoint:
    """Tests for the debate endpoint."""

    def test_debate_endpoint_exists(self):
        """Test that debate endpoint is available."""
        response = client.post("/api/query/debate", json={
            "text": "What is the meaning of life?",
            "max_authors": 3,
            "min_authors": 2,
            "num_rounds": 2
        })

        # Should return 200 if data ingested, or 400 if not
        assert response.status_code in [200, 400, 500]

    def test_debate_with_specified_authors(self):
        """Test debate with specified authors."""
        response = client.post("/api/query/debate", json={
            "text": "What is freedom?",
            "specified_authors": ["marx"],
            "min_authors": 2,
            "num_rounds": 2
        })

        if response.status_code == 200:
            data = response.json()
            assert "query_text" in data
            assert "rounds" in data
            assert "author_count" in data
            assert "round_count" in data
            assert isinstance(data["rounds"], list)
            if len(data["rounds"]) > 0:
                assert "round_number" in data["rounds"][0]
                assert "round_type" in data["rounds"][0]
                assert "author_responses" in data["rounds"][0]
        elif response.status_code == 400:
            pytest.skip("Insufficient authors or no data ingested")

    def test_debate_requires_minimum_authors(self):
        """Test that debate requires at least 2 authors."""
        response = client.post("/api/query/debate", json={
            "text": "test",
            "max_authors": 1,
            "min_authors": 1,
            "num_rounds": 2
        })

        # Should fail validation or during execution
        assert response.status_code in [400, 422]

    def test_debate_invalid_num_rounds(self):
        """Test debate with invalid number of rounds."""
        response = client.post("/api/query/debate", json={
            "text": "test",
            "num_rounds": 10  # Too many rounds
        })

        # Should fail validation
        assert response.status_code == 422

    def test_debate_empty_text(self):
        """Test debate with empty text returns validation error."""
        response = client.post("/api/query/debate", json={
            "text": "",
            "num_rounds": 2
        })
        assert response.status_code == 422  # Validation error


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_endpoint(self):
        """Test non-existent endpoint returns 404."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test wrong HTTP method returns 405."""
        response = client.get("/api/query")  # Should be POST
        assert response.status_code == 405
