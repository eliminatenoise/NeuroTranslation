// Plain numeric CSV from the named source export. Verify the bytes first.
function parseWalk(text, source, member) {
  const lines = text.trimEnd().split(/\r?\n/);
  const header = lines.shift().replace(/^\uFEFF/,"").split(",");
  const cols = [source.frame_column, ...source.columns].map(name => {
    const index = header.indexOf(name);
    if (index < 0 || index !== header.lastIndexOf(name)) throw Error("The source columns differ from the study.");
    return index;
  });
  const frames = [], pairs = [], cuts = [];
  let allRun = 0, kneeRun = 0;
  const prefix = [];
  for (const [i,line] of lines.entries()) {
    const fields = line.split(",");
    const selected = cols.map(c => fields[c]?.trim() ? Number(fields[c]) : NaN);
    const [frame,...six] = selected;
    const knees = six.slice(2,4);
    const validFrame = Number.isSafeInteger(frame);
    const consecutive = validFrame && i > 0 && frame === frames[i-1]+1;
    allRun = validFrame && six.every(Number.isFinite) ? (consecutive ? allRun+1 : 1) : 0;
    kneeRun = validFrame && knees.every(Number.isFinite) ? (consecutive ? kneeRun+1 : 1) : 0;
    frames.push(frame); pairs.push(knees); prefix.push(kneeRun >= 240);
    // Legacy eligibility also requires six finite angle columns from cutoff−24
    // through cutoff+15. Only knee pairs up through cutoff enter the models.
    if (allRun >= 40 && prefix[i-15]) cuts.push(i-15);
  }
  if (pairs.length !== member.rows || cuts.length !== member.long_windows || !cuts.length) throw Error("The file's complete windows differ from the study counts.");
  return {mode:"recorded",frames,pairs,cuts,member};
}
async function openWalk(file, source) {
  if (!file || !/\.csv$/i.test(file.name)) throw Error("Choose an original Joint_Angles_ZXY.csv from one of the 12 held-out walks.");
  if (!file.size || file.size > 32*1024*1024) throw Error("Choose a nonempty CSV smaller than 32 MiB.");
  if (!globalThis.crypto?.subtle) throw Error("Open the saved page directly or use HTTPS to verify your file.");
  const bytes = await file.arrayBuffer();
  const binary = new Uint8Array(await crypto.subtle.digest("SHA-256",bytes));
  const hash = Array.from(binary,v => v.toString(16).padStart(2,"0")).join("");
  const member = source.members.find(m => m.sha256 === hash);
  if (!member) throw Error("These bytes do not match one of the 12 held-out walks. Choose an original, unedited CSV.");
  return parseWalk(new TextDecoder().decode(bytes),source,member);
}
function inventedWalk() {
  const pairs = [], frames = [], cuts = [];
  for (let i=0; i<660; i++) {
    const phase = i*2*Math.PI/93 + 0.29*Math.sin(i/78) + 0.00022*i;
    const bend = (p, swing) => 7 + 7*(1-Math.cos(p)) + swing*Math.pow((1+Math.cos(p-.82))/2,6);
    pairs.push([bend(phase,41+4*Math.sin(i/72)),bend(phase+Math.PI+.14,36+6*Math.sin(i/75+.6))]);
    frames.push(i);
    if (i>=239 && i<660-15) cuts.push(i);
  }
  return {mode:"invented",pairs,frames,cuts};
}
function atCutoff(trial,index) {
  const i = trial.cuts[index];
  return {trial,index,cutoff:trial.frames[i],history:trial.pairs.slice(i-239,i+1),futureIndex:i+15};
}
