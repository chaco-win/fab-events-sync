import fs from 'node:fs';
import dotenv from 'dotenv';

// Load base .env if present
if (fs.existsSync('.env')) {
  dotenv.config({ path: '.env' });
}
// Then override with .env.local if present
if (fs.existsSync('.env.local')) {
  dotenv.config({ path: '.env.local', override: true });
}

