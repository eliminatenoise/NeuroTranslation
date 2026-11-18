# Open NeuroTranslation

[Open Palm replay](https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay) or [download a launcher for Windows, macOS or Linux](https://eliminatenoise.github.io/NeuroTranslation/START.html). These shortcuts lead to the same current replay as the browser link.

Import a prepared IACKD right-hand trial and choose **Compare estimates**. The browser runs two fitted regressions and plots their estimates beside the tracked palm position. It also lets you inspect and align compatible JSON and CSV recordings. Your files stay in the browser. [Study and trial preparation](benchmarks/scalp-eeg-palm-history/) · [Import and alignment guide](demo/README.md)

- **Windows** — Download and open `NeuroTranslation-Windows.url`.
- **macOS** — Download and open `NeuroTranslation-macOS.webloc`.
- **Linux** — Open `NeuroTranslation-Linux.desktop` using your desktop’s usual launcher handling. For an application-menu entry, extract the ZIP and run `sh Install-NeuroTranslation-Linux.sh` in that folder.

The installer writes one per-user menu entry. It prefers the installed Omarchy opener and otherwise uses `xdg-open`. Installation opens no browser. An earlier entry from this installer still opens the preview. Choose **Palm replay** in its navigation. The installer preserves existing entries, including customized files and symlinks.

Keep the filename extensions and follow your operating system’s normal trust prompts. Opening the preview requires a network connection and browser. The shortcuts carry the URL only. The study parameters are served to the browser, and you provide the trial file. A general NeuroTranslate model and live decoding remain outside the preview.

Windows and macOS shortcut formats were checked. Isolated installation was tested on Linux. Native shortcut opening on Windows and macOS remains unchecked.
