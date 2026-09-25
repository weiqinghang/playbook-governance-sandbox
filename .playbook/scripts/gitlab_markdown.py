"""Prepare and verify lossless GitLab Markdown payloads."""
import argparse
import json
import re
import subprocess
from pathlib import Path


def _outside_code_lines(text: str):
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced:
            yield number, re.sub(r"`[^`]*`", "", line)


def validate(markdown: str) -> str:
    if not isinstance(markdown, str):
        raise ValueError("Markdown must be text")
    for number, line in _outside_code_lines(markdown):
        if r"\n" in line:
            raise ValueError(f"literal\\n outside code at line {number}; provide an actual newline")
    return markdown


def matches_readback(expected: str, actual: str) -> bool:
    validate(expected)
    validate(actual)
    # GitLab's API may remove one terminal line-feed from the sent body. This is
    # deliberately one-way: an unexpected LF in readback remains a mismatch.
    expected = expected.replace("\r\n", "\n")
    actual = actual.replace("\r\n", "\n")
    return actual == expected or (expected.endswith("\n") and actual == expected[:-1])


def _read_markdown(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def prepare_payload(markdown: str, field: str = "description") -> dict:
    """Return the JSON body accepted by a GitLab description or note endpoint."""
    if field not in {"description", "body"}:
        raise ValueError("GitLab Markdown field must be description or body")
    return {field: validate(markdown)}


def managed_write_readback(write_endpoint: str, read_endpoint: str, method: str, markdown: str,
                           field: str = "description", runner=subprocess.run) -> str:
    """Write through glab, GET the authoritative object, then fail closed on a mismatch."""
    payload = json.dumps(prepare_payload(markdown, field), ensure_ascii=False)
    written = runner(
        ["glab", "api", "-X", method, write_endpoint, "--raw-field", f"{field}={markdown}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if written.returncode:
        raise RuntimeError(f"GitLab write failed: {written.stderr.strip() or written.stdout.strip()}")
    read = runner(["glab", "api", read_endpoint], text=True, capture_output=True, check=False)
    if read.returncode:
        raise RuntimeError(f"GitLab readback failed: {read.stderr.strip() or read.stdout.strip()}")
    try:
        actual = json.loads(read.stdout)[field]
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"GitLab readback did not contain {field!r}") from error
    if not isinstance(actual, str) or not matches_readback(markdown, actual):
        raise ValueError("GitLab Markdown readback differs from the sent body")
    return actual


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="validate Markdown and emit a GitLab JSON payload")
    prepare.add_argument("--input", required=True, help="UTF-8 Markdown source file")
    prepare.add_argument("--output", help="optional JSON payload file; otherwise stdout")
    prepare.add_argument("--field", choices=("description", "body"), default="description")

    verify = commands.add_parser("verify-readback", help="compare sent and returned Markdown")
    verify.add_argument("--expected", required=True, help="sent UTF-8 Markdown file")
    verify.add_argument("--actual", required=True, help="read-back UTF-8 Markdown file")

    write = commands.add_parser("managed-write", help="write via glab and verify authoritative GET readback")
    write.add_argument("--write-endpoint", required=True, help="GitLab API endpoint for POST/PUT")
    write.add_argument("--read-endpoint", required=True, help="GitLab API endpoint for authoritative GET")
    write.add_argument("--method", choices=("POST", "PUT"), required=True)
    write.add_argument("--input", required=True, help="UTF-8 Markdown source file")
    write.add_argument("--field", choices=("description", "body"), default="description")

    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            payload = json.dumps(prepare_payload(_read_markdown(args.input), args.field), ensure_ascii=False) + "\n"
            if args.output:
                Path(args.output).write_text(payload, encoding="utf-8")
            else:
                print(payload, end="")
            return 0

        if args.command == "managed-write":
            managed_write_readback(
                args.write_endpoint,
                args.read_endpoint,
                args.method,
                _read_markdown(args.input),
                args.field,
            )
            return 0

        if not matches_readback(_read_markdown(args.expected), _read_markdown(args.actual)):
            print("GitLab Markdown readback differs from the sent body", flush=True)
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"gitlab_markdown: {error}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
