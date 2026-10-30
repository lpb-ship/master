import { readConfig } from '../src/server/config.mjs';

try {
  const config = readConfig(process.env);
  console.log(`Configuration valid for ${config.appEnv}.`);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
