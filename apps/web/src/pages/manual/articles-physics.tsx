import { Link } from "react-router-dom";

import { Chain, Steps } from "../../components/content";
import { Callout, Panel, PanelBody, PanelHeader, Table, Td, Th } from "../../components/ui";
import type { ManualArticle } from "./model";

function DocLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link to={to} className="text-link hover:underline">
      {children}
    </Link>
  );
}

const SHAPE_FAMILIES = [
  {
    name: "Plate with hole",
    look: "A flat rectangular bar with one round hole.",
    interest:
      "Stress gathers at the hole edge. It is the classic textbook case and was the project's first shape.",
  },
  {
    name: "Two-hole plate",
    look: "Two holes arranged along the length of the plate.",
    interest:
      "Close holes affect each other's stress fields, so the weak spot can move between them.",
  },
  {
    name: "Tapered plate",
    look: "Wide where it is clamped, narrower toward the free end.",
    interest:
      "Removes material where bending demand is low — a simple weight-saving idea.",
  },
  {
    name: "Stepped plate",
    look: "A full-thickness section that steps down to a thinner one.",
    interest:
      "The rounded inner corner is the weak spot; the step changes stiffness along the part.",
  },
  {
    name: "I-beam",
    look: "The classic structural profile in miniature: flanges plus a thin web.",
    interest:
      "Bending stiffness from little material — the shape bridges are made from.",
  },
  {
    name: "L-bracket",
    look: "An angle bracket instead of a straight bar.",
    interest:
      "The load path turns a corner through the inner fillet, which becomes the weak spot.",
  },
];

