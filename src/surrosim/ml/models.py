"""Scalar surrogate model adapters with a common fit/predict/save contract.

All models are trained on ``log(target)`` because the engineering targets are
strictly positive and span two orders of magnitude; predictions are returned
in log space and exponentiated by the training pipeline.
"""

from pathlib import Path

import numpy as np

MODEL_NAMES = (
    "ridge",
    "random_forest",
    "xgboost",
    "mlp",
    "gaussian_process",
    "ensemble",
)


class SklearnModel:
    def __init__(self, name: str, estimator) -> None:
        self.name = name
        self.estimator = estimator

    def fit(self, X, y, X_val=None, y_val=None):
        if self.name == "xgboost" and X_val is not None:
            self.estimator.fit(
                X, y, eval_set=[(X_val, y_val)], verbose=False
            )
        else:
            self.estimator.fit(X, y)
        return self

    def predict(self, X) -> np.ndarray:
        return np.asarray(self.estimator.predict(X), dtype=float)

    def save(self, path: Path) -> None:
        import joblib

        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.estimator, path)

    @staticmethod
    def load(path: Path) -> "SklearnModel":
        import joblib

        return SklearnModel(Path(path).stem, joblib.load(path))


class TorchMLP:
    """Small fully connected network with internal feature standardization."""

    name = "mlp"

    def __init__(
        self,
        hidden: tuple[int, ...] = (128, 128),
        learning_rate: float = 1e-3,
        epochs: int = 400,
        patience: int = 40,
        batch_size: int = 64,
        seed: int = 42,
    ) -> None:
        self.hidden = hidden
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.patience = patience
        self.batch_size = batch_size
        self.seed = seed
        self.module = None
        self.x_mean = None
        self.x_std = None

    def _build(self, input_dim: int):
        import torch
        from torch import nn

        layers: list[nn.Module] = []
        previous = input_dim
        for width in self.hidden:
            layers += [nn.Linear(previous, width), nn.SiLU()]
            previous = width
        layers.append(nn.Linear(previous, 1))
        return nn.Sequential(*layers)

    def fit(self, X, y, X_val=None, y_val=None):
        import torch

        torch.manual_seed(self.seed)
        X = np.asarray(X, dtype=np.float32)
        y = np.asarray(y, dtype=np.float32)
        self.x_mean = X.mean(axis=0, keepdims=True)
        self.x_std = X.std(axis=0, keepdims=True) + 1e-9
        Xs = (X - self.x_mean) / self.x_std
        self.module = self._build(X.shape[1])
        optimizer = torch.optim.Adam(self.module.parameters(), lr=self.learning_rate)
        criterion = torch.nn.MSELoss()
        tensor_x = torch.from_numpy(Xs)
        tensor_y = torch.from_numpy(y).reshape(-1, 1)
        dataset = torch.utils.data.TensorDataset(tensor_x, tensor_y)
        generator = torch.Generator().manual_seed(self.seed)
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=self.batch_size, shuffle=True, generator=generator
        )
        if X_val is not None:
            val_x = torch.from_numpy(
                (np.asarray(X_val, dtype=np.float32) - self.x_mean) / self.x_std
            )
            val_y = torch.from_numpy(np.asarray(y_val, dtype=np.float32)).reshape(-1, 1)
        best_loss = float("inf")
        best_state = None
        waited = 0
        for _epoch in range(self.epochs):
            self.module.train()
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                loss = criterion(self.module(batch_x), batch_y)
                loss.backward()
                optimizer.step()
            if X_val is None:
                continue
            self.module.eval()
            with torch.no_grad():
                val_loss = float(criterion(self.module(val_x), val_y))
            if val_loss < best_loss - 1e-7:
                best_loss = val_loss
                best_state = {
                    key: value.detach().clone()
                    for key, value in self.module.state_dict().items()
                }
                waited = 0
            else:
                waited += 1
                if waited >= self.patience:
                    break
        if best_state is not None:
            self.module.load_state_dict(best_state)
        return self

    def predict(self, X) -> np.ndarray:
        import torch

        X = np.asarray(X, dtype=np.float32)
        Xs = (X - self.x_mean) / self.x_std
        self.module.eval()
        with torch.no_grad():
            return self.module(torch.from_numpy(Xs)).numpy().reshape(-1)

    def save(self, path: Path) -> None:
        import torch

        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self.module.state_dict(),
                "x_mean": self.x_mean,
                "x_std": self.x_std,
                "hidden": self.hidden,
                "seed": self.seed,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> "TorchMLP":
        import torch

        payload = torch.load(path, map_location="cpu", weights_only=False)
        model = cls(hidden=tuple(payload["hidden"]), seed=payload["seed"])
        model.x_mean = payload["x_mean"]
        model.x_std = payload["x_std"]
        model.module = model._build(int(model.x_mean.shape[1]))
        model.module.load_state_dict(payload["state_dict"])
        model.module.eval()
        return model


