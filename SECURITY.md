# SECURITY — credentials and the pre-publication scrub

## Credential design

- No API key, token, or credential of any kind is stored in this
  repository — not in code, not in results, not in logs.
- During the runs, the operator's keys stayed in a separate credential
  vault. The runners fetched a short-lived **surrogate** value per
  connection and put it in the websocket auth header; the operator's
  network layer swapped it for the real key on egress. Run artifacts
  therefore record only the literal auth path string `surrogate_header`.
- The string `hsurr:` appears in `code/common.py` because the code
  asserts that the value it received is a surrogate (prefix check).
  It is a format check, not a credential — no surrogate value appears
  anywhere in this repo.
- If you re-run the harness with your own keys, keep them out of the
  tree: use environment variables or a vault, and note that `.gitignore`
  already excludes `.env`, key files, and local credential stores.

## Pre-publication scrub (run Nov 6, 2026, before the first commit)

The entire repo tree — code, JSONs, logs, CSVs, docs — was grepped for:

| Pattern class | Result |
|---|---|
| API key shapes (`sk-…`, `AIza…`, `xai-…`) | none found |
| Surrogate values (`hsurr:` followed by a value) | none found (prefix literal in code only, see above) |
| Email addresses | none found |
| Account / org / project IDs (`org-`, `acct_`, `proj_`, session IDs) | none found |
| Absolute home paths (`/home/…`) | found in 13 run `.log` files (final "saved …" line); **redacted** to repo-relative paths — see RESULTS.md |
| Operator name | removed from all current files; historical references use "the operator". Original commit history retains the as-run record, accepted by the operator; history and release tags are unchanged. |

Environment-specific paths that remain, deliberately, in the as-run code:
the vault-client helper path in `code/common.py` / `code/openai_runner.py`
and a source-document path in the `code/script_turns.py` docstring. These
identify the operator's tooling layout, not any credential, and the code
is published exactly as it ran.

## Found something?

If you spot anything in this repo that looks like a credential or
personal data, please open an issue before sharing it further.
