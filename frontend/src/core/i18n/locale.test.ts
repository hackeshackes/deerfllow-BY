import { describe, it, expect, vi, afterEach } from "vitest";

import {
  DEFAULT_LOCALE,
  detectLocale,
  getLocaleByLang,
  isLocale,
  normalizeLocale,
  SUPPORTED_LOCALES,
} from "./locale";

describe("isLocale", () => {
  it("returns true for supported locales", () => {
    expect(isLocale("en-US")).toBe(true);
    expect(isLocale("zh-CN")).toBe(true);
  });

  it("returns false for unsupported or malformed values", () => {
    expect(isLocale("fr-FR")).toBe(false);
    expect(isLocale("en")).toBe(false);
    expect(isLocale("")).toBe(false);
  });
});

describe("getLocaleByLang", () => {
  it("matches a known supported lang prefix case-insensitively", () => {
    expect(getLocaleByLang("en")).toBe("en-US");
    expect(getLocaleByLang("EN")).toBe("en-US");
    expect(getLocaleByLang("zh")).toBe("zh-CN");
  });

  it("returns the default locale for unknown languages", () => {
    expect(getLocaleByLang("fr")).toBe(DEFAULT_LOCALE);
  });

  it("returns the default locale for full tags that don't prefix-match a supported locale", () => {
    // "zh-cn" lower-cased won't prefix-match "zh-CN" because the source isn't
    // lower-cased before comparison — only the input is.
    expect(getLocaleByLang("zh-cn")).toBe(DEFAULT_LOCALE);
  });
});

describe("normalizeLocale", () => {
  it("returns the default locale for null / undefined / empty", () => {
    expect(normalizeLocale(null)).toBe(DEFAULT_LOCALE);
    expect(normalizeLocale(undefined)).toBe(DEFAULT_LOCALE);
    expect(normalizeLocale("")).toBe(DEFAULT_LOCALE);
  });

  it("returns the value unchanged when it is already a supported locale", () => {
    expect(normalizeLocale("en-US")).toBe("en-US");
    expect(normalizeLocale("zh-CN")).toBe("zh-CN");
  });

  it("promotes any zh-prefixed value to zh-CN", () => {
    expect(normalizeLocale("zh")).toBe("zh-CN");
    expect(normalizeLocale("zh-Hant")).toBe("zh-CN");
    expect(normalizeLocale("zh-TW")).toBe("zh-CN");
  });

  it("falls back to the default locale for unsupported values", () => {
    expect(normalizeLocale("fr-FR")).toBe(DEFAULT_LOCALE);
    expect(normalizeLocale("ja-JP")).toBe(DEFAULT_LOCALE);
  });
});

describe("detectLocale", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the default locale when window is undefined (server context)", () => {
    // happy-dom defines window, so simulate SSR by stubbing undefined behavior.
    const originalWindow = globalThis.window;
    delete (globalThis as { window?: unknown }).window;
    try {
      expect(detectLocale()).toBe(DEFAULT_LOCALE);
    } finally {
      (globalThis as { window?: unknown }).window = originalWindow;
    }
  });

  it("reads navigator.language and normalizes it", () => {
    vi.stubGlobal("navigator", { language: "zh-CN" });
    expect(detectLocale()).toBe("zh-CN");
  });

  it("falls back to the default when navigator reports an unsupported language", () => {
    vi.stubGlobal("navigator", { language: "ja-JP" });
    expect(detectLocale()).toBe(DEFAULT_LOCALE);
  });

  it("exposes the supported locales list", () => {
    expect(SUPPORTED_LOCALES).toEqual(["en-US", "zh-CN"]);
  });
});
