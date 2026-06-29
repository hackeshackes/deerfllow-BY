"use client";

import { useEffect, useRef, useState } from "react";

export interface MentionSuggestion {
  /** Insertion token, e.g. "@alice". The leading "@" is optional; the
   *  component strips it before inserting. */
  handle: string;
  /** Optional display name (used as a secondary line in the dropdown). */
  displayName?: string;
  /** Optional id for keyed rendering; falls back to `handle`. */
  id?: string;
}

interface MentionInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  /**
   * Static suggestions. Mutually exclusive with `fetchSuggestions`; if both
   * are supplied, `fetchSuggestions` wins. Useful for tests and Storybook.
   */
  suggestions?: ReadonlyArray<string>;
  /**
   * Async resolver that returns up to N suggestions for the given query
   * (the text after the last `@`). Wired to `/api/users/search` in
   * production; stubs in tests.
   */
  fetchSuggestions?: (query: string) => Promise<ReadonlyArray<MentionSuggestion>>;
  /** Debounce (ms) before calling `fetchSuggestions`. Default 150. */
  debounceMs?: number;
}

const DEFAULT_SUGGESTIONS: ReadonlyArray<string> = [
  "@alice",
  "@bob",
  "@product-team",
  "@engineering",
];

const SUGGEST_DEBOUNCE_MS = 150;

/**
 * Plain text input with @-trigger autocomplete. When the user types an `@`
 * at the end of the input, a suggestion list appears; clicking a suggestion
 * inserts it (minus the leading `@`) and closes the list.
 *
 * Two modes:
 *  - `suggestions` (static): used for tests and offline demos.
 *  - `fetchSuggestions` (async): hits `/api/users/search` in production.
 */
export function MentionInput({
  value,
  onChange,
  placeholder = "Type @ to mention…",
  suggestions,
  fetchSuggestions,
  debounceMs = SUGGEST_DEBOUNCE_MS,
}: MentionInputProps) {
  const [showSuggest, setShowSuggest] = useState<boolean>(value.endsWith("@"));
  const [query, setQuery] = useState<string>("");
  const [dynamic, setDynamic] = useState<ReadonlyArray<MentionSuggestion>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastFetchId = useRef<number>(0);

  // Keep suggestion visibility in sync with the controlled `value`.
  useEffect(() => {
    setShowSuggest(value.endsWith("@"));
  }, [value]);

  // Debounced fetch when the user types past the `@` trigger.
  useEffect(() => {
    if (!showSuggest || !fetchSuggestions) {
      setDynamic([]);
      setIsLoading(false);
      return;
    }
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    setIsLoading(true);
    setLoadError(null);
    const fetchId = ++lastFetchId.current;
    debounceTimer.current = setTimeout(() => {
      fetchSuggestions(query)
        .then((results) => {
          if (fetchId !== lastFetchId.current) return; // stale
          setDynamic(results);
          setIsLoading(false);
        })
        .catch((e: unknown) => {
          if (fetchId !== lastFetchId.current) return;
          setLoadError(e instanceof Error ? e.message : String(e));
          setDynamic([]);
          setIsLoading(false);
        });
    }, debounceMs);
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [query, showSuggest, fetchSuggestions, debounceMs]);

  const staticList: ReadonlyArray<MentionSuggestion> = (suggestions ?? DEFAULT_SUGGESTIONS).map(
    (handle) => ({ handle }),
  );
  const list: ReadonlyArray<MentionSuggestion> = fetchSuggestions ? dynamic : staticList;

  return (
    <div className="relative" data-testid="mention-input-wrapper">
      <textarea
        data-testid="mention-input"
        className="w-full border p-2"
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          onChange(v);
          const at = v.lastIndexOf("@");
          setQuery(at >= 0 ? v.slice(at + 1) : "");
          setShowSuggest(v.endsWith("@"));
        }}
        placeholder={placeholder}
      />
      {showSuggest && (
        <ul
          data-testid="mention-suggest"
          className="absolute z-10 border bg-white shadow"
        >
          {isLoading && (
            <li
              data-testid="mention-loading"
              className="p-2 text-sm text-gray-500"
            >
              Loading…
            </li>
          )}
          {loadError && !isLoading && (
            <li
              data-testid="mention-error"
              className="p-2 text-sm text-red-600"
            >
              {loadError}
            </li>
          )}
          {!isLoading && !loadError && list.length === 0 && (
            <li
              data-testid="mention-empty"
              className="p-2 text-sm text-gray-500"
            >
              No matches
            </li>
          )}
          {list.map((s) => {
            const key = s.id ?? s.handle;
            const insert = s.handle.startsWith("@") ? s.handle.slice(1) : s.handle;
            return (
              <li
                key={key}
                data-testid={`mention-opt-${s.handle}`}
                className="cursor-pointer p-2 hover:bg-gray-100"
                onClick={() => {
                  onChange(value + insert + " ");
                  setShowSuggest(false);
                }}
              >
                <span className="font-medium">{s.handle}</span>
                {s.displayName && (
                  <span className="ml-2 text-xs text-gray-500">{s.displayName}</span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
