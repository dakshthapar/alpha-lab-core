print("Step 1: Start")
import sys
import os
print(f"Step 2: Imports done. ARGV: {sys.argv}")
from pathlib import Path
print("Step 3: Pathlib imported")

current_dir = Path(os.getcwd())
print(f"Step 4: CWD is {current_dir}")

p1 = str(current_dir / "libs" / "abides" / "abides-core")
sys.path.append(p1)
print(f"Step 5: Appended {p1}")

print("Step 6: Importing Kernel...")
from abides_core.kernel import Kernel
print("Step 7: Kernel Imported!")

p2 = str(current_dir / "libs" / "abides" / "abides-markets")
sys.path.append(p2)
print("Step 8: Appended Markets Path")

from abides_markets.agents.exchange_agent import ExchangeAgent
print("Step 9: ExchangeAgent Imported!")

