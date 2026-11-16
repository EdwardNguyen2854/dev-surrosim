import { useEffect, useId, useRef, type ReactNode } from "react";

import { Icon } from "./Icon";

/** Native modal semantics supply focus trapping, Escape, and focus restoration. */
export function Drawer({
  id, title, open, onClose, children,
}: {
  id: string;
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (!open) {
      if (dialog.open) dialog.close();
      return;
    }
    if (!dialog.open) dialog.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
      if (dialog.open) dialog.close();
    };
  }, [open]);

  return (
    <dialog
      ref={ref} id={id} aria-labelledby={titleId}
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
      }}
      className="drawer fixed inset-y-0 left-0 m-0 h-dvh max-h-none w-[min(20rem,calc(100vw-2rem))] max-w-none border-0 border-r border-line bg-canvas p-0 text-ink shadow-overlay"
    >
      <div className="flex h-full flex-col">
        <div className="flex shrink-0 items-center justify-between border-b border-line px-4 py-2">
          <h2 id={titleId} className="text-sm font-semibold">{title}</h2>
          <button
            type="button" onClick={onClose} aria-label={`Close ${title.toLowerCase()}`}
            className="flex h-11 w-11 items-center justify-center rounded text-ink-muted hover:bg-wash hover:text-ink"
          >
            <Icon name="close" className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
