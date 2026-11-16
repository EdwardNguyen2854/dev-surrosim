import { cx } from "../lib/cx";

/**
 * DesignKit icon sprite catalog. The vendored sprite lives in
 * `public/icons/icons.svg` and is the app's only icon source
 * (see DesignKit `assets/icons/README.md`).
 */
export type IconName =
  | "alert-triangle"
  | "arrow-down"
  | "arrow-left"
  | "arrow-right"
  | "arrow-up"
  | "book-open"
  | "calendar"
  | "check"
  | "check-circle"
  | "chevron-down"
  | "chevron-left"
  | "chevron-right"
  | "chevron-up"
  | "clock"
  | "close"
  | "copy"
  | "cpu"
  | "download"
  | "edit"
  | "external-link"
  | "file-text"
  | "folder"
  | "git-branch"
  | "grid"
  | "home"
  | "info"
  | "layers"
  | "loader"
  | "maximize"
  | "menu"
  | "minimize"
  | "minus"
  | "moon"
  | "more-horizontal"
  | "package"
  | "panel-chevron-left"
  | "panel-chevron-right"
  | "play"
  | "plus"
  | "plus-circle"
  | "rotate-ccw"
  | "search"
  | "server"
  | "settings"
  | "shield-alert"
  | "shield-check"
  | "sliders"
  | "sun"
  | "target"
  | "trash"
  | "upload"
  | "user"
  | "x-circle";

const SPRITE_URL = `${import.meta.env.BASE_URL}icons/icons.svg`;

export function Icon({
  name,
  className,
  title,
}: {
  name: IconName;
  className?: string;
  /** Accessible name. Omit for decorative icons that sit next to text. */
  title?: string;
}) {
  return (
    <svg
      className={cx("icon h-4 w-4", className)}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      role={title ? "img" : undefined}
      focusable="false"
    >
      <use href={`${SPRITE_URL}#dk-icon-${name}`} />
    </svg>
  );
}
