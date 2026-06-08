"""
Generate a self-signed SSL certificate for localhost development.

Requirements: OpenSSL installed and on PATH.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


OPENSSL_CONFIG = """[req]
distinguished_name=req_distinguished_name
x509_extensions=v3_req
prompt=no

[req_distinguished_name]
CN=localhost

[v3_req]
subjectAltName=@alt_names
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth

[alt_names]
DNS.1=localhost
IP.1=127.0.0.1
"""


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    certs_dir = project_root / ".certs"
    certs_dir.mkdir(exist_ok=True)

    key_file = certs_dir / "localhost-key.pem"
    cert_file = certs_dir / "localhost.pem"
    cnf_file = certs_dir / "localhost-openssl.cnf"

    if not cnf_file.exists():
        cnf_file.write_text(OPENSSL_CONFIG, encoding="ascii")
        print(f"OpenSSL config created: {cnf_file}")

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
    print("  3. Choose 'Local Machine' -> Next")
    print("  4. Select 'Place all certificates in the following store' -> Browse")
    print("  5. Choose 'Trusted Root Certification Authorities' -> OK -> Next -> Finish")


if __name__ == "__main__":
    main()
