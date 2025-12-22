"""
Comprehensive Data Quality Validation for ABIDES LOB Data

This script assesses the synthetic market data against ML-readiness criteria:
1. LOB Depth Density (5-level coverage)
2. Spread Statistics & Distribution
3. Volatility Patterns across Regimes
4. Regime Distribution Balance
5. Microstructure Feature Completeness
6. Temporal Coverage & Anomalies
7. Overall ML Readiness Score

Usage:
    python 9_validate_data_quality.py                          # Validates TRAIN.parquet (default)
    python 9_validate_data_quality.py --input data/VAL.parquet # Validate specific file
    python 9_validate_data_quality.py --input data/TEST_OOD.parquet
    python 9_validate_data_quality.py --batch-dir data/training_batches
"""

import argparse
import glob
import os

import numpy as np
import polars as pl
from tabulate import tabulate


class DataQualityValidator:
    def __init__(self, data_source, is_batch=False):
        self.data_source = data_source
        self.is_batch = is_batch
        self.df = None
        self.metrics = {}
        self.warnings = []
        self.passed_checks = []

    def load_data(self):
        """Load data from single file or batch directory"""
        print(f"📂 Loading data from: {self.data_source}")

        if self.is_batch:
            files = glob.glob(f"{self.data_source}/*.parquet")
            if not files:
                raise FileNotFoundError(f"No parquet files found in {self.data_source}")
            print(f"   Found {len(files)} day-files")
            self.df = pl.scan_parquet(f"{self.data_source}/*.parquet").collect()
        else:
            if not os.path.exists(self.data_source):
                raise FileNotFoundError(f"File not found: {self.data_source}")
            self.df = pl.read_parquet(self.data_source)

        print(f"   Loaded {self.df.height:,} snapshots\n")

    def validate_depth_density(self):
        """Check LOB depth coverage across all 5 levels"""
        print("=" * 80)
        print("📊 VALIDATION 1: LOB Depth Density (5-Level Coverage)")
        print("=" * 80)

        total_rows = self.df.height

        # Check each level
        level_stats = []
        for i in range(1, 6):
            bid_col = f"bid_px_{i}"
            ask_col = f"ask_px_{i}"

            bid_valid = self.df.filter(pl.col(bid_col) > 0).height
            ask_valid = self.df.filter(pl.col(ask_col) > 0).height

            bid_pct = (bid_valid / total_rows) * 100
            ask_pct = (ask_valid / total_rows) * 100

            level_stats.append(
                {
                    "Level": i,
                    "Bid Coverage": f"{bid_pct:.2f}%",
                    "Ask Coverage": f"{ask_pct:.2f}%",
                    "Both Sides": f"{min(bid_pct, ask_pct):.2f}%",
                }
            )

            # Store for scoring
            self.metrics[f"level_{i}_coverage"] = min(bid_pct, ask_pct)

        print(tabulate(level_stats, headers="keys", tablefmt="grid"))

        # Depth Quality Score
        l5_coverage = self.metrics["level_5_coverage"]
        if l5_coverage >= 80:
            self.passed_checks.append("✅ Level 5 depth excellent (≥80%)")
        elif l5_coverage >= 50:
            self.warnings.append("⚠️  Level 5 depth acceptable but thin (50-80%)")
        else:
            self.warnings.append(
                "❌ Level 5 depth insufficient (<50%) - need more value agents"
            )

        print(f"\n🎯 Depth Quality Score: {l5_coverage:.1f}%")
        print()

    def validate_spread_statistics(self):
        """Analyze spread distribution and statistics"""
        print("=" * 80)
        print("📏 VALIDATION 2: Spread Statistics & Distribution")
        print("=" * 80)

        # Calculate spread
        df_with_spread = self.df.with_columns(
            [
                (pl.col("ask_px_1") - pl.col("bid_px_1")).alias("spread_abs"),
                (
                    (pl.col("ask_px_1") - pl.col("bid_px_1"))
                    / pl.col("mid_price")
                    * 10000
                ).alias("spread_bps"),
            ]
        ).filter(pl.col("mid_price") > 0)

        spread_stats = df_with_spread.select(
            [
                pl.col("spread_abs").mean().alias("mean_abs"),
                pl.col("spread_abs").median().alias("median_abs"),
                pl.col("spread_abs").std().alias("std_abs"),
                pl.col("spread_bps").mean().alias("mean_bps"),
                pl.col("spread_bps").median().alias("median_bps"),
                pl.col("spread_bps").quantile(0.95).alias("p95_bps"),
                pl.col("spread_bps").quantile(0.99).alias("p99_bps"),
            ]
        ).to_dicts()[0]

        stats_table = [
            ["Metric", "Absolute", "Basis Points"],
            [
                "Mean",
                f"{spread_stats['mean_abs']:.2f}",
                f"{spread_stats['mean_bps']:.2f}",
            ],
            [
                "Median",
                f"{spread_stats['median_abs']:.2f}",
                f"{spread_stats['median_bps']:.2f}",
            ],
            ["Std Dev", f"{spread_stats['std_abs']:.2f}", "—"],
            ["95th Percentile", "—", f"{spread_stats['p95_bps']:.2f}"],
            ["99th Percentile", "—", f"{spread_stats['p99_bps']:.2f}"],
        ]

        print(tabulate(stats_table, headers="firstrow", tablefmt="grid"))

        # Store metrics
        self.metrics["mean_spread_bps"] = spread_stats["mean_bps"]
        self.metrics["spread_variability"] = (
            spread_stats["std_abs"] / spread_stats["mean_abs"]
        )

        # Validation
        if spread_stats["mean_bps"] < 1:
            self.warnings.append(
                "⚠️  Very tight spreads (<1 bps) - may not reflect real markets"
            )
        elif spread_stats["mean_bps"] > 100:
            self.warnings.append(
                "⚠️  Very wide spreads (>100 bps) - increase value agents or reduce sigma_n"
            )
        else:
            self.passed_checks.append(
                f"✅ Realistic spread range ({spread_stats['mean_bps']:.1f} bps)"
            )

        print()

    def validate_volatility_patterns(self):
        """Analyze volatility characteristics"""
        print("=" * 80)
        print("📈 VALIDATION 3: Volatility Patterns & Dynamics")
        print("=" * 80)

        # Calculate returns (log returns for numerical stability)
        df_volatility = self.df.with_columns(
            [
                (pl.col("mid_price").log() - pl.col("mid_price").log().shift(1)).alias(
                    "log_return"
                ),
            ]
        ).filter(pl.col("log_return").is_not_null())

        # Overall volatility
        vol_stats = df_volatility.select(
            [
                (pl.col("log_return").std() * np.sqrt(252 * 6.25 * 3600)).alias(
                    "annual_vol"
                ),  # Annualized
                pl.col("log_return").abs().mean().alias("mean_abs_return"),
                pl.col("log_return").skew().alias("skewness"),
                pl.col("log_return").kurtosis().alias("kurtosis"),
            ]
        ).to_dicts()[0]

        vol_table = [
            ["Metric", "Value", "Interpretation"],
            [
                "Annualized Volatility",
                f"{vol_stats['annual_vol']:.2%}",
                "Market-wide vol",
            ],
            [
                "Mean Absolute Return",
                f"{vol_stats['mean_abs_return']:.6f}",
                "Per-snapshot movement",
            ],
            ["Skewness", f"{vol_stats['skewness']:.3f}", "Asymmetry (0=symmetric)"],
            ["Kurtosis", f"{vol_stats['kurtosis']:.3f}", "Fat tails (3=normal)"],
        ]

        print(tabulate(vol_table, headers="firstrow", tablefmt="grid"))

        # Store metrics
        self.metrics["annual_volatility"] = vol_stats["annual_vol"]
        self.metrics["kurtosis"] = vol_stats["kurtosis"]

        # Validation
        if vol_stats["annual_vol"] < 0.05:
            self.warnings.append("⚠️  Very low volatility (<5%) - increase fund_vol")
        elif vol_stats["annual_vol"] > 2.0:
            self.warnings.append(
                "⚠️  Extremely high volatility (>200%) - reduce fund_vol"
            )
        else:
            self.passed_checks.append(
                f"✅ Realistic volatility ({vol_stats['annual_vol']:.1%})"
            )

        if vol_stats["kurtosis"] > 10:
            self.passed_checks.append(
                f"✅ Fat tails detected (K={vol_stats['kurtosis']:.1f}) - good for stress testing"
            )

        print()

    def validate_regime_distribution(self):
        """Check regime balance if filenames contain regime info"""
        print("=" * 80)
        print("🎲 VALIDATION 4: Regime Distribution Balance")
        print("=" * 80)

        if not self.is_batch:
            print("⚠️  Regime analysis requires batch mode (--batch-dir)")
            print()
            return

        files = glob.glob(f"{self.data_source}/*.parquet")
        regime_counts = {}

        for f in files:
            basename = os.path.basename(f).replace(".parquet", "")
            parts = basename.split("_")

            if len(parts) >= 4:
                regime = parts[3]  # sim_day_SEED_REGIME
            else:
                regime = "LEGACY"

            regime_counts[regime] = regime_counts.get(regime, 0) + 1

        total = sum(regime_counts.values())
        regime_table = []

        for regime, count in sorted(regime_counts.items()):
            pct = (count / total) * 100
            regime_table.append(
                {
                    "Regime": regime,
                    "Days": count,
                    "Percentage": f"{pct:.1f}%",
                    "Target": "60%"
                    if regime == "STANDARD"
                    else "20%"
                    if regime in ["VOLATILE", "MOMENTUM"]
                    else "—",
                }
            )
            self.metrics[f"regime_{regime}_pct"] = pct

        print(tabulate(regime_table, headers="keys", tablefmt="grid"))

        # Validation
        if "STANDARD" in regime_counts:
            std_pct = self.metrics.get("regime_STANDARD_pct", 0)
            vol_pct = self.metrics.get("regime_VOLATILE_pct", 0)
            mom_pct = self.metrics.get("regime_MOMENTUM_pct", 0)

            if 55 <= std_pct <= 65 and 15 <= vol_pct <= 25 and 15 <= mom_pct <= 25:
                self.passed_checks.append(
                    "✅ Regime distribution balanced (60/20/20 target)"
                )
            else:
                self.warnings.append(
                    f"⚠️  Regime imbalance: STD={std_pct:.0f}%, VOL={vol_pct:.0f}%, MOM={mom_pct:.0f}%"
                )

        print()

    def validate_microstructure_readiness(self):
        """Check if data supports microstructure feature engineering"""
        print("=" * 80)
        print("🔬 VALIDATION 5: Microstructure Feature Readiness")
        print("=" * 80)

        # Check available columns
        required_cols = [
            "bid_px_1",
            "bid_qty_1",
            "ask_px_1",
            "ask_qty_1",
            "mid_price",
            "timestamp",
        ]
        depth_cols = [f"{side}_px_{i}" for side in ["bid", "ask"] for i in range(1, 6)]
        depth_qty_cols = [
            f"{side}_qty_{i}" for side in ["bid", "ask"] for i in range(1, 6)
        ]

        available = set(self.df.columns)
        feature_status = []

        # Basic features
        basic_ok = all(col in available for col in required_cols)
        feature_status.append(
            [
                "Basic LOB Features",
                "✅" if basic_ok else "❌",
                "bid/ask/mid prices, timestamp",
            ]
        )

        # Depth features
        depth_ok = all(col in available for col in depth_cols + depth_qty_cols)
        feature_status.append(
            ["5-Level Depth", "✅" if depth_ok else "❌", "Price-qty pairs for L1-L5"]
        )

        # Derivable features (check if we can compute them)
        spread_ok = self.df.filter((pl.col("ask_px_1") > pl.col("bid_px_1"))).height > 0
        feature_status.append(
            ["Spread Computation", "✅" if spread_ok else "❌", "ask_px_1 - bid_px_1"]
        )

        # Order flow imbalance (need quantities)
        qty_ok = (
            self.df.filter((pl.col("bid_qty_1") > 0) & (pl.col("ask_qty_1") > 0)).height
            > 0
        )
        feature_status.append(
            [
                "Order Flow Imbalance",
                "✅" if qty_ok else "❌",
                "(bid_qty - ask_qty) / total",
            ]
        )

        # Volatility (need sequential data)
        can_compute_vol = self.df.height > 100
        feature_status.append(
            [
                "Realized Volatility",
                "✅" if can_compute_vol else "❌",
                "rolling std of returns",
            ]
        )

        # Missing: Trade direction
        has_trade_info = "trade_direction" in available or "aggressor" in available
        feature_status.append(
            [
                "Trade Direction",
                "✅" if has_trade_info else "⚠️ ",
                "buyer/seller initiated (missing)",
            ]
        )

        # Missing: Order arrival timestamps
        has_order_flow = "order_arrival_rate" in available
        feature_status.append(
            [
                "Order Flow Metrics",
                "✅" if has_order_flow else "⚠️ ",
                "arrival rate, intensity (missing)",
            ]
        )

        print(
            tabulate(
                feature_status,
                headers=["Feature Category", "Status", "Description"],
                tablefmt="grid",
            )
        )

        # Scoring
        computable = sum(1 for row in feature_status[:5] if "✅" in row[1])
        self.metrics["microstructure_readiness"] = (computable / 5) * 100

        if computable >= 4:
            self.passed_checks.append(
                f"✅ Core microstructure features available ({computable}/5)"
            )
        else:
            self.warnings.append(
                f"❌ Insufficient microstructure features ({computable}/5)"
            )

        print()

    def validate_temporal_coverage(self):
        """Check temporal distribution and anomalies"""
        print("=" * 80)
        print("⏰ VALIDATION 6: Temporal Coverage & Anomalies")
        print("=" * 80)

        # Time range
        time_stats = self.df.select(
            [
                pl.col("timestamp").min().alias("start"),
                pl.col("timestamp").max().alias("end"),
                pl.col("timestamp").count().alias("snapshots"),
            ]
        ).to_dicts()[0]

        # Detect gaps (if sorted by time)
        df_sorted = self.df.sort("timestamp")
        time_diffs = df_sorted.select(
            [(pl.col("timestamp").diff()).alias("time_gap")]
        ).filter(pl.col("time_gap").is_not_null())

        gap_stats = time_diffs.select(
            [
                pl.col("time_gap").mean().alias("mean_gap"),
                pl.col("time_gap").median().alias("median_gap"),
                pl.col("time_gap").max().alias("max_gap"),
            ]
        ).to_dicts()[0]

        temporal_table = [
            ["Metric", "Value"],
            ["Total Snapshots", f"{time_stats['snapshots']:,}"],
            ["Time Range", f"{time_stats['start']} → {time_stats['end']}"],
            ["Mean Snapshot Gap", f"{gap_stats['mean_gap']}"],
            ["Median Snapshot Gap", f"{gap_stats['median_gap']}"],
            ["Max Gap (anomaly?)", f"{gap_stats['max_gap']}"],
        ]

        print(tabulate(temporal_table, headers="firstrow", tablefmt="grid"))

        # Validation
        if time_stats["snapshots"] < 1_000_000:
            self.warnings.append(
                f"⚠️  Low snapshot count ({time_stats['snapshots']:,}) - consider more days"
            )
        else:
            self.passed_checks.append(
                f"✅ Sufficient snapshots ({time_stats['snapshots']:,})"
            )

        print()

    def calculate_ml_readiness_score(self):
        """Compute overall ML readiness score"""
        print("=" * 80)
        print("🎯 OVERALL ML READINESS SCORE")
        print("=" * 80)

        # Scoring components (weighted)
        scores = {
            "Depth Density (25%)": min(
                self.metrics.get("level_5_coverage", 0) * 0.25, 25
            ),
            "Spread Quality (15%)": 15
            if 1 <= self.metrics.get("mean_spread_bps", 0) <= 100
            else 0,
            "Volatility (15%)": 15
            if 0.05 <= self.metrics.get("annual_volatility", 0) <= 2.0
            else 0,
            "Regime Balance (20%)": 20 if len(self.warnings) <= 2 else 10,
            "Microstructure (25%)": self.metrics.get("microstructure_readiness", 0)
            * 0.25,
        }

        total_score = sum(scores.values())

        score_table = []
        for component, score in scores.items():
            max_score = float(component.split("(")[1].strip("%)"))
            percentage = (score / max_score) * 100
            score_table.append(
                [component, f"{score:.1f}/{max_score}", f"{percentage:.0f}%"]
            )

        score_table.append(["—" * 30, "—" * 10, "—" * 10])
        score_table.append(
            ["**TOTAL**", f"**{total_score:.1f}/100**", f"**{total_score:.0f}%**"]
        )

        print(
            tabulate(
                score_table,
                headers=["Component", "Score", "Achievement"],
                tablefmt="grid",
            )
        )
        print()

        # Grade
        if total_score >= 85:
            grade = "A (Excellent)"
            emoji = "🏆"
        elif total_score >= 70:
            grade = "B (Good)"
            emoji = "✅"
        elif total_score >= 55:
            grade = "C (Acceptable)"
            emoji = "⚠️"
        else:
            grade = "D (Needs Improvement)"
            emoji = "❌"

        print(f"{emoji} **ML Readiness Grade: {grade}** ({total_score:.0f}/100)")
        print()

        return total_score

    def print_summary(self, score):
        """Print validation summary"""
        print("=" * 80)
        print("📋 VALIDATION SUMMARY")
        print("=" * 80)

        print(f"\n✅ **Passed Checks ({len(self.passed_checks)}):**")
        for check in self.passed_checks:
            print(f"   {check}")

        if self.warnings:
            print(f"\n⚠️  **Warnings & Recommendations ({len(self.warnings)}):**")
            for warning in self.warnings:
                print(f"   {warning}")

        print("\n" + "=" * 80)
        print("🎬 NEXT STEPS")
        print("=" * 80)

        if score >= 85:
            print("✨ Your data is ML-ready! Proceed to:")
            print("   1. Add target labels (future returns, spread changes, etc.)")
            print("   2. Split into train/val/test sets")
            print("   3. Begin model training")
        elif score >= 70:
            print("👍 Data quality is good. Before training:")
            print("   1. Address warnings above")
            print("   2. Add missing microstructure features")
            print("   3. Create target labels for supervised learning")
        else:
            print("🔧 Data needs improvement:")
            print("   1. Fix critical issues in warnings")
            print("   2. Re-generate data with adjusted ABIDES parameters")
            print("   3. Re-run this validation")

        print()

    def run_all_validations(self):
        """Run complete validation suite"""
        self.load_data()
        self.validate_depth_density()
        self.validate_spread_statistics()
        self.validate_volatility_patterns()
        self.validate_regime_distribution()
        self.validate_microstructure_readiness()
        self.validate_temporal_coverage()
        score = self.calculate_ml_readiness_score()
        self.print_summary(score)


def main():
    parser = argparse.ArgumentParser(
        description="Validate ABIDES LOB data quality for ML"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/TRAIN.parquet",
        help="Input parquet file (TRAIN.parquet, VAL.parquet, TEST.parquet, or TEST_OOD.parquet)",
    )
    parser.add_argument(
        "--batch-dir",
        type=str,
        default=None,
        help="Alternative: validate batch directory",
    )

    args = parser.parse_args()

    if args.batch_dir:
        validator = DataQualityValidator(args.batch_dir, is_batch=True)
    else:
        validator = DataQualityValidator(args.input, is_batch=False)

    validator.run_all_validations()


if __name__ == "__main__":
    main()
