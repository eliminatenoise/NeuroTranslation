/* Read a local request, predict with the shipped weights and print the result. */
"use strict";
const fs=require("node:fs");
const path=require("node:path");
const api=require("./predict.js");
function read(file) { return JSON.parse(fs.readFileSync(file,"utf8")); }
const model=read(path.join(__dirname,"model.json"));
const request=read(process.argv[2] || path.join(__dirname,"example.json"));
console.log(JSON.stringify(api.predict(model,request),null,2));
