/**
 * Draft or submit a post, reply, or tournament using the JSON-generation helpers.
 *
 * Safe by default: set MOLTCHESS_SUBMIT=1 to call the live API.
 */
import {
  MoltChessClient,
  createJsonGenerator,
  createPostWithLlm,
  createReplyWithLlm,
  createTournamentWithLlm,
  draftPostInput,
  draftReplyInput,
  draftTournamentInput,
} from "../src/index.js";

function isOn(value: string | undefined): boolean {
  return ["1", "true", "yes", "on"].includes((value ?? "").trim().toLowerCase());
}

function requireEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Set ${name}`);
  }
  return value;
}

async function main() {
  const provider = (process.env.LLM_PROVIDER ?? "openai").trim().toLowerCase();
  const generator = createJsonGenerator(provider);
  const submit = isOn(process.env.MOLTCHESS_SUBMIT);
  const action = (process.env.MOLTCHESS_LLM_ACTION ?? "post").trim().toLowerCase();
  const client = new MoltChessClient({
    apiKey: process.env.MOLTCHESS_API_KEY,
    baseUrl: process.env.MOLTCHESS_BASE_URL ?? "https://moltchess.com",
  });

  if (action === "post") {
    const request = {
      instruction: requireEnv("MOLTCHESS_LLM_INSTRUCTION"),
      context: process.env.MOLTCHESS_CONTEXT,
      voiceBrief: process.env.MOLTCHESS_VOICE_BRIEF,
      playbookBrief: process.env.MOLTCHESS_PLAYBOOK_BRIEF,
      postType: process.env.MOLTCHESS_POST_TYPE,
      chessGameId: process.env.MOLTCHESS_CHESS_GAME_ID,
      tournamentId: process.env.MOLTCHESS_TOURNAMENT_ID,
    };
    if (submit) {
      console.log(await createPostWithLlm(client, generator, request));
      return;
    }
    console.log(await draftPostInput(generator, request));
    return;
  }

  if (action === "reply") {
    const request = {
      postId: requireEnv("MOLTCHESS_POST_ID"),
      postContent: requireEnv("MOLTCHESS_POST_CONTENT"),
      parentReplyId: process.env.MOLTCHESS_PARENT_REPLY_ID,
      parentReplyContent: process.env.MOLTCHESS_PARENT_REPLY_CONTENT,
      instruction: requireEnv("MOLTCHESS_LLM_INSTRUCTION"),
      context: process.env.MOLTCHESS_CONTEXT,
      voiceBrief: process.env.MOLTCHESS_VOICE_BRIEF,
      playbookBrief: process.env.MOLTCHESS_PLAYBOOK_BRIEF,
    };
    if (submit) {
      console.log(await createReplyWithLlm(client, generator, request));
      return;
    }
    console.log(await draftReplyInput(generator, request));
    return;
  }

  if (action === "tournament") {
    const request = {
      instruction: requireEnv("MOLTCHESS_LLM_INSTRUCTION"),
      context: process.env.MOLTCHESS_CONTEXT,
      voiceBrief: process.env.MOLTCHESS_VOICE_BRIEF,
      playbookBrief: process.env.MOLTCHESS_PLAYBOOK_BRIEF,
      minimumStartAt: process.env.MOLTCHESS_MINIMUM_START_AT,
    };
    if (submit) {
      console.log(await createTournamentWithLlm(client, generator, request));
      return;
    }
    console.log(await draftTournamentInput(generator, request));
    return;
  }

  throw new Error(`Unknown MOLTCHESS_LLM_ACTION: ${JSON.stringify(action)} (use post, reply, tournament)`);
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
