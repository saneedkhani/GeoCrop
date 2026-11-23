"""geocrop_model.py - load the saved GeoCrop cropland model and predict.

MODEL INPUT (one row per pixel)
    77 numbers = 7 months (April..October) x 11 values per month, month-major:
    B02 B03 B04 B05 B06 B07 B08 B8A B11 B12 NDVI for April, then the same 11 for May, ... October.
    Reflectance 0-1 (Sentinel-2 L2A DN x 0.0001), monthly median of cloud-masked observations, 30 m grid.
    Either an array (N, 77) or (N, 7, 11).
MODEL OUTPUT
    probability that the pixel is cropland (1 = cropland, 0 = non-cropland), shape (N,).

Usage
    from geocrop_model import load_model
    model = load_model("model")                # folder with model.pt or model.joblib
    p = model.predict_proba(X)                 # (N,)
    cls = model.predict(X, threshold=0.5)      # (N,) 0 / 1
"""
import math
from pathlib import Path

import numpy as np

MONTHS = [4, 5, 6, 7, 8, 9, 10]
BANDS11 = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12", "NDVI"]
T, NB = len(MONTHS), len(BANDS11)
FEATURE_NAMES = [f"{b}_m{m:02d}" for m in MONTHS for b in BANDS11]

try:
    import torch
    import torch.nn as nn
    HAVE_TORCH = True
except Exception:  # PyTorch is only needed when the saved model is an LSTM
    HAVE_TORCH = False

if HAVE_TORCH:
    class UnrolledLSTM(nn.Module):
        """Gajardo 2023 / Kerner 2020 UnrolledLSTM: one LSTM cell, dropout on the hidden state after every step."""
        def __init__(self, n_in, hidden, dropout):
            super().__init__(); self.H = hidden
            self.gates = nn.Linear(n_in + hidden, 4 * hidden); self.drop = nn.Dropout(dropout)
        def forward(self, x):
            B, Tn, _ = x.shape; h = x.new_zeros(B, self.H); c = x.new_zeros(B, self.H)
            for t in range(Tn):
                f, i, g, o = self.gates(torch.cat([x[:, t], h], 1)).chunk(4, 1)
                c = torch.sigmoid(f) * c + torch.sigmoid(i) * torch.tanh(g); h = self.drop(torch.sigmoid(o) * torch.tanh(c))
            return h

    def mlp_head(n_in, n_layers):
        L = []
        for i in range(n_layers):
            L.append(nn.Linear(n_in, 1 if i == n_layers - 1 else n_in))
            if i < n_layers - 1: L.append(nn.ReLU())
        return nn.Sequential(*L)

    class Net(nn.Module):
        def __init__(self, kind, n_in=NB, hidden=64, dropout=0.2, cls_layers=2):
            super().__init__(); self.kind = kind
            if kind == "authors": self.base = UnrolledLSTM(n_in, hidden, dropout); h, cl = hidden, cls_layers
            elif kind == "lstm50": self.base = nn.LSTM(n_in, 50, batch_first=True); h, cl = 50, 1
            elif kind == "bilstm": self.base = nn.LSTM(n_in, 50, num_layers=2, bidirectional=True, batch_first=True); h, cl = 100, 1
            else: raise ValueError(kind)
            self.g_head = mlp_head(h, cl)
        def encode(self, x):
            if self.kind == "authors": return self.base(x)
            _, (hn, _) = self.base(x)
            return hn[-1] if self.kind == "lstm50" else torch.cat([hn[-2], hn[-1]], 1)
        def forward(self, x): return torch.sigmoid(self.g_head(self.encode(x)))

    class VariationalDropout(nn.Module):
        def __init__(self, p): super().__init__(); self.p, self.mask = p, None
        def update_mask(self, shape): self.mask = torch.bernoulli(torch.ones(shape) * (1 - self.p)) / (1 - self.p)
        def forward(self, x): return x if not self.training else self.mask * x

    class UnrolledLSTMCell(nn.Module):
        def __init__(self, input_size, hidden_size):
            super().__init__(); self.hidden_size = hidden_size
            mk = lambda act: nn.Sequential(nn.Linear(input_size + hidden_size, hidden_size, bias=True), act)
            self.forget_gate, self.update_gate, self.update_candidates, self.output_gate = mk(nn.Sigmoid()), mk(nn.Sigmoid()), mk(nn.Tanh()), mk(nn.Sigmoid())
        def forward(self, x, state):
            hidden, cell = state; hidden, cell = torch.transpose(hidden, 0, 1), torch.transpose(cell, 0, 1); z = torch.cat((x, hidden), dim=-1)
            updated_cell = self.forget_gate(z) * cell + self.update_gate(z) * self.update_candidates(z); updated_hidden = self.output_gate(z) * torch.tanh(updated_cell)
            return torch.transpose(updated_hidden, 0, 1), (torch.transpose(updated_hidden, 0, 1), torch.transpose(updated_cell, 0, 1))

    class CHUnrolledLSTM(nn.Module):
        def __init__(self, input_size, hidden_size, dropout):
            super().__init__(); self.hidden_size = hidden_size; self.rnn = UnrolledLSTMCell(input_size, hidden_size); self.dropout = VariationalDropout(dropout)
        def forward(self, x):
            Tn, B = x.shape[1], x.shape[0]; hidden, cell = torch.zeros(1, B, self.hidden_size), torch.zeros(1, B, self.hidden_size); outputs = []
            for i in range(Tn):
                _, (hidden, cell) = self.rnn(x[:, i, :].unsqueeze(1), (hidden, cell)); outputs.append(hidden)
                if self.training and i == 0: self.dropout.update_mask(hidden.shape)
                hidden = self.dropout(hidden)
            return torch.stack(outputs, dim=0), (hidden, cell)

    class CHClassifier(nn.Module):
        """CropHarvest (Tseng 2021) classifier."""
        def __init__(self, input_size, vec=128, drop=0.2, base_layers=1, cls_layers=2):
            super().__init__()
            self.base = nn.ModuleList([CHUnrolledLSTM(input_size if i == 0 else vec, vec, drop) for i in range(base_layers)])
            self.batchnorm = nn.BatchNorm1d(num_features=vec, affine=False); layers = []
            for i in range(cls_layers):
                block = [nn.Linear(vec, 1 if i == cls_layers - 1 else vec, bias=(i == cls_layers - 1))]
                if i < cls_layers - 1: block += [nn.GELU(), nn.BatchNorm1d(num_features=vec, affine=False)]
                layers.append(nn.Sequential(*block))
            self.global_classifier = nn.ModuleList(layers)
        def forward(self, x):
            for lstm in self.base: x, (hn, _) = lstm(x); x = x[:, 0, :, :]
            x = self.batchnorm(hn[-1, :, :])
            for layer in self.global_classifier: x = layer(x)
            return torch.sigmoid(x)

    def _build_net(kind, st):
        """Rebuild the network from the saved weights (sizes are read from the weight shapes)."""
        if kind == "authors":
            w = st["base.gates.weight"]; H = w.shape[0] // 4
            return Net("authors", w.shape[1] - H, hidden=H, cls_layers=len([k for k in st if k.startswith("g_head.") and k.endswith(".weight")]))
        if kind in ("lstm50", "bilstm"): return Net(kind, NB)
        if kind == "ch":
            w = st["base.0.rnn.forget_gate.0.weight"]; H = w.shape[0]
            return CHClassifier(w.shape[1] - H, H, 0.0, len({k.split(".")[1] for k in st if k.startswith("base.")}), len({k.split(".")[1] for k in st if k.startswith("global_classifier.")}))
        raise ValueError(f"unknown model kind {kind}")


