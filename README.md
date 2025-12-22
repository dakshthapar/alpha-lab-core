# Alpha Lab Core

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/platform-linux-lightgrey.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Alpha Lab Core** is a high-fidelity market simulation and data harvesting pipeline designed for training High Frequency Trading (HFT) and Reinforcement Learning (RL) agents.

It leverages [ABIDES](https://github.com/jpmorganchase/abides-jpmc-public) (Agent-Based Interactive Discrete Event Simulator) to generate realistic synthetic Limit Order Book (LOB) data across multiple market regimes (Standard, Volatile, Momentum).

---

> [!WARNING]
> **Research and Educational Use Only**
> 
> This software is intended for research, backtesting, and educational purposes only. It is NOT intended for live trading without extensive additional testing and risk management. Trading financial instruments carries substantial risk of loss. Use at your own risk.

> [!IMPORTANT]
> **Simulation Disclaimer**
> 
> Synthetic market data, while useful for training and research, may not fully capture real market dynamics, microstructure effects, or extreme events. Always validate strategies on real historical data before considering any form of live deployment.

---

## 🚀 Project Pipeline

Alpha Lab Core is organized into **4 development phases**:

**Phase 1: Data Collection** ✅ **(Current)**
- Synthetic market simulation (ABIDES-based)
- Real market data harvesting (Fyers API)
- Data processing and validation
- Located in: `data_collection/`, `validation/`

**Phase 2: Benchmarking** 🚧 **(Future)**
- Baseline strategy performance
- Backtesting framework
- Located in: `benchmarking/`

**Phase 3: ML Models** 🚧 **(Future)**
- LOB prediction models (LSTM, Transformers)
- RL agent training
- Located in: `models/`

**Phase 4: Trading System** 🚧 **(Future)**
- Live strategy execution
- Risk management
- Located in: `trading/`

---

## ✨ Features

### 🎯 Multi-Regime Simulation
- **Standard Regime**: Normal market conditions with typical volatility
- **Volatile Regime**: Flash crash scenarios and high volatility periods
- **Momentum Regime**: Trending markets with sustained directional moves
- Configurable parameters for each regime (`fund_vol`, `sigma_n`, number of agents)

### ⚡ High-Performance Data Pipeline
- Built on **Polars** and **PyArrow** for blazing-fast tick-by-tick data processing
- Efficient Parquet file format for storage and retrieval
- **Streaming merge engine** - processes datasets of any size without RAM constraints
- Handles millions of order book updates with minimal memory overhead

### 🚀 Parallel Processing
- Mass-produce years of synthetic market data using multi-core processing
- Built-in parallel launcher (`14_launch_parallel.py`) with configurable worker count
- Time-limited execution for cloud budget management
- Automatic batch merging and deduplication

### 📊 Real Market Integration
- Fyers API integration for harvesting real-time Indian market data
- **24/7 AWS cloud deployment** - Continuous data collection (see [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md))
- Data validation and calibration against live order books
- Side-by-side comparison tools for synthetic vs real data

### 🔍 Quality Validation
- Comprehensive data quality metrics (`9_validate_data_quality.py`)
- Spread analysis and volatility verification
- LOB depth statistics and density checks
- Automated sanity checks for generated datasets

---

## 📦 Installation

### Quick Start (Arch Linux / Ubuntu)

**Full installation instructions available in [INSTALL_GUIDE.md](INSTALL_GUIDE.md)**

**For 24/7 cloud data harvesting, see [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md)**

```bash
# 1. Clone the repository
git clone https://github.com/dakshthapar/alpha-lab-core.git
cd alpha-lab-core

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install uv (fast package installer)
pip install uv

# 4. Install dependencies
# For GPU (CUDA 12.1):
uv pip install -r requirements-gpu.txt --index-strategy unsafe-best-match
# OR for CPU only:
uv pip install -r requirements.txt (CPU)

# 5. Install ABIDES from source
cd libs/abides/abides-core && uv pip install -e .
cd ../abides-markets && uv pip install -e .
cd ../../../
```

---

## 🚀 Quick Start

### 1️⃣ Generate Test Data (3 Days)
Verify your setup with a quick test:
```bash
python data_collection/simulation/regime_factory.py --test-mode
```

### 2️⃣ Large-Scale Simulation
Generate thousands of trading days using parallel processing:
```bash
# Example: 5000 days using 16 cores
python data_collection/simulation/launch_parallel.py --total-days 5000 --cores 16

# With time limit (useful for cloud budgets):
python data_collection/simulation/launch_parallel.py --total-days 10000 --cores 32 --duration 4.0
```

### 3️⃣ Split and Merge Data
Split batch files by regime into train/val/test, then merge each:
```bash
python data_collection/processing/split_and_merge.py
```
**Output**: `TRAIN.parquet` (70%), `VAL.parquet` (15%), `TEST.parquet` (15%)

✨ **Stratified splitting** maintains regime distribution across all splits using streaming merge for memory efficiency.

### 4️⃣ (Optional) Generate OOD Test Data
For robustness testing, generate fresh data with different random seeds:
```bash
# Generate 500 new days with seed offset
python data_collection/simulation/launch_parallel.py --total-days 500 --start-seed 20000 --cores 16

# Merge OOD data
python data_collection/processing/merge_ood.py
```
**Output**: `TEST_OOD.parquet` - tests model on completely unseen trajectories

### 5️⃣ Validate Data Quality
Verify spread, volatility, and LOB statistics:
```bash
python validation/validate_data_quality.py
```

---

## 📂 Repository Structure

```
alpha-lab-core/
│
├── 📁 libs/
│   └── abides/                  # ABIDES Simulation Engine (JPMC fork)
│       ├── abides-core/         # Core discrete event simulator
│       └── abides-markets/      # Financial markets extension
│
├── 📁 data/                     # Generated data (gitignored)
│   ├── training_batches/        # Daily simulation outputs (.parquet)
│   ├── TRAIN.parquet            # Training set (70%)
│   ├── VAL.parquet              # Validation set (15%)
│   ├── TEST.parquet             # Test set (15%)
│   └── TEST_OOD.parquet         # Out-of-distribution test (optional)
│
├── 📁 data_collection/                     # Phase 1: Data Generation & Harvesting
│   ├── simulation/
│   │   ├── regime_factory.py               # ⭐ Multi-regime market simulator
│   │   └── launch_parallel.py              # ⭐ Parallel batch orchestrator
│   ├── harvesting/
│   │   ├── smart_harvester.py              # Real-time market data collector (24/7)
│   │   └── get_token.py                    # Fyers authentication
│   └── processing/
│       ├── split_and_merge.py              # ⭐ Train/val/test splitter
│       ├── merge_ood.py                    # OOD test data merger
│       └── process_depth.py                # Depth data processor
│
├── 📁 validation/                          # Data Quality Assurance
│   ├── validate_data_quality.py            # Comprehensive quality metrics
│   ├── verify_density.py                   # LOB density statistics
│   ├── sanity_check.py                     # Basic verification
│   └── inspection/
│       ├── reconstruct_lob.py              # LOB reconstruction tools
│       ├── inspect_depth.py                # Order book depth viewer
│       └── inspect_abides.py               # ABIDES output inspector
│
├── 📁 benchmarking/                        # Phase 2: Performance Baselines (Future)
│   └── README.md
│
├── 📁 models/                              # Phase 3: ML Models (Future) 
│   ├── training/
│   ├── inference/
│   └── architectures/
│
├── 📁 trading/                             # Phase 4: Live Trading System (Future)
│   ├── strategies/
│   ├── execution/
│   └── risk_management/
│
│
├── 📄 Documentation
│   ├── README.md                # ⭐ You are here
│   ├── INSTALL_GUIDE.md         # Detailed installation instructions
│   ├── CLOUD_HARVESTER_GUIDE.md # ⭐ AWS deployment & 24/7 data collection
│   ├── CONTRIBUTING.md          # Contribution guidelines
│   └── LICENSE                  # Apache 2.0 License
│
└── 📦 Dependencies
    ├── requirements.txt         # Base dependencies
    ├── requirements.txt (CPU)     # CPU-only PyTorch
    └── requirements-gpu.txt     # CUDA 12.1 PyTorch
```

---

## 🗄️ Data Schema

### Generated Parquet Files

Each simulation day produces a Parquet file with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | `int64` | Nanosecond timestamp from market open |
| `event_type` | `str` | Event type (e.g., `ORDER_ACCEPTED`, `ORDER_EXECUTED`) |
| `order_id` | `int64` | Unique order identifier |
| `side` | `str` | `BID` or `ASK` |
| `price` | `float64` | Order price in cents |
| `quantity` | `int64` | Order quantity |
| `agent_id` | `int64` | ID of submitting agent |

**File Naming Convention:**
- `sim_day_1000_STANDARD.parquet` - Standard regime
- `sim_day_1001_VOLATILE.parquet` - Volatile regime  
- `sim_day_1002_MOMENTUM.parquet` - Momentum regime

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- 🐛 How to report bugs
- 💡 How to suggest features
- 📝 Code style guidelines
- 🔄 Pull request process

### Development Setup
```bash
# Install development dependencies
uv pip install pytest black flake8 mypy

# Format code before committing
black *.py

# Run tests (if available)
pytest tests/
```

---

## 🗺️ Roadmap

### ✅ Completed
- ✅ Multi-regime simulation (Standard, Volatile, Momentum)
- ✅ Parallel data generation pipeline
- ✅ Polars/PyArrow high-performance data stack
- ✅ Fyers API integration for real market data
- ✅ Comprehensive data quality validation

### 🚧 In Progress
- 🚧 Neural network training scripts (LSTM/Transformer for LOB prediction)
- 🚧 Reinforcement learning environment (OpenAI Gym interface)

### 📋 Planned
- 📋 Options market simulation support
- 📋 Intraday regime switching (change regime mid-day)
- 📋 Order flow imbalance indicators
- 📋 Market maker agent strategies
- 📋 Multi-asset correlation modeling
- 📋 Dockerized deployment for cloud environments
- 📋 Interactive web dashboard for monitoring simulations
- 📋 Pre-trained model weights for common strategies

---

## ⚠️ Known Limitations

### Simulation Fidelity
- **No latency modeling**: Assumes instantaneous order execution (no network/exchange delays)
- **Simplified agent behavior**: Agents use basic strategies (value, momentum, noise)
- **No exchange microstructure**: Does not model:
  - Queue priority and order book dynamics at tick level
  - Hidden liquidity or iceberg orders
  - Exchange-specific fees and rebates
  
### Data Quality
- **Regime stationarity**: Each simulation day has a fixed regime; no intraday regime changes
- **Limited market impact**: Large orders may not exhibit realistic price impact
- **Spread consistency**: Spreads may be narrower than real markets in some regimes

### Performance
- **Memory usage**: Full LOB reconstruction can require significant RAM for long simulations
  - ✅ **Merge operations** use streaming mode and can process datasets larger than available RAM
- **CPU bound**: Simulation speed scales linearly with CPU cores, not GPU accelerated
- **Storage**: A year of tick data (252 days) can require 50-100GB of disk space

### Platform
- **Linux only**: Tested on Arch Linux and Ubuntu; macOS/Windows support not guaranteed
- **Python 3.10+**: Requires modern Python due to Polars and PyArrow dependencies

---

## 📜 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

### Third-Party Dependencies
- **ABIDES**: Licensed under Apache 2.0 (© JPMorgan Chase & Co.)
- This project includes a modified version of ABIDES located in `libs/abides/`

---

## 🙏 Acknowledgments

- **JPMorgan Chase & Co.** for open-sourcing [ABIDES](https://github.com/jpmorganchase/abides-jpmc-public)
- **Fyers Securities** for providing market data API access
- The quantitative finance and machine learning research community

---

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/dakshthapar/alpha-lab-core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dakshthapar/alpha-lab-core/discussions)

---

**Built with ❤️ for the algorithmic trading research community**

