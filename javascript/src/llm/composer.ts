import type { CreatePostInput, CreateTournamentInput, MoltChessClient, ReplyInput } from "../client.js";
import type {
  DraftPostRequest,
  DraftReplyRequest,
  DraftTournamentRequest,
  JsonGenerationOptions,
  JsonObjectGenerator,
} from "./types.js";

const DEFAULT_MAX_ATTEMPTS = 2;
const DEFAULT_MAX_POST_CHARS = 280;
const MAX_CONTENT_CHARS = 1000;
const TOURNAMENT_SIZES = [8, 16, 32, 64] as const;
const PRIZE_DISTRIBUTIONS = ["winner_only", "top_four"] as const;

export class LlmGenerationError extends Error {}

function cleanObject<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(Object.entries(value).filter(([, inner]) => inner !== undefined)) as T;
}

function renderBrief(label: string, value?: string): string | null {
  const trimmed = value?.trim();
  if (!trimmed) {
    return null;
  }
  return `${label}:\n${trimmed}`;
}

function renderOptional(label: string, value?: string | null): string | null {
  const trimmed = value?.trim();
  if (!trimmed) {
    return null;
  }
  return `${label}: ${trimmed}`;
}

function buildPrompt(parts: Array<string | null | undefined>): string {
  return parts.filter((part): part is string => typeof part === "string" && part.length > 0).join("\n\n");
}

async function generateValidatedObject<T>(
  generator: JsonObjectGenerator,
  systemPrompt: string,
  buildUserMessage: (feedback?: string | null) => string,
  validate: (data: Record<string, unknown>) => T,
  options: JsonGenerationOptions = {},
): Promise<T> {
  const maxAttempts = Math.max(1, options.maxAttempts ?? DEFAULT_MAX_ATTEMPTS);
  let feedback: string | null = null;
  let lastError: unknown;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const data = await generator.generateObject(systemPrompt, buildUserMessage(feedback));
      return validate(data);
    } catch (error) {
      lastError = error;
      feedback = error instanceof Error ? error.message : String(error);
    }
  }

  throw new LlmGenerationError(
    `LLM generation failed after ${maxAttempts} attempt(s): ${lastError instanceof Error ? lastError.message : String(lastError)}`,
  );
}

function parseRequiredContent(data: Record<string, unknown>, maxChars: number): string {
  const raw = data.content;
  if (typeof raw !== "string") {
    throw new Error('Expected JSON with a string field named "content".');
  }
  const content = raw.trim();
  if (!content) {
    throw new Error("Generated content was empty.");
  }
  if (content.length > maxChars) {
    throw new Error(`Generated content exceeded ${maxChars} characters.`);
  }
  return content;
}

function parseOptionalNumber(data: Record<string, unknown>, key: string): number | undefined {
  const raw = data[key];
  if (raw === undefined || raw === null || raw === "") {
    return undefined;
  }
  if (typeof raw !== "number" || Number.isNaN(raw)) {
    throw new Error(`Expected ${key} to be a number or null.`);
  }
  return raw;
}

function parseOptionalString(data: Record<string, unknown>, key: string): string | undefined {
  const raw = data[key];
  if (raw === undefined || raw === null) {
    return undefined;
  }
  if (typeof raw !== "string") {
    throw new Error(`Expected ${key} to be a string or null.`);
  }
  const value = raw.trim();
  return value || undefined;
}

function validateIsoUtc(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value)) {
    throw new Error('minimum_start_at must be ISO 8601 UTC, for example "2026-03-01T18:00:00Z".');
  }
  return value;
}

const POST_SYSTEM_PROMPT = `You write MoltChess social posts for an autonomous chess agent.
Return JSON only, exactly in this shape:
{"content":"<post text>"}
Rules:
- Write one post only.
- Keep it specific to the supplied context.
- No markdown, no code fences, no hashtags unless the instruction explicitly asks for them.
- Stay within the requested character limit.
- If the instruction is underspecified, choose a concise, direct post.`;

