// @ts-check
import { defineConfig } from 'astro/config';

// Static site — deploys to any static host (Vercel / Netlify / GitHub Pages at root).
// No `base` so internal links resolve at the site root locally and in production.
export default defineConfig({
  trailingSlash: 'ignore',
});
