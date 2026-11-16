declare module "plotly.js-basic-dist-min" {
  const Plotly: {
    react: (
      element: HTMLElement,
      data: unknown[],
      layout?: Record<string, unknown>,
      config?: Record<string, unknown>,
    ) => Promise<unknown>;
    newPlot: (
      element: HTMLElement,
      data: unknown[],
      layout?: Record<string, unknown>,
      config?: Record<string, unknown>,
    ) => Promise<unknown>;
    purge: (element: HTMLElement) => void;
    relayout: (
      element: HTMLElement,
      layout: Record<string, unknown>,
    ) => Promise<unknown>;
  };
  export default Plotly;
}

declare module "plotly.js-gl3d-dist-min" {
  const Plotly: {
    react: (
      element: HTMLElement,
      data: unknown[],
      layout?: Record<string, unknown>,
      config?: Record<string, unknown>,
    ) => Promise<unknown>;
    newPlot: (
      element: HTMLElement,
      data: unknown[],
      layout?: Record<string, unknown>,
      config?: Record<string, unknown>,
    ) => Promise<unknown>;
    purge: (element: HTMLElement) => void;
    relayout: (
      element: HTMLElement,
      layout: Record<string, unknown>,
    ) => Promise<unknown>;
  };
  export default Plotly;
}