class EnsembleModel:
    """Unweighted average of member predictions in log space.

    Pairing a Gaussian process with a neural network hedges the GP's
    occasional large extrapolation errors with the MLP's smoother behaviour,
    and member disagreement is a useful confidence signal.
    """

    name = "ensemble"

    def __init__(self, members: list) -> None:
        self.members = members

    def fit(self, X, y, X_val=None, y_val=None):
        for member in self.members:
            member.fit(X, y, X_val, y_val)
        return self

    def predict(self, X) -> np.ndarray:
        return np.mean([member.predict(X) for member in self.members], axis=0)

    def member_predictions(self, X) -> np.ndarray:
        return np.vstack([member.predict(X) for member in self.members])

    def save(self, path: Path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        import json

        manifest = []
        for index, member in enumerate(self.members):
            member_path = path / f"member_{index}{model_suffix(member.name)}"
            member.save(member_path)
            manifest.append({"name": member.name, "file": member_path.name})
        (path / "members.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> "EnsembleModel":
        path = Path(path)
        import json

        manifest = json.loads((path / "members.json").read_text(encoding="utf-8"))
        members = [
            load_model(path / entry["file"], entry["name"]) for entry in manifest
        ]
        return cls(members)


def make_model(name: str, seed: int = 42):
    if name == "ridge":
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        return SklearnModel(name, make_pipeline(StandardScaler(), Ridge(alpha=1.0)))
    if name == "random_forest":
        from sklearn.ensemble import RandomForestRegressor

        return SklearnModel(
            name,
            RandomForestRegressor(
                n_estimators=500, min_samples_leaf=1, n_jobs=-1, random_state=seed
            ),
        )
    if name == "xgboost":
        from xgboost import XGBRegressor

        return SklearnModel(
            name,
            XGBRegressor(
                n_estimators=800,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_lambda=1.0,
                early_stopping_rounds=50,
                random_state=seed,
                n_jobs=-1,
            ),
        )
    if name == "mlp":
        return TorchMLP(seed=seed)
    if name == "gaussian_process":
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, WhiteKernel
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        kernel = 1.0 * RBF() + WhiteKernel(1e-3)
        return SklearnModel(
            name,
            make_pipeline(
                StandardScaler(),
                GaussianProcessRegressor(
                    kernel=kernel, normalize_y=True, n_restarts_optimizer=0,
                    random_state=seed,
                ),
            ),
        )
    if name == "ensemble":
        return EnsembleModel([TorchMLP(seed=seed), make_model("gaussian_process", seed)])
    raise ValueError(f"Unknown model: {name}")


def load_model(path: str | Path, name: str):
    path = Path(path)
    if path.is_dir():
        return EnsembleModel.load(path)
    if path.suffix == ".pt":
        return TorchMLP.load(path)
    return SklearnModel.load(path)


def model_suffix(name: str) -> str:
    if name == "ensemble":
        return ""
    return ".pt" if name == "mlp" else ".joblib"
