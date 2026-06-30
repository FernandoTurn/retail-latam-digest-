# romania/img — trip photos

These JPGs are downloaded from **Wikimedia Commons** (free licenses), resized
with Pillow, and committed here by
[`build_images.py`](../../build_images.py). `credits.json` holds the per-photo
attribution shown in the site footer.

They are generated/updated automatically by the **Build Romania trip photos**
GitHub Actions workflow (`.github/workflows/romania-images.yml`), which runs
the script on a runner with internet access and commits the results back to the
default branch. The site (`romania/index.html`) serves them locally — no
hotlinking.

To regenerate them yourself instead, run from the repo root:

```bash
pip install Pillow
python build_images.py
git add romania/img && git commit -m "Update Romania trip photos" && git push
```
