import { useMemo } from "react";
import { entryDateKey } from "../lib/dates";
import type { JournalEntry } from "../types";

function daysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function startWeekday(year: number, month: number) {
  return new Date(year, month, 1).getDay();
}

export function CalendarGrid({
  year,
  month,
  selected,
  entries,
  onSelect,
}: {
  year: number;
  month: number;
  selected: string;
  entries: JournalEntry[];
  onSelect: (isoDate: string) => void;
}) {
  const entryDays = useMemo(() => {
    const set = new Set<string>();
    for (const e of entries) {
      set.add(entryDateKey(e));
    }
    return set;
  }, [entries]);

  const total = daysInMonth(year, month);
  const start = startWeekday(year, month);
  const cells: React.ReactNode[] = [];

  const prevMonthDays = daysInMonth(year, month - 1);
  for (let i = start - 1; i >= 0; i--) {
    cells.push(
      <span key={`p${i}`} className="cal-day muted">{prevMonthDays - i}</span>,
    );
  }

  for (let d = 1; d <= total; d++) {
    const iso = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    const classes = ["cal-day"];
    if (entryDays.has(iso)) classes.push("has-entry");
    if (iso === selected) classes.push("selected");
    cells.push(
      <button
        key={iso}
        type="button"
        className={classes.join(" ")}
        onClick={() => onSelect(iso)}
        style={{ border: "none", background: "transparent", font: "inherit" }}
      >
        {d}
      </button>,
    );
  }

  return (
    <div className="cal-grid" aria-label="Calendar">
      {["S", "M", "T", "W", "T", "F", "S"].map((d) => (
        <span key={d} className="cal-dow">{d}</span>
      ))}
      {cells}
    </div>
  );
}
