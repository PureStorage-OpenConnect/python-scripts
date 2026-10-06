#!/usr/bin/env python3
"""Renew the FlashArray management certificate through the REST 2.x API.

The script deliberately defaults to a read-only dry run. It can either:
  * import a CA-signed certificate and matching private key; or
  * generate a new self-signed management certificate on the array.

Example: inspect the current certificate
    python flasharray_certificate_renewal.py --array fa01.example.com --api-token "$FLASHARRAY_API_TOKEN"

Example: install a CA-signed certificate when 30 days or less remain
    python flasharray_certificate_renewal.py \
        --array fa01.example.com \
        --api-token "$FLASHARRAY_API_TOKEN" \
        --certificate /secure/certs/fa01.crt \
        --private-key /secure/certs/fa01.key \
        --intermediate-certificate /secure/certs/chain.crt \
        --apply

Example: regenerate a self-signed certificate
    python flasharray_certificate_renewal.py --array fa01.example.com --api-token "$FLASHARRAY_API_TOKEN" --self-signed --apply

Dependencies:
    python -m pip install requests cryptography
"""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from cryptography import x509
from cryptography.hazmat.primitives import serialization

LOG = logging.getLogger("flasharray_certificate_renewal")
CERTIFICATE_NAME = "management"


class FlashArrayApiError(RuntimeError):
    """Raised when the FlashArray REST API returns an error."""


@dataclass(frozen=True)
class CertificateStatus:
    name: str
    valid_to: datetime
    days_remaining: float
    common_name: str | None = None


class FlashArrayRestClient:
    """Small REST 2.x client for the FlashArray certificate workflow."""

    def __init__(
        self,
        array: str,
        api_token: str,
        api_version: str,
        verify: bool | str,
        timeout: float,
    ) -> None:
        self.base_url = f"https://{array.rstrip('/')}/api/{api_version}"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "flasharray-certificate-renewal/1.0",
            }
        )
        self._api_token = api_token

    def __enter__(self) -> "FlashArrayRestClient":
        self.login()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.logout()

    def login(self) -> None:
        """Exchange the API token for a REST session cookie."""
        response = self.session.post(
            f"{self.base_url}/auth/session",
            data={"api_token": self._api_token},
            timeout=self.timeout,
        )
        self._raise_for_status(response, "creating REST session")

    def logout(self) -> None:
        """Invalidate the REST session, without hiding the original exception."""
        try:
            response = self.session.delete(
                f"{self.base_url}/auth/session", timeout=self.timeout
            )
            if response.status_code not in (200, 204):
                LOG.warning("REST session cleanup returned HTTP %s", response.status_code)
        except requests.RequestException as exc:
            LOG.warning("REST session cleanup failed: %s", exc.__class__.__name__)

    def get_management_certificate(self) -> dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/certificates",
            params={"names": CERTIFICATE_NAME},
            timeout=self.timeout,
        )
        self._raise_for_status(response, "reading management certificate")
        payload = response.json()
        certificates = self._items(payload)
        if not certificates:
            raise FlashArrayApiError(
                f"FlashArray returned no certificate named {CERTIFICATE_NAME!r}"
            )
        return certificates[0]

    def import_management_certificate(
        self,
        certificate_pem: str,
        private_key_pem: str,
        passphrase: str | None = None,
        intermediate_certificate_pem: str | None = None,
    ) -> dict[str, Any]:
        # FlashArray uses `key` for the private key in CertificatePost-style
        # certificate imports. The names query parameter selects the built-in
        # management certificate.
        body: dict[str, Any] = {
            "certificate": certificate_pem,
            "key": private_key_pem,
        }
        if passphrase:
            body["passphrase"] = passphrase
        if intermediate_certificate_pem:
            body["intermediate_certificate"] = intermediate_certificate_pem

        response = self.session.patch(
            f"{self.base_url}/certificates",
            params={"names": CERTIFICATE_NAME},
            json=body,
            timeout=self.timeout,
        )
        self._raise_for_status(response, "importing management certificate")
        payload = response.json()
        certificates = self._items(payload)
        return certificates[0] if certificates else payload

    def regenerate_self_signed_certificate(self) -> dict[str, Any]:
        response = self.session.patch(
            f"{self.base_url}/certificates",
            params={
                "names": CERTIFICATE_NAME,
                "generate_new_key": "true",
            },
            json={},
            timeout=self.timeout,
        )
        self._raise_for_status(response, "regenerating self-signed certificate")
        payload = response.json()
        certificates = self._items(payload)
        return certificates[0] if certificates else payload

    @staticmethod
    def _items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            return [item for item in payload["items"] if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict) and "name" in payload:
            return [payload]
        return []

    @staticmethod
    def _raise_for_status(response: requests.Response, operation: str) -> None:
        if response.ok:
            return
        # Do not print response headers or request details: those can contain
        # session material. The response body is included only for API errors.
        detail = response.text.strip().replace("\n", " ")[:1000]
        raise FlashArrayApiError(
            f"Failed while {operation}: HTTP {response.status_code}: {detail}"
        )


