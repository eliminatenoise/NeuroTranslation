// Each worker owns one verified archive. While decompressing, keep only the latest selection.
let archive;
let reading = false;
let pending;

async function readLatest() {
  if (reading) return;
  reading = true;
  try {
    while (pending) {
      const {id,block,trial} = pending;
      pending = null;
      try {
        const result = await archive.readTrial(block,trial);
        if (!pending) self.postMessage({type:"result",id,trial:result});
      } catch {
        if (!pending) self.postMessage({type:"read-error",id});
      }
    }
  } finally { reading = false; }
}

self.onmessage = async ({data}) => {
  if (data.type === "open" && !archive) {
    try {
      archive = await self.WristArchive.open(data.file);
      self.postMessage({type:"opened"});
    } catch { self.postMessage({type:"open-error"}); }
  } else if (data.type === "read" && archive) {
    pending = data;
    await readLatest();
  }
};
