import { Link } from "react-router-dom";

import { Callout, Panel, PanelBody, PanelHeader } from "../../components/ui";
import type { ManualArticle } from "./model";

function DocLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link to={to} className="text-link hover:underline">
      {children}
    </Link>
  );
}

export const appExplorer: ManualArticle = {
  id: "app-explorer",
  to: "/manual/app-explorer",
  group: "app",
  title: "Using the Design Explorer",
  summary:
    "The home page: move a slider, watch the drawing and the prediction change, and read the confidence signal before you believe the numbers.",
  minutes: 5,
  body: (
    <>
      <Callout title="In plain words">
        The Design Explorer is a what-if machine. Pick a shape family, move the
        sliders, and the learned model answers in microseconds — with a
        confidence panel that says how much the answer deserves to be believed.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="How to read it"
          title="Left to right, top to bottom"
          description="The page is arranged in the order you should read it: inputs, geometry, trust, numbers."
        />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            <strong className="text-ink">Parameters (left).</strong> Shape-family
            chips switch the whole page to that geometry; the sliders below
            follow. A slider pinned to zero for a hole means "no hole" — the
            app reports the reduced model support for it. Material is fixed:
            steel, not a slider.
          </p>
          <p>
            <strong className="text-ink">Schematic (centre).</strong> A live
            drawing of the current geometry with the clamp and the load
            direction marked, so you can see what the numbers describe.
          </p>
          <p>
            <strong className="text-ink">Confidence panel (centre).</strong>{" "}
            Bounds check, distance from training data and ensemble disagreement,
            boiled down to one recommendation. Read this before the numbers —
            it tells you how far to lean on them. The logic is explained on the{" "}
            <DocLink to="/manual/trust">trust page</DocLink>.
          </p>
          <p>
            <strong className="text-ink">Predicted response (right).</strong>{" "}
            The three answers: how far it bends, the highest stress anywhere,
            and the stress at the weak spot. The small "+−%" under each value
            is the spread between ensemble members — a preview of the
            disagreement signal.
          </p>
          <p>
            <strong className="text-ink">Analytical beam comparison.</strong> A
            transparent textbook formula, side by side with the model. It
            ignores holes, fillets and shear, so a big gap is normal — it is a
            sanity reference, not a label or a competitor.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Behind the scenes" title="What happens when you drag a slider" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            Each change is sent to the server (slightly delayed, so dragging
            stays smooth) and answered by the trained ensemble: a few arithmetic
            passes, roughly ten microseconds of model time. The confidence
            checks run in the same request.
          </p>
          <p>
            The response also carries its provenance — which model registry
            answered, the dataset fingerprint, the git commit — shown in the
            right-hand column. Nothing is retrained when the app starts; the
            numbers come from the frozen registry shown on the Model page.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Next steps" title="When a prediction becomes a decision" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            Two buttons lead onward:{" "}
            <DocLink to="/manual/app-verify">FEA Verify</DocLink> solves the
            exact design with the real physics engine, and{" "}
            <DocLink to="/manual/app-field">Field Prediction</DocLink> draws the
            full stress or displacement picture.
          </p>
          <p className="text-2xs text-ink-faint">
            Open the page: the{" "}
            <DocLink to="/">Design Explorer</DocLink> always works on the design
            set in the Explorer, shared by every analysis page.
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};

export const appField: ManualArticle = {
  id: "app-field",
  to: "/manual/app-field",
  group: "app",
  title: "Using Field Prediction",
  summary:
    "A colour map of the whole part — where it bends and where stress gathers — produced by the graph neural network in seconds.",
  minutes: 4,
  body: (
    <>
      <Callout title="In plain words">
        The Explorer gives you three numbers. This page gives you the picture:
        a colour map across the whole shape, so you can see where stress
        concentrates and how the part actually deforms.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="How to read it"
          title="Run, watch, switch, read"
          description="Field prediction is a background job: the server builds a coarse mesh, runs the graph network, and returns every point's value."
        />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            <strong className="text-ink">Run.</strong> Press "Predict field".
            Progress and the server log stream in as the job works; a run takes
            a few seconds.
          </p>
          <p>
            <strong className="text-ink">Switch.</strong> The toggle chooses
            between Von Mises stress and displacement magnitude. The colour
            scale adapts to the predicted range; the legend shows the minimum
            and maximum.
          </p>
          <p>
            <strong className="text-ink">Read.</strong> Red means "high" on
            either map. On the stress map that is where the part is working
            hardest; on the displacement map it is where it moves most. The
            scalar summary reduces the picture back to the same three headline
            numbers as the Explorer.
          </p>
          <p>
            <strong className="text-ink">Compare.</strong> If the design
            changed after a prediction, the page warns you — the field belongs
            to the previous geometry. Re-run for the current one.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Behind the scenes" title="Messages between points" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            The server generates the coarse graph mesh used during training —
            far fewer nodes than a production solve — then runs several rounds
            of message passing: each point updates what it knows from its
            neighbours, so information travels across the whole part. The
            result is a value at every point, and that is what becomes the
            colour map.
          </p>
          <p className="text-2xs text-ink-faint">
            The model, its accuracy and its coarse-mesh caveat are documented on
            the <DocLink to="/model">Model page</DocLink>.
          </p>
        </PanelBody>
      </Panel>

      <Callout tone="warning" title="Use the picture, not the peak">
        The field model is for patterns, not final numbers. For peak values read
        the scalar ensemble and verify with a real solve — the peak stresses of
        a coarse mesh are exactly where the two disagree most.
      </Callout>
    </>
  ),
};

