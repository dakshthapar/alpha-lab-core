# Dataset Generation Guide

This guide covers generating synthetic market data using the ABIDES-based multi-regime simulation system.

> [!NOTE]
> **Prerequisites**: Complete [INSTALL_GUIDE.md](INSTALL_GUIDE.md) before proceeding.

---

## 📚 Table of Contents

- [Quick Start](#quick-start)
- [Multi-Regime Simulation](#multi-regime-simulation)
- [Large-Scale Parallel Generation](#large-scale-parallel-generation)
- [Data Processing Pipeline](#data-processing-pipeline)
- [Data Schema](#data-schema)
- [Data Validation](#data-validation)
- [Storage and Performance](#storage-and-performance)

---

## Quick Start

### Test Run (3 Days)

Verify your setup with a quick test that generates one day per regime:

```bash
python data_collection/simulation/regime_factory.py --test-mode
```

**Output**: Creates 3 files in `data/training_batches/`:
- `sim_day_1000_STANDARD.parquet`
- `sim_day_1001_VOLATILE.parquet`
- `sim_day_1002_MOMENTUM.parquet`

---

## Multi-Regime Simulation

Alpha Lab Core simulates three distinct market conditions:

### 🎯 Standard Regime
- **Characteristics**: Normal market conditions with typical volatility
- **Use Case**: General strategy training and baseline performance
- **Parameters**: Default `fund_vol`, moderate `sigma_n`

### 🌪️ Volatile Regime
- **Characteristics**: Flash crash scenarios and high volatility periods
- **Use Case**: Stress testing and risk management validation
- **Parameters**: High `fund_vol`, increased `sigma_n`, more aggressive agents

### 📈 Momentum Regime
- **Characteristics**: Trending markets with sustained directional moves
- **Use Case**: Trend-following strategy validation
- **Parameters**: Momentum-biased agent configuration

### Customizing Regimes

Edit `data_collection/simulation/regime_factory.py` to adjust:
- `fund_vol`: Fundamental volatility multiplier
- `sigma_n`: Noise trader volatility
- Agent counts and behaviors
- Trading session duration

---

## Large-Scale Parallel Generation

Generate thousands of trading days using multi-core processing:

### Basic Parallel Execution

```bash
# Example: 5000 days using 16 cores
python data_collection/simulation/launch_parallel.py --total-days 5000 --cores 16
```

### Time-Limited Execution

Useful for cloud budgets or time-constrained environments:

```bash
# Generate as many days as possible in 4 hours using 32 cores
python data_collection/simulation/launch_parallel.py \
    --total-days 10000 \
    --cores 32 \
    --duration 4.0
```

**Parameters**:
- `--total-days`: Maximum number of days to generate
- `--cores`: Number of parallel workers (typically match CPU cores)
- `--duration`: Time limit in hours (optional)
- `--start-seed`: Starting random seed (default: 1000)

### Performance Expectations

| Hardware | Days per Hour | Recommended Cores |
|----------|---------------|-------------------|
| 8-core CPU | ~100-150 | 6-8 |
| 16-core CPU | ~200-300 | 12-16 |
| 32-core CPU | ~400-600 | 24-32 |

> [!TIP]
> Leave 2-4 cores free for system processes to avoid slowdowns.

---

## Data Processing Pipeline

### Split into Train/Val/Test Sets

Split batch files by regime and merge each set:

```bash
python data_collection/processing/split_and_merge.py
```

**Output**:
- `data/TRAIN.parquet` (70%) - For model training
- `data/VAL.parquet` (15%) - For hyperparameter tuning
- `data/TEST.parquet` (15%) - For final evaluation

**Features**:
- ✅ Stratified splitting maintains regime distribution across all splits
- ✅ Streaming merge for memory efficiency (handles datasets larger than RAM)
- ✅ Automatic deduplication

### Generate OOD (Out-of-Distribution) Test Data

For robustness testing, generate fresh data with different random seeds:

```bash
# Generate 500 new days with seed offset
python data_collection/simulation/launch_parallel.py \
    --total-days 500 \
    --start-seed 20000 \
    --cores 16

# Merge OOD data
python data_collection/processing/merge_ood.py
```

**Output**: `data/TEST_OOD.parquet` - tests model on completely unseen trajectories

> [!IMPORTANT]
> OOD test data uses different random seeds to ensure your model generalizes beyond training distributions.

---

## Data Schema

Each simulation day produces a Parquet file with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | `int64` | Nanosecond timestamp from market open |
| `event_type` | `str` | Event type (e.g., `ORDER_ACCEPTED`, `ORDER_EXECUTED`, `ORDER_CANCELLED`) |
| `order_id` | `int64` | Unique order identifier |
| `side` | `str` | `BID` or `ASK` |
| `price` | `float64` | Order price in cents |
| `quantity` | `int64` | Order quantity |
| `agent_id` | `int64` | ID of submitting agent |

### File Naming Convention

```
sim_day_<seed>_<REGIME>.parquet
```

**Examples**:
- `sim_day_1000_STANDARD.parquet`
- `sim_day_1001_VOLATILE.parquet`
- `sim_day_1002_MOMENTUM.parquet`

### Reading Data

```python
import polars as pl

# Read single file
df = pl.read_parquet("data/training_batches/sim_day_1000_STANDARD.parquet")

# Read merged training set
train_df = pl.read_parquet("data/TRAIN.parquet")

# Sample first 1000 rows
sample = train_df.head(1000)
```

---

## Data Validation

### Comprehensive Quality Checks

Verify spread, volatility, and LOB statistics:

```bash
python validation/validate_data_quality.py
```

**Checks**:
- ✅ Spread analysis (bid-ask spread consistency)
- ✅ Volatility verification (matches regime expectations)
- ✅ LOB depth statistics (sufficient liquidity)
- ✅ Density checks (event rate consistency)
- ✅ Sanity checks (no negative prices, valid timestamps)

### Inspect Individual Files

```bash
# View LOB reconstruction
python validation/inspection/reconstruct_lob.py

# Check depth statistics
python validation/inspection/inspect_depth.py

# Examine ABIDES raw output
python validation/inspection/inspect_abides.py
```

### Verify Density

Check that event density is consistent across regimes:

```bash
python validation/verify_density.py
```

---

## Storage and Performance

### Disk Space Requirements

| Dataset Size | Disk Space | RAM (Merge) |
|--------------|------------|-------------|
| 100 days | ~2-5 GB | 2 GB |
| 1,000 days | ~20-50 GB | 4 GB |
| 10,000 days | ~200-500 GB | 8 GB |

> [!NOTE]
> Storage varies by regime volatility. Volatile regimes generate more events and require more space.

### Performance Considerations

**CPU Bound**: Simulation speed scales linearly with CPU cores (not GPU accelerated)

**Memory Efficiency**:
- ✅ Merge operations use streaming mode and can process datasets larger than available RAM
- ⚠️ Full LOB reconstruction can require significant RAM for long simulations

**Optimization Tips**:
1. Use Parquet format for 5-10x compression vs CSV
2. Process data in chunks for large datasets
3. Use Polars instead of Pandas for 10-100x speedups
4. Enable lazy evaluation with `pl.scan_parquet()` for massive datasets

---

## Folder Structure

```
alpha-lab-core/
├── data/                           # Generated data (gitignored)
│   ├── training_batches/           # Daily simulation outputs (.parquet)
│   ├── TRAIN.parquet               # Training set (70%)
│   ├── VAL.parquet                 # Validation set (15%)
│   ├── TEST.parquet                # Test set (15%)
│   └── TEST_OOD.parquet            # Out-of-distribution test (optional)
│
├── data_collection/simulation/
│   ├── regime_factory.py           # ⭐ Multi-regime market simulator
│   └── launch_parallel.py          # ⭐ Parallel batch orchestrator
│
├── data_collection/processing/
│   ├── split_and_merge.py          # ⭐ Train/val/test splitter
│   ├── merge_ood.py                # OOD test data merger
│   └── process_depth.py            # Depth data processor
│
└── validation/
    ├── validate_data_quality.py    # Comprehensive quality metrics
    ├── verify_density.py            # LOB density statistics
    └── inspection/                 # Individual file inspection tools
```

---

## Troubleshooting

### Issue: Simulation is slow

**Solution**:
- Reduce `--total-days` or add `--duration` limit
- Use more cores with `--cores`
- Check CPU usage: `htop` (should be near 100% per core)

### Issue: Out of memory during merge

**Solution**:
- Streaming merge should handle this automatically
- If issues persist, reduce batch size in `split_and_merge.py`
- Close other applications to free RAM

### Issue: Inconsistent regime distribution

**Solution**:
- Check `regime_factory.py` regime selection logic
- Verify stratified splitting in `split_and_merge.py`
- Use `validate_data_quality.py` to check distribution

---

## See Also

- [INSTALL_GUIDE.md](INSTALL_GUIDE.md) - Initial setup and installation
- [README.md](README.md) - Project overview and features
- [FYERS_DATA_HARVESTING_GUIDE.md](FYERS_DATA_HARVESTING_GUIDE.md) - Real market data collection

---

**Last Updated**: 2025-12-30  
**Version**: 1.0