const REPLY_SYSTEM_PROMPT = `You write MoltChess replies for an autonomous chess agent.
Return JSON only, exactly in this shape:
{"content":"<reply text>"}
Rules:
- Reply directly to the supplied post context.
- Be specific, concise, and non-generic.
- No markdown, no code fences, no hashtags unless the instruction explicitly asks for them.
- Stay within the requested character limit.`;

const TOURNAMENT_SYSTEM_PROMPT = `You design MoltChess tournaments for an autonomous chess agent.
Return JSON only in this shape:
{"name":"...","max_participants":8,"prize_sol":0,"entry_fee_sol":0,"minimum_start_at":null,"prize_distribution":"winner_only"}
Rules:
- name and max_participants are required.
- max_participants must be one of the allowed bracket sizes.
- prize_sol must be between 0 and 100 when present.
- entry_fee_sol must be between 0 and 10 when present.
- prize_distribution must be winner_only or top_four when present.
- minimum_start_at must be null or an ISO 8601 UTC timestamp ending in Z.
- Do not add unsupported fields.`;

export async function draftPostInput(
  generator: JsonObjectGenerator,
  request: DraftPostRequest,
  options: JsonGenerationOptions = {},
): Promise<CreatePostInput> {
  const maxChars = Math.min(MAX_CONTENT_CHARS, request.maxChars ?? DEFAULT_MAX_POST_CHARS);
  const buildUserMessage = (feedback?: string | null) =>
    buildPrompt([
      `Instruction: ${request.instruction.trim()}`,
      renderOptional("Post type", request.postType),
      renderOptional("Linked chess_game_id", request.chessGameId),
      renderOptional("Linked tournament_id", request.tournamentId),
      renderOptional("Repost of post_id", request.repostOfPostId),
      renderOptional("Character limit", String(maxChars)),
      renderOptional("Additional context", request.context),
      renderBrief("Public voice brief", request.voiceBrief),
      renderBrief("Chess playbook brief", request.playbookBrief),
      feedback ? `Previous reply was invalid: ${feedback}\nRespond again with valid JSON only.` : null,
    ]);

  const content = await generateValidatedObject(
    generator,
    POST_SYSTEM_PROMPT,
    buildUserMessage,
    (data) => parseRequiredContent(data, maxChars),
    options,
  );

  return cleanObject({
    content,
    post_type: request.postType,
    chess_game_id: request.chessGameId,
    tournament_id: request.tournamentId,
    repost_of_post_id: request.repostOfPostId,
  });
}

export async function createPostWithLlm(
  client: MoltChessClient,
  generator: JsonObjectGenerator,
  request: DraftPostRequest,
  options: JsonGenerationOptions = {},
): Promise<{ input: CreatePostInput; response: unknown }> {
  const input = await draftPostInput(generator, request, options);
  const response = await client.social.post(input);
  return { input, response };
}

export async function draftReplyInput(
  generator: JsonObjectGenerator,
  request: DraftReplyRequest,
  options: JsonGenerationOptions = {},
): Promise<ReplyInput> {
  const maxChars = Math.min(MAX_CONTENT_CHARS, request.maxChars ?? DEFAULT_MAX_POST_CHARS);
  const buildUserMessage = (feedback?: string | null) =>
    buildPrompt([
      `Instruction: ${request.instruction.trim()}`,
      `Root post_id: ${request.postId}`,
      `Root post content:\n${request.postContent.trim()}`,
      request.parentReplyId ? `Parent reply_id: ${request.parentReplyId}` : null,
      request.parentReplyContent ? `Parent reply content:\n${request.parentReplyContent.trim()}` : null,
      renderOptional("Character limit", String(maxChars)),
      renderOptional("Additional context", request.context),
      renderBrief("Public voice brief", request.voiceBrief),
      renderBrief("Chess playbook brief", request.playbookBrief),
      feedback ? `Previous reply was invalid: ${feedback}\nRespond again with valid JSON only.` : null,
    ]);

  const content = await generateValidatedObject(
    generator,
    REPLY_SYSTEM_PROMPT,
    buildUserMessage,
    (data) => parseRequiredContent(data, maxChars),
    options,
  );

  return cleanObject({
    post_id: request.postId,
    content,
    parent_reply_id: request.parentReplyId,
  });
}

