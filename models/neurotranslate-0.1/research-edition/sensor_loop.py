"""A causal measurement path through the Inkling 2 Mini Research Edition decoder."""

# The traversal is adapted from Transformers 5.24.0, modeling_inkling2_loop.py.
# Copyright 2026 the HuggingFace Team. Licensed under Apache-2.0.
# https://www.apache.org/licenses/LICENSE-2.0
# Changes: require explicit measurement evidence, condition the four cross-pass
# messages on that evidence, and choose the number of passes per forward call.

import torch
from torch import nn
from torch.nn import functional as F
from transformers.masking_utils import create_causal_mask, create_recurrent_attention_mask, create_sliding_window_causal_mask
from transformers.modeling_outputs import MoeModelOutputWithPast
from transformers.models.inkling2_loop.modeling_inkling2_loop import Inkling2LoopTextModel, get_relative_distance


class SensorMessages(nn.Module):
    def __init__(self, width, rank):
        super().__init__()
        if type(rank) is not int or rank < 1:
            raise ValueError('The sensor message projection needs a positive integer rank.')
        self.measurement_projection = nn.Linear(width, rank, bias=False)
        self.state_projection = nn.Linear(width, rank, bias=False)
        self.message_projection = nn.Linear(rank, 4 * width, bias=False)
        nn.init.zeros_(self.message_projection.weight)

    def encode_prefix(self, evidence, available):
        valid = available.unsqueeze(-1)
        clean = torch.where(valid, evidence.float(), 0.0)
        running_sum = clean.cumsum(1)
        if not torch.isfinite(running_sum).all():
            raise ValueError('Available evidence exceeds the precision of the sensor history.')
        mean = running_sum / valid.cumsum(1).clamp_min(1)
        scale = mean.abs().amax(dim=-1, keepdim=True).clamp_min(1.0)
        scaled = mean / scale
        normalized = scaled * torch.rsqrt(scaled.square().mean(dim=-1, keepdim=True) + (1e-6 / scale) / scale)
        return self.measurement_projection(normalized.to(self.measurement_projection.weight.dtype))

    def forward(self, projected_evidence, previous_hidden):
        state = F.rms_norm(previous_hidden.float(), (previous_hidden.shape[-1],), eps=1e-6)
        gate = self.state_projection(state.to(self.state_projection.weight.dtype)).sigmoid()
        correction = self.message_projection(projected_evidence * gate)
        return correction.unflatten(-1, (4, previous_hidden.shape[-1]))


class SensorLoopDecoder(nn.Module):
    """Run native Inkling layers with measurement-conditioned messages between passes."""

    def __init__(self, decoder: Inkling2LoopTextModel, rank):
        super().__init__()
        self.native = decoder
        self.config = decoder.config
        self.sensor_messages = SensorMessages(self.config.hidden_size, rank).to(decoder.embed_tokens.weight.device)

    def forward(self, inputs_embeds, evidence, available, *, passes=None):
        """Process one measured history without a generation cache."""
        depth = self.config.loop_num_passes if passes is None else passes
        if type(depth) is not int or depth < 1:
            raise ValueError('Use a positive integer number of passes.')
        if (inputs_embeds.ndim != 3 or not inputs_embeds.numel() or inputs_embeds.shape != evidence.shape
                or inputs_embeds.shape[-1] != self.config.hidden_size or available.shape != inputs_embeds.shape[:2]
                or available.dtype != torch.bool or inputs_embeds.device != evidence.device
                or inputs_embeds.device != available.device or not inputs_embeds.is_floating_point()
                or not evidence.is_floating_point()):
            raise ValueError('Supply equal-shaped embedded histories, sensor evidence and its availability mask.')
        if not torch.isfinite(torch.where(available.unsqueeze(-1), evidence, 0.0)).all():
            raise ValueError('Available sensor embeddings must be finite.')

        tokens = inputs_embeds.to(self.native.embed_tokens.weight.dtype)
        if not torch.isfinite(tokens).all():
            raise ValueError('The decoder input must be finite in its working precision.')
        positions = torch.arange(tokens.shape[1], device=tokens.device).unsqueeze(0)
        mask_kwargs = dict(config=self.config, inputs_embeds=tokens, attention_mask=None, cache=None,
                           position_ids=positions)
        masks = {'full_attention': create_causal_mask(**mask_kwargs),
                 'sliding_attention': create_sliding_window_causal_mask(**mask_kwargs)}
        convolution_mask = create_recurrent_attention_mask(**mask_kwargs)
        distances = {name: get_relative_distance(tokens, None, is_sliding=name == 'sliding_attention') for name in masks}

        def apply_layer(layer, hidden, blocks, message=None):
            kwargs = {} if message is None else {'messages': message}
            next_hidden = layer(hidden, blocks, attention_mask=masks[layer.attention_type],
                                relative_distance=distances[layer.attention_type], conv_mask=convolution_mask,
                                cache=None, position_ids=positions, **kwargs)
            if layer.is_block_boundary:
                blocks = torch.cat((blocks.to(hidden.device), hidden.unsqueeze(-2)), dim=-2)
            return next_hidden, blocks

        start, end = self.config.loop_layer_index_start, self.config.loop_layer_index_end
        hidden = tokens
        blocks = tokens.new_zeros(*tokens.shape[:-1], 0, tokens.shape[-1])
        for layer in self.native.layers[:start]:
            hidden, blocks = apply_layer(layer, hidden, blocks)
        start_hidden, start_blocks = hidden, blocks
        loop_layers = self.native.layers[start:end]
        for layer in loop_layers:
            hidden, blocks = apply_layer(layer, hidden, blocks)

        if depth > 1:
            projected = self.sensor_messages.encode_prefix(evidence, available)
        for _ in range(1, depth):
            previous_hidden = hidden
            previous_blocks = blocks[..., start_blocks.shape[-2] + 1:, :]
            correction = self.sensor_messages(projected, previous_hidden)
            hidden, blocks = start_hidden, start_blocks
            for index, layer in enumerate(loop_layers):
                native_message = self.native.message_input(previous_blocks, previous_hidden, index)
                message = native_message + correction.to(native_message)
                hidden, blocks = apply_layer(layer, hidden, blocks, message)

        for layer in self.native.layers[end:]:
            hidden, blocks = apply_layer(layer, hidden, blocks)
        combined = self.native.final_input(blocks, hidden)[0]
        output = self.native.norm(combined).to(tokens.dtype)
        if not torch.isfinite(output).all():
            raise ValueError('The decoder state exceeds its working precision.')
        return MoeModelOutputWithPast(last_hidden_state=output, cache=None)
