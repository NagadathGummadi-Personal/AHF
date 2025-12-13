"""
Real Tests for Metrics Store.

Tests the in-memory and DynamoDB metrics stores.
No mocks - uses real storage implementations.
"""

import pytest
import time
from core.memory import (
    InMemoryMetricsStore,
    DynamoDBMetricsStore,
    create_metrics_store,
)


class TestInMemoryMetricsStore:
    """Tests for in-memory metrics store."""
    
    @pytest.mark.asyncio
    async def test_record_and_retrieve(self, metrics_store):
        """Test recording and retrieving metrics."""
        entry_id = await metrics_store.record(
            entity_id="prompt-123",
            entity_type="prompt",
            metric_type="evaluation",
            scores={"relevance": 0.95, "coherence": 0.88},
            metadata={"evaluator": "llm", "model": "gpt-4"}
        )
        
        assert entry_id is not None
        
        # Retrieve
        metrics = await metrics_store.get_metrics("prompt-123")
        
        assert len(metrics) == 1
        assert metrics[0]["scores"]["relevance"] == 0.95
        assert metrics[0]["metadata"]["evaluator"] == "llm"
    
    @pytest.mark.asyncio
    async def test_multiple_entries(self, metrics_store):
        """Test storing multiple entries for same entity."""
        for i in range(5):
            await metrics_store.record(
                entity_id="prompt-multi",
                entity_type="prompt",
                metric_type="evaluation",
                scores={"relevance": 0.8 + (i * 0.02)},
            )
        
        metrics = await metrics_store.get_metrics("prompt-multi")
        
        assert len(metrics) == 5
    
    @pytest.mark.asyncio
    async def test_get_aggregated(self, metrics_store):
        """Test aggregated metrics computation."""
        # Add varied scores
        scores = [0.7, 0.8, 0.9, 0.85, 0.75]
        for score in scores:
            await metrics_store.record(
                entity_id="prompt-agg",
                entity_type="prompt",
                metric_type="evaluation",
                scores={"relevance": score},
            )
        
        aggregated = await metrics_store.get_aggregated("prompt-agg")
        
        assert aggregated["total_entries"] == 5
        assert aggregated["entity_id"] == "prompt-agg"
        
        # Check average
        expected_avg = sum(scores) / len(scores)
        assert abs(aggregated["avg_scores"]["relevance"] - expected_avg) < 0.01
        
        # Check min/max
        assert aggregated["min_scores"]["relevance"] == min(scores)
        assert aggregated["max_scores"]["relevance"] == max(scores)
        
        # Check percentiles exist
        assert "relevance" in aggregated["percentiles"]
    
    @pytest.mark.asyncio
    async def test_filter_by_metric_type(self, metrics_store):
        """Test filtering by metric type."""
        # Add different metric types
        await metrics_store.record(
            entity_id="prompt-filter",
            entity_type="prompt",
            metric_type="evaluation",
            scores={"relevance": 0.9},
        )
        await metrics_store.record(
            entity_id="prompt-filter",
            entity_type="prompt",
            metric_type="runtime",
            scores={"latency_ms": 150},
        )
        
        # Filter by evaluation
        eval_metrics = await metrics_store.get_metrics(
            "prompt-filter",
            metric_type="evaluation"
        )
        
        assert len(eval_metrics) == 1
        assert "relevance" in eval_metrics[0]["scores"]
    
    @pytest.mark.asyncio
    async def test_list_entities(self, metrics_store):
        """Test listing all entities."""
        # Add metrics for multiple entities
        for i in range(3):
            await metrics_store.record(
                entity_id=f"entity-{i}",
                entity_type="prompt",
                metric_type="evaluation",
                scores={"relevance": 0.9},
            )
        
        entities = await metrics_store.list_entities()
        
        assert len(entities) >= 3
        assert "entity-0" in entities
    
    @pytest.mark.asyncio
    async def test_delete_metrics(self, metrics_store):
        """Test deleting metrics."""
        await metrics_store.record(
            entity_id="to-delete",
            entity_type="prompt",
            metric_type="evaluation",
            scores={"relevance": 0.9},
        )
        
        # Verify exists
        metrics = await metrics_store.get_metrics("to-delete")
        assert len(metrics) == 1
        
        # Delete
        deleted = await metrics_store.delete_metrics("to-delete")
        assert deleted == 1
        
        # Verify gone
        metrics = await metrics_store.get_metrics("to-delete")
        assert len(metrics) == 0
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when over capacity."""
        store = InMemoryMetricsStore(
            cache_max_entries=5,  # Small limit
            max_samples_per_entity=10,
        )
        
        # Add more entities than limit
        for i in range(10):
            await store.record(
                entity_id=f"lru-entity-{i}",
                entity_type="prompt",
                metric_type="evaluation",
                scores={"relevance": 0.9},
            )
        
        entities = await store.list_entities()
        
        # Should have at most 5 entities (LRU eviction)
        assert len(entities) <= 5
        
        # Most recent should still be there
        assert "lru-entity-9" in entities


class TestDynamoDBMetricsStoreLocalFallback:
    """Tests for DynamoDB metrics store with local fallback."""
    
    @pytest.mark.asyncio
    async def test_local_fallback_creation(self, temp_storage_path):
        """Test that local fallback works when DynamoDB unavailable."""
        store = DynamoDBMetricsStore(
            table_name="nonexistent_table",
            use_local_fallback=True,
            local_path=temp_storage_path,
        )
        
        # Should fall back to local
        entry_id = await store.record(
            entity_id="local-test-1",
            entity_type="prompt",
            metric_type="evaluation",
            scores={"relevance": 0.9},
        )
        
        assert entry_id is not None
        assert store.is_using_local == True
    
    @pytest.mark.asyncio
    async def test_local_persistence(self, temp_storage_path):
        """Test that local fallback persists to files."""
        import os
        
        store = DynamoDBMetricsStore(
            table_name="nonexistent_table",
            use_local_fallback=True,
            local_path=temp_storage_path,
        )
        
        await store.record(
            entity_id="persist-test",
            entity_type="prompt",
            metric_type="evaluation",
            scores={"relevance": 0.9},
        )
        
        # Check that file was created
        files = list(os.listdir(temp_storage_path))
        assert len(files) > 0
    
    @pytest.mark.asyncio
    async def test_local_load_after_clear(self, temp_storage_path):
        """Test loading from local after clearing memory cache."""
        store = DynamoDBMetricsStore(
            table_name="nonexistent_table",
            use_local_fallback=True,
            local_path=temp_storage_path,
        )
        
        await store.record(
            entity_id="reload-test",
            entity_type="prompt",
            metric_type="evaluation",
            scores={"relevance": 0.9},
        )
        
        # Create new store instance (simulates restart)
        store2 = DynamoDBMetricsStore(
            table_name="nonexistent_table",
            use_local_fallback=True,
            local_path=temp_storage_path,
        )
        
        # Should load from local file
        metrics = await store2.get_metrics("reload-test")
        
        assert len(metrics) == 1
        assert metrics[0]["scores"]["relevance"] == 0.9


class TestMetricsStoreFactory:
    """Tests for metrics store factory function."""
    
    def test_create_memory_store(self):
        """Test creating in-memory store via factory."""
        store = create_metrics_store("memory")
        
        assert isinstance(store, InMemoryMetricsStore)
    
    def test_create_dynamodb_store(self, temp_storage_path):
        """Test creating DynamoDB store via factory."""
        store = create_metrics_store(
            "dynamodb",
            use_local_fallback=True,
            local_path=temp_storage_path,
        )
        
        assert isinstance(store, DynamoDBMetricsStore)

