"""Tests for DrawConfig."""

from wc_draw.config import DrawConfig


def test_default_config():
    """Test default DrawConfig has all features disabled."""
    config = DrawConfig()
    assert config.uefa_group_winners_separated is False
    assert config.uefa_playoffs_seeded is False


def test_config_with_features_enabled():
    """Test creating config with features enabled."""
    config = DrawConfig(
        uefa_group_winners_separated=True,
        uefa_playoffs_seeded=True,
    )
    assert config.uefa_group_winners_separated is True
    assert config.uefa_playoffs_seeded is True


def test_config_partial_features():
    """Test enabling features independently."""
    config1 = DrawConfig(uefa_group_winners_separated=True)
    assert config1.uefa_group_winners_separated is True
    assert config1.uefa_playoffs_seeded is False

    config2 = DrawConfig(uefa_playoffs_seeded=True)
    assert config2.uefa_group_winners_separated is False
    assert config2.uefa_playoffs_seeded is True


def test_config_to_dict():
    """Test config can be converted to dictionary."""
    config = DrawConfig(uefa_group_winners_separated=True, uefa_playoffs_seeded=False)
    data = config.to_dict()

    assert isinstance(data, dict)
    assert data["uefa_group_winners_separated"] is True
    assert data["uefa_playoffs_seeded"] is False


def test_config_from_dict():
    """Test config can be created from dictionary."""
    data = {
        "uefa_group_winners_separated": True,
        "uefa_playoffs_seeded": True,
    }
    config = DrawConfig.from_dict(data)

    assert config.uefa_group_winners_separated is True
    assert config.uefa_playoffs_seeded is True


def test_config_from_dict_ignores_unknown_keys():
    """Test from_dict ignores unknown keys for forward compatibility."""
    data = {
        "uefa_group_winners_separated": True,
        "uefa_playoffs_seeded": False,
        "unknown_feature": True,  # Should be ignored
    }
    config = DrawConfig.from_dict(data)

    assert config.uefa_group_winners_separated is True
    assert config.uefa_playoffs_seeded is False
    assert not hasattr(config, "unknown_feature")


def test_config_roundtrip():
    """Test config survives to_dict -> from_dict roundtrip."""
    original = DrawConfig(uefa_group_winners_separated=True, uefa_playoffs_seeded=True)
    data = original.to_dict()
    restored = DrawConfig.from_dict(data)

    assert original.uefa_group_winners_separated == restored.uefa_group_winners_separated
    assert original.uefa_playoffs_seeded == restored.uefa_playoffs_seeded


def test_config_str_default():
    """Test string representation of default config."""
    config = DrawConfig()
    result = str(config)
    assert "default" in result.lower()
    assert "all features off" in result.lower()


def test_config_str_with_features():
    """Test string representation with features enabled."""
    config = DrawConfig(uefa_group_winners_separated=True, uefa_playoffs_seeded=True)
    result = str(config)
    assert "UEFA group winners separated" in result
    assert "UEFA playoffs seeded" in result


def test_config_str_partial_features():
    """Test string representation with one feature enabled."""
    config = DrawConfig(uefa_group_winners_separated=True)
    result = str(config)
    assert "UEFA group winners separated" in result
    assert "UEFA playoffs seeded" not in result
