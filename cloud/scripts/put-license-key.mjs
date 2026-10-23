// Uploads the vendor's license signing key to Cloudflare as the LICENSE_PRIVATE_KEY secret,
// without printing it. Usage: npm run license-key -- "C:\path\to\setu-license-private.pem"
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

const file = process.argv[2];
if(!file){ console.error('PEM file ka path dein: npm run license-key -- "C:\...\setu-license-private.pem"'); process.exit(1); }
const body = readFileSync(file, 'utf8').replace(/-----[^-]+-----|\s/g, '');
if(!body.startsWith('MI')){ console.error('Ye PEM private key nahi lagti'); process.exit(1); }
execSync('npx wrangler secret put LICENSE_PRIVATE_KEY', { input: body, stdio: ['pipe', 'inherit', 'inherit'] });
console.log('LICENSE_PRIVATE_KEY Cloudflare par set ho gayi.');
