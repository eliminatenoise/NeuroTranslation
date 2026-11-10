NEUROTRANSLATION: OPEN THE CURRENT PREVIEW

Open the data companion to load the invented example or inspect compatible JSON and CSV recordings. File processing stays in your browser.

Windows: download NeuroTranslation-Windows.url and double-click it.
macOS: download NeuroTranslation-macOS.webloc and double-click it.
Linux: open NeuroTranslation-Linux.desktop with your desktop's normal launcher handling.
Keep each filename's extension. If the browser displays the file as text,
download the ZIP, extract it, and open the launcher for your system.
Follow normal OS opening/trust prompts. Native Windows/macOS operation has
not been tested by this package's Linux-only format checks.

For a Linux application-menu entry, extract the ZIP, open a terminal in that
folder and run:
  sh Install-NeuroTranslation-Linux.sh
The installer opens no browser. It writes one per-user application entry in
${XDG_DATA_HOME:-$HOME/.local/share}/applications. It prefers the installed
Omarchy web-app opener, otherwise xdg-open. It needs normal Linux shell/core
utilities and a configured browser; it installs no software or background job.
An identical managed entry is left intact. Any different file or symlink
using the destination name is preserved. The URL stays current when the
published preview changes, so a new build does not require reinstallation.
To remove the menu entry later, delete brain2body-neurotranslation.desktop from the
location printed by the installer. Downloaded bookmarks can be deleted normally.

Direct preview: https://eliminatenoise.github.io/NeuroTranslation/index.html
Project and source: https://github.com/eliminatenoise/NeuroTranslation
Source ZIP: https://github.com/eliminatenoise/NeuroTranslation/archive/refs/heads/main.zip

This is a data inspector and alignment tool. No trained NeuroTranslate model or model backend is connected. R11 manuscripts and the portable interface are source-only previews; no weights or runnable model download are included.

These are online URL launchers, not offline model/app bundles. Opening the
public preview needs a network connection and browser. No Node/Python install
is needed to open it. Document viewing may use your normal PDF/DOCX application.
The launchers contain no weights, recordings, credentials or private paths.
SHA256SUMS identifies the five launcher/instruction files in this package;
it does not establish OS trust, scientific validation or source authentication.
