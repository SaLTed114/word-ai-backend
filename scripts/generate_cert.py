"""
Generate a self-signed SSL certificate for localhost development.

Requirements: OpenSSL installed and on PATH.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    certs_dir = project_root / ".certs"
    certs_dir.mkdir(exist_ok=True)

    key_file = certs_dir / "localhost-key.pem"
    cert_file = certs_dir / "localhost.pem"
    cnf_file = certs_dir / "localhost-openssl.cnf"

    if not cnf_file.exists():
        print(f"ERROR: OpenSSL config not found at {cnf_file}")
        sys.exit(1)

    print("Generating self-signed certificate for localhost...")

    # Generate private key
    subprocess.run(
        ["openssl", "genrsa", "-out", str(key_file), "2048"],
        check=True,
    )

    # Generate certificate
    subprocess.run(
        [
            "openssl", "req", "-new", "-x509",
            "-key", str(key_file),
            "-out", str(cert_file),
            "-days", "3650",
            "-config", str(cnf_file),
        ],
        check=True,
    )

    print(f"Certificate created: {cert_file}")
    print(f"Private key:         {key_file}")
    print()
    print("To trust this certificate on Windows:")
    print(f"  1. Double-click {cert_file}")
    print("  2. Click 'Install Certificate...'")
    print("  3. Choose 'Local Machine' → Next")
    print("  4. Select 'Place all certificates in the following store' → Browse")
    print("  5. Choose 'Trusted Root Certification Authorities' → OK → Next → Finish")


if __name__ == "__main__":
    main()
