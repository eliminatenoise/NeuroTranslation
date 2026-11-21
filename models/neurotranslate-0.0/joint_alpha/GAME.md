# Run a local game with the joint checkpoint

An independently supplied game can use the same running model as the forecast demo. From the extracted model folder, launch `python joint_demo.py --game "/path/to/extracted/game"`. The browser opens the game. Open the printed address without `/game/` to reach the measurement demo. Both clients use the checkpoint fingerprint shown by the server.

The game directory supplies `joint-game.json`. List every public-facing static asset relative to that directory, for example:

```json
{"version":1,"files":["index.html","app.js","style.css"]}
```

The server serves the declared files only, at `/game/`. It rejects symlinks and verifies each file against its content at launch. Restart after changing assets. Limits are 128 MiB per file, 1 GiB for the whole game and 16,384 assets. The model download contains the compatibility interface. The separate application supplies its own scene, camera and command handling.

From a game page, fetch `/api/tasks` to read the named task schemas, input layouts and fictional examples. Post one JSON input object with `task`, a one-row batch `X`, and an optional boolean candidate mask `valid` to `/api/forecast`. The result identifies the checkpoint with `checkpoint_sha256` and includes `task`, `outputs`, `output_units` and the numeric batch `prediction`. Errors return JSON with an `error` message. The browser, game and forecast service must share the local address printed by the launcher. Unit names and the observation window belong to the selected task. A game command can set a goal in a simulation. A measured forecast requires the appropriate observed or explicitly invented numeric history.
