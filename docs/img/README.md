# /img — trip photos

Photos are **not committed** here. They are downloaded fresh from
**Wikimedia Commons** (free licenses), resized with Pillow, and written into
this folder by [`build_images.py`](../../build_images.py) — which runs
automatically in the **Deploy Romania trip site to Pages** GitHub Actions
workflow. The resized JPGs and `credits.json` (photo attribution shown in the
site footer) end up in the published site, served locally (no hotlinking).

To populate this folder locally instead (e.g. to commit the images into the
repo), run from the repo root on a machine with internet access:

```bash
pip install Pillow
python build_images.py
```
