import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import { formatFixed } from "../lib/format";
import { Icon } from "./Icon";
import { Button, Chip, ErrorNote, Panel, PanelBody, PanelHeader, cx } from "./ui";
import { PLOT_FONT, PlotlyPlot } from "./Plotly";

const FEA_COLORSCALE: [number, string][] = [
  [0.0, "#1B2A6B"],
  [0.2, "#1F6FB2"],
  [0.4, "#2FA5A0"],
  [0.6, "#A8C93A"],
  [0.8, "#F2A03D"],
  [1.0, "#C22B1F"],
];

export function FieldViewer({
  jobId,
  field,
  title,
  height = 380,
}: {
  jobId: string;
  field: string;
  title: string;
  height?: number;
}) {
  const [viewKey, setViewKey] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const panelRef = useRef<HTMLElement | null>(null);
  const query = useQuery({
    queryKey: ["field", jobId, field],
    queryFn: () => api.field(jobId, field),
    staleTime: Infinity,
  });
  const payload = query.data;

  useEffect(() => {
    const panel = panelRef.current;
    const onChange = () => setFullscreen(document.fullscreenElement === panel);
    document.addEventListener("fullscreenchange", onChange);
    return () => {
      document.removeEventListener("fullscreenchange", onChange);
      if (panel && document.fullscreenElement === panel) {
        void document.exitFullscreen();
      }
    };
  }, []);

  const toggleFullscreen = useCallback(() => {
    const panel = panelRef.current;
    if (!panel) {
      return;
    }
    if (document.fullscreenElement === panel) {
      void document.exitFullscreen();
    } else {
      void panel.requestFullscreen().catch(() => undefined);
    }
  }, []);

  const data = useMemo(() => {
    if (!payload) {
      return [];
    }
    return [
      {
        type: "mesh3d",
        x: payload.vertices.map((vertex) => vertex[0]),
        y: payload.vertices.map((vertex) => vertex[1]),
        z: payload.vertices.map((vertex) => vertex[2]),
        i: payload.faces.map((face) => face[0]),
        j: payload.faces.map((face) => face[1]),
        k: payload.faces.map((face) => face[2]),
        intensity: payload.intensity,
        intensitymode: payload.intensity_mode ?? "vertex",
        colorscale: FEA_COLORSCALE,
        cmin: payload.min,
        cmax: payload.max,
        flatshading: false,
        lighting: { ambient: 0.55, diffuse: 0.9, specular: 0.08, roughness: 0.85 },
        colorbar: {
          title: { text: payload.unit, side: "right" },
          thickness: 11,
          len: 0.74,
          outlinewidth: 0,
          tickfont: { ...PLOT_FONT, size: 10 },
        },
        hovertemplate: `${payload.label}: %{intensity:.4g} ${payload.unit}<extra></extra>`,
      },
    ];
  }, [payload]);

  const layout = useMemo<Record<string, unknown>>(
    () => ({
      paper_bgcolor: "rgba(0,0,0,0)",
      margin: { l: 0, r: 0, t: 8, b: 0 },
      font: PLOT_FONT,
      showlegend: false,
      scene: {
        bgcolor: "var(--color-surface-default)",
        aspectmode: "data",
        camera: { eye: { x: 1.55, y: -1.15, z: 1.2 }, up: { x: 0, y: 0, z: 1 } },
        xaxis: { title: "x (mm)", gridcolor: "var(--color-border-default)", zerolinecolor: "var(--color-border-hover)", backgroundcolor: "var(--color-surface-default)" },
        yaxis: { title: "y (mm)", gridcolor: "var(--color-border-default)", zerolinecolor: "var(--color-border-hover)", backgroundcolor: "var(--color-surface-default)" },
        zaxis: { title: "z (mm)", gridcolor: "var(--color-border-default)", zerolinecolor: "var(--color-border-hover)", backgroundcolor: "var(--color-surface-default)" },
      },
      hoverlabel: {
        bgcolor: "var(--color-text-primary)", bordercolor: "var(--color-text-primary)",
        font: { ...PLOT_FONT, color: "var(--color-surface-canvas)" },
      },
    }),
    [],
  );

  return (
    <Panel
      ref={panelRef}
      className={cx(fullscreen && "flex h-full w-full flex-col rounded-none border-0")}
    >
      <PanelHeader
        kicker="Field viewer"
        title={title}
        actions={
          <>
            {payload && (
              <span className="tnum font-mono text-2xs text-ink-faint">
                {formatFixed(payload.min, 3)} – {formatFixed(payload.max, 3)}{" "}
                {payload.unit}
              </span>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={toggleFullscreen}
              disabled={!payload}
              aria-label={fullscreen ? "Exit full screen" : "Enter full screen"}
            >
              {fullscreen ? (
                <Icon name="minimize" className="h-3.5 w-3.5" />
              ) : (
                <Icon name="maximize" className="h-3.5 w-3.5" />
              )}
              {fullscreen ? "Exit" : "Full screen"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setViewKey((current) => current + 1)}
              disabled={!payload}
            >
              <Icon name="rotate-ccw" className="h-3.5 w-3.5" />
              Reset view
            </Button>
          </>
        }
      />
      <PanelBody
        className={cx("pt-3", fullscreen && "flex min-h-0 flex-1 flex-col")}
      >
        {query.isLoading && (
          <div
            className={cx(
              "grid-paper animate-pulse rounded border border-line bg-wash",
              fullscreen && "min-h-0 flex-1",
            )}
            style={{ height: fullscreen ? "100%" : height }}
          />
        )}
        {query.error && (
          <ErrorNote>
            Field data unavailable: {String(query.error)}
          </ErrorNote>
        )}
        {payload && (
          <PlotlyPlot
            key={`${viewKey}-${fullscreen ? "fullscreen" : "inline"}`}
            engine="gl3d"
            navigation="creo"
            data={data}
            layout={layout}
            height={fullscreen ? "100%" : height}
            className={fullscreen ? "min-h-0 flex-1" : undefined}
          />
        )}
        {payload && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Chip tone="neutral">
              {payload.vertices.length.toLocaleString()} vertices
            </Chip>
            <Chip tone="neutral">
              {payload.faces.length.toLocaleString()} surface faces
            </Chip>
            <span className="text-2xs text-ink-muted">
              Middle-drag to orbit, Shift+middle-drag to pan, Ctrl+middle-drag or
              wheel to zoom; color maps the nodal {payload.label.toLowerCase()}.
            </span>
          </div>
        )}
      </PanelBody>
    </Panel>
  );
}
