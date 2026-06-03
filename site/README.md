# CONFIDE-Bench — site

Static [Astro](https://astro.build) site for the CONFIDE-Bench project: the problem,
the benchmark, an about section, and how to contribute. Styled with the same
Tufte design tokens as the benchmark report (`src/styles/tufte.css`).

## Develop

```bash
npm install
npm run dev        # http://localhost:4321
```

## Build

```bash
npm run build      # → dist/  (prebuild copies the latest report from ../results)
npm run preview
```

`npm run build` runs `prebuild` → `sync:report`, which copies the current
`../results/benchmark-report.html` and `.ru.html` into `public/report/`, so the
deployed site always ships the latest interactive report. Those copies and the
build output are git-ignored.

## Structure

- `src/pages/` — `index` (problem + headline), `about`, `benchmark`, `contribute`
- `src/layouts/Base.astro` — nav, footer, head
- `src/styles/tufte.css` — shared design system
- `public/images/hero.png` — hero art (generated via the gpt-image-2 skill)
- `public/report/*` — the interactive report, synced from `../results` at build

## Deploy

Static output (`dist/`) deploys to any static host (Vercel / Netlify / GitHub
Pages at root). No `base` path is set, so links resolve from the site root.
