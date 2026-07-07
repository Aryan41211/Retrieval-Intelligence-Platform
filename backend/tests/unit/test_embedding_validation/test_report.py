"""Tests for benchmark report."""



from backend.embedding_validation.benchmark_report import BenchmarkReport
from backend.embedding_validation.embedding_benchmark import BenchmarkResult, LatencyMetrics
from backend.embedding_validation.embedding_statistics import EmbeddingQualityReport, NormStatistics
from backend.embedding_validation.similarity_analyzer import SimilarityMetrics


class TestBenchmarkReport:
    """Tests for BenchmarkReport class."""

    def test_generate_markdown(self):
        report = BenchmarkReport()
        benchmarking_result = BenchmarkResult(
            provider_name="test-provider",
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=100,
            total_embeddings=10,
            total_chunks=10,
            latency_metrics=LatencyMetrics(average_latency_ms=50.0),
        )
        report.add_benchmark_result("test", benchmarking_result)

        md = report.generate_markdown()

        assert "# Embedding Benchmark Report" in md
        assert "test-provider" in md
        assert "test-model" in md

    def test_generate_json(self):
        report = BenchmarkReport()
        benchmarking_result = BenchmarkResult(
            provider_name="test-provider",
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=100,
            total_embeddings=10,
            total_chunks=10,
            latency_metrics=LatencyMetrics(average_latency_ms=50.0),
        )
        report.add_benchmark_result("test", benchmarking_result)

        json_data = report.generate_json()

        assert json_data["title"] == "Embedding Benchmark Report"
        assert "benchmarks" in json_data
        assert "test" in json_data["benchmarks"]

    def test_save_markdown(self, tmp_path):
        report = BenchmarkReport()
        benchmarking_result = BenchmarkResult(
            provider_name="test-provider",
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=100,
            total_embeddings=10,
            total_chunks=10,
            latency_metrics=LatencyMetrics(average_latency_ms=50.0),
        )
        report.add_benchmark_result("test", benchmarking_result)

        md_path = tmp_path / "report.md"
        report.save_markdown(md_path)

        assert md_path.exists()
        content = md_path.read_text()
        assert "# Embedding Benchmark Report" in content

    def test_save_json(self, tmp_path):
        report = BenchmarkReport()
        benchmarking_result = BenchmarkResult(
            provider_name="test-provider",
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=100,
            total_embeddings=10,
            total_chunks=10,
            latency_metrics=LatencyMetrics(average_latency_ms=50.0),
        )
        report.add_benchmark_result("test", benchmarking_result)

        json_path = tmp_path / "report.json"
        report.save_json(json_path)

        assert json_path.exists()

    def test_add_statistics(self):
        report = BenchmarkReport()
        quality_report = EmbeddingQualityReport(
            total_embeddings=5,
            embedding_dimension=100,
            norm_statistics=NormStatistics(mean_norm=1.0),
            warnings=["test warning"],
        )
        report.add_statistics("quality", quality_report)

        json_data = report.generate_json()
        assert "quality" in json_data["statistics"]

    def test_add_similarity_metrics(self):
        report = BenchmarkReport()
        sim_metrics = SimilarityMetrics(average_similarity=0.5)
        report.add_similarity_metrics("similarity", sim_metrics)

        json_data = report.generate_json()
        assert "similarity" in json_data["similarity_metrics"]

    def test_report_with_errors(self):
        report = BenchmarkReport()
        benchmarking_result = BenchmarkResult(
            provider_name="test-provider",
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=100,
            total_embeddings=10,
            total_chunks=10,
            latency_metrics=LatencyMetrics(average_latency_ms=50.0),
            errors=["test error"],
        )
        report.add_benchmark_result("test", benchmarking_result)

        md = report.generate_markdown()
        assert "Errors" in md

    def test_report_with_cache_stats(self):
        report = BenchmarkReport()
        benchmarking_result = BenchmarkResult(
            provider_name="test-provider",
            model_name="test-model",
            model_version="1.0",
            embedding_dimension=100,
            total_embeddings=10,
            total_chunks=10,
            latency_metrics=LatencyMetrics(average_latency_ms=50.0),
            cache_hits=8,
            cache_misses=2,
        )
        report.add_benchmark_result("test", benchmarking_result)

        md = report.generate_markdown()
        assert "Cache Statistics" in md
        assert "80.0%" in md
