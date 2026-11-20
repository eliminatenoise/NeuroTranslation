# Forecast a cortical event count

Extract the whole folder and open **index.html** in a modern browser. Dedicated launchers are included for Windows, macOS and Linux. The page runs from disk with JavaScript enabled. Internet access is needed only for links to the atlas, paper, sources and online download.

Choose a date, phase, original trial and forecast offset. Select a contact to compare its expected and observed count over the next 100 ms. Switch between three independently trained Transformer seeds, a Poisson regression and two simple comparisons. Choose “Earlier trial’s movement” to replace the handle history with a matched earlier trial. Windows without a match keep their recorded outcomes and have no forecast for that comparison.

“Edit a copy” lets you change the handle’s earlier X and Y position in centimetres and the events counted at one contact in one 10-ms sample. “Apply sample” recomputes all 26 forecasts. Invented histories have no observed outcome. “Restore recording” reloads the original history and count. The study comparison beneath the chart always uses the original recorded trials.

The Windows launcher uses the default browser file association. The macOS launcher uses the system open command and Linux uses xdg-open. If your desktop restricts opening a launcher, open index.html directly. The text table and controls also work with a keyboard. The group intervals and the source selection rule are described on the page and in NOTICE.md.
