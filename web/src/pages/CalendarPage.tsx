import { useMemo, useState } from "react";
import { CalendarGrid } from "../components/CalendarGrid";
import { EntryRow } from "../components/EntryRow";
import { PageToolbar, ScanLink } from "../components/Layout";
import { useAuth } from "../lib/auth";
import { entryDateKey, formatDisplayDate, monthYearLabel } from "../lib/dates";
import { useEntries } from "../hooks/useEntries";

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function CalendarPage() {
  const { accessToken } = useAuth();
  const { entries, loading, error } = useEntries(accessToken);
  const [view, setView] = useState(() => {
    const t = new Date();
    return { year: t.getFullYear(), month: t.getMonth() };
  });
  const [selected, setSelected] = useState(todayIso);

  const dayEntries = useMemo(
    () => entries.filter((e) => entryDateKey(e) === selected),
    [entries, selected],
  );

  const shiftMonth = (delta: number) => {
    setView((v) => {
      const d = new Date(v.year, v.month + delta, 1);
      return { year: d.getFullYear(), month: d.getMonth() };
    });
  };

  return (
    <>
      <PageToolbar title={monthYearLabel(view.year, view.month)} action={<ScanLink />} />
      <div className="content">
        {error ? <p className="login-error">{error}</p> : null}
        <div className="cal-header">
          <span className="cal-month">{monthYearLabel(view.year, view.month)}</span>
          <div className="cal-nav">
            <button type="button" aria-label="Previous month" onClick={() => shiftMonth(-1)}>
              ‹
            </button>
            <button type="button" aria-label="Next month" onClick={() => shiftMonth(1)}>
              ›
            </button>
          </div>
        </div>

        <CalendarGrid
          year={view.year}
          month={view.month}
          selected={selected}
          entries={entries}
          onSelect={setSelected}
        />

        <div className="group">
          <p className="group-label">{formatDisplayDate(selected)}</p>
          <div className="inset">
            {loading && dayEntries.length === 0 ? (
              <p className="footnote" style={{ padding: 16 }}>Loading…</p>
            ) : null}
            {!loading && dayEntries.length === 0 ? (
              <p className="footnote" style={{ padding: 16 }}>No entries for this day.</p>
            ) : null}
            {dayEntries.map((e) => <EntryRow key={e.id} entry={e} />)}
          </div>
        </div>

        <p className="footnote">Days with a dot have at least one entry.</p>
      </div>
    </>
  );
}
