ARG TORCH_VERSION=2.10.0
ARG CUDA_VERSION=cuda12.6

FROM pytorch/pytorch:${TORCH_VERSION}-${CUDA_VERSION}-cudnn9-devel

ENV PIP_BREAK_SYSTEM_PACKAGES=1

# ── System dependencies ─────────────────────────────────────────
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    graphviz graphviz-dev \
    && rm -rf /var/lib/apt/lists/*

# ── PyTorch Geometric ────────────────────────────────────────────
ARG TORCH_VERSION
ARG CUDA_VERSION
RUN pip install --no-cache-dir torch_geometric && \
    pip install --no-cache-dir \
    pyg_lib torch_scatter torch_sparse torch_cluster torch_spline-conv \
    -f https://data.pyg.org/whl/torch-${TORCH_VERSION}+${CUDA_VERSION}.html || true

# ── CayleyPy (PyPI, requires torch>=2.6.0) ──────────────────────
RUN pip install --no-cache-dir cayleypy

# ── Core Python ──────────────────────────────────────────────────
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# ── Jupyter Lab ──────────────────────────────────────────────────
RUN pip install --no-cache-dir jupyterlab==4.2.5 ipywidgets jupyterlab-git

# ── Non-root user ────────────────────────────────────────────────
RUN useradd -m -s /bin/bash researcher && mkdir -p /workspace && chown -R researcher:researcher /workspace
USER researcher

WORKDIR /workspace

# ── Verify ───────────────────────────────────────────────────────
RUN python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.version.cuda}')" && \
    python -c "import torch_geometric; print(f'PyG {torch_geometric.__version__}')" && \
    python -c "import cayleypy; print('CayleyPy OK')" && \
    python -c "import neo4j; print(f'Neo4j driver {neo4j.__version__}')" || true

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser"]