export const designSpace: ManualArticle = {
  id: "design-space",
  to: "/manual/design-space",
  group: "physics",
  title: "What can be designed here",
  summary:
    "The six cantilever shape families, the numbers that describe them, and the three answers the system predicts.",
  minutes: 6,
  body: (
    <>
      <Callout title="In plain words">
        Everything in SurroSim is a cantilever: think of a shelf bracket bolted
        to a wall, with a weight hanging on the free end. Six versions of that
        idea are in scope. Each has a handful of dimensions you can change, and
        each is judged by the same three questions: how far does it bend, how
        stressed does it get anywhere, and how stressed does it get at its weak
        spot?
      </Callout>

      <Panel>
        <PanelHeader
          kicker="Coverage"
          title="The six shape families"
          description="Every trained model and every prediction is conditioned on exactly this set. Anything outside it is out of scope by design."
        />
        <PanelBody>
          <Table>
            <thead>
              <tr>
                <Th>Family</Th>
                <Th>What it looks like</Th>
                <Th>What makes it interesting</Th>
              </tr>
            </thead>
            <tbody>
              {SHAPE_FAMILIES.map((shape) => (
                <tr key={shape.name}>
                  <Td>
                    <span className="font-medium text-ink">{shape.name}</span>
                  </Td>
                  <Td className="max-w-[16rem] text-ink-muted">{shape.look}</Td>
                  <Td className="max-w-[22rem] text-ink-muted">
                    {shape.interest}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Inputs"
          title="The numbers you can change"
          description="Each family exposes only the dimensions that make sense for it. The table shows the plainest family — the plate with a hole."
        />
        <PanelBody className="space-y-3">
          <Table>
            <thead>
              <tr>
                <Th>Quantity</Th>
                <Th>Symbol</Th>
                <Th align="right">Typical range</Th>
                <Th>In plain words</Th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <Td>Length</Td>
                <Td mono>L</Td>
                <Td align="right" mono>
                  100–160 mm
                </Td>
                <Td className="text-ink-muted">How far the part reaches from the wall.</Td>
              </tr>
              <tr>
                <Td>Width</Td>
                <Td mono>W</Td>
                <Td align="right" mono>
                  30–60 mm
                </Td>
                <Td className="text-ink-muted">
                  The in-plane dimension across the load direction.
                </Td>
              </tr>
              <tr>
                <Td>Thickness</Td>
                <Td mono>T</Td>
                <Td align="right" mono>
                  4–10 mm
                </Td>
                <Td className="text-ink-muted">
                  The bending stiffness driver — and the mesh sizing driver.
                </Td>
              </tr>
              <tr>
                <Td>Hole diameter ratio</Td>
                <Td mono>d/W</Td>
                <Td align="right" mono>
                  0.20–0.45
                </Td>
                <Td className="text-ink-muted">
                  Hole size relative to width; 0 means no hole.
                </Td>
              </tr>
              <tr>
                <Td>Hole position ratio</Td>
                <Td mono>x/L</Td>
                <Td align="right" mono>
                  0.35–0.65
                </Td>
                <Td className="text-ink-muted">
                  Where the hole sits along the length, measured from the wall.
                </Td>
              </tr>
              <tr>
                <Td>Total force</Td>
                <Td mono>F</Td>
                <Td align="right" mono>
                  100–800 N
                </Td>
                <Td className="text-ink-muted">
                  The push at the free end, spread across the end face.
                </Td>
              </tr>
            </tbody>
          </Table>
          <p className="text-2xs leading-relaxed text-ink-faint">
            The material is fixed, not a slider: steel with a stiffness
            (Young's modulus) of 210,000 MPa and a sideways-squeeze ratio
            (Poisson's ratio) of 0.30. The{" "}
            <DocLink to="/dataset">Dataset page</DocLink> lists the exact range
            observed for every quantity in the live dataset, per shape family.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Outputs"
          title="The three answers — and a picture"
          description="These are the quantities the real solver computes and the models learn to reproduce."
        />
        <PanelBody>
          <Table>
            <thead>
              <tr>
                <Th>Answer</Th>
                <Th align="right">Unit</Th>
                <Th>What it tells you</Th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <Td>Max displacement</Td>
                <Td align="right" mono>
                  mm
                </Td>
                <Td className="text-ink-muted">
                  How far the free end moves. The "is it stiff enough?" number.
                </Td>
              </tr>
              <tr>
                <Td>Global max Von Mises stress</Td>
                <Td align="right" mono>
                  MPa
                </Td>
                <Td className="text-ink-muted">
                  The single highest stress anywhere in the part — the number a
                  strength check reads.
                </Td>
              </tr>
              <tr>
                <Td>Weak-spot (ROI) stress</Td>
                <Td align="right" mono>
                  MPa
                </Td>
                <Td className="text-ink-muted">
                  The highest stress around the hole or rounded corner, where
                  cracks usually start. Empty for shapes without a weak spot.
                </Td>
              </tr>
              <tr>
                <Td>Full field</Td>
                <Td align="right" mono>
                  every node
                </Td>
                <Td className="text-ink-muted">
                  Movement and stress at every mesh point — the raw material for
                  the colour maps and the picture model.
                </Td>
              </tr>
            </tbody>
          </Table>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Assumptions"
          title="The physics that is (and is not) in force"
          description="Every number in the app inherits these choices. They are the reason predictions need engineering judgement."
        />
        <PanelBody className="space-y-3">
          <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                <strong className="text-ink">Linear elastic.</strong> Twice the
                load means twice the movement, and the part springs back when
                unloaded. Real metals stop behaving this way past their yield
                limit.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                <strong className="text-ink">Static.</strong> One load,
                applied slowly. No vibration, impact or fatigue.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                <strong className="text-ink">One material, one load case.</strong>{" "}
                Steel, a single transverse force at the free end, fully clamped
                at the base.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                <strong className="text-ink">Fillets, not sharp corners.</strong>{" "}
                Stepped, I-beam and L-bracket shapes are rounded at re-entrant
                corners so the stress stays finite. Sharp inner corners are
                deliberately out of scope.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                <strong className="text-ink">Above yield, "what-if".</strong>{" "}
                Many dataset cases exceed the yield strength of steel as
                linear-elastic solutions. Those are real solver outputs under
                the elasticity assumption — not what a physical part would do.
                The <DocLink to="/manual/limitations">limits page</DocLink> is
                explicit about this.
              </span>
            </li>
          </ul>
          <p className="border-t border-line pt-3 text-2xs leading-relaxed text-ink-faint">
            The physics itself — mesh, load application, solver and validation —
            is explained on the <DocLink to="/solver">Solver page</DocLink>.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Try it" title="Bring your own numbers" />
        <PanelBody className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <p>
            The <DocLink to="/">Design Explorer</DocLink> turns these sliders
            into a live schematic and an instant prediction, with the
            confidence panel right underneath. Change the shape family and the
            parameter set follows you.
          </p>
          <p>
            If a value leaves the trained range, the app will not pretend to
            know the answer — it flags the design and points you at the real
            solver instead.
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};

export const groundTruth: ManualArticle = {
  id: "ground-truth",
  to: "/manual/ground-truth",
  group: "physics",
  title: "Where the training answers come from",
  summary:
    "The six-step factory that turns design numbers into trusted solved examples, and the gates that reject everything else.",
  minutes: 6,
  body: (
    <>
      <Callout title="In plain words">
        A learned model can only be as good as its study material. This page is
        the factory that produced that material: how designs were chosen, how
        each was solved with the real physics engine, and the checks that let a
        solved case become teaching material. Nothing in the dataset was
        estimated.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="How it was made"
          title="Six steps from parameters to a solved case"
          description="Every case in the dataset went through the same pipeline. The current build holds around 2,800 cases across the six families; the Dataset page shows the exact live counts."
        />
        <PanelBody>
          <Steps
            items={[
              {
                title: "Pick a design",
                body: "A sampling routine spreads parameter combinations across the whole allowed range, then adds explicitly awkward corner cases. The list — and the division into training, validation, test and challenge groups — is frozen before any solving starts, so nothing can be tuned after the fact.",
              },
              {
                title: "Build the shape",
                body: "The numbers become real 3D geometry with the free program Gmsh: plate with hole, two-hole plate, tapered plate, stepped plate, I-beam or L-bracket, including rounded corners where the physics needs them.",
              },
              {
                title: "Cut it into a mesh",
                body: "The solid is divided into quadratic tetrahedra (CalculiX name C3D10) so bending is computed accurately. Holes and corners are refined where stress changes fastest; elsewhere the mesh is coarser to keep the solve affordable.",
              },
              {
                title: "Solve it for real",
                body: "CalculiX clamps the base, spreads the requested total force across the free-end face and solves the static physics. Median cost: about ten seconds per case — roughly eleven hours of pure computing across the full dataset.",
              },
              {
                title: "Record the answers",
                body: "Each case keeps the three headline values plus a full-field file: displacement and stress at every mesh point. Those files are the raw material the picture model learns from.",
              },
              {
                title: "Pass the gates",
                body: "Only after every quality check passes does a case join the dataset. A failure is written to a rejection log and never becomes training material.",
              },
            ]}
          />
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Quality"
          title="The gates: nothing gets in by accident"
          description="These are the checks behind the claim 'every label is a completed, physical simulation'."
        />
        <PanelBody className="space-y-3">
          <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
            {[
              {
                plain: "The solver must report a clean finish.",
                code: "solver status == SUCCESS",
              },
              {
                plain:
                  "The load actually applied must equal the load that was requested — meshing must never change the total force.",
                code: "deck total force matches requested force",
              },
              {
                plain:
                  "The mesh must be fine enough (at least 500 nodes) for the answer to mean anything.",
                code: "mesh nodes >= 500",
              },
              {
                plain:
                  "The full-field result file must exist, so the field model has something to learn from.",
                code: "fields.npz present",
              },
              {
                plain:
                  "Displacement and stress must be real, finite, positive numbers — no zeros, no infinities.",
                code: "displacement and global stress finite and positive",
              },
              {
                plain:
                  "Where the shape defines a weak spot, its stress must be valid too.",
                code: "ROI stress finite and positive when defined",
              },
            ].map((gate) => (
              <li key={gate.code} className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  {gate.plain}
                  <span className="ml-2 font-mono text-2xs text-ink-faint">
                    {gate.code}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Splits"
          title="Four piles, fixed before training"
          description="The dataset is divided once, before any model sees it, and the division never changes. That is what makes the accuracy numbers honest."
        />
        <PanelBody>
          <Table>
            <thead>
              <tr>
                <Th>Pile</Th>
                <Th>What it is for</Th>
                <Th>The school equivalent</Th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Training</span>
                </Td>
                <Td className="text-ink-muted">
                  The cases the models actually learn from.
                </Td>
                <Td className="text-ink-muted">Study material.</Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Validation</span>
                </Td>
                <Td className="text-ink-muted">
                  Used to choose between competing model designs.
                </Td>
                <Td className="text-ink-muted">A practice exam.</Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Test</span>
                </Td>
                <Td className="text-ink-muted">
                  Untouched until the model was frozen, then checked once.
                </Td>
                <Td className="text-ink-muted">The final exam.</Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Challenge</span>
                </Td>
                <Td className="text-ink-muted">
                  The awkward corners of the range — never used for tuning.
                </Td>
                <Td className="text-ink-muted">Trick questions on purpose.</Td>
              </tr>
            </tbody>
          </Table>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Provenance"
          title="The chain of custody"
          description="Any label can be walked back from the dataset to the exact mesh and solver log that produced it."
        />
        <PanelBody className="space-y-3">
          <Chain
            lines={[
              "dataset row",
              "  └─ per-case run.json     (mesh policy, deck summary, solver status, runtime)",
              "       └─ geometry metadata  (element order, refinement, mesh quality)",
              "            └─ fields.npz      (displacement and stress at every node)",
            ]}
          />
          <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              The design table, the dataset and every model registry record a
              SHA-256 content fingerprint and the git commit of the run that
              made them.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              If a dataset changes, every model trained on it becomes invalid
              by hash mismatch — retraining is forced rather than assumed.
            </li>
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Why the effort" title="A model cannot outgrow its examples" />
        <PanelBody className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <p>
            A wrong answer that slips into training data teaches the model a
            wrong pattern — silently, because there is no label to argue with.
            That is why failed simulations never enter a dataset, why every
            case is fingerprinted, and why the test and challenge piles are
            locked away until after the models are final.
          </p>
          <p className="border-t border-line pt-3">
            The physics inside a solve is explained on the{" "}
            <DocLink to="/solver">Solver page</DocLink>; the live dataset
            contents, ranges and gates are on the{" "}
            <DocLink to="/dataset">Dataset page</DocLink>.
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};