class TorchCropModel:
    """LSTM models (model.pt): the file holds the weights, the kind and the per-band mean / std used in training."""
    def __init__(self, path):
        if not HAVE_TORCH: raise ImportError("PyTorch is required for this model: pip install torch")
        ck = torch.load(path, map_location="cpu", weights_only=False)      # file written by our own training notebook - only load trusted files
        self.kind, st = ck["kind"], ck["state"]
        self.mean, self.std = np.asarray(ck["mean"], np.float32), np.asarray(ck["std"], np.float32)
        self.net = _build_net(self.kind, st); self.net.load_state_dict(st); self.net.eval()
    def predict_proba(self, X, batch=50000):
        X = np.asarray(X, np.float32).reshape(-1, T, NB); out = []
        with torch.no_grad():
            for i in range(0, len(X), batch):
                xb = torch.from_numpy(((X[i:i + batch] - self.mean) / self.std).astype(np.float32)); out.append(self.net(xb).reshape(-1).numpy())
        return np.concatenate(out) if out else np.zeros(0, np.float32)
    def predict(self, X, threshold=0.5): return (self.predict_proba(X) > threshold).astype(np.uint8)


class SkCropModel:
    """scikit-learn / XGBoost / CatBoost models (model.joblib), trained on the flat 77 features."""
    def __init__(self, path):
        import joblib
        self.model = joblib.load(path); self.kind = type(self.model).__name__
    def predict_proba(self, X):
        X = np.asarray(X, np.float32).reshape(-1, T * NB); m = self.model
        if hasattr(m, "centroids_"):                                                                 # minimum distance: distance to the non-cropland vs cropland centroid
            c = m.centroids_; d = np.stack([np.sqrt(((X - ci) ** 2).sum(1)) for ci in c], 1)
            return 1.0 / (1.0 + np.exp(-(d[:, 0] - d[:, 1])))
        if hasattr(m, "predict_proba"): return m.predict_proba(X)[:, 1]
        return 1.0 / (1.0 + np.exp(-m.decision_function(X)))                                         # SVM score squashed to 0-1 (not a calibrated probability)
    def predict(self, X, threshold=0.5): return (self.predict_proba(X) > threshold).astype(np.uint8)


def load_model(model_dir):
    d = Path(model_dir)
    if (d / "model.pt").exists(): return TorchCropModel(d / "model.pt")
    if (d / "model.joblib").exists(): return SkCropModel(d / "model.joblib")
    raise FileNotFoundError(f"no model.pt / model.joblib in {d}")
