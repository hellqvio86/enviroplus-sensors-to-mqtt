"""Basic package smoke tests."""

import enviroplussensorstomqtt


def test_package_metadata():
    """Test package version and basic import integrity."""
    assert enviroplussensorstomqtt is not None
    assert hasattr(enviroplussensorstomqtt, "__version__")
    assert enviroplussensorstomqtt.__version__ == "0.1.0"
