# Publish your first repository

The project's public repository is
[yuhh7743-nyx/doclink-checker](https://github.com/yuhh7743-nyx/doclink-checker).
The instructions below are for publishing your own copy under your own account.
No package has been uploaded to PyPI.

## Before publishing

- Review the source and the MIT license, and confirm you want to release it.
- Install and run the tests in the [README](README.md#development).
- Choose a repository name and a short description.

## Create the repository

On GitHub, create an empty **public** repository. Do not initialize it with a
README, license, or `.gitignore`, because this folder already contains them.
Copy its HTTPS Git URL. In a terminal inside this project folder, run:

```sh
git init -b main
git add .
git commit -m "Initial Doclink checker"
git remote add origin YOUR_COPIED_GITHUB_HTTPS_URL
git push -u origin main
```

Replace `YOUR_COPIED_GITHUB_HTTPS_URL` with the URL you copied. If Git requests
your identity, set `git config user.name` and `git config user.email` to your
chosen commit identity (a GitHub noreply address is an option), then retry the
commit. Authenticate through your own Git credential manager when prompted.
Never put a token into a tracked file or send it in chat.

The included GitHub Actions workflow will run tests and check this project's
documentation on pushes and pull requests. Verify the first run is green.

## Grow it honestly

Try the checker on your own documentation, fix actual problems, and invite
feedback. Track real issues and releases. A new repository alone does not
establish adoption or maintenance history, and does not guarantee eligibility
for any open-source support program. This project makes no claims about users,
stars, contributions, or an application for Codex for Open Source.
