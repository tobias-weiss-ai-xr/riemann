#!/bin/bash
# Wrapper for spectral rigidity analysis — launches and logs
cd /workspace
python3 scripts/train_spectral_rigidity.py > scripts/_thread_r.log 2>&1
echo "Exit code: $?" >> scripts/_thread_r.log
