# External files not stored in Git

A fresh clone of this repository is playable as-is: the built
WebNP2 player (`../player/`), the disk images, and the chapter
server are all committed. Two items that were used while
building the prototype are deliberately **not** in Git, and
this file is the complete list of them, so that nothing is
silently missing.

## 1. `Suika3-SDK-Full.zip` — official Suika3 SDK archive

| | |
|---|---|
| Expected location | `prototype/vendor/Suika3-SDK-Full.zip` (this folder) |
| Size | 207,109,925 bytes (197.5 MiB) |
| SHA-256 | `fb1b8cf4d1d1b178426028d9c364448ff0288c03d2cc858a26432846628b624c` |
| Why it is not in Git | It exceeds GitHub's 100 MB per-file limit, and it is an upstream release archive that can be re-downloaded verbatim. |
| What it was used for | Reference only: the source of the official `suika-98.exe` kept beside it (which **is** committed, at 1.4 MB) and of the stock sample game used during the feasibility work. The shipped game does **not** need this archive to run or to be rebuilt, because the engine in `../engine/` was compiled from the Suika3 source tree. |
| How to get it | Download the Suika3 Full SDK from the official Suika3 site (suika3.vn) or from the releases page of the Suika3 GitHub repository (`awemorris/suika3`, now `suika3-community/suika3`). The release asset is the Full SDK zip (current releases name it `Suika3-Full-SDK.zip`). Save or rename it to `Suika3-SDK-Full.zip` in this folder. |
| How to verify | Run `sha256sum Suika3-SDK-Full.zip` here and compare with the hash above. Only a byte-identical archive matches; a different SDK release will still work as reference material but will not match the hash. |

## 2. `webnp2-src/` — upstream WebNP2 source checkout

| | |
|---|---|
| Expected location | `prototype/vendor/webnp2-src/` (a Git checkout, this folder) |
| Why it is not in Git | It is an unmodified upstream repository with its own history; embedding it would either swallow that history or require submodule plumbing that this feasibility branch does not need. |
| What it was used for | Building the WebNP2 player. Only small URL/disk-configuration plumbing in the player shell differs from upstream, as described in `../README-EMULATION.md`. |
| Do you need it? | Only to rebuild the player. The built player is committed under `../player/`, and the game runs from it directly (`node ../server.mjs`, then open http://localhost:4173/). |
| How to get it | Clone the upstream project: `git clone https://github.com/uraraworks/webnp2.git webnp2-src` from inside this `vendor/` folder, then build with `npm install` followed by the TypeScript and Vite builds (`node node_modules/typescript/bin/tsc && node node_modules/vite/bin/vite.js build`) and copy `dist/` over `../player/`. |

## Rule for future large files

Anything over roughly 50 MB, or any upstream release archive
that can be re-downloaded, belongs in this file instead of in
Git: record the expected path, exact size, SHA-256, purpose,
and download source here, and add the path to `.gitignore` in
this folder in the same change.
