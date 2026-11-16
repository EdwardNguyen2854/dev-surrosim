"""MeshGraphNet-style field surrogate and a per-node MLP baseline."""

import torch
from torch import nn


def _mlp(dimensions: tuple[int, ...], activation=nn.SiLU) -> nn.Sequential:
    layers: list[nn.Module] = []
    for index in range(len(dimensions) - 1):
        layers.append(nn.Linear(dimensions[index], dimensions[index + 1]))
        if index < len(dimensions) - 2:
            layers.append(activation())
    return nn.Sequential(*layers)


class MessagePassingBlock(nn.Module):
    """One edge-update / node-update step with residual LayerNorm."""

    def __init__(self, hidden: int) -> None:
        super().__init__()
        self.edge_mlp = _mlp((3 * hidden, hidden, hidden))
        self.node_mlp = _mlp((2 * hidden, hidden, hidden))
        self.edge_norm = nn.LayerNorm(hidden)
        self.node_norm = nn.LayerNorm(hidden)

    def forward(self, h_v, edge_index, h_e):
        src, dst = edge_index[0], edge_index[1]
        edge_input = torch.cat([h_e, h_v[src], h_v[dst]], dim=-1)
        h_e = self.edge_norm(h_e + self.edge_mlp(edge_input))
        aggregated = torch.zeros_like(h_v).index_add_(0, dst, h_e)
        h_v = self.node_norm(h_v + self.node_mlp(torch.cat([h_v, aggregated], -1)))
        return h_v, h_e


class MeshGraphNet(nn.Module):
    def __init__(
        self,
        node_features: int,
        edge_features: int,
        hidden: int = 80,
        layers: int = 8,
        outputs: int = 9,
    ) -> None:
        super().__init__()
        self.node_encoder = _mlp((node_features, hidden, hidden))
        self.edge_encoder = _mlp((edge_features, hidden, hidden))
        self.blocks = nn.ModuleList(
            [MessagePassingBlock(hidden) for _ in range(layers)]
        )
        self.decoder = _mlp((hidden, hidden, outputs))

    def forward(self, x, edge_index, edge_attr):
        h_v = self.node_encoder(x)
        h_e = self.edge_encoder(edge_attr)
        for block in self.blocks:
            h_v, h_e = block(h_v, edge_index, h_e)
        return self.decoder(h_v)


class NodeMLP(nn.Module):
    """Field baseline without message passing (per-node coordinate MLP)."""

    def __init__(
        self, node_features: int, hidden: int = 128, layers: int = 3, outputs: int = 9
    ) -> None:
        super().__init__()
        dimensions = (node_features, *([hidden] * layers), outputs)
        self.mlp = _mlp(dimensions)

    def forward(self, x, edge_index=None, edge_attr=None):
        return self.mlp(x)


def build_model(name: str, node_features: int, edge_features: int, **kwargs):
    if name == "meshgraphnet":
        return MeshGraphNet(node_features, edge_features, **kwargs)
    if name == "node_mlp":
        return NodeMLP(node_features, **kwargs)
    raise ValueError(f"Unknown field model: {name}")
