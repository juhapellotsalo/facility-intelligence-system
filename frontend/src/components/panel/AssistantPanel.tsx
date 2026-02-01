import { useState, useRef, useEffect, useCallback } from "react";
import { Send, HelpCircle } from "lucide-react";
import { ChatMessage, TypingIndicator, ThinkingIndicator } from "./ChatMessage";
import {
  type ChatMessage as ChatMessageType,
  getWelcomeMessage,
  getHelpMessage,
  generateMessageId,
} from "../../data/mockResponses";
import {
  chatWithAgent,
  type VisualizationSpec,
  type VisualizationIdea,
} from "../../lib/api";

export interface AssistantPanelHandle {
  sendQuery: (query: string) => Promise<void>;
  hasUserMessages: boolean;
  focusInput: () => void;
  sendVisualizationRequest: (idea: VisualizationIdea) => Promise<void>;
  requestIdeas: () => Promise<void>;
}

interface AssistantPanelProps {
  sessionId: string;
  onResize?: (delta: number) => void;
  onReady?: (handle: AssistantPanelHandle) => void;
  onVisualizationReady?: (
    spec: VisualizationSpec,
    ideaId: string,
    title: string,
  ) => void;
  onIdeasReady?: (ideas: VisualizationIdea[]) => void;
}

/**
 * AI Assistant panel with functional chat and resizable width.
 * Shows morning summary on load, handles user input, returns mock responses.
 */
