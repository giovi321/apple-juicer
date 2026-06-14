import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://giovi321.github.io',
  base: '/apple-juicer',
  integrations: [
    starlight({
      title: 'Apple Juicer',
      description: 'Self-hosted tool for extracting and analyzing data from iOS backups — documentation',
      components: {
        Head: './src/components/Head.astro',
      },
      customCss: ['./src/styles/diagrams.css'],
      head: [
        {
          tag: 'link',
          attrs: { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        },
        {
          tag: 'link',
          attrs: { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        },
        {
          tag: 'link',
          attrs: {
            rel: 'stylesheet',
            href: 'https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600&display=swap',
          },
        },
      ],
      logo: {
        src: './src/assets/logo.svg',
        replacesTitle: false,
      },
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/giovi321/apple-juicer',
        },
      ],
      editLink: {
        baseUrl: 'https://github.com/giovi321/apple-juicer/edit/main/docs/',
      },
      sidebar: [
        { label: 'Home', link: '/' },
        {
          label: 'Getting Started',
          items: [
            { label: 'Quick Start', link: '/getting-started/quickstart/' },
            { label: 'Docker Compose', link: '/getting-started/docker-compose/' },
            { label: 'Local Development', link: '/getting-started/local-development/' },
          ],
        },
        {
          label: 'Architecture',
          items: [
            { label: 'Overview', link: '/architecture/overview/' },
            { label: 'Backend API', link: '/architecture/backend/' },
            { label: 'Worker Pipeline', link: '/architecture/worker/' },
            { label: 'Frontend UI', link: '/architecture/frontend/' },
            { label: 'Data Storage', link: '/architecture/storage/' },
          ],
        },
        {
          label: 'Operations',
          items: [
            { label: 'Configuration', link: '/operations/configuration/' },
            { label: 'Tasks & Workflows', link: '/operations/tasks/' },
            { label: 'Troubleshooting', link: '/operations/troubleshooting/' },
            { label: 'Security', link: '/operations/security/' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'API', link: '/reference/api/' },
            { label: 'Directory Layout', link: '/reference/directory-layout/' },
          ],
        },
      ],
    }),
  ],
});
