/**
 * Copy the current Pi session JSONL into /app/sessions/ on shutdown.
 *
 * Harbor's built-in pi writes under /logs/agent/pi/sessions. This path is the
 * stable, agent-facing folder for prior turns in a multi-step trial.
 */
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { basename, join } from "node:path";

const SESSIONS_DIR = "/app/sessions";

export default function (pi: {
  on: (
    event: "session_shutdown",
    handler: (
      event: unknown,
      ctx: {
        sessionManager: { getSessionFile: () => string | undefined };
      },
    ) => void | Promise<void>,
  ) => void;
}) {
  pi.on("session_shutdown", async (_event, ctx) => {
    const src = ctx.sessionManager.getSessionFile();
    if (!src || !existsSync(src)) {
      return;
    }
    mkdirSync(SESSIONS_DIR, { recursive: true });
    const dest = join(SESSIONS_DIR, basename(src));
    copyFileSync(src, dest);
  });
}
