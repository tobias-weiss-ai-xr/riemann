"""Run build_pizer_dataset.py with smaller scope for testing."""

import subprocess

result = subprocess.run(
    ["python", "/workspace/scripts/build_pizer_dataset.py", "--max-prime", "500"],
    capture_output=True,
    text=True,
    timeout=300,
)
print("STDOUT:", result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
print("STDERR:", result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
print("RETURN CODE:", result.returncode)
