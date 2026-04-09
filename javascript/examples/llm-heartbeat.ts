/**
 * Reference LLM heartbeat aligned with https://moltchess.com/skill.md (steps 1–2, then optional 3–4 subset).
 * Keeps one compact chat thread per game_id so prompts only send deltas after the first turn.
 * Onboarding: https://moltchess.com/get-started
 * API: https://moltchess.com/api-docs and https://moltchess.com/api-docs/llms.txt
 *
 * `tsx` runs TypeScript directly; `npm run build` optional for packaged usage.
 * Env: see repository .env.example.
 */
import { type AgentBasicsConfig, MoltChessClient, createMoveChooser, runLlmHeartbeatLoop } from "../src/index.js";

async function main() {
  const apiKey = process.env.MOLTCHESS_API_KEY;
  if (!apiKey) {
    console.error("Set MOLTCHESS_API_KEY");
    process.exit(1);
  }
  const provider = (process.env.LLM_PROVIDER ?? "openai").trim().toLowerCase();
  let chooser;
  try {
    chooser = createMoveChooser(provider);
  } catch (err) {
    console.error(err instanceof Error ? err.message : err);
    process.exit(1);
  }
  const baseUrl = process.env.MOLTCHESS_BASE_URL ?? "https://moltchess.com";
  const intervalSec = Number(process.env.LLM_HEARTBEAT_INTERVAL_SEC ?? "45");
  const client = new MoltChessClient({ apiKey, baseUrl });
  const basicsOff = ["0", "false", "no", "off"];
  let agentBasics: AgentBasicsConfig | null = {};
  const flag = (process.env.MOLTCHESS_AGENT_BASICS ?? "1").trim().toLowerCase();
  if (basicsOff.includes(flag)) {
    agentBasics = null;
  }
  console.info(`[llm] provider=${provider} interval=${intervalSec}s — Ctrl+C to stop`);
  if (agentBasics) {
    console.info("[llm] agent basics on: open challenges, free open tournaments, unseen likes");
  }
  await runLlmHeartbeatLoop(client, chooser, { intervalSec, log: console.log, agentBasics });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
