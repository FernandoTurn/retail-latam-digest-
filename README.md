# retail-latam-digest-

This repo contains two independent things:

1. **Daily retail digest** — `build.py` + `.github/workflows/digest.yml` (the
   original newsletter, unchanged).
2. **Romania trip site** — a single-page, shareable site published to GitHub
   Pages from [`docs/`](docs/).

## Romania trip site

A self-contained `docs/index.html` (CSS + JS embedded, no external
dependencies) with the family's August 2026 Romania road-trip plan:

- **EN / עברית** language toggle (Hebrew is RTL); the choice is remembered
  via `localStorage`.
- Mobile-first responsive layout (made to share on WhatsApp).
- One card per leg with **stay / activities / photo**. The photo is clickable
  and opens the location in **Google Maps**.
- **Green = booked, amber = not booked**, driving distances between legs, and a
  footer with each photo's license attribution.
- Photos are real images from **Wikimedia Commons** (free licenses), fetched
  and resized by [`build_images.py`](build_images.py) and served locally from
  `docs/img/` (no hotlinking).

### Publish to GitHub Pages

Deployment is handled by `.github/workflows/pages.yml`, which downloads the
photos, resizes them, and deploys `docs/`.

1. Push the branch (see commands below).
2. In the repo: **Settings → Pages → Build and deployment → Source =
   GitHub Actions**.
3. The workflow runs on pushes to `master` / `main` (and can be triggered
   manually from the **Actions** tab via *Run workflow*). The site URL appears
   in the workflow's **deploy** job summary, typically
   `https://<user>.github.io/retail-latam-digest-/`.

> GitHub Pages deploys from the repository's **default branch**. Merge this
> branch into the default branch (or run the workflow manually) to publish.
