import pytest
from src.data.multivariate import (
    MultivariateAnalyzer,
    calculate_cramers_v,
    interpret_cramers_v,
)
from src.data.database import get_multivariate_report_from_db


def test_calculate_cramers_v():
    # Perfect independence (chi2 = 0)
    assert calculate_cramers_v(0.0, 1500, 2, 2) == 0.0
    # Boundary / negative checks
    assert calculate_cramers_v(10.0, 0, 2, 2) == 0.0
    assert calculate_cramers_v(10.0, 1500, 1, 2) == 0.0

    # Normal calculation: chi2 = 1251.93, n = 1500, r = 5, k = 12 -> min(4, 11) = 4
    v = calculate_cramers_v(1251.93, 1500, 5, 12)
    assert 0.40 <= v <= 0.50
    assert "Sangat Kuat" in interpret_cramers_v(v)


def test_multivariate_analyzer_pipeline():
    analyzer = MultivariateAnalyzer()
    df = analyzer.load_data()
    assert len(df) == 1500

    # 1. Independence tests
    ind_tests = analyzer.compute_independence_tests(df)
    assert len(ind_tests) >= 5
    for t in ind_tests:
        assert "chi2_statistic" in t
        assert "cramers_v" in t
        assert 0.0 <= t["cramers_v"] <= 1.0
        assert t["p_value"] < 0.05  # all primary pairs are significant

    # 2. Crosstabs
    crosstabs = analyzer.compute_crosstabs(df)
    assert "gender_x_articleType" in crosstabs
    assert "usage_x_articleType" in crosstabs
    assert "colour_x_articleType" in crosstabs
    ga = crosstabs["gender_x_articleType"]
    assert len(ga["rows"]) > 0
    assert len(ga["columns"]) > 0
    assert len(ga["matrix"]) == len(ga["rows"])

    # 3. NPMI
    npmi_data = analyzer.compute_pairwise_npmi(df)
    assert npmi_data["total_evaluated_cross_pairs"] > 0
    assert len(npmi_data["top_positive_npmi"]) > 0
    assert len(npmi_data["top_negative_npmi"]) > 0
    for p in npmi_data["top_positive_npmi"]:
        assert -1.0 <= p["npmi"] <= 1.0
        assert p["lift"] > 0

    # 4. Benchmark queries profiling
    bm_queries = analyzer.analyze_benchmark_queries(df)
    assert len(bm_queries) == 30
    assert bm_queries[0]["id"] == "Q01"
    assert bm_queries[-1]["id"] == "Q30"

    # 5. Full analysis report
    full_report = analyzer.run_full_analysis()
    assert "independence_tests" in full_report
    assert "crosstabs" in full_report
    assert "pairwise_npmi" in full_report
    assert "benchmark_query_cooccurrence" in full_report
    assert "research_synthesis" in full_report
    assert len(full_report["research_synthesis"]) == 4


def test_get_multivariate_report_from_db():
    report = get_multivariate_report_from_db()
    assert report is not None
    assert "independence_tests" in report
    assert "pairwise_npmi" in report
    assert len(report["independence_tests"]) >= 5
