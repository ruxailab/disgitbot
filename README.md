Documentation test PR !!

   curl -X POST \
     -H "Authorization: token YOUR_GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/repos/YOUR_USERNAME/YOUR_REPO/actions/workflows/update_discord_roles.yml/dispatches \
     -d '{"ref":"main"}'

GSOC 2025 project, 

project idea: 'Integration of GitHub Actions with Discord Role Management (90h)',

source: https://github.com/ruxailab/gsoc/blob/main/ideas2025.md