export function AssistantPanel({
  sessionId,
  onResize,
  onReady,
  onVisualizationReady,
  onIdeasReady,
}: AssistantPanelProps) {
  const [messages, setMessages] = useState<ChatMessageType[]>(() => [
    { ...getWelcomeMessage(), id: generateMessageId() },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [thinkingText, setThinkingText] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll user message to top of container
  const scrollUserMessageToTop = useCallback((messageId: string) => {
    setTimeout(() => {
      const container = messagesContainerRef.current;
      const msgEl = document.getElementById(`msg-${messageId}`);
      if (container && msgEl) {
        // Calculate position to put message at top with small padding
        const containerRect = container.getBoundingClientRect();
        const msgRect = msgEl.getBoundingClientRect();
        const scrollOffset =
          msgRect.top - containerRect.top + container.scrollTop - 8;
        container.scrollTo({ top: scrollOffset, behavior: "smooth" });
      }
    }, 50);
  }, []);

  // Auto-scroll to bottom when streaming completes
  useEffect(() => {
    if (!isStreaming) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming]);

  // Session ID passed from parent for conversation continuity

  // Core send logic - can be called externally via handle
  const sendQuery = useCallback(
    async (query: string) => {
      if (!query.trim() || isTyping) return;

      // Add user message
      const userMessage: ChatMessageType = {
        id: generateMessageId(),
        role: "user",
        content: query,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setIsTyping(true);

      // Scroll user message to top
      scrollUserMessageToTop(userMessage.id);

      // Handle "help" specially - no LLM call, just static response
      if (query.toLowerCase().trim() === "help") {
        const helpMessage: ChatMessageType = {
          ...getHelpMessage(),
          id: generateMessageId(),
        };
        setMessages((prev) => [...prev, helpMessage]);
        setIsTyping(false);
        return;
      }

      // Check if this is an incident report request
      const isReportRequest = /incident\s*report/i.test(query);

      // Call real agent API with streaming
      try {
          // Create a placeholder message that we'll update as content streams in
          const streamingMessageId = generateMessageId();
          const streamingMessage: ChatMessageType = {
            id: streamingMessageId,
            role: "assistant",
            content: "",
            isReport: isReportRequest,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, streamingMessage]);
          setIsStreaming(true);
          setThinkingText("Thinking..."); // Show spinner immediately

          // Buffer text to determine if it's intermediate (thinking) or final (answer)
          // Pattern: text → tool_use = intermediate, text → done = final answer
          let pendingText: string | null = null;

          await chatWithAgent(query, sessionId, (event) => {
            if (event.type === "progress" && event.data.message) {
              // Progress events from backend (e.g., "Analyzing your question...")
              setThinkingText(event.data.message);
            } else if (event.type === "text" && event.data.content) {
              // Store text as pending - we'll decide what to do when we see the next event
              pendingText = event.data.content;
              // Show intermediate text immediately
              setThinkingText(event.data.content.trim());
            } else if (
              event.type === "tool_use" &&
              event.data.status === "running"
            ) {
              // Tool starting - show friendly message from backend
              const message = event.data.message || `Using ${event.data.tool || "tool"}...`;
              setThinkingText(message);
              // Clear pending since we're now in tool execution
              pendingText = null;
            } else if (
              event.type === "tool_use" &&
              event.data.status === "done"
            ) {
              // Tool done - just wait for next event
            } else if (event.type === "done") {
              // Stream complete - any pending text is the final answer
              if (pendingText) {
                const finalContent = pendingText;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === streamingMessageId
                      ? { ...msg, content: finalContent }
                      : msg,
                  ),
                );
                pendingText = null;
              }
              setThinkingText(null);
            }
          });

          // Clear thinking state
          setThinkingText(null);

          // Ensure we have content; if empty, show error
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamingMessageId && !msg.content
                ? {
                    ...msg,
                    content: "I apologize, but I couldn't generate a response.",
                  }
                : msg,
            ),
          );
        } catch (error) {
          const errorMessage: ChatMessageType = {
            id: generateMessageId(),
            role: "assistant",
            content: `Error: ${error instanceof Error ? error.message : "Failed to get response"}`,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errorMessage]);
        } finally {
          setIsTyping(false);
          setIsStreaming(false);
        }
    },
    [isTyping, scrollUserMessageToTop, sessionId],
  );

  // Derive hasUserMessages - true if any user messages exist
  const hasUserMessages = messages.some((msg) => msg.role === "user");

  // Focus the input field
  const focusInput = useCallback(() => {
    inputRef.current?.focus();
  }, []);

  // Send visualization generation request through the chat endpoint
  const sendVisualizationRequest = useCallback(
    async (idea: VisualizationIdea) => {
      if (isTyping) return;

      // Add user message showing request
      const userMessage: ChatMessageType = {
        id: generateMessageId(),
        role: "user",
        content: `Generate "${idea.title}" visualization`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsTyping(true);

      // Scroll user message to top
      scrollUserMessageToTop(userMessage.id);

      // Create streaming placeholder
      const streamingId = generateMessageId();
      setMessages((prev) => [
        ...prev,
        {
          id: streamingId,
          role: "assistant",
          content: "",
          timestamp: new Date(),
        },
      ]);
      setIsStreaming(true);
      setThinkingText("Generating visualization...");

      try {
        await chatWithAgent(
          JSON.stringify({ type: "generate_viz", idea }),
          sessionId,
          (event) => {
            if (event.type === "text" && event.data.content) {
              setThinkingText(event.data.content);
            } else if (event.type === "progress") {
              // Custom progress events from the backend
              const message = event.data.message || "Processing...";
              setThinkingText(message);
            } else if (event.type === "tool_use") {
              // Show tool activity during data gathering
              const status = event.data.status;
              const message = event.data.message;
              if (status === "running" && message) {
                setThinkingText(message);
              }
            } else if (event.type === "visualization") {
              onVisualizationReady?.(
                event.data.spec!,
                event.data.ideaId!,
                event.data.title!,
              );
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamingId
                    ? {
                        ...msg,
                        content: `Visualization "${event.data.title}" ready.`,
                      }
                    : msg,
                ),
              );
            } else if (event.type === "error") {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === streamingId
                    ? {
                        ...msg,
                        content: `Failed to generate visualization: ${event.data.message}`,
                      }
                    : msg,
                ),
              );
            } else if (event.type === "done") {
              setIsStreaming(false);
              setIsTyping(false);
              setThinkingText(null);
            }
          },
        );
      } catch (error) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === streamingId
              ? {
                  ...msg,
                  content: `Failed to generate visualization: ${error instanceof Error ? error.message : "Unknown error"}`,
                }
              : msg,
          ),
        );
        setIsStreaming(false);
        setIsTyping(false);
        setThinkingText(null);
      }
    },
    [sessionId, isTyping, onVisualizationReady, scrollUserMessageToTop],
  );

  // Request visualization ideas through the chat endpoint
  const requestIdeas = useCallback(async () => {
    if (isTyping) return;

    // Add user message showing request
    const userMessage: ChatMessageType = {
      id: generateMessageId(),
      role: "user",
      content: "Suggest some visualizations based on our conversation",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    // Scroll user message to top
    scrollUserMessageToTop(userMessage.id);

    // Create streaming placeholder
    const streamingId = generateMessageId();
    setMessages((prev) => [
      ...prev,
      {
        id: streamingId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
      },
    ]);
    setIsStreaming(true);
    setThinkingText("Analyzing conversation...");

    try {
      await chatWithAgent(
        JSON.stringify({ type: "request_ideas" }),
        sessionId,
        (event) => {
          if (event.type === "text" && event.data.content) {
            setThinkingText(event.data.content);
          } else if (event.type === "ideas") {
            onIdeasReady?.(event.data.ideas || []);
            const count = event.data.ideas?.length || 0;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === streamingId
                  ? {
                      ...msg,
                      content: `I've suggested ${count} visualization${count !== 1 ? "s" : ""} based on our conversation. Check the Charts tab to see them.`,
                    }
                  : msg,
              ),
            );
          } else if (event.type === "error") {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === streamingId
                  ? {
                      ...msg,
                      content: `Failed to generate ideas: ${event.data.message}`,
                    }
                  : msg,
              ),
            );
          } else if (event.type === "done") {
            setIsStreaming(false);
            setIsTyping(false);
            setThinkingText(null);
          }
        },
      );
    } catch (error) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === streamingId
            ? {
                ...msg,
                content: `Failed to generate ideas: ${error instanceof Error ? error.message : "Unknown error"}`,
              }
            : msg,
        ),
      );
      setIsStreaming(false);
      setIsTyping(false);
      setThinkingText(null);
    }
  }, [sessionId, isTyping, onIdeasReady, scrollUserMessageToTop]);

  // Expose handle to parent
  useEffect(() => {
    onReady?.({
      sendQuery,
      hasUserMessages,
      focusInput,
      sendVisualizationRequest,
      requestIdeas,
    });
  }, [
    onReady,
    sendQuery,
    hasUserMessages,
    focusInput,
    sendVisualizationRequest,
    requestIdeas,
  ]);

  // Send from input field
  const handleSend = useCallback(() => {
    sendQuery(input.trim());
  }, [input, sendQuery]);

  // Handle Enter key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <aside className="relative flex flex-col overflow-hidden border-l border-bg-border bg-bg-surface">
      {/* Resize handle */}
      {onResize && <ResizeHandle onResize={onResize} />}

      {/* Header */}
      <div className="border-b border-bg-border px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-text-primary">
            ★ Facility Assistant
          </h3>
          <button
            type="button"
            onClick={() => sendQuery("help")}
            disabled={isTyping}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-text-muted transition-colors hover:bg-bg-raised hover:text-cyan-400 disabled:opacity-50"
            title="Show available options"
          >
            <HelpCircle size={14} />
            <span>Help</span>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div
        ref={messagesContainerRef}
        className="flex-1 space-y-3 overflow-y-auto p-4"
      >
        {messages.map((message) => (
          <div key={message.id} id={`msg-${message.id}`}>
            <ChatMessage message={message} onAction={sendQuery} />
          </div>
        ))}
        {thinkingText && <ThinkingIndicator text={thinkingText} />}
        {isTyping && !isStreaming && !thinkingText && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-bg-border p-3">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your facility..."
            disabled={isTyping}
            className="flex-1 rounded-sm border border-bg-border bg-bg-raised px-3 py-2.5 text-sm text-text-primary outline-none transition-colors placeholder:text-text-disabled focus:border-cyan-400 disabled:opacity-50"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="flex h-10 w-10 items-center justify-center rounded-sm bg-cyan-500 text-white transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}

/**
 * Draggable resize handle for the panel's left edge.
 */
function ResizeHandle({ onResize }: { onResize: (delta: number) => void }) {
  const [isDragging, setIsDragging] = useState(false);
  const startXRef = useRef(0);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    startXRef.current = e.clientX;
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - startXRef.current;
      startXRef.current = e.clientX;
      onResize(delta);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    // Change cursor globally while dragging
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isDragging, onResize]);

  return (
    <div
      onMouseDown={handleMouseDown}
      className={`absolute -left-1 top-0 z-10 h-full w-2 cursor-col-resize transition-colors hover:bg-cyan-400/40 ${
        isDragging ? "bg-cyan-400/60" : ""
      }`}
      title="Drag to resize"
    />
  );
}
