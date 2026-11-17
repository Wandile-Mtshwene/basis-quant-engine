"use client";
import katex from "katex";

// Thin KaTeX wrapper (avoids react-katex peer-dependency friction on React 19).
export function TeX({ children, block = false }: { children: string; block?: boolean }) {
  const html = katex.renderToString(children, {
    throwOnError: false,
    displayMode: block,
  });
  return (
    <span
      className={block ? "block my-1 overflow-x-auto" : "inline-block"}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
