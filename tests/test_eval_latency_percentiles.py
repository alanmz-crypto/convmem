"""Latency percentile outputs use raw samples and the frozen rank rule."""

from eval_corpus.runner import LatencyReport, LatencySample, latency_report_to_dict
from eval_corpus.subprocess_compare import LatencyReport as WorkerLatencyReport
from eval_corpus.subprocess_compare import latency_summary


def test_runner_latency_report_uses_nearest_rank_and_raw_samples():
    samples = [float(index) + 0.123456 for index in range(1, 21)]
    report = LatencyReport(
        view="embedding_influenced",
        samples=[
            LatencySample(
                query="q",
                view="embedding_influenced",
                elapsed_ms=value,
            )
            for value in samples
        ],
        count=20,
        mean_ms=sum(samples) / 20,
        p50_ms=samples[9],
        p95_ms=samples[18],
        max_ms=samples[-1],
    )
    output = latency_report_to_dict(report)
    assert output["percentile_algorithm"] == "nearest_rank_v1"
    assert output["p50_ms"] == samples[9]
    assert output["p95_ms"] == samples[18]
    assert output["samples"][0]["elapsed_ms"] == samples[0]


def test_worker_latency_summary_retains_raw_samples_and_percentiles():
    samples = [float(index) + 0.123456 for index in range(1, 21)]
    report = WorkerLatencyReport(
        retrieval_ms={
            "embedding_influenced": {
                "baseline": samples,
                "challenger": list(reversed(samples)),
            }
        },
        process_startup_ms={"baseline": 2.5, "challenger": 3.5},
    )
    output = latency_summary(report)
    baseline = output["retrieval_ms"]["embedding_influenced"]["baseline"]
    assert baseline["percentile_algorithm"] == "nearest_rank_v1"
    assert baseline["p50"] == samples[9]
    assert baseline["p95"] == samples[18]
    assert baseline["samples"][0] == samples[0]
