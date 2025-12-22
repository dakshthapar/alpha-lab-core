# Alpha Lab Core - Installation Guide

This guide covers the setup process for the Alpha Lab Core market simulation environment.

> [!NOTE]
> **Looking for cloud deployment?** For 24/7 AWS data harvesting, see [CLOUD_HARVESTER_GUIDE.md](CLOUD_HARVESTER_GUIDE.md).

## Phase 1: System Preparation

### Option A: Arch Linux (Local Development)

```bash
# 1. Install System Basics
sudo pacman -S git python python-pip base-devel cuda

# 2. Install uv (Fast pip replacement)
pip install uv --break-system-packages

# 3. Add uv to PATH (if not already added)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 4. Verify uv installation
uv --version
```

### Option B: Ubuntu / Debian (Cloud Server / AWS)

```bash
# 1. Install System Basics
sudo apt update && sudo apt install -y git python3-pip python3-venv build-essential

# 2. Install uv
pip3 install uv

# 3. Add uv to PATH (if not already added)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 4. Verify uv installation
uv --version
```

## Phase 2: Project Setup & Environment

1. **Clone the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/alpha-lab-core.git
   cd alpha-lab-core
   ```

2. **Create Virtual Environment**
   We use `uv` for significantly faster dependency resolution.
   ```bash
   uv venv .venv --python 3.10
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   Choose the appropriate command for your hardware:

   **Option A: For NVIDIA GPU (CUDA 12.1)**
   *Recommended for 3080 Ti and faster training.*
   ```bash
   uv pip install -r requirements-gpu.txt --index-strategy unsafe-best-match
   ```

   **Verify GPU Setup:**
   ```bash
   # Check comprehensive GPU info
   python -c "import torch; print(f'PyTorch Version: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Version: {torch.version.cuda}'); print(f'Number of GPUs: {torch.cuda.device_count()}'); print(f'Current GPU: {torch.cuda.current_device()}') if torch.cuda.is_available() else None; print(f'GPU Name: {torch.cuda.get_device_name(0)}') if torch.cuda.is_available() else None; print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB') if torch.cuda.is_available() else None"

   # Test actual GPU computation
   python -c "import torch; x = torch.rand(5, 3).cuda() if torch.cuda.is_available() else None; print(f'✅ Tensor created on GPU: {x.device}') if torch.cuda.is_available() else print('❌ CUDA not available'); print(f'Tensor:\n{x}') if torch.cuda.is_available() else None"
   ```

   **Option B: For CPU Only**
   *Use this for cloud servers without GPU or basic laptops.*
   ```bash
   uv pip install -r requirements.txt (CPU)
   ```

   **Verify CPU Setup:**
   ```bash
   # Check PyTorch installation and perform basic computation
   python -c "import torch; print(f'PyTorch Version: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); x = torch.rand(5, 3); print(f'✅ Tensor created on CPU: {x.device}'); print(f'Tensor:\n{x}')"
   ```

## Phase 3: Installing ABIDES (From Source)

The ABIDES (Agent-Based Interactive Discrete Event Simulator) library is a core component and must be installed in editable mode. The source code is located in `libs/abides`.

```bash
# 1. Install Core
cd libs/abides/abides-core
uv pip install -e .

# 2. Install Markets Extension
cd ../abides-markets
uv pip install -e .

# 3. Return to Project Root
cd ../../../
```

**Verification:**
Run this command to check if ABIDES is correctly installed and importable:
```bash
python -c "import abides_core; import abides_markets; print('✅ ABIDES Installed Successfully')"
```

## Phase 4: Validation Run

To verify that the Simulation Factory and detailed market regimes are working correctly, run the factory in test mode.

**Run the Factory (Test Mode):**
This command simulates 3 days of market data (one for each market regime: Standard, Volatile, Momentum).
```bash
python data_collection/simulation/regime_factory.py --test-mode
```

**Check the Data:**
Verify that the output files have been generated:
```bash
ls -lh data/training_batches/
```
*Success: You should see files like `sim_day_1000_STANDARD.parquet`, `sim_day_1001_VOLATILE.parquet`, etc.*

## Phase 5: Data Pipeline (After Simulation)

Once you have generated simulation data, process it into train/val/test sets:

```bash
# Split batch files by regime and merge each set
python data_collection/processing/split_and_merge.py
```

**This creates:**
- `data/TRAIN.parquet` (70% of data) - For model training
- `data/VAL.parquet` (15% of data) - For hyperparameter tuning
- `data/TEST.parquet` (15% of data) - For final evaluation

**Optional: Generate OOD (Out-of-Distribution) Test Data**
```bash
# Generate fresh data with different seeds for robustness testing
python data_collection/simulation/launch_parallel.py --total-days 500 --start-seed 20000 --cores 16

# After completion, merge OOD data
python data_collection/processing/merge_ood.py
```
This creates `data/TEST_OOD.parquet` for testing model generalization on completely unseen trajectories.

---
**Folder Structure Reference**

```plaintext
alpha-lab-core/
├── .venv/                   # Active Environment
├── data/                    # (Ignored by Git)
│   ├── training_batches/    # Raw Daily Simulation Files
│   ├── TRAIN.parquet        # Training Set (70%)
│   ├── VAL.parquet          # Validation Set (15%)
│   ├── TEST.parquet         # Test Set (15%)
│   └── TEST_OOD.parquet     # OOD Test (Optional)
├── libs/
│   └── abides/              # The JPMC Source Code
├── data_collection/simulation/regime_factory.py     # Advanced Regime Simulator
├── data_collection/simulation/launch_parallel.py    # Parallel Execution Launcher
├── data_collection/processing/split_and_merge.py    # Train/Val/Test Splitter
├── data_collection/processing/merge_ood.py          # OOD Test Data Merger
├── data_collection/harvesting/smart_harvester.py       # Real-time market data collector
├── data_collection/harvesting/get_token.py             # Fyers token generator
├── harvested_data/          # Real market depth data (created by harvester)
├── requirements.txt         # Dependency File
├── INSTALL_GUIDE.md         # This Guide
└── CLOUD_HARVESTER_GUIDE.md # AWS Deployment Guide
```

