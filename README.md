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
- **15-day automated token refresh** - Manual login only once every 15 days! (see [TOKEN_REFRESH_GUIDE.md](TOKEN_REFRESH_GUIDE.md))
- **24/7 AWS cloud deployment** - Continuous data collection (see [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md))
- AWS Lambda automation for daily access token renewal
- Data validation and calibration against live order books
- Side-by-side comparison tools for synthetic vs real data

### 🔍 Quality Validation
- Comprehensive data quality metrics (`9_validate_data_quality.py`)
- Spread analysis and volatility verification
- LOB depth statistics and density checks
- Automated sanity checks for generated datasets

---

## 📦 Installation

**Complete installation guide**: [INSTALL_GUIDE.md](INSTALL_GUIDE.md)

### Quick Setup

```bash
# Clone repository
git clone https://github.com/dakshthapar/alpha-lab-core.git
cd alpha-lab-core

# Initialize ABIDES submodule
git submodule update --init --recursive

# Create environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install uv
uv pip install -r requirements-gpu.txt --index-strategy unsafe-best-match  # or requirements.txt for CPU

# Install ABIDES
cd libs/abides/abides-core && uv pip install -e .
cd ../abides-markets && uv pip install -e . && cd ../../../
```

**Next steps**: See [INSTALL_GUIDE.md](INSTALL_GUIDE.md) for platform-specific instructions and validation.

---

## 🚀 Quick Start

### Choose Your Path

**📊 Generate Synthetic Market Data**
- Multi-regime simulation (Standard, Volatile, Momentum)
- Parallel processing for mass production
- Complete guide: [DATASET_GENERATION_GUIDE.md](DATASET_GENERATION_GUIDE.md)

**📈 Collect Real Market Data (Fyers API)**
- Real-time Indian market depth data
- Local development or 24/7 cloud deployment
- Getting started: [FYERS_DATA_HARVESTING_GUIDE.md](FYERS_DATA_HARVESTING_GUIDE.md)
- Production deployment: [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md)

### Quick Test (Synthetic Data)

```bash
# Verify installation with test run (3 days, one per regime)
python data_collection/simulation/regime_factory.py --test-mode

# Check output
ls -lh data/training_batches/
```

For complete workflows, see the specialized guides above.

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
│   ├── README.md                           # ⭐ You are here - Project overview
│   ├── INSTALL_GUIDE.md                    # Installation instructions
│   ├── DATASET_GENERATION_GUIDE.md         # Synthetic data generation
│   ├── FYERS_DATA_HARVESTING_GUIDE.md       # Real market data basics
│   ├── CLOUD_HARVESTER_GUIDE.md            # AWS 24/7 deployment
│   ├── TOKEN_REFRESH_GUIDE.md              # Automated token refresh
│   ├── CONTRIBUTING.md                     # Contribution guidelines
│   └── LICENSE                             # Apache 2.0 License
│
└── 📦 Dependencies
    ├── requirements.txt                    # Base dependencies (CPU)
    └── requirements-gpu.txt                # CUDA 12.1 PyTorch
```

---

## 📚 Documentation Guide

### Installation & Setup
- [INSTALL_GUIDE.md](INSTALL_GUIDE.md) - System setup for local development or AWS

### Data Generation
- [DATASET_GENERATION_GUIDE.md](DATASET_GENERATION_GUIDE.md) - Synthetic market simulation
  - Multi-regime simulation details
  - Parallel processing at scale
  - Data schema and formats
  - Train/val/test splitting
  - Validation tools

### Real Market Data
- [FYERS_DATA_HARVESTING_GUIDE.md](FYERS_DATA_HARVESTING_GUIDE.md) - Getting started with real data
  - Fyers API setup
  - Local harvester usage
  - Data formats
  
- [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md) - 24/7 AWS deployment
  - AWS EC2 setup
  - Background operation
  - Monitoring and maintenance
  
- [TOKEN_REFRESH_GUIDE.md](TOKEN_REFRESH_GUIDE.md) - Automated authentication
  - 15-day token automation
  - AWS Lambda setup
  - Troubleshooting

### Contributing
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines

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

