#!/bin/sh
# Brain2Body per-user URL launcher installer. No download, browser launch, sudo or global configuration.
set -eu
if [ "$#" -ne 0 ]; then
  printf '%s\n' 'Run this installer without arguments.' >&2
  exit 2
fi
app_data_dir=${XDG_DATA_HOME:-${HOME:?HOME is required when XDG_DATA_HOME is unset}/.local/share}
case "$app_data_dir" in /*) ;; *) printf '%s\n' 'XDG_DATA_HOME must be an absolute path.' >&2; exit 1 ;; esac
applications_dir=$app_data_dir/applications
destination=$applications_dir/brain2body-neurotranslation.desktop
target='https://eliminatenoise.github.io/NeuroTranslation/index.html#palm-replay'
marker='X-Brain2Body-Launcher=neurotranslation-web-preview-v2'
if command -v omarchy >/dev/null 2>&1 && command -v omarchy-launch-webapp >/dev/null 2>&1; then
  launcher_exec='omarchy launch webapp'
  launcher_tryexec='omarchy'
elif command -v xdg-open >/dev/null 2>&1; then
  launcher_exec='xdg-open'
  launcher_tryexec='xdg-open'
else
  printf 'No desktop URL opener was found. Open %s in your browser.\n' "$target" >&2
  exit 1
fi
if [ -L "$applications_dir" ] || { [ -e "$applications_dir" ] && [ ! -d "$applications_dir" ]; }; then
  printf '%s\n' 'The applications destination is not a regular directory; nothing was installed.' >&2
  exit 1
fi
mkdir -p -- "$applications_dir"
temporary=$(mktemp "$applications_dir/.brain2body-neurotranslation.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT HUP INT TERM
cat > "$temporary" <<_BRAIN2BODY_DESKTOP_
[Desktop Entry]
Version=1.0
Type=Application
Name=NeuroTranslator
Comment=Open NeuroTranslator at the palm-position replay
Exec=$launcher_exec "$target"
TryExec=$launcher_tryexec
Icon=web-browser
Terminal=false
Categories=Education;Science;
StartupNotify=true
$marker
_BRAIN2BODY_DESKTOP_
chmod 0644 "$temporary"
if [ -e "$destination" ] || [ -L "$destination" ]; then
  if [ ! -L "$destination" ] && [ -f "$destination" ]; then
    if cmp -s "$temporary" "$destination"; then
      printf 'Already installed: %s\n' "$destination"
      exit 0
    fi
    # Exact outputs of the previous installer, using xdg-open or Omarchy.
    # Their stable preview URL still leads to Palm replay through the page navigation.
    if previous_entry=$(sha256sum < "$destination"); then
      case "${previous_entry%% *}" in
        803708a27a1bee65a5e5f4ef47d0cb8e118c5b6c9bb6bf188392316b020fbc43|a254e05887f1c2c361db2c4b557c50f63100b0874175acf764aeba922a1c92e2)
          printf 'Already installed: %s\nOpen it and choose Palm replay in the browser.\n' "$destination"
          exit 0 ;;
        # The entry the installer before this one wrote, under the app's earlier name, with either opener.
        eb432dc4b15c591b3bf105a566472d4d6ce7903e37671b87a5eb1cf372b17dc4|de85edf843cc0b1dd319b2b75865c2c45105d1927e7615ec73eccb6d35396845)
          printf 'Already installed: %s\nIt keeps its earlier name, NeuroTranslation Data Companion.\n' "$destination"
          exit 0 ;;
      esac
    fi
  fi
  printf 'Existing file preserved: %s\n' "$destination" >&2
  printf '%s\n' 'A different file already uses this name. Nothing was replaced.' >&2
  exit 1
fi
# -T treats destination as one file. Hard-link creation cannot replace an existing file/symlink/directory.
if ! ln -T -- "$temporary" "$destination"; then
  printf '%s\n' 'The destination appeared or could not be created; nothing was replaced.' >&2
  exit 1
fi
printf 'Installed: %s\n' "$destination"
printf '%s\n' 'Open your application menu and search for NeuroTranslator.'
