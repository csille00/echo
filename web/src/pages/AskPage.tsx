import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { PageToolbar } from "../components/Layout";
import { useAuth } from "../lib/auth";
import { searchEntries } from "../lib/api";
import { formatShortDate } from "../lib/dates";
import type { SearchHit } from "../types";

type Turn = { role: "user" | "assistant"; query?: string; hits?: SearchHit[] };

export function AskPage() {
  const { accessToken, authenticated } = useAuth();
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!authenticated || !q || busy) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", query: q }]);
    setBusy(true);
    try {
      const hits = await searchEntries(accessToken, q, 6);
      setTurns((t) => [...t, { role: "assistant", hits }]);
    } catch {
      setTurns((t) => [...t, { role: "assistant", hits: [] }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageToolbar title="Ask" />
      <div className="content chat-content">
        <div className="chat-thread">
          {turns.length === 0 ? (
            <p className="footnote">
              Ask in plain language. Answers use semantic search over your journal text (no LLM yet).
            </p>
          ) : null}
          {turns.map((turn, i) =>
            turn.role === "user" ? (
              <div key={i} className="bubble-user">{turn.query}</div>
            ) : (
              <div key={i} className="bubble-assistant">
                {!turn.hits?.length
                  ? "I could not find anything related in your journals."
                  : "Here are the closest passages I found:"}
                {turn.hits?.map((h) => (
                  <Link key={`${h.entry_id}-${h.chunk_text.slice(0, 20)}`} className="citation-card" to={`/entry/${h.entry_id}`}>
                    <div className="citation-meta">
                      {formatShortDate(h.journal_date)}
                      {h.tags.length ? ` · ${h.tags.join(", ")}` : ""}
                    </div>
                    <div className="citation-quote">“{h.chunk_text}”</div>
                  </Link>
                ))}
              </div>
            ),
          )}
        </div>
      </div>

      <form className="chat-composer" onSubmit={(e) => void send(e)}>
        <div className="chat-composer-inner">
          <input
            type="text"
            placeholder="Ask about your journals"
            aria-label="Message"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
          />
          <button type="submit" aria-label="Send" disabled={busy || !input.trim()}>
            ↑
          </button>
        </div>
      </form>
    </>
  );
}
