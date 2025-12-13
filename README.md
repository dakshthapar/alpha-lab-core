# Alpha Lab Core

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/platform-linux-lightgrey.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**Alpha Lab Core** is a high-fidelity market simulation and data harvesting pipeline designed for training High Frequency Trading (HFT) and Reinforcement Learning (RL) agents.

It leverages [ABIDES](https://github.com/jpmorganchase/abides) (Agent-Based Interactive Discrete Event Simulator) to generate realistic synthetic Limit Order Book (LOB) data across multiple market regimes (Standard, Volatile, Momentum).

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

## ✨ Features

### 🎯 Multi-Regime Simulation
- **Standard Regime**: Normal market conditions with typical volatility
- **Volatile Regime**: Flash crash scenarios and high volatility periods
- **Momentum Regime**: Trending markets with sustained directional moves
- Configurable parameters for each regime (`fund_vol`, `sigma_n`, number of agents)

### ⚡ High-Performance Data Pipeline
- Built on **Polars** and **PyArrow** for blazing-fast tick-by-tick data processing
- Efficient Parquet file format for storage and retrieval
- Handles millions of order book updates with minimal memory overhead

### 🚀 Parallel Processing
- Mass-produce years of synthetic market data using multi-core processing
- Built-in parallel launcher (`14_launch_parallel.py`) with configurable worker count
- Time-limited execution for cloud budget management
- Automatic batch merging and deduplication

### 📊 Real Market Integration
- Fyers API integration for harvesting real-time Indian market data
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

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/alpha-lab-core.git
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
uv pip install -r requirements-cpu.txt

# 5. Install ABIDES from source
cd libs/abides/abides-core && uv pip install -e .
cd ../abides-markets && uv pip install -e .
cd ../../../
```

---

## 🚀 Quick Start

### 1️⃣ Generate Test Data (3 Days)
Run the regime factory in test mode to verify your setup:
```bash
python 13_regime_factory.py --test-mode
```
This creates `data/training_batches/sim_day_1000_STANDARD.parquet` (and similar files).

### 2️⃣ Large-Scale Simulation
Generate a year of trading data (252 trading days):
```bash
python 14_launch_parallel.py --total-days 252 --cores 8
```

**Time-Limited Execution** (useful for cloud environments):
```bash
# Stop all workers after 2.5 hours
python 14_launch_parallel.py --total-days 1000 --cores 16 --duration 2.5
```

### 3️⃣ Validate Data Quality
Check spread, volatility, and LOB depth statistics:
```bash
python 9_validate_data_quality.py
```

### 4️⃣ Merge Batches
Combine individual simulation files into a single training dataset:
```bash
python 12_merge_batches.py
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
│   └── TRAIN_FULL.parquet       # Merged training dataset
│
├── 🔧 Simulation Scripts
│   ├── 13_regime_factory.py     # ⭐ Main simulation engine with regime support
│   ├── 14_launch_parallel.py    # ⭐ Parallel execution orchestrator
│   ├── 11_mass_production.py    # Legacy basic simulator
│   └── 3_abides_factory.py      # ABIDES configuration builder
│
├── 🔍 Analysis & Validation
│   ├── 9_validate_data_quality.py  # Comprehensive quality metrics
│   ├── 8_verify_density.py         # LOB density statistics
│   ├── 7_sanity_check.py           # Basic data verification
│   ├── 10_reconstruct_lob.py       # LOB reconstruction tools
│   ├── 5_inspect_depth.py          # Order book depth viewer
│   └── 4_inspect_abides.py         # ABIDES output inspector
│
├── 📡 Data Harvesting
│   ├── 1_fyers_harvester.py     # Real-time Indian market data collector
│   └── 0_simulate_fyers.py      # Fyers API simulator (testing)
│
├── 🛠️ Utilities
│   ├── 12_merge_batches.py      # Batch merger and deduplicator
│   ├── 6_process_depth.py       # Depth data processor
│   └── debug_*.py               # Debugging utilities
│
├── 📄 Documentation
│   ├── README.md                # ⭐ You are here
│   ├── INSTALL_GUIDE.md         # Detailed installation instructions
│   ├── CONTRIBUTING.md          # Contribution guidelines
│   └── LICENSE                  # Apache 2.0 License
│
└── 📦 Dependencies
    ├── requirements.txt         # Base dependencies
    ├── requirements-cpu.txt     # CPU-only PyTorch
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

- **JPMorgan Chase & Co.** for open-sourcing [ABIDES](https://github.com/jpmorganchase/abides)
- **Fyers Securities** for providing market data API access
- The quantitative finance and machine learning research community

---

## 📧 Contact

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/alpha-lab-core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/alpha-lab-core/discussions)

---

**Built with ❤️ for the algorithmic trading research community**

