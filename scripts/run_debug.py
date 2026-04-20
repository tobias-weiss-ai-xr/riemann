import subprocess

r = subprocess.run(
    ["python3", "/workspace/scripts/debug_batch.py"],
    capture_output=True,
    text=True,
    timeout=30,
)
print(r.stdout)
print("ERR:", r.stderr[-300:] if r.stderr else "")
