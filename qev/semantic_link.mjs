// The Python adapter supplies source bytes only after validating sources.lock.json.
// A data URL executes those very bytes and avoids a later read or imported cache.
// This bridge has no business rules and returns the native linkEdge result.
import { readFileSync } from "node:fs";

const request = JSON.parse(readFileSync(0, "utf8"));
const { linkEdge } = await import(`data:text/javascript;base64,${request.source_base64}`);
process.stdout.write(JSON.stringify(linkEdge(request.producer, request.consumer)) + "\n");
