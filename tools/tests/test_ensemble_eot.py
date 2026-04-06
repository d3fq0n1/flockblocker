"""Tests for ensemble EOT optimization."""

import pytest
import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from ensemble_eot import (
    EnsembleEOTConfig,
    WhiteBoxEngineLoss,
    BlackBoxEngineLoss,
    OptimizationResult,
    optimize_ensemble_patch,
    _apply_random_transform,
    _total_variation,
    _apply_printability_constraint,
)


# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

class TestEnsembleEOTConfig:
    def test_default_weights(self):
        config = EnsembleEOTConfig()
        assert config.engine_weights["easyocr"] == 1.0
        assert config.engine_weights["paddleocr"] == 1.0
        assert config.engine_weights["tesseract"] == 1.0

    def test_custom_weights(self):
        config = EnsembleEOTConfig(engine_weights={
            "easyocr": 2.0,
            "paddleocr": 0.5,
            "tesseract": 0.0,
        })
        assert config.engine_weights["easyocr"] == 2.0
        assert config.engine_weights["tesseract"] == 0.0

    def test_aggregation_modes(self):
        for mode in ["weighted_mean", "weighted_max"]:
            config = EnsembleEOTConfig(aggregation=mode)
            assert config.aggregation == mode


# ═══════════════════════════════════════════════════════════════════════════
# White-box engine loss
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch required")
class TestWhiteBoxEngineLoss:
    def test_easyocr_loss_returns_scalar(self):
        loss_fn = WhiteBoxEngineLoss("easyocr")
        device = torch.device("cpu")
        patch = torch.rand(1, 3, 120, 480, device=device)
        loss = loss_fn.compute_loss(patch, device)
        assert loss.dim() == 0  # scalar

    def test_paddleocr_loss_returns_scalar(self):
        loss_fn = WhiteBoxEngineLoss("paddleocr")
        device = torch.device("cpu")
        patch = torch.rand(1, 3, 120, 480, device=device)
        loss = loss_fn.compute_loss(patch, device)
        assert loss.dim() == 0

    def test_loss_has_gradient(self):
        loss_fn = WhiteBoxEngineLoss("easyocr")
        device = torch.device("cpu")
        patch = torch.rand(1, 3, 120, 480, device=device, requires_grad=True)
        loss = loss_fn.compute_loss(patch, device)
        loss.backward()
        assert patch.grad is not None
        assert patch.grad.shape == patch.shape

    def test_different_engines_different_weights(self):
        """Different engines should produce different loss values due to weight profiles."""
        device = torch.device("cpu")
        patch = torch.rand(1, 3, 120, 480, device=device)

        easy_loss = WhiteBoxEngineLoss("easyocr").compute_loss(patch, device)
        paddle_loss = WhiteBoxEngineLoss("paddleocr").compute_loss(patch, device)

        # They may be close but shouldn't be identical (different weight profiles)
        # Allow for numerical coincidence by checking over multiple patches
        differences = 0
        for _ in range(5):
            p = torch.rand(1, 3, 120, 480, device=device)
            el = WhiteBoxEngineLoss("easyocr").compute_loss(p, device)
            pl = WhiteBoxEngineLoss("paddleocr").compute_loss(p, device)
            if abs(el.item() - pl.item()) > 1e-6:
                differences += 1
        assert differences > 0


# ═══════════════════════════════════════════════════════════════════════════
# EOT transforms
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch required")
class TestEOTTransforms:
    def test_random_transform_preserves_shape(self):
        config = EnsembleEOTConfig()
        device = torch.device("cpu")
        patch = torch.rand(1, 3, 120, 480, device=device)
        transformed = _apply_random_transform(patch, config, device)
        assert transformed.shape == patch.shape

    def test_random_transform_values_in_range(self):
        config = EnsembleEOTConfig()
        device = torch.device("cpu")
        patch = torch.rand(1, 3, 120, 480, device=device)
        transformed = _apply_random_transform(patch, config, device)
        assert transformed.min() >= 0.0
        assert transformed.max() <= 1.0

    def test_total_variation(self):
        device = torch.device("cpu")
        # Uniform image: TV = 0
        uniform = torch.ones(1, 3, 10, 10, device=device) * 0.5
        assert _total_variation(uniform).item() == 0.0

        # Random image: TV > 0
        noisy = torch.rand(1, 3, 10, 10, device=device)
        assert _total_variation(noisy).item() > 0.0

    def test_printability_constraint(self):
        device = torch.device("cpu")
        # Create oversaturated patch
        patch = torch.zeros(1, 3, 10, 10, device=device)
        patch[0, 0, :, :] = 1.0  # full red, no green/blue
        constrained = _apply_printability_constraint(patch)
        # Saturation should be reduced
        max_ch = constrained.max(dim=1).values
        min_ch = constrained.min(dim=1).values
        sat = (max_ch - min_ch) / (max_ch + 1e-8)
        assert sat.max().item() <= 0.96  # was 1.0, now reduced