export const appVerify: ManualArticle = {
  id: "app-verify",
  to: "/manual/app-verify",
  group: "app",
  title: "Using FEA Verify",
  summary:
    "The ground-truth button: solve the current design with the real physics engine, then compare it with the surrogate side by side.",
  minutes: 5,
  body: (
    <>
      <Callout title="In plain words">
        Everything else in the app is a fast estimate. This page is the real
        thing: it sends the current design through the same pipeline that built
        the training data — mesh, solver, extraction — and puts the honest
        answer next to the surrogate's guess.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="How to read it"
          title="Run, watch the log, read the table"
          description="The solver runs as a background job, so the app stays responsive while it works."
        />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            <strong className="text-ink">Run.</strong> Press "Run CalculiX
            verification". The job streams its stages and log: mesh generation,
            solver execution, result extraction.
          </p>
          <p>
            <strong className="text-ink">Read the comparison.</strong> Each row
            holds the surrogate value, the solver value and the error between
            them. Errors are colour-coded: below 5% green, 5–10% amber, above
            10% red. The solver column is the reference; the error is what you
            are judging.
          </p>
          <p>
            <strong className="text-ink">Check the run details.</strong> Mesh
            nodes, element count, element type, solver runtime and surrogate
            latency appear under the table — the same scale comparison that
            makes the surrogate worth having (seconds versus microseconds).
          </p>
          <p>
            <strong className="text-ink">Cached vs fresh.</strong> A design that
            was already solved is reused instantly; the chip says so. Turn on
            "Force re-run" to solve it again from scratch.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Behind the scenes" title="The production pipeline, one click away" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            The job builds the production mesh for the current shape family —
            quadratic tetrahedra, refined around holes and rounded corners —
            writes the solver deck, runs CalculiX in a worker process, then
            parses displacement and stress from the result files. The full
            pipeline is explained on the{" "}
            <DocLink to="/solver">Solver page</DocLink>.
          </p>
          <p>
            If CalculiX is not installed on the machine, the button is disabled
            and the page explains how to enable it.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="When to use it" title="The verification habit" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            Before any decision that matters: when the confidence panel says
            caution or run FEA, when the design sits at the edge of the trained
            range, when an optimisation finalist needs confirming, or simply
            when a number surprises you. Verification is cheap here — a few
            seconds — and it turns an approximation into measured evidence.
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};

export const appOptimize: ManualArticle = {
  id: "app-optimize",
  to: "/manual/app-optimize",
  group: "app",
  title: "Using Optimization",
  summary:
    "Search for the lightest design that still passes the stress and displacement limits — with the finalists checked by the real solver.",
  minutes: 5,
  body: (
    <>
      <Callout title="In plain words">
        Optimization answers one question: among all allowed designs, which is
        the lightest one that still keeps stress and bending under the limits
        you set? The surrogate does the searching because thousands of
        evaluations are needed; the real solver checks the finalists because
        the answer has to be true.
      </Callout>

      <Panel>
        <PanelHeader kicker="The problem" title="Fixed conditions, free dimensions" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            Length, force, material and the two limits are set by you at the
            top. The optimizer then moves the four free variables — width,
            thickness, hole ratio, hole position — and minimises mass{" "}
            <em>while</em> keeping peak stress below the allowed stress and
            deflection below the displacement limit.
          </p>
          <p>
            A design that violates a limit is not rejected outright; it is
            penalised in proportion to the square of the violation, which
            gently steers the search back toward feasibility.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Behind the scenes"
          title="A population of guesses that evolves"
          description="The method is differential evolution — a well-known search technique that needs no gradients and tolerates a rough objective landscape."
        />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            Start with a population of random designs. Score each one on the
            surrogate. Then repeatedly create new candidates by mixing the best
            designs with each other, keep whichever improves the score, and
            repeat for many generations. Thousands of evaluations happen in
            seconds — impossible if each one needed a real solve.
          </p>
          <p>
            When the search finishes, the lowest-mass feasible candidates are
            de-duplicated and ranked. If candidate verification is on, each
            finalist is solved with CalculiX and the table gains FEA columns:
            the solver's stress, its error against the prediction, and whether
            the design still passes.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="How to read it" title="One picture and one table" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            <strong className="text-ink">All evaluations</strong> plots mass
            against predicted peak stress for every design the optimizer tried.
            The star markers are the winning candidates, sitting at the
            low-mass edge of the feasible region.
          </p>
          <p>
            <strong className="text-ink">Best feasible mass</strong> shows the
            search improving over time — the running record.
          </p>
          <p>
            <strong className="text-ink">Candidate designs</strong> lists the
            finalists with predicted values, and with verified values when
            verification ran. A verified candidate whose solver stress is below
            the limit is the real deliverable.
          </p>
        </PanelBody>
      </Panel>

      <Callout tone="warning" title="Limits are not safety factors">
        The stress limit and displacement limit are numbers you type in. A
        verified candidate sitting at 99% of a limit is feasible on paper — add
        your own engineering safety margin before treating it as design advice.
      </Callout>
    </>
  ),
};
