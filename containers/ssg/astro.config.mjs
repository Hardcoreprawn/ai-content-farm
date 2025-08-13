import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import sitemap from '@astrojs/sitemap';
import rss from '@astrojs/rss';
import node from '@astrojs/node';

// https://astro.build/config
export default defineConfig({
  site: 'https://ai-content-farm.com', // Replace with your domain
  integrations: [
    tailwind(),
    sitemap(),
    rss({
      title: 'AI Content Farm',
      description: 'Curated tech content powered by AI',
      site: 'https://ai-content-farm.com',
      items: import.meta.glob('./src/content/**/*.md')
    })
  ],
  output: 'hybrid',
  adapter: node({
    mode: 'standalone'
  }),
  server: {
    host: '0.0.0.0',
    port: 3000
  },
  markdown: {
    shikiConfig: {
      theme: 'github-dark-dimmed'
    }
  }
});