# ═══════════════════════════════════════════════════════════════════════════
# Full optimizer
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch required")
class TestOptimizer:
    def test_optimize_runs_minimal(self):
        """Run optimizer with minimal steps to verify pipeline works."""
        config = EnsembleEOTConfig(
            width=60,
            height=30,
            num_steps=3,
            eot_samples=2,
            engine_weights={"easyocr": 1.0, "paddleocr": 1.0},
            seed=42,
        )
        result = optimize_ensemble_patch(config)
        assert isinstance(result, OptimizationResult)
        assert result.image.size == (60, 30)
        assert result.steps_completed == 3
        assert len(result.aggregate_loss_history) == 3

    def test_optimize_weighted_max_aggregation(self):
        config = EnsembleEOTConfig(
            width=60,
            height=30,
            num_steps=2,
            eot_samples=2,
            aggregation="weighted_max",
            engine_weights={"easyocr": 1.0, "paddleocr": 1.0},
            seed=42,
        )
        result = optimize_ensemble_patch(config)
        assert result.steps_completed == 2

    def test_optimize_weighted_mean_aggregation(self):
        config = EnsembleEOTConfig(
            width=60,
            height=30,
            num_steps=2,
            eot_samples=2,
            aggregation="weighted_mean",
            engine_weights={"easyocr": 1.0, "paddleocr": 1.0},
            seed=42,
        )
        result = optimize_ensemble_patch(config)
        assert result.steps_completed == 2

    def test_optimize_seed_reproducibility(self):
        config = EnsembleEOTConfig(
            width=60,
            height=30,
            num_steps=5,
            eot_samples=2,
            engine_weights={"easyocr": 1.0},
            seed=42,
        )
        r1 = optimize_ensemble_patch(config)
        r2 = optimize_ensemble_patch(config)
        # Same seed → same result
        arr1 = np.array(r1.image)
        arr2 = np.array(r2.image)
        assert np.array_equal(arr1, arr2)

    def test_optimize_saves_output(self):
        import tempfile
        from pathlib import Path

        config = EnsembleEOTConfig(
            width=60,
            height=30,
            num_steps=2,
            eot_samples=2,
            engine_weights={"easyocr": 1.0},
            seed=42,
        )
        with tempfile.TemporaryDirectory() as tmp:
            out_path = str(Path(tmp) / "patch.png")
            result = optimize_ensemble_patch(config, output_path=out_path)
            assert Path(out_path).exists()


@pytest.mark.skipif(not HAS_PIL, reason="Pillow required")
class TestFallback:
    def test_fallback_heuristic(self):
        """When torch is unavailable, should produce a heuristic patch."""
        from ensemble_eot import _fallback_heuristic
        config = EnsembleEOTConfig(width=120, height=60, seed=42)
        result = _fallback_heuristic(config, None)
        assert isinstance(result, OptimizationResult)
        assert result.image.size == (120, 60)
        assert result.steps_completed == 0

    def test_fallback_saves_output(self):
        import tempfile
        from pathlib import Path
        from ensemble_eot import _fallback_heuristic

        config = EnsembleEOTConfig(width=120, height=60, seed=42)
        with tempfile.TemporaryDirectory() as tmp:
            out_path = str(Path(tmp) / "fallback.png")
            result = _fallback_heuristic(config, out_path)
            assert Path(out_path).exists()
