NEUROTRANSLATION
Open Palm replay

Import a prepared IACKD trial and choose Compare estimates. For R1 the
browser compares estimates with and without EEG. For R2 it compares fixed
and personally calibrated estimates on the same recorded palm movement.
Choose the model inputs to switch the chart and its sample table. Your
recording stays in your browser.

Windows — Download and open NeuroTranslation-Windows.url.
macOS — Download and open NeuroTranslation-macOS.webloc.
Linux — Open NeuroTranslation-Linux.desktop using your desktop's usual
launcher handling. If you see text instead, extract the launchers ZIP and
open the file for your system. Keep its extension and follow normal
operating-system trust prompts.

To add a Linux application-menu entry, extract the ZIP, open a terminal in
that folder and run:

  sh Install-NeuroTranslation-Linux.sh

Look for NeuroTranslator in your applications. The installer
creates one entry for your user in
${XDG_DATA_HOME:-$HOME/.local/share}/applications. It uses the installed
Omarchy web-app opener when available and otherwise uses xdg-open. It opens
no browser or background service during installation. If you already have
an entry from the previous installer, use it and choose Palm replay in the
preview's navigation. The installer preserves existing files and symlinks,
including any customizations. To remove an installed entry, delete
brain2body-neurotranslation.desktop from the location printed by the
installer.

An entry made by the installer before this one is called NeuroTranslation
Data Companion. It opens the same page and is left as it is.

Palm replay
https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay

First recording (R1) and trial preparation
https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/scalp-eeg-palm-history/

Second recording (R2) and personal calibration
https://github.com/eliminatenoise/NeuroTranslation/tree/main/benchmarks/scalp-eeg-personal-calibration/#replay-a-second-recording

Project source and licences
https://github.com/eliminatenoise/NeuroTranslation

The shortcuts need a browser and a network connection. They carry only the
URL. The browser loads the fitted research parameters from the preview, and
you supply the trial file. The replay covers retrospective estimation on a
stored recording clock. Live decoding and a general model remain outside the
preview.

SHA256SUMS covers the five launcher and instruction files. Windows and macOS
shortcut formats were checked, and isolated installation was tested on Linux.
Native shortcut opening on Windows and macOS remains unchecked.