def read_text_file(path: str | None, label: str, required: bool = False) -> str | None:
    if not path:
        if required:
            raise ValueError(f"--{label.replace(' ', '-')} is required")
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Unable to read {label} file {path!r}: {exc}") from exc


def parse_certificate_pem(pem: str, source: str) -> x509.Certificate:
    try:
        return x509.load_pem_x509_certificate(pem.encode("utf-8"))
    except ValueError as exc:
        raise ValueError(f"{source} is not a valid PEM X.509 certificate") from exc


def validate_certificate_and_key(
    certificate_pem: str,
    private_key_pem: str,
    passphrase: str | None,
) -> x509.Certificate:
    certificate = parse_certificate_pem(certificate_pem, "Certificate")
    try:
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=passphrase.encode("utf-8") if passphrase else None,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Private key is invalid or the passphrase is incorrect") from exc

    cert_public = certificate.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_public = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if cert_public != key_public:
        raise ValueError("Certificate and private key do not form a matching key pair")
    return certificate


def parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def certificate_status(certificate: dict[str, Any]) -> CertificateStatus:
    valid_to = parse_datetime(
        certificate.get("valid_to")
        or certificate.get("not_after")
        or certificate.get("expiration_date")
    )
    if valid_to is None and isinstance(certificate.get("certificate"), str):
        parsed = parse_certificate_pem(certificate["certificate"], "Array certificate")
        valid_to = getattr(parsed, "not_valid_after_utc", parsed.not_valid_after.replace(tzinfo=timezone.utc))
        common_name = parsed.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        common_name_value = common_name[0].value if common_name else None
    else:
        common_name_value = certificate.get("common_name")

    if valid_to is None:
        raise FlashArrayApiError("The API response did not include a parseable certificate expiry")

    now = datetime.now(timezone.utc)
    return CertificateStatus(
        name=str(certificate.get("name", CERTIFICATE_NAME)),
        valid_to=valid_to,
        days_remaining=(valid_to - now).total_seconds() / 86400,
        common_name=common_name_value if isinstance(common_name_value, str) else None,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--array", required=True, help="FlashArray management hostname or IP")
    parser.add_argument(
        "--api-token",
        default=os.getenv("FLASHARRAY_API_TOKEN"),
        help="FlashArray API token; prefer FLASHARRAY_API_TOKEN",
    )
    parser.add_argument(
        "--api-version",
        default="2.0",
        help="REST API version, for example 2.0 or 2.49 (default: 2.0)",
    )
    parser.add_argument(
        "--renew-within-days",
        type=float,
        default=30,
        help="Renew only when fewer than this many days remain (default: 30)",
    )
    parser.add_argument("--certificate", help="CA-signed certificate PEM file")
    parser.add_argument("--private-key", help="Matching private key PEM file")
    parser.add_argument("--intermediate-certificate", help="Optional intermediate chain PEM file")
    parser.add_argument(
        "--passphrase",
        help="Passphrase for an encrypted private key; prefer FLASHARRAY_KEY_PASSPHRASE",
    )
    parser.add_argument(
        "--self-signed",
        action="store_true",
        help="Regenerate a self-signed certificate instead of importing PEM files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Renew even when the current certificate is outside the threshold",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the PATCH; without this flag the script is read-only",
    )
    parser.add_argument(
        "--ca-bundle",
        help="CA bundle path for verifying the array certificate",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (avoid outside isolated testing)",
    )
    parser.add_argument("--timeout", type=float, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.renew_within_days < 0:
        parser.error("--renew-within-days must be non-negative")
    if args.insecure and args.ca_bundle:
        parser.error("use either --insecure or --ca-bundle, not both")
    if args.self_signed and (args.certificate or args.private_key or args.intermediate_certificate):
        parser.error("--self-signed cannot be combined with PEM file arguments")
    if bool(args.certificate) != bool(args.private_key):
        parser.error("--certificate and --private-key must be supplied together")
    if not args.api_token:
        parser.error("provide --api-token or set FLASHARRAY_API_TOKEN")

    passphrase = args.passphrase or os.getenv("FLASHARRAY_KEY_PASSPHRASE")
    verify: bool | str = False if args.insecure else (args.ca_bundle or True)
    if args.insecure:
        LOG.warning("TLS certificate verification is disabled")

    certificate_pem = read_text_file(args.certificate, "certificate", required=False)
    private_key_pem = read_text_file(args.private_key, "private-key", required=False)
    intermediate_pem = read_text_file(
        args.intermediate_certificate, "intermediate-certificate", required=False
    )
    new_certificate: x509.Certificate | None = None
    if certificate_pem and private_key_pem:
        new_certificate = validate_certificate_and_key(certificate_pem, private_key_pem, passphrase)
        LOG.info("Validated the replacement certificate and matching private key")
        if intermediate_pem:
            # Validate the first certificate in the supplied chain. The API still
            # receives the original PEM text, preserving the complete chain.
            parse_certificate_pem(intermediate_pem, "Intermediate certificate")

    try:
        with FlashArrayRestClient(
            args.array, args.api_token, args.api_version, verify, args.timeout
        ) as client:
            current = client.get_management_certificate()
            status = certificate_status(current)
            LOG.info(
                "Current %s certificate expires %s (%.1f days remaining)%s",
                status.name,
                status.valid_to.isoformat(),
                status.days_remaining,
                f", CN={status.common_name}" if status.common_name else "",
            )

            should_renew = args.force or status.days_remaining <= args.renew_within_days
            if not should_renew:
                LOG.info("No renewal needed; threshold is %.1f days", args.renew_within_days)
                return 0

            if not args.apply:
                if args.self_signed:
                    LOG.info("DRY RUN: would regenerate the self-signed management certificate")
                elif certificate_pem and private_key_pem:
                    assert new_certificate is not None
                    LOG.info(
                        "DRY RUN: would import the supplied certificate, expiring %s",
                        getattr(new_certificate, "not_valid_after_utc", new_certificate.not_valid_after.replace(tzinfo=timezone.utc)).isoformat(),
                    )
                else:
                    LOG.info(
                        "DRY RUN: renewal is due; provide --certificate/--private-key or --self-signed"
                    )
                return 0

            if args.self_signed:
                LOG.info("Regenerating self-signed management certificate")
                client.regenerate_self_signed_certificate()
            elif certificate_pem and private_key_pem:
                LOG.info("Importing CA-signed management certificate")
                client.import_management_certificate(
                    certificate_pem,
                    private_key_pem,
                    passphrase,
                    intermediate_pem,
                )
            else:
                raise ValueError(
                    "Renewal is due. Supply --certificate and --private-key, or use --self-signed"
                )

            # Read back the certificate after the PATCH to confirm that the array
            # reports the new expiry. This also avoids logging certificate contents.
            updated = certificate_status(client.get_management_certificate())
            LOG.info(
                "Renewal complete; management certificate now expires %s",
                updated.valid_to.isoformat(),
            )
            return 0
    except (FlashArrayApiError, OSError, ValueError, requests.RequestException) as exc:
        LOG.error("Certificate renewal failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
