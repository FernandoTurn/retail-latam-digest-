# retail-latam-digest-

This repo contains two independent things:

1. **Daily retail digest** — `build.py` + `.github/workflows/digest.yml` (the
   original newsletter, unchanged).
2. **Romania trip site** — a single-page, shareable site published to GitHub
   Pages at the [`/romania/`](romania/) path.

## Romania trip site

A self-contained `romania/index.html` (CSS + JS embedded, no external
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
  `romania/img/` (no hotlinking).

### Publish to GitHub Pages

The site is served by GitHub Pages straight from the **default branch root**
(the same setup that publishes the retail newsletter at `/`):

- **Newsletter** → `https://<user>.github.io/retail-latam-digest-/`
- **Romania trip** → `https://<user>.github.io/retail-latam-digest-/romania/`

So nothing special is needed to publish — just keep Pages on
**Settings → Pages → Deploy from a branch → `master` / `(root)`**.

The photos live in `romania/img/` and are produced by
`.github/workflows/romania-images.yml`: on a push that touches
`build_images.py` / `romania/index.html` (or via **Actions → Run workflow**),
it downloads + resizes the images on the runner and commits them back to the
branch, where Pages serves them.
