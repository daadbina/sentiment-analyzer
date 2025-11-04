"""
Performance benchmarks for NER Entity Linking Service.
"""
import pytest
import time
from datetime import datetime
from src.normalization.entity_normalizer import EntityNormalizer
from src.linking.entity_linker import EntityLinker
from src.ner.orchestrator import NEROrchestrator
from src.models import Entity, EntityType


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmarks for NER service."""

    @pytest.fixture
    def normalizer(self):
        """Create entity normalizer."""
        return EntityNormalizer()

    @pytest.fixture
    def linker(self):
        """Create entity linker."""
        return EntityLinker()

    @pytest.fixture
    def orchestrator(self):
        """Create NER orchestrator."""
        return NEROrchestrator()

    def test_normalization_throughput(self, normalizer: EntityNormalizer):
        """Benchmark entity normalization throughput."""
        entities = [
            "John Smith",
            "Dr. Jane Doe",
            "Microsoft Corporation",
            "Barack Hussein Obama",
            "The United States of America",
        ] * 100  # 500 entities
        
        start_time = time.time()
        for entity in entities:
            normalizer.normalize(entity)
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = len(entities) / duration
        
        # Should process at least 1000 entities per second
        assert throughput >= 1000, f"Throughput {throughput} < 1000 entities/sec"
        print(f"Normalization throughput: {throughput:.0f} entities/sec")

    def test_entity_linking_latency(self, linker: EntityLinker):
        """Benchmark entity linking latency."""
        entity_text = "Barack Obama"
        entity_type = "PERSON"
        language = "en"
        
        latencies = []
        for _ in range(10):
            start_time = time.time()
            linker.link_entity(
                entity_text=entity_text,
                entity_type=entity_type,
                language=language,
            )
            end_time = time.time()
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        # Average latency should be < 500ms
        assert avg_latency < 500, f"Average latency {avg_latency}ms > 500ms"
        print(f"Entity linking - Avg: {avg_latency:.1f}ms, P95: {p95_latency:.1f}ms")

    def test_ner_extraction_latency(self, orchestrator: NEROrchestrator):
        """Benchmark NER extraction latency."""
        text = "John Smith works at Microsoft in Seattle. He is the CEO of the company."
        language = "en"
        
        latencies = []
        for _ in range(5):
            start_time = time.time()
            orchestrator.extract_entities(text, language)
            end_time = time.time()
            latencies.append((end_time - start_time) * 1000)  # Convert to ms
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        # Average latency should be < 1000ms
        assert avg_latency < 1000, f"Average latency {avg_latency}ms > 1000ms"
        print(f"NER extraction - Avg: {avg_latency:.1f}ms, P95: {p95_latency:.1f}ms")

    def test_multilingual_extraction_performance(self, orchestrator: NEROrchestrator):
        """Benchmark multilingual extraction performance."""
        test_cases = [
            ("John Smith works at Microsoft", "en"),
            ("محمد علي يعمل في شركة", "ar"),
            ("Владимир Путин работает в Кремле", "ru"),
            ("张三在微软工作", "zh"),
        ]
        
        for text, language in test_cases:
            start_time = time.time()
            orchestrator.extract_entities(text, language)
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000
            print(f"{language}: {latency:.1f}ms")
            
            # Each language should complete in < 2000ms
            assert latency < 2000, f"Language {language} latency {latency}ms > 2000ms"

    def test_batch_processing_throughput(self, orchestrator: NEROrchestrator):
        """Benchmark batch processing throughput."""
        articles = [
            "John Smith works at Microsoft in Seattle.",
            "Jane Doe is the CEO of Apple Inc.",
            "Google is located in Mountain View, California.",
            "Amazon was founded by Jeff Bezos.",
            "Tesla is an electric vehicle company.",
        ] * 20  # 100 articles
        
        start_time = time.time()
        for article in articles:
            orchestrator.extract_entities(article, "en")
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = len(articles) / duration
        
        # Should process at least 10 articles per second
        assert throughput >= 10, f"Throughput {throughput} < 10 articles/sec"
        print(f"Batch processing throughput: {throughput:.1f} articles/sec")

    def test_memory_efficiency(self, orchestrator: NEROrchestrator):
        """Test memory efficiency of model caching."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process multiple articles
        for i in range(50):
            text = f"Article {i}: John Smith works at Microsoft in Seattle."
            orchestrator.extract_entities(text, "en")
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 500MB)
        assert memory_increase < 500, f"Memory increase {memory_increase}MB > 500MB"
        print(f"Memory efficiency - Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB, Increase: {memory_increase:.1f}MB")

    def test_context_extraction_performance(self, orchestrator: NEROrchestrator):
        """Benchmark context extraction performance."""
        text = "John Smith works at Microsoft in Seattle. He is the CEO of the company. Microsoft is located in Redmond, Washington."
        
        start_time = time.time()
        for _ in range(100):
            orchestrator.extract_context(text, 10, 20)
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = 100 / duration
        
        # Should extract context at least 1000 times per second
        assert throughput >= 1000, f"Throughput {throughput} < 1000 extractions/sec"
        print(f"Context extraction throughput: {throughput:.0f} extractions/sec")

    def test_coverage_calculation_performance(self, orchestrator: NEROrchestrator):
        """Benchmark coverage calculation performance."""
        entities = [
            Entity(
                entity_id=f"e{i}",
                text=f"Entity {i}",
                entity_type="PERSON",
                confidence=0.95,
                start_char=i*10,
                end_char=i*10+8,
                context_snippet=f"Context for entity {i}",
            )
            for i in range(100)
        ]
        
        start_time = time.time()
        for _ in range(1000):
            orchestrator.calculate_coverage(entities, 1000)
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = 1000 / duration
        
        # Should calculate coverage at least 10000 times per second
        assert throughput >= 10000, f"Throughput {throughput} < 10000 calculations/sec"
        print(f"Coverage calculation throughput: {throughput:.0f} calculations/sec")

