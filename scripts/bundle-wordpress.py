"""Trusted GitHub build step: download only predefined WordPress template assets."""
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ASSETS = {
    "shop": ("woocommerce.zip", "https://downloads.wordpress.org/plugin/woocommerce.latest-stable.zip", "installPlugin", "pluginData"),
    "portfolio": ("twentytwentyfour.zip", "https://downloads.wordpress.org/theme/twentytwentyfour.latest-stable.zip", "installTheme", "themeData"),
    "blog": ("sample-content.xml", "https://raw.githubusercontent.com/WordPress/theme-test-data/master/themeunittestdata.wordpress.xml", "importWxr", "file"),
}
MAX_BYTES = 128 * 1024 * 1024

def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "AstraPanel-APK-Builder/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("Asset redirected to an insecure URL")
        data = response.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("WordPress asset is empty or too large")
    return data

def bundle(project, fetch=download):
    project = Path(project)
    manifest = project / "astra-wordpress.json"
    if not manifest.exists():
        return []  # Ordinary Web/HTML apps remain unchanged.
    config = json.loads(manifest.read_text())
    template = config.get("template")
    if config.get("version") != 1 or template not in ("blank", *ASSETS):
        raise ValueError("Unsupported WordPress template")
    blueprint = config["blueprint"]
    output = project / "app/src/main/assets/www/wordpress"
    output.mkdir(parents=True, exist_ok=True)
    assets = []
    if template in ASSETS:
        name, url, step, field = ASSETS[template]
        matching = [i for i, value in enumerate(blueprint["steps"]) if value.get("step") == step]
        if len(matching) != 1:
            raise ValueError("Invalid WordPress template blueprint")
        data = fetch(url)
        if name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if archive.testzip() or not archive.namelist():
                    raise ValueError("Invalid WordPress archive")
        elif b"<rss" not in data:
            raise ValueError("Invalid WordPress sample content")
        (output / name).write_bytes(data)
        assets.append({"name": name, "step": matching[0], "field": field, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (output / "bundle.json").write_text(json.dumps({"blueprint": blueprint, "assets": assets}))
    manifest.unlink()
    print("Bundled WordPress assets:", ", ".join(asset["name"] for asset in assets) or "WordPress defaults (SQLite managed by runtime)")
    return assets

if __name__ == "__main__":
    bundle(sys.argv[1] if len(sys.argv) > 1 else "proj")