"""Bounded ZIP range reader: downloads selected summary members, never raw genomes."""
import argparse
from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import urllib.request
import zlib
import zipfile

ROOT = Path(__file__).resolve().parent
RECORD = "https://zenodo.org/records/17489849"
MODELS = ("ss_intf", "sa_intf", "ss_poiss", "sa_poiss")


def verify_definitions(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for cousin in range(1, 9):
            text = archive.read(f"deg{2 * cousin + 1}-full.def").decode("utf8")
            declarations = [line.strip() for line in text.splitlines() if line.strip().startswith("def ")]
            if declarations != [f"def {cousin}c 50000 {cousin + 2}"]:
                raise ValueError("Ped-sim copy count/relationship definition changed; zero restoration refused")
        readme = archive.read("README.sh").decode("utf8")
        if "50,000 pairs" not in readme or "50,001 - [line count" not in readme:
            raise ValueError("Expected zero-omission documentation changed; review source")
    return {"pairs_per_batch": 50000, "full_cousin_definitions_checked": 8, "readme_sha256": hashlib.sha256(readme.encode()).hexdigest()}


@dataclass
class Member:
    name: str
    compressed: int
    uncompressed: int
    offset: int
    crc32: int
    method: int
    flags: int


def central_members(data):
    members, position = [], 0
    while position < len(data):
        if data[position:position + 4] != b"PK\x01\x02":
            raise ValueError("Invalid ZIP central directory")
        h = struct.unpack_from("<4s6H3I5H2I", data, position)
        length = 46 + h[10] + h[11] + h[12]
        if position + length > len(data):
            raise ValueError("Truncated ZIP directory")
        name = data[position + 46:position + 46 + h[10]].decode("utf8")
        members.append(Member(name, h[8], h[9], h[16], h[7], h[4], h[3]))
        position += length
    return members


def inflate_member(compressed, member):
    if member.flags & 1 or member.uncompressed > 10_000_000:
        raise ValueError("Encrypted/oversized ZIP member refused")
    if member.method == 8:
        inflater = zlib.decompressobj(-15)
        raw = inflater.decompress(compressed, member.uncompressed + 1)
        if not inflater.eof or inflater.unused_data:
            raise ValueError("Malformed or oversized deflate stream")
    elif member.method == 0:
        raw = compressed
    else:
        raise ValueError("Unsupported ZIP compression")
    if len(raw) != member.uncompressed or zlib.crc32(raw) != member.crc32:
        raise ValueError("ZIP member length/CRC integrity check failed")
    return raw


class RemoteZip:
    def __init__(self, url, size, budget=40_000_000):
        self.url, self.size, self.budget, self.received = url, size, budget, 0
        start = max(0, size - 65557)
        tail = self.fetch(start, size - 1)
        footer = tail.rfind(b"PK\x05\x06")
        if footer < 0:
            raise ValueError("ZIP footer missing")
        e = struct.unpack_from("<4s4H2IH", tail, footer)
        if e[1] or e[2] or e[3] != e[4] or e[4] == 65535:
            raise ValueError("Multi-disk/ZIP64 archives are outside this bounded downloader")
        cd_size, cd_offset = e[5], e[6]
        if cd_size > 1_000_000 or cd_offset + cd_size > size:
            raise ValueError("Unexpected central-directory bounds")
        central = tail[cd_offset - start:cd_offset - start + cd_size] if cd_offset >= start else self.fetch(cd_offset, cd_offset + cd_size - 1)
        self.members = central_members(central)
        if len(self.members) != e[4]:
            raise ValueError("ZIP entry count mismatch")

    def fetch(self, start, end):
        size = end - start + 1
        if start < 0 or end >= self.size or size < 1 or self.received + size > self.budget:
            raise ValueError("Range exceeds file or download budget")
        # A range-specific cache key avoids intermediary caches reusing a suffix response.
        url = self.url + ("&" if "?" in self.url else "?") + f"kinfold_range={start}-{end}"
        request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"})
        with urllib.request.urlopen(request, timeout=45) as response:
            if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{self.size}":
                raise ValueError("Server did not honor exact byte range; full download refused")
            raw = response.read(size + 1)
        self.received += len(raw)
        if len(raw) != size:
            raise ValueError("Truncated/oversized range response")
        return raw

    def read(self, member):
        if member.compressed > 5_000_000:
            raise ValueError("Oversized summary member refused")
        header = self.fetch(member.offset, member.offset + 29)
        h = struct.unpack("<4s5H3I2H", header)
        if h[0] != b"PK\x03\x04" or h[3] != member.method:
            raise ValueError("Invalid local ZIP header")
        start = member.offset + 30 + h[9] + h[10]
        return inflate_member(self.fetch(start, start + member.compressed - 1), member)


def download(models=MODELS, max_bytes=40_000_000, only_degree=None):
    with urllib.request.urlopen(RECORD + "/export/json", timeout=30) as response:
        record = json.load(response)
    rights = [r["id"] for r in record["metadata"]["rights"]]
    if "cc-by-4.0" not in rights:
        raise ValueError("Expected public CC BY4.0 metadata changed; review before downloading")
    definitions_info = record["files"]["entries"]["ped-sim-defs.zip"]
    definitions_path = ROOT / "cache/ped-sim-defs.zip"
    definitions_path.parent.mkdir(exist_ok=True)
    definition_bytes_fetched = 0
    if definitions_path.exists():
        definitions = definitions_path.read_bytes()
    else:
        if definitions_info["size"] > 100000:
            raise ValueError("Unexpected definition archive size")
        with urllib.request.urlopen(RECORD + "/files/ped-sim-defs.zip?download=1", timeout=30) as response:
            definitions = response.read(100001)
        definition_bytes_fetched = len(definitions)
    if "md5:" + hashlib.md5(definitions).hexdigest() != definitions_info["checksum"]:
        raise ValueError("Definition archive published checksum mismatch")
    definition_check = verify_definitions(definitions)
    definitions_path.write_bytes(definitions)
    manifest = {"record": RECORD, "doi": "10.5281/zenodo.17489849", "attribution": "Amy L. Williams (2025), Ped-sim cousin simulations, CC BY4.0", "selection": "full first-through-eighth cousins only; odd relationship degrees3..17, batches1/2", "archive_md5_verified": False, "member_crc32_verified": True, "files": [], "network_bytes": 0}
    manifest["definitions"] = {**definition_check, "path": "cache/ped-sim-defs.zip", "published_md5_verified": True, "sha256": hashlib.sha256(definitions).hexdigest()}
    manifest["network_bytes"] += definition_bytes_fetched
    for model in models:
        info = record["files"]["entries"][f"segs_summary_stats-{model}.zip"]
        archive = RemoteZip(RECORD + f"/files/segs_summary_stats-{model}.zip?download=1", info["size"], max_bytes - manifest["network_bytes"])
        selected = []
        for member in archive.members:
            match = re.fullmatch(r"[^/]+/deg(3|5|7|9|11|13|15|17)-full-b([12])\.tot", member.name)
            if match and (only_degree is None or int(match[1]) == only_degree):
                selected.append((member, match))
        if len(selected) != (2 if only_degree else 16):
            raise ValueError("Unexpected cousin summary selection")
        for member, match in selected:
            destination = ROOT / "cache" / "tot" / model / Path(member.name).name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raw = destination.read_bytes()
                if len(raw) != member.uncompressed or zlib.crc32(raw) != member.crc32:
                    raise ValueError(f"Cached source is modified: {destination.name}")
            else:
                raw = archive.read(member)
                destination.write_bytes(raw)
            manifest["files"].append({"model": model, "degree": int(match[1]), "cousin_number": (int(match[1]) - 1) // 2, "batch": int(match[2]), "path": str(destination.relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(raw).hexdigest(), "archive": info["key"], "published_archive_checksum": info["checksum"], "member": asdict(member)})
        manifest["network_bytes"] += archive.received
        print(json.dumps({"model": model, "members": len(selected), "network_bytes": archive.received}), flush=True)
    (ROOT / "cache" / "data_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--max-bytes", type=int, default=40_000_000)
    parser.add_argument("--only-degree", type=int, choices=list(range(3, 18, 2)))
    args = parser.parse_args()
    result = download(args.models, args.max_bytes, args.only_degree)
    print(json.dumps({"downloaded_summary_files": len(result["files"]), "network_bytes": result["network_bytes"]}))
