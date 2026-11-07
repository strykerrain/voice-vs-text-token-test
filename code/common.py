"""Shared helpers: surrogate fetching (never logs/returns real credentials),
sentence/word counting, result writing."""
import json, os, re, sys

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import dynamic_credential_entry  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
AUDIO = os.path.join(ROOT, "audio")
RESULTS = os.path.join(ROOT, "results")

def patch_websockets_connection_check():
    """OpenAI's Realtime edge (Cloudflare) answers the upgrade with
    'Connection: close' alongside 'Upgrade: websocket'; websockets 17 rejects
    that. Patch out ONLY the Connection-header check; status, Upgrade and
    Sec-WebSocket-Accept validation stay intact."""
    from websockets.client import ClientProtocol
    from websockets.exceptions import InvalidHeader, InvalidHeaderValue, InvalidUpgrade, InvalidStatus
    from websockets.headers import parse_upgrade
    from websockets.utils import accept_key
    from websockets.datastructures import MultipleValuesError

    def process_response(self, response):
        if response.status_code != 101:
            raise InvalidStatus(response)
        headers = response.headers
        upgrade = sum([parse_upgrade(v) for v in headers.get_all("Upgrade")], [])
        if not (len(upgrade) == 1 and upgrade[0].lower() == "websocket"):
            raise InvalidUpgrade("Upgrade", ", ".join(upgrade) if upgrade else None)
        try:
            s_w_accept = headers["Sec-WebSocket-Accept"]
        except KeyError:
            raise InvalidHeader("Sec-WebSocket-Accept") from None
        except MultipleValuesError:
            raise InvalidHeader("Sec-WebSocket-Accept", "multiple values") from None
        if s_w_accept != accept_key(self.key):
            raise InvalidHeaderValue("Sec-WebSocket-Accept", s_w_accept)
        self.extensions = self.process_extensions(headers)
        self.subprotocol = self.process_subprotocol(headers)

    ClientProtocol.process_response = process_response

def get_surrogate(connector):
    """Return the hsurr:* surrogate string for a connector (not a real key)."""
    entry = dynamic_credential_entry(connector)
    s = str(entry["surrogate"]).strip()
    assert s.startswith("hsurr:"), "non-surrogate value returned"
    return s

def count_sentences(text):
    text = (text or "").strip()
    if not text:
        return 0
    # Poem lines etc.: terminator-based count, min 1 for non-empty
    parts = [p for p in re.split(r"[.!?]+(?:\s|$)", text) if p.strip()]
    return max(len(parts), 1)

def count_words(text):
    return len((text or "").split())

def load_pcm(sub, turn):
    with open(os.path.join(AUDIO, sub, f"turn{turn:02d}.pcm"), "rb") as f:
        return f.read()

def save_result(obj, filename):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, filename)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"saved {path}")
    return path
