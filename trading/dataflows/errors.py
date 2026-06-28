"""Vendor error taxonomy."""


class VendorError(Exception):
    """Base exception for data vendor errors."""


class NoMarketDataError(VendorError):
    """No market data available for the requested symbol/date."""


class VendorRateLimitError(VendorError):
    """Vendor rate limit exceeded."""


class VendorNotConfiguredError(VendorError):
    """Vendor not configured (missing API key, etc.)."""


class VendorAuthError(VendorError):
    """Vendor authentication failure."""