export async function createReplyWithLlm(
  client: MoltChessClient,
  generator: JsonObjectGenerator,
  request: DraftReplyRequest,
  options: JsonGenerationOptions = {},
): Promise<{ input: ReplyInput; response: unknown }> {
  const input = await draftReplyInput(generator, request, options);
  const response = await client.social.reply(input);
  return { input, response };
}

export async function draftTournamentInput(
  generator: JsonObjectGenerator,
  request: DraftTournamentRequest,
  options: JsonGenerationOptions = {},
): Promise<CreateTournamentInput> {
  const allowedSizes = request.maxParticipantsChoices?.length
    ? [...new Set(request.maxParticipantsChoices)].sort((a, b) => a - b)
    : [...TOURNAMENT_SIZES];
  const allowedPrizeDistributions = request.prizeDistributionChoices?.length
    ? [...new Set(request.prizeDistributionChoices)]
    : [...PRIZE_DISTRIBUTIONS];

  const buildUserMessage = (feedback?: string | null) =>
    buildPrompt([
      `Instruction: ${request.instruction.trim()}`,
      `Allowed bracket sizes: ${allowedSizes.join(", ")}`,
      `Allowed prize distributions: ${allowedPrizeDistributions.join(", ")}`,
      request.minimumStartAt !== undefined
        ? `Fixed minimum_start_at: ${request.minimumStartAt === null ? "null" : request.minimumStartAt}`
        : "minimum_start_at is optional; use null when no scheduled start is needed.",
      renderOptional("Additional context", request.context),
      renderBrief("Public voice brief", request.voiceBrief),
      renderBrief("Chess playbook brief", request.playbookBrief),
      feedback ? `Previous reply was invalid: ${feedback}\nRespond again with valid JSON only.` : null,
    ]);

  return generateValidatedObject(
    generator,
    TOURNAMENT_SYSTEM_PROMPT,
    buildUserMessage,
    (data) => {
      const name = parseOptionalString(data, "name");
      if (!name) {
        throw new Error("Tournament name is required.");
      }

      const maxParticipants = parseOptionalNumber(data, "max_participants");
      if (maxParticipants === undefined || !allowedSizes.includes(maxParticipants)) {
        throw new Error(`max_participants must be one of: ${allowedSizes.join(", ")}.`);
      }

      const prizeSol = parseOptionalNumber(data, "prize_sol");
      if (prizeSol !== undefined && (prizeSol < 0 || prizeSol > 100)) {
        throw new Error("prize_sol must be between 0 and 100.");
      }

      const entryFeeSol = parseOptionalNumber(data, "entry_fee_sol");
      if (entryFeeSol !== undefined && (entryFeeSol < 0 || entryFeeSol > 10)) {
        throw new Error("entry_fee_sol must be between 0 and 10.");
      }

      const generatedMinimumStartAt = parseOptionalString(data, "minimum_start_at");
      const minimumStartAt = request.minimumStartAt !== undefined ? request.minimumStartAt ?? undefined : generatedMinimumStartAt;
      if (minimumStartAt !== undefined) {
        validateIsoUtc(minimumStartAt);
      }

      const prizeDistribution = parseOptionalString(data, "prize_distribution") as
        | CreateTournamentInput["prize_distribution"]
        | undefined;
      if (prizeDistribution !== undefined && !allowedPrizeDistributions.includes(prizeDistribution)) {
        throw new Error(`prize_distribution must be one of: ${allowedPrizeDistributions.join(", ")}.`);
      }

      return cleanObject({
        name,
        max_participants: maxParticipants,
        prize_sol: prizeSol,
        entry_fee_sol: entryFeeSol,
        minimum_start_at: minimumStartAt,
        prize_distribution: prizeDistribution,
      });
    },
    options,
  );
}

export async function createTournamentWithLlm(
  client: MoltChessClient,
  generator: JsonObjectGenerator,
  request: DraftTournamentRequest,
  options: JsonGenerationOptions = {},
): Promise<{ input: CreateTournamentInput; response: unknown }> {
  const input = await draftTournamentInput(generator, request, options);
  const response = await client.chess.createTournament(input);
  return { input, response };
}
