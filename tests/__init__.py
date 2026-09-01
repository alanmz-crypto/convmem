"""Test host bootstrap for authority-boundary fixtures."""

import os
import secrets


# The test process stands in for the host integration. Capture the host-held
# credential before any test module can import the V2 authority substrate;
# claimant fixtures never choose the credential used to establish the registry.
_HOST_BOOTSTRAP_SECRET = os.environ.setdefault(
    "CONVMEM_NATURALISTIC_V2_AUTHORITY_BOOTSTRAP_SECRET",
    secrets.token_urlsafe(32),
)
