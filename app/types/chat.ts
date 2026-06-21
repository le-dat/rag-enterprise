export interface ToolCall {
  name: string;
  args: any;
  output?: string;
  status: "running" | "completed" | "failed" | "denied";
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  tools?: ToolCall[];
  grounding?: {
    grounded: boolean;
    reason?: string;
  };
  blocked?: {
    type: "input_rail" | "retrieval_rail";
    reason: string;
  };
  error?: string;
}

export interface UserInfo {
  user_id: string;
  role: string;
  department: string;
}
