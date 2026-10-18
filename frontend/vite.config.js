import {defineConfig} from 'vite';
const backend=process.env.SPACE_ODYSSEY_BACKEND||'http://127.0.0.1:8000';
export default defineConfig({server:{proxy:{'/ws':{target:backend.replace(/^http/,'ws'),ws:true},'/api':backend,'/health':backend,'/state':backend}}});
