export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** Citation labels the backend returned, e.g. "arac.docx — 3. ARAC TAHSIS". */
  citations?: string[];
  grounded?: boolean;
  error?: string;
  createdAt: number;
};

export type DocumentInfo = { filename: string; chunkCount: number };

export type Conversation = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  documentName: string | null;
  messages: Message[];
  /** Everything older than `summarizedUpTo`, folded into one paragraph. */
  summary: string | null;
  summarizedUpTo: number;
};
