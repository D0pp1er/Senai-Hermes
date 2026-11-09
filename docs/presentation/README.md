# Senai presentation

Eight chapters: introduction, setup, CLI, student/BJJ/AI profiles, Telegram, cron,
UFC fixtures skill and Obsidian. Buildless HTML/CSS/JS with no external font/library,
tracking, server or credential form. All accounts/commands are local to the reader.

## Preview

From the repository root in WSL:

~~~bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory docs/presentation
~~~

Open http://localhost:8765. Stop your preview server with Ctrl+C.
Use Present, arrow keys and Escape for chapter mode; the normal page is printable.
Copy buttons need clipboard permission or the local fallback; manual selection always works.

## GitHub Pages

The committed .github/workflows/pages.yml uploads only docs/presentation, excluding
runtime outputs, secrets and contributor history. It runs on main presentation changes
or explicit Run workflow. No workflow was executed or remote settings changed locally.

1. Push these reviewed commits to your GitHub main branch.
2. Open repository Settings -> Pages -> Build and deployment -> Source: GitHub Actions.
3. Open Actions -> Publish Senai presentation -> Run workflow on main if necessary.
4. Use the successful deployment's reported URL. With the current owner/repository
   and no custom domain, the expected address is https://D0pp1er.github.io/Senai-Hermes/.
   This is an expected URL, not evidence of an actual deployment.

[GitHub's official Pages workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
explains configuration/permissions. Repository visibility and account plan determine
Pages availability. Do not change repository visibility merely to publish this page.

## Updating

Edit index.html, styles.css or app.js. Keep assets/ufc-fixtures/SKILL.md aligned with
the displayed workflow. The fixture example researches official live sources when run;
no actual upcoming event list is embedded. Source: [UFC events](https://www.ufc.com/events).
Instructions/provenance do not make the resulting model output independently verified.

Check all eight navigation anchors, presenter next/previous/Escape, copy feedback,
mobile horizontal overflow, print layout and the downloadable skill before presenting.
