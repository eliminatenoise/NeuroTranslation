# Forearm array reader

Open an invented pinch, move the cutoff, and compare the two EMG windows. Select one of the five grids, then use the mouse, touch, or arrow keys to inspect an electrode. Lock the scale to compare different cutoffs without changing the colour range. The forecast table shows what each offline fit would predict at the same later force index. You can reveal that packet’s later value or score all 592 cutoffs.

## Open the reader offline

Extract the complete archive. Open the launcher for your operating system. You can also open `index.html` in a current browser. The reader needs no server and sends no packet readings or weights over the network.

| System | Launcher |
| --- | --- |
| Linux | `Open Array Reader on Linux.sh` |
| macOS | `Open Array Reader on macOS.command` |
| Windows | `Open Array Reader on Windows.cmd` |

The public bundle uses invented signals and invented weights. The separate private study bundle labels its fitted TRAIN weights. Its demonstration pinch still uses invented signals. A model selected through the file picker displays the origin declared in that file. The browser cannot verify how a locally selected file was produced.

To convert original trials or fit the reader on your own selected set, use the included Python tools. Keep genuine original data, packets, and fitted weights private. The clinical, anatomical and physical-latency limits of this task are described in the protocol. [Local Python tools](./LOCAL-USE.md) · [Study protocol](./PROTOCOL.md)
