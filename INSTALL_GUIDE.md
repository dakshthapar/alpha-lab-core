# Alpha Lab Core - Installation Guide

This guide covers the setup process for the Alpha Lab Core market simulation environment.

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
   python -c "
import torch
print(f'PyTorch Version: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
print(f'CUDA Version: {torch.version.cuda}')
print(f'Number of GPUs: {torch.cuda.device_count()}')
if torch.cuda.is_available():
    print(f'Current GPU: {torch.cuda.current_device()}')
    print(f'GPU Name: {torch.cuda.get_device_name(0)}')
    print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB')
"

   # Test actual GPU computation
   python -c "
import torch
if torch.cuda.is_available():
    x = torch.rand(5, 3).cuda()
    print(f'✅ Tensor created on GPU: {x.device}')
    print(f'Tensor:\n{x}')
else:
    print('❌ CUDA not available')
"
   ```

   **Option B: For CPU Only**
   *Use this for cloud servers without GPU or basic laptops.*
   ```bash
   uv pip install -r requirements-cpu.txt
   ```

   **Verify CPU Setup:**
   ```bash
   # Check PyTorch installation and perform basic computation
   python -c "
import torch
print(f'PyTorch Version: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
x = torch.rand(5, 3)
print(f'✅ Tensor created on CPU: {x.device}')
print(f'Tensor:\n{x}')
"
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
python 13_regime_factory.py --test-mode
```

**Check the Data:**
Verify that the output files have been generated:
```bash
ls -lh data/training_batches/
```
*Success: You should see files like `sim_day_1000_STANDARD.parquet`, `sim_day_1001_VOLATILE.parquet`, etc.*

## Phase 5: Mass Production (Advanced)

For generating large datasets (e.g., 20,000 days), use the parallel launcher script which utilizes multiple CPU cores.

```bash
# Example: Generate 100 days using 16 cores
python 14_launch_parallel.py --total-days 100 --cores 16

# Example: Run for a maximum of 4 hours (useful for strict cloud budgets)
python 14_launch_parallel.py --total-days 5000 --cores 32 --duration 4.0
```

---
**Folder Structure Reference**

```plaintext
alpha-lab-core/
├── .venv/                   # Active Environment
├── data/                    # (Ignored by Git)
│   ├── training_batches/    # Raw Daily Simulation Files
│   └── TRAIN_FULL.parquet   # Merged Dataset
├── libs/
│   └── abides/              # The JPMC Source Code
├── 1_fyers_harvester.py     # Real Data Collector
├── 11_mass_production.py    # Basic Simulator
├── 13_regime_factory.py     # Advanced Regime Simulator
├── 14_launch_parallel.py    # Parallel Execution Launcher
├── requirements.txt         # Dependency File
└── INSTALL_GUIDE.md         # This Guide
```
