import {
  forwardRef,
  useContext,
  useEffect,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";
import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";

import { cx } from "../lib/cx";
import { Icon, type IconName } from "./Icon";
import { DocumentationContext, sectionId } from "./documentation";

export { cx };

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "secondary", size = "md", type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded border font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-45",
        variant === "primary" &&
          "border-action-border bg-action text-action-text hover:bg-action-hover",
        variant === "secondary" &&
          "border-line-strong bg-surface text-ink hover:bg-wash",
        variant === "ghost" &&
          "border-transparent text-ink-muted hover:bg-wash hover:text-ink",
        size === "sm" && "h-7 px-2.5 text-xs",
        size === "md" && "h-9 px-3.5 text-sm",
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export const Panel = forwardRef<HTMLElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <section
      ref={ref}
      className={cx(
        "rounded-md border border-line bg-surface shadow-panel",
        className,
      )}
      {...props}
    />
  ),
);
Panel.displayName = "Panel";

export function PanelHeader({
  title,
  kicker,
  description,
  actions,
  className,
}: {
  title: ReactNode;
  kicker?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  const documentation = useContext(DocumentationContext);
  const headingId = documentation && typeof title === "string" ? sectionId(title) : undefined;
  return (
    <header
      className={cx(
        "flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-3",
        className,
      )}
    >
      <div className="min-w-0">
        {kicker && (
          <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
            {kicker}
          </div>
        )}
        <h2 id={headingId} tabIndex={headingId ? -1 : undefined} className={cx("font-semibold tracking-tight text-ink", documentation ? "text-base" : "text-sm")}>
          {title}
          {headingId && <a href={`#${headingId}`} aria-label={`Link to ${title}`} className="ml-1 inline-flex h-9 w-9 items-center justify-center rounded font-mono text-xs font-normal text-ink-muted hover:bg-wash hover:text-link">#</a>}
        </h2>
        {description && (
          <p className="mt-0.5 max-w-2xl text-xs leading-relaxed text-ink-muted">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}

export function PanelBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("p-4", className)} {...props} />;
}

type Tone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

const chipTones: Record<Tone, string> = {
  neutral: "border-line bg-wash text-ink-muted",
  accent: "border-accent-border bg-accent-soft text-accent-ink",
  success: "border-success bg-success-soft text-success",
  warning: "border-warning bg-warning-soft text-warning",
  danger: "border-danger bg-danger-soft text-danger",
  info: "border-accent-border bg-info-soft text-info",
};

export function Chip({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5 text-2xs font-medium uppercase tracking-wider",
        chipTones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Stat({
  label,
  value,
  unit,
  sub,
  tone,
  className,
}: {
  label: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  sub?: ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "accent";
  className?: string;
}) {
  return (
    <div className={cx("min-w-0", className)}>
      <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
        {label}
      </div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span
          className={cx(
            "tnum font-mono text-lg font-medium leading-none tracking-tight",
            tone === "success" && "text-success",
            tone === "warning" && "text-warning",
            tone === "danger" && "text-danger",
            tone === "accent" && "text-accent-strong",
          )}
        >
          {value}
        </span>
        {unit && <span className="text-xs text-ink-faint">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-xs text-ink-muted">{sub}</div>}
    </div>
  );
}

function roundTo(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

function decimalsForStep(step: number): number {
  const text = String(step);
  const dot = text.indexOf(".");
  return dot === -1 ? 0 : text.length - dot - 1;
}

export function NumberInput({
  value,
  onChange,
  min,
  max,
  step,
  decimals,
  disabled,
  className,
  ariaLabel,
}: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  decimals?: number;
  disabled?: boolean;
  className?: string;
  ariaLabel?: string;
}) {
  const places = decimals ?? (step ? decimalsForStep(step) : 3);
  const [text, setText] = useState(() => String(value));
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) {
      setText(String(roundTo(value, places)));
    }
  }, [value, focused, places]);

  const commit = () => {
    const parsed = Number(text);
    let next = Number.isFinite(parsed) ? parsed : value;
    if (min !== undefined) {
      next = Math.max(next, min);
    }
    if (max !== undefined) {
      next = Math.min(next, max);
    }
    setFocused(false);
    setText(String(roundTo(next, places)));
    onChange(next);
  };

  return (
    <input
      type="text"
      inputMode="decimal"
      aria-label={ariaLabel}
      value={text}
      disabled={disabled}
      onChange={(event) => setText(event.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          commit();
          (event.target as HTMLInputElement).blur();
        }
      }}
      className={cx(
        "tnum h-7 rounded border border-line bg-surface px-1.5 text-right font-mono text-xs text-ink transition-colors hover:border-line-strong focus:border-accent disabled:bg-wash disabled:text-ink-faint",
        className,
      )}
    />
  );
}

export function SliderField({
  label,
  unit,
  value,
  min,
  max,
  step,
  onChange,
  disabled,
  hint,
  inputWidth = "w-[4.5rem]",
}: {
  label: string;
  unit?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  hint?: ReactNode;
  inputWidth?: string;
}) {
  return (
    <div className={cx(disabled && "opacity-60")}>
      <div className="flex items-baseline justify-between gap-2">
        <label className="text-xs font-medium text-ink-muted">{label}</label>
        <div className="flex items-baseline gap-1">
          <NumberInput
            value={value}
            min={min}
            max={max}
            step={step}
            disabled={disabled}
            onChange={onChange}
            ariaLabel={label}
            className={inputWidth}
          />
          {unit && <span className="w-7 text-2xs text-ink-faint">{unit}</span>}
        </div>
      </div>
      <SliderPrimitive.Root
        className="relative mt-2 flex h-4 w-full touch-none select-none items-center"
        value={[value]}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        onValueChange={([next]) => onChange(roundTo(next, decimalsForStep(step)))}
        aria-label={label}
      >
        <SliderPrimitive.Track className="relative h-[3px] grow rounded-full bg-line">
          <SliderPrimitive.Range className="absolute h-full rounded-full bg-accent" />
        </SliderPrimitive.Track>
        <SliderPrimitive.Thumb className="block h-3.5 w-3.5 rounded-full border border-accent-strong bg-control-thumb shadow-sm transition-transform hover:scale-110 focus-visible:scale-110 disabled:cursor-not-allowed" />
      </SliderPrimitive.Root>
      {hint && <div className="mt-1 text-2xs text-ink-muted">{hint}</div>}
    </div>
  );
}

export function SwitchField({
  label,
  description,
  checked,
  onCheckedChange,
  disabled,
}: {
  label: string;
  description?: ReactNode;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className={cx("flex items-start gap-3", disabled && "opacity-60")}>
      <SwitchPrimitive.Root
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
        className="relative mt-0.5 h-[18px] w-8 shrink-0 rounded-full border border-line-strong bg-wash transition-colors data-[state=checked]:border-accent data-[state=checked]:bg-accent disabled:cursor-not-allowed"
        aria-label={label}
      >
        <SwitchPrimitive.Thumb className="block h-3.5 w-3.5 translate-x-[1px] rounded-full bg-control-thumb shadow-sm transition-transform data-[state=checked]:translate-x-[14px]" />
      </SwitchPrimitive.Root>
      <div className="min-w-0">
        <div className="text-xs font-medium text-ink">{label}</div>
        {description && (
          <div className="mt-0.5 text-xs leading-relaxed text-ink-muted">
            {description}
          </div>
        )}
      </div>
    </div>
  );
}

export function ProgressBar({
  value,
  tone = "accent",
  className,
}: {
  value: number | null;
  tone?: "accent" | "success" | "danger";
  className?: string;
}) {
  const fill =
    tone === "success" ? "bg-success" : tone === "danger" ? "bg-danger" : "bg-accent";
  return (
    <div
      className={cx("h-1.5 w-full overflow-hidden rounded-full bg-line", className)}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value === null ? undefined : Math.round(value * 100)}
    >
      {value === null ? (
        <div className="h-full w-1/3 animate-shimmer rounded-full bg-[linear-gradient(90deg,transparent,var(--color-accent-strong),transparent)] bg-[length:200%_100%]" />
      ) : (
        <div
          className={cx("h-full rounded-full transition-[width] duration-500", fill)}
          style={{ width: `${Math.max(2, Math.min(100, value * 100))}%` }}
        />
      )}
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Icon name="loader" className={cx("h-4 w-4 animate-spin text-accent", className)} />;
}

export function Table({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("thin-scroll overflow-x-auto", className)}>
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  );
}

export function Th({
  children,
  align = "left",
  className,
}: {
  children?: ReactNode;
  align?: "left" | "right" | "center";
  className?: string;
}) {
  return (
    <th
      className={cx(
        "border-b border-line px-2 py-1.5 text-2xs font-medium uppercase tracking-wider text-ink-faint",
        align === "left" && "text-left",
        align === "right" && "text-right",
        align === "center" && "text-center",
        className,
      )}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  align = "left",
  mono,
  className,
}: {
  children?: ReactNode;
  align?: "left" | "right" | "center";
  mono?: boolean;
  className?: string;
}) {
  return (
    <td
      className={cx(
        "border-b border-line px-2 py-1.5 text-ink",
        align === "left" && "text-left",
        align === "right" && "text-right",
        align === "center" && "text-center",
        mono && "tnum font-mono",
        className,
      )}
    >
      {children}
    </td>
  );
}

export function Tooltip({
  label,
  children,
  side = "top",
}: {
  label: ReactNode;
  children: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
}) {
  return (
    <TooltipPrimitive.Root delayDuration={120}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className="z-[70] max-w-xs rounded border border-ink bg-ink px-2.5 py-1.5 text-xs leading-relaxed text-canvas shadow-overlay"
        >
          {label}
          <TooltipPrimitive.Arrow className="fill-ink" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

export function InfoTip({ children }: { children: ReactNode }) {
  return (
    <Tooltip label={children}>
      <button
        type="button"
        className="inline-flex text-ink-faint transition-colors hover:text-ink"
        aria-label="More information"
      >
        <Icon name="info" className="h-3.5 w-3.5" />
      </button>
    </Tooltip>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <div className="rounded border border-danger bg-danger-soft px-3 py-2 text-xs leading-relaxed text-danger">
      {children}
    </div>
  );
}

/**
 * A short, plain-language explanation block. Used on the evidence pages to
 * introduce technical content to readers without a modelling background.
 */
export function Callout({
  tone = "accent",
  title,
  icon = "info",
  children,
}: {
  tone?: "accent" | "warning" | "neutral";
  title?: ReactNode;
  icon?: IconName;
  children: ReactNode;
}) {
  return (
    <div
      className={cx(
        "flex gap-3 rounded border px-3.5 py-3",
        tone === "accent" && "border-accent-border bg-accent-soft",
        tone === "warning" && "border-warning bg-warning-soft",
        tone === "neutral" && "border-line bg-wash",
      )}
    >
      <Icon
        name={icon}
        className={cx(
          "mt-0.5 h-4 w-4 shrink-0",
          tone === "warning" ? "text-warning" : "text-accent-strong",
        )}
      />
      <div className="min-w-0">
        {title && <div className="text-xs font-semibold text-ink">{title}</div>}
        <div
          className={cx(
            "text-xs leading-relaxed text-ink-muted",
            title && "mt-0.5",
          )}
        >
          {children}
        </div>
      </div>
    </div>
  );
}

/** Progressive disclosure for the technical layer of a page. */
export function Disclosure({
  title,
  description,
  defaultOpen = false,
  children,
}: {
  title: ReactNode;
  description?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-start gap-2 rounded px-1.5 py-1.5 text-left transition-colors hover:bg-wash"
      >
        <Icon
          name={open ? "chevron-down" : "chevron-right"}
          className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-faint"
        />
        <span className="min-w-0">
          <span className="block text-xs font-medium text-ink">{title}</span>
          {description && (
            <span className="mt-0.5 block text-xs leading-relaxed text-ink-muted">
              {description}
            </span>
          )}
        </span>
      </button>
      {open && <div className="mt-2.5 pl-7">{children}</div>}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-2 py-6">
      <div className="text-sm font-medium text-ink">{title}</div>
      {description && (
        <div className="max-w-md text-xs leading-relaxed text-ink-muted">
          {description}
        </div>
      )}
      {action}
    </div>
  );
}

export function KeyValue({
  label,
  children,
  mono,
}: {
  label: ReactNode;
  children: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <span className="text-xs text-ink-muted">{label}</span>
      <span
        className={cx(
          "min-w-0 truncate text-right text-xs text-ink",
          mono && "tnum font-mono",
        )}
      >
        {children}
      </span>
    </div>
  );
}
