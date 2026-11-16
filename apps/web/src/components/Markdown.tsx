import { Children, isValidElement } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cx } from "./ui";
import { CodeBlock } from "./CodeBlock";

export function Markdown({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <div
      className={cx(
        "prose prose-sm max-w-none",
        "prose-headings:font-semibold prose-headings:tracking-tight prose-headings:text-ink",
        "prose-h1:text-base prose-h2:mt-6 prose-h2:text-sm prose-h3:text-xs",
        "prose-p:text-xs prose-p:leading-relaxed prose-p:text-ink-muted",
        "prose-li:text-xs prose-li:leading-relaxed prose-li:text-ink-muted",
        "prose-strong:text-ink",
        "prose-table:text-xs prose-th:border-line prose-th:text-2xs prose-th:uppercase prose-th:tracking-wider prose-th:text-ink-faint",
        "prose-td:border-line prose-td:py-1.5",
        "prose-code:font-mono prose-code:text-[0.72rem] prose-code:text-accent-strong",
        "prose-pre:bg-wash prose-pre:text-ink",
        "prose-a:text-link prose-a:no-underline hover:prose-a:underline",
        "prose-hr:border-line",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ node: _node, children: tableChildren, ...props }) => (
            <div className="thin-scroll overflow-x-auto">
              <table {...props}>{tableChildren}</table>
            </div>
          ),
          pre: ({ children: codeChildren }) => {
            const element = Children.toArray(codeChildren).find((child) => isValidElement(child));
            if (!isValidElement<{ className?: string; children?: string }>(element)) return <pre>{codeChildren}</pre>;
            const language = /language-([\w+-]+)/.exec(element.props.className ?? "")?.[1] ?? "text";
            return <div className="not-prose my-4"><CodeBlock language={language}>{String(element.props.children ?? "")}</CodeBlock></div>;
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
