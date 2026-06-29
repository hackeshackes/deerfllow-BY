"use client";

import { useEffect, useState } from "react";

interface MentionInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  /** Static suggestion list — production will fetch from the subscriptions API. */
  suggestions?: ReadonlyArray<string>;
}

const DEFAULT_SUGGESTIONS: ReadonlyArray<string> = [
  "@alice",
  "@bob",
  "@product-team",
  "@engineering",
];

/**
 * Plain text input with @-trigger autocomplete. When the user types an `@`
 * at the end of the input, a suggestion list appears; clicking a suggestion
 * inserts it (minus the leading `@`) and closes the list.
 *
 * This MVP is intentionally simple — no fuzzy match, no async lookup, no
 * keyboard navigation. Those will land when the real mention system
 * (subscriptions + notifications) is wired in.
 */
export function MentionInput({
  value,
  onChange,
  placeholder = "Type @ to mention…",
  suggestions = DEFAULT_SUGGESTIONS,
}: MentionInputProps) {
  const [showSuggest, setShowSuggest] = useState<boolean>(value.endsWith("@"));

  // Keep the suggestion visibility in sync if the parent changes `value`
  // out-of-band (e.g. reset, autofill).
  useEffect(() => {
    setShowSuggest(value.endsWith("@"));
  }, [value]);

  return (
    <div className="relative" data-testid="mention-input-wrapper">
      <textarea
        data-testid="mention-input"
        className="w-full border p-2"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setShowSuggest(e.target.value.endsWith("@"));
        }}
        placeholder={placeholder}
      />
      {showSuggest && (
        <ul
          data-testid="mention-suggest"
          className="absolute z-10 border bg-white shadow"
        >
          {suggestions.map((s) => (
            <li
              key={s}
              data-testid={`mention-opt-${s}`}
              className="cursor-pointer p-2 hover:bg-gray-100"
              onClick={() => {
                // Insert everything after the leading "@".
                onChange(value + s.slice(1) + " ");
                setShowSuggest(false);
              }}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
