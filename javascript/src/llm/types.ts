import type { CreatePostInput, CreateTournamentInput } from "../client.js";

export interface MovePromptContext {
  gameId: string;
  fen: string;
  myColor: string;
  legalSans: string[];
  legalUci: string[];
  movesSummary: string;
}

export interface ParsedMoveChoice {
  moveSan?: string | null;
  moveUci?: string | null;
}

export interface JsonObjectGenerator {
  generateObject(systemPrompt: string, userMessage: string): Promise<Record<string, unknown>>;
}

export interface LlmMoveChooser {
  chooseMove(ctx: MovePromptContext, feedback?: string | null): Promise<ParsedMoveChoice>;
}

export interface DraftPostRequest {
  instruction: string;
  context?: string;
  voiceBrief?: string;
  playbookBrief?: string;
  postType?: CreatePostInput["post_type"];
  chessGameId?: string;
  tournamentId?: string;
  repostOfPostId?: string;
  maxChars?: number;
}

export interface DraftReplyRequest {
  postId: string;
  postContent: string;
  instruction: string;
  parentReplyId?: string;
  parentReplyContent?: string;
  context?: string;
  voiceBrief?: string;
  playbookBrief?: string;
  maxChars?: number;
}

export interface DraftTournamentRequest {
  instruction: string;
  context?: string;
  voiceBrief?: string;
  playbookBrief?: string;
  maxParticipantsChoices?: number[];
  prizeDistributionChoices?: NonNullable<CreateTournamentInput["prize_distribution"]>[];
  minimumStartAt?: string | null;
}

export interface JsonGenerationOptions {
  maxAttempts?: number;
}
