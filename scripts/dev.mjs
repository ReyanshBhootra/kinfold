import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import { createServer } from 'node:net';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(import.meta.url);
const python=resolve(root,process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
async function checkPort(port){await new Promise((ok,fail)=>{const server=createServer();server.once('error',()=>fail(new Error(`Port ${port} is already in use. Stop the existing Kinfold server or use the separate start commands.`)));server.listen(port,'127.0.0.1',()=>server.close(ok))})}
try{
 if(!existsSync(python))throw new Error('Create .venv and install requirements.txt first. See README.md.');
 const vite=resolve(dirname(require.resolve('vite/package.json')),'bin/vite.js');
 await checkPort(8000);await checkPort(5173);
 const children=[];let stopping=false;
 function stop(code=0){if(stopping)return;stopping=true;for(const child of children)child.kill();process.exitCode=code;}
 function start(command,args,cwd){const child=spawn(command,args,{cwd,stdio:'inherit',windowsHide:true});children.push(child);child.on('error',e=>{console.error(e.message);stop(1)});child.on('exit',code=>{if(!stopping){console.log('A Kinfold service stopped; shutting down the other service.');stop(code??1)}});return child;}
 start(python,['-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000'],root);
 start(process.execPath,[vite,'--host','127.0.0.1','--port','5173','--strictPort'],resolve(root,'frontend'));
 console.log('Kinfold: http://127.0.0.1:5173 · API: http://127.0.0.1:8000 · Ctrl+C stops both.');
 process.on('SIGINT',()=>stop());process.on('SIGTERM',()=>stop());
}catch(e){console.error(e.message);process.exitCode=1}
