# Alpha Lab Core

**Alpha Lab Core** is a high-fidelity market simulation and data harvesting pipeline designed for training High Frequency Trading (HFT) and Reinforcement Learning (RL) agents.

It leverages [ABIDES](https://github.com/jpmorganchase/abides) (Agent-Based Interactive Discrete Event Simulator) to generate realistic synthetic Limit Order Book (LOB) data across multiple market regimes (Standard, Volatile, Momentum).

## Features

- **Multi-Regime Simulation**: Generates data mimicking different market conditions (Normal, Flash Crash/High Volatility, Momentum rallies).
- **Parallel Generation**: Includes tools to mass-produce years of synthetic market data using multi-core processing (`14_launch_parallel.py`).
- **High-Performance Data Stack**: Built on `Polars` and `PyArrow` for efficient handling of tick-by-tick data.
- **Real Market Harvesting**: Includes modules for harvesting real-time data from Fyers API for validation and calibration.

## Installation

Please refer to the [INSTALL_GUIDE.md](INSTALL_GUIDE.md) for detailed setup instructions for Arch Linux and Ubuntu/Debian systems.

## Quick Start

### 1. Generate Synthetic Data
Run the regime factory in test mode to generate a small sample of data:
```bash
python 13_regime_factory.py --test-mode
```
This will create parquet files in `data/training_batches/`.

### 2. Large Scale Simulation
To generate a large dataset (e.g., 1 year of trading):
```bash
python 14_launch_parallel.py --total-days 252 --cores 8
```

### 3. Verify Data Density
Check the statistical properties of the generated order books:
```bash
python 8_verify_density.py
```

## Repository Structure

- `libs/abides`: Core simulation engine (forked/modified from JPMC ABIDES).
- `13_regime_factory.py`: Main logic for configuring and running simulations with specific market regimes.
- `14_launch_parallel.py`: Orchestrator for running multiple simulations in parallel.
- `11_mass_production.py`: (Legacy) Basic simulation script.
- `1_fyers_harvester.py`: Tool for recording real market data.
- `data/`: Storage for generated inputs and outputs (Parquet format).

## License

This project relies on ABIDES which is open source. All custom logic in this repository is for research and educational purposes.
