"""Temporal CNN architecture, seeded sampler and fitting loop."""
import numpy as np
import torch
from torch import nn

BATCH = 128
EPOCHS = 30

class TemporalNet(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv1d(channels, 16, kernel_size=3),
            nn.ReLU(),
            nn.Conv1d(16, 16, kernel_size=3),
            nn.ReLU(),
            nn.Flatten(),
        )
        self.predictor = nn.Sequential(nn.Linear(16 * 12 + 8, 32), nn.ReLU(), nn.Linear(32, 2))

    def forward(self, bins, auxiliary):
        return self.predictor(torch.cat((self.encoder(bins), auxiliary), dim=1))


def torch_inputs(arrays):
    bins, auxiliary = arrays
    return (
        torch.from_numpy(np.ascontiguousarray(bins.transpose(0, 2, 1), dtype=np.float32)),
        torch.from_numpy(np.ascontiguousarray(auxiliary, dtype=np.float32)),
    )


def schedule_for_seed(subjects, seed, epochs=EPOCHS):
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(subjects == number) for number in np.unique(subjects)]
    group_sizes = np.array([len(group) for group in groups])
    group_starts = np.r_[0, np.cumsum(group_sizes)[:-1]]
    row_list = np.concatenate(groups)
    batches = (len(subjects) + BATCH - 1) // BATCH
    people = rng.integers(len(groups), size=(epochs, batches, BATCH))
    locations = rng.integers(group_sizes[people])
    return row_list[group_starts[people] + locations]


def fit_temporal(model_channels, inputs, target, initial_bias, seed, schedule):
    torch.manual_seed(seed)
    model = TemporalNet(model_channels)
    with torch.no_grad():
        model.predictor[-1].weight.zero_()
        model.predictor[-1].bias.copy_(torch.from_numpy(initial_bias.astype(np.float32)))
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.0001)
    history = []
    for epoch in schedule:
        batch_losses = []
        for indices in epoch:
            bins, auxiliary = (array[indices] for array in inputs)
            loss = nn.functional.mse_loss(model(bins, auxiliary), target[indices])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            batch_losses.append(loss.detach())
        mean_loss = float(torch.stack(batch_losses).mean())
        if not np.isfinite(mean_loss):
            raise ValueError("Nonfinite temporal training loss")
        history.append(mean_loss)
    return model, history


def save_parameters(model):
    return {name: parameter.detach().numpy().copy() for name, parameter in model.state_dict().items()}


def restore_parameters(channels, parameters):
    model = TemporalNet(channels)
    expected = model.state_dict()
    if set(parameters) != set(expected):
        raise ValueError("Saved parameter names do not match architecture")
    tensors = {}
    for name, value in parameters.items():
        if value.dtype != np.float32 or value.shape != tuple(expected[name].shape) or not np.isfinite(value).all():
            raise ValueError(f"Invalid persisted temporal parameter {name}")
        tensors[name] = torch.from_numpy(value)
    model.load_state_dict(tensors)
    return model.eval()


@torch.no_grad()
def predict_temporal(model, inputs):
    bins, auxiliary = inputs
    return np.concatenate([
        model(bins[start:start+1024], auxiliary[start:start+1024]).numpy()
        for start in range(0, len(bins), 1024)
    ])
