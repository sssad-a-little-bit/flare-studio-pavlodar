import { mkdir, copyFile, writeFile } from 'node:fs/promises';
for (const route of ['batyr', 'picasso']) {
  await mkdir(`dist/${route}`, { recursive: true });
  await copyFile('dist/index.html', `dist/${route}/index.html`);
}
await writeFile('dist/.nojekyll', '');
