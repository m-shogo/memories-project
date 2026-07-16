#!/usr/bin/env python3
"""Offline validator for Memory OS Sign in with Apple server-auth contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROFILE_PATH = Path(
    "docs/fixtures/memory-os-security/"
    "apple-auth-validation-profile.round9.valid.v1.json"
)
CASE_SET_PATH = Path(
    "docs/fixtures/memory-os-security/"
    "apple-auth-validation-cases.round9.v1.json"
)
ISSUE_REGISTRY_PATH = Path(
    "docs/fixtures/memory-os-security/"
    "security-issue-code-registry.round9.v1.json"
)


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"expected JSON object: {path}")
    return value


def validate_profile(profile: dict[str, Any]) -> None:
    if profile["issuer"] != "https://appleid.apple.com":
        raise ValidationFailure("Apple issuer is not exact")
    if profile["jwksUrl"] != "https://appleid.apple.com/auth/keys":
        raise ValidationFailure("Apple JWKS URL is not exact")
    if profile["tokenEndpoint"] != "https://appleid.apple.com/auth/token":
        raise ValidationFailure("Apple token endpoint is not exact")
    if profile["allowedAlgorithms"] != ["RS256"]:
        raise ValidationFailure("only RS256 is allowed")
    if not profile["allowedAudiences"]:
        raise ValidationFailure("at least one exact audience is required")

    nonce = profile["nonce"]
    if not all(
        nonce[field] is True
        for field in (
            "required",
            "clientRequestUsesSha256",
            "serverComparesExactClaim",
            "singleUse",
        )
    ):
        raise ValidationFailure("nonce controls are incomplete")

    keys = profile["keyRotation"]
    if not all(
        keys[field] is True
        for field in (
            "cacheAllowed",
            "unknownKidRefreshOnce",
            "failClosedAfterRefresh",
            "tlsRequired",
        )
    ):
        raise ValidationFailure("JWKS rotation controls are incomplete")

    code = profile["authorizationCode"]
    if not all(
        code[field] is True
        for field in (
            "serverExchangeRequired",
            "singleUse",
            "exactClientIdBinding",
            "replayRejected",
        )
    ):
        raise ValidationFailure("authorization-code controls are incomplete")
    if code["redirectUriPolicy"] != "must_match_original_when_present":
        raise ValidationFailure("redirect URI policy is unsafe")

    binding = profile["accountBinding"]
    if binding["canonicalKey"] != ["issuer", "subject"]:
        raise ValidationFailure("account binding must use issuer + subject")
    if binding["emailAutoLinkAllowed"] is not False:
        raise ValidationFailure("email auto-linking is forbidden")
    if binding["privateRelayEmailIsIdentity"] is not False:
        raise ValidationFailure("private relay email cannot be identity")

    client = profile["clientAuthority"]
    if any(client.values()):
        raise ValidationFailure("client identity fields must not be trusted")


def decide(case: dict[str, Any], profile: dict[str, Any]) -> tuple[str, str]:
    if case["issuer"] != profile["issuer"]:
        return "deny", "SEC_APPLE_ISSUER_INVALID"
    if case["audience"] not in profile["allowedAudiences"]:
        return "deny", "SEC_APPLE_AUDIENCE_INVALID"
    if case["algorithm"] not in profile["allowedAlgorithms"]:
        return "deny", "SEC_APPLE_ALGORITHM_FORBIDDEN"
    if not case["kidKnownBeforeRefresh"] and not case["kidKnownAfterRefresh"]:
        return "deny", "SEC_APPLE_KEY_ID_UNKNOWN"
    if not case["signatureValid"]:
        return "deny", "SEC_APPLE_SIGNATURE_INVALID"
    if case["tokenExpired"]:
        return "deny", "SEC_APPLE_TOKEN_EXPIRED"
    if not case["issuedAtWithinWindow"]:
        return "deny", "SEC_APPLE_ISSUED_AT_INVALID"
    if not case["noncePresent"]:
        return "deny", "SEC_APPLE_NONCE_REQUIRED"
    if not case["nonceMatches"]:
        return "deny", "SEC_APPLE_NONCE_MISMATCH"
    if not case["subjectPresent"]:
        return "deny", "SEC_APPLE_SUBJECT_REQUIRED"
    if case["authorizationCodeAlreadyUsed"]:
        return "deny", "SEC_APPLE_CODE_REPLAY"
    if not case["authorizationCodeClientMatches"]:
        return "deny", "SEC_APPLE_CODE_CLIENT_MISMATCH"
    if not case["authorizationCodeRedirectMatches"]:
        return "deny", "SEC_APPLE_CODE_REDIRECT_MISMATCH"
    if case["emailOnlyLinkAttempt"]:
        return "deny", "SEC_APPLE_EMAIL_LINK_FORBIDDEN"
    if case["accountBindingConflict"]:
        return "deny", "SEC_APPLE_ACCOUNT_BINDING_CONFLICT"
    return "allow", "SEC_AUTHORIZED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()

    try:
        profile = load_json(root / PROFILE_PATH)
        case_set = load_json(root / CASE_SET_PATH)
        issue_registry = load_json(root / ISSUE_REGISTRY_PATH)
        issue_codes = {entry["code"] for entry in issue_registry["codes"]}

        if case_set["profileRef"] != PROFILE_PATH.as_posix():
            raise ValidationFailure("Apple auth cases point to a different profile")
        validate_profile(profile)

        seen_ids: set[str] = set()
        allow_count = 0
        deny_count = 0
        for case in case_set["cases"]:
            case_id = case["caseId"]
            if case_id in seen_ids:
                raise ValidationFailure(f"duplicate Apple auth case ID: {case_id}")
            seen_ids.add(case_id)
            if case["expectedIssueCode"] not in issue_codes:
                raise ValidationFailure(
                    f"unknown issue code in Apple auth case: {case['expectedIssueCode']}"
                )
            actual = decide(case, profile)
            expected = (case["expectedDecision"], case["expectedIssueCode"])
            if actual != expected:
                raise ValidationFailure(
                    f"Apple auth case mismatch {case_id}: expected={expected} actual={actual}"
                )
            if actual[0] == "allow":
                allow_count += 1
            else:
                deny_count += 1
    except ValidationFailure as exc:
        print(f"APPLE AUTH CONTRACT VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"APPLE AUTH CONTRACT VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    print("Memory OS Sign in with Apple contract validation PASS")
    print(f"cases: {allow_count + deny_count}")
    print(f"allow: {allow_count}")
    print(f"deny: {deny_count}")
    print("canonical account binding: issuer + subject")
    print("email auto-link: disabled")
    print("client identity authority: disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
