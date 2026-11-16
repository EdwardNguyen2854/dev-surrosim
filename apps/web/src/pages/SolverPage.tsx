import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Chain, Steps, Terms } from "../components/content";
import { Icon } from "../components/Icon";
import {
  Button,
  Callout,
  Chip,
  Disclosure,
  Panel,
  PanelBody,
  PanelHeader,
  Stat,
  Table,
  Td,
  Th,
} from "../components/ui";
import { api } from "../lib/api";
import { formatSeconds } from "../lib/format";
import { useDesign } from "../state/design";
import { ManualFooterNav, ManualLayout } from "./manual/ManualLayout";
import { manualNeighbours } from "./manual/registry";

/*
 * The dedicated reference page for the real solver (CalculiX). Layer order is
 * the evidence-page convention: plain language first, the process and the
 * validation numbers second, deeper disclosures last, so a non-technical
 * reader can stop early and a reviewer can keep going.
 */

function hoursFromSeconds(seconds?: number | null): string {
  if (!seconds || !Number.isFinite(seconds)) {
    return "n/a";
  }
  return `${(seconds / 3600).toFixed(1)} h`;
}

export function SolverPage() {
  const { config } = useDesign();
  const dataset = useQuery({
    queryKey: ["dataset-report"],
    queryFn: api.datasetReport,
    staleTime: Infinity,
  });

  const data = dataset.data;
  const versions = data?.manifest?.solver?.versions ?? [];
  const calculixReady = config?.capabilities.calculix ?? false;
  const medianSolve = data?.median_runtime_seconds ?? null;
  const nodes = data?.mesh?.median_nodes ?? null;
  const elements = data?.mesh?.median_elements ?? null;
  const elementType = data?.mesh?.element_type ?? null;
  const cases = data?.manifest?.cases_in_dataset ?? data?.row_count ?? null;
  const failed = data?.manifest?.cases_failed ?? null;
  const totalSeconds = data?.manifest?.solver?.total_solver_seconds ?? null;
  const unknowns = nodes !== null ? nodes * 3 : null;
  const { previous, next } = manualNeighbours("solver");

  return (
    <ManualLayout
      kicker="Documentation · The physics side"
      title="The solver"
      description="The physics engine behind every answer in SurroSim: what a finite-element solve actually does, and why its results can carry the weight the models put on them."
      actions={
        <Chip tone={calculixReady ? "success" : "danger"}>
          {calculixReady
            ? versions.length
              ? `CalculiX ${versions.join(", ")}`
              : "CalculiX ready"
            : "No CalculiX found"}
        </Chip>
      }
    >
      <Callout title="In plain words">
        SurroSim answers in milliseconds because it memorised the answers to
        much slower questions. Those questions were answered by CalculiX, a
        real finite-element solver. This page is the story of what happens
        inside it: how a shape becomes a mesh, how the load and the support
        become instructions, how thousands of equations are solved at once, and
        how every answer was checked before it was allowed to teach the models.
        When the app says "run FEA", this is what runs.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="At a glance"
          title="The engine, as configured right now"
          description="Numbers pulled live from the running service: the solver the app will use, and the work it already did to build the training data."
        />
        <PanelBody className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
          <Stat
            label="Engine"
            value={
              versions.length ? `CalculiX ${versions.join(", ")}` : "CalculiX"
            }
            sub="finite-element solver"
          />
          <Stat
            label="Status"
            value={calculixReady ? "Ready" : "Not found"}
            tone={calculixReady ? "success" : "danger"}
            sub="on this machine"
          />
          <Stat
            label="Typical solve"
            value={formatSeconds(medianSolve)}
            sub="per case, median"
          />
          <Stat
            label="Mesh per case"
            value={nodes !== null ? nodes.toLocaleString() : "n/a"}
            sub={
              elements !== null
                ? `${elements.toLocaleString()} elements · ${elementType ?? ""}`
                : "median nodes"
            }
          />
          <Stat
            label="Cases produced"
            value={cases !== null ? cases.toLocaleString() : "n/a"}
            sub={
              failed !== null
                ? `${failed.toLocaleString()} rejected by the gates`
                : "all passed the gates"
            }
          />
          <Stat
            label="Solver compute"
            value={hoursFromSeconds(totalSeconds)}
            sub="total across the dataset"
          />
        </PanelBody>
      </Panel>

      {!calculixReady && (
        <Callout tone="warning" title="CalculiX is not available on this machine">
          The live numbers above and the validation evidence below still
          describe the engine that produced the dataset, but the FEA Verify page
          cannot run. To enable it, place <code>ccx</code> in{" "}
          <code>tools/calculix/</code>, install CalculiX on the system PATH, or
          set the <code>SURROSIM_CCX</code> environment variable.
        </Callout>
      )}

      <Panel>
        <PanelHeader
          kicker="The big idea"
          title="Divide and conquer: finite-element analysis without equations"
          description="FEA (finite-element analysis) is the branch of computing that solves physics on a shape by cutting the shape into small pieces. The concept is simpler than the name."
        />
        <PanelBody className="space-y-4">
          <Steps
            items={[
              {
                title: "A smooth shape has infinitely many points",
                body: "Nobody can compute the stress at every single point of a continuous solid — there are too many. So the first move is always the same: approximate the solid with a finite number of points.",
              },
              {
                title: "Cut it into small pieces",
                body: "The shape is divided into simple solids — here tetrahedra, small pyramid-like pieces. They meet at shared points called nodes, and the collection is called the mesh.",
              },
              {
                title: "Give every piece one simple rule",
                body: "Each piece behaves like a tiny spring: stretch it, and the force it pulls back with is proportional to how far it stretched. That single rule is Hooke's law, and it is the only material behaviour the calculation needs.",
              },
              {
                title: "Make the pieces agree with each other",
                body: "Where pieces share a node, they must move together, and at every node the forces must balance. Writing those conditions for every node turns the whole part into one large system of equations.",
              },
              {
                title: "Solve everything at once",
                body: "The computer finds the one set of movements that satisfies all the equations simultaneously. From those movements it computes the stress in every piece. That is the entire calculation — everything else is bookkeeping.",
              },
            ]}
          />
          <div className="rounded border border-line bg-wash px-3.5 py-3">
            <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
              The whole solve, in one line
            </div>
            <div className="mt-1.5 font-mono text-sm text-ink">
              stiffness × movement = force
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">
              The solver's job is to find the movement that balances the applied
              force, given how stiff the part is. Everything that makes a real
              analysis slow comes from the size of that system, not from
              conceptual complexity.
            </p>
          </div>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Step by step"
          title="Inside one solve"
          description="What actually happens between 'a design' and 'an answer', using the pipeline that built the dataset and that the FEA Verify page runs on demand."
        />
        <PanelBody>
          <Steps
            items={[
              {
                icon: "package",
                title: "Numbers become a shape",
                body: "Gmsh builds the exact 3D solid from the design values: hole or holes, taper, step, flanges, rounded corners. Named faces are attached for the clamp, the load and every stress-riser surface, so the next steps know where things are.",
              },
              {
                icon: "grid",
                title: "The shape becomes a mesh",
                body: "The solid is cut into quadratic tetrahedra — CalculiX name C3D10, ten nodes per piece, capable of bending correctly. In this dataset the meshes run from thousands to tens of thousands of nodes (the live median is in the panel above). Holes and rounded corners are refined because stress changes fastest there; the rest stays coarse to keep the solve affordable.",
              },
              {
                icon: "layers",
                title: "The load case is written down",
                body: "The clamped face is fully held. The requested total force is spread across the free-end face as consistent nodal loads, so refining the mesh never changes the total force. Material: steel. Outputs requested: displacement and stress at every node.",
              },
              {
                icon: "cpu",
                title: "The equations are solved",
                body: "Every element contributes its stiffness; the solver assembles one large system — stiffness × movement = force — and solves it for every allowed movement at once. Linear-elastic means one pass, no iteration: push twice as hard and every answer exactly doubles.",
              },
              {
                icon: "file-text",
                title: "The answer is read out",
                body: "Displacement at every node; the six stress components combined into Von Mises stress; the peak values extracted as the three headline answers. The full field is saved as well — it is what the picture model later learned from.",
              },
              {
                icon: "shield-check",
                title: "The answer is checked",
                body: "Six gates decide whether the case may train a model: clean solver finish, exact force balance, enough mesh nodes, the field file present, finite positive displacement and stress, and a valid weak-spot value wherever the shape defines one. Anything failing is logged and excluded.",
              },
            ]}
          />
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Behind the scenes"
          title="The details a reviewer would ask for"
          description="Three disclosures: the solver deck, the mesh policy, and the one equation every solve is built on."
        />
        <PanelBody className="space-y-1">
          <Disclosure
            title="The deck: the exact instructions CalculiX receives"
            description="One text file turns a geometry into a solvable problem."
          >
            <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
              <li className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  <strong className="text-ink">Support:</strong> every node on
                  the clamped face has all three movements locked, so the base
                  cannot translate or rotate.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  <strong className="text-ink">Load:</strong> the requested
                  total force is distributed over the free-end face with
                  consistent nodal loads — a finer mesh spreads the same total
                  over more nodes, so the applied force never changes with mesh
                  refinement.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  <strong className="text-ink">Material:</strong> steel with
                  Young's modulus 210,000 MPa and Poisson's ratio 0.30, fixed by
                  the dataset.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  <strong className="text-ink">Weak-spot window (ROI):</strong>{" "}
                  a region of 1.5 × the hole diameter around the hole, with the
                  first 10% of the length excluded so the clamp's local effect
                  cannot contaminate it.
                </span>
              </li>
            </ul>
          </Disclosure>

          <Disclosure
            title="The mesh policy: where the mesh is fine, and why"
            description="Refining everything would multiply solve time for almost no gain, so only the stress-risers are graded."
          >
            <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
              <li className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  <strong className="text-ink">Global size:</strong> the smaller
                  of 3.0 mm and half the part's characteristic thickness.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  <strong className="text-ink">Holes:</strong> refined to the
                  smaller of 0.6 × the global size and one tenth of the hole
                  diameter, blended smoothly into the surrounding mesh.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  <strong className="text-ink">Rounded corners:</strong> refined
                  to the smaller of 0.6 × the global size and 0.6 × the corner
                  radius, for the same reason.
                </span>
              </li>
              <li className="flex gap-2">
                <span className="text-ink-faint">—</span>
                <span>
                  <strong className="text-ink">Element type:</strong> order 2
                  (C3D10) is mandatory. The cheaper linear element was measured
                  about 19% too stiff in bending — see the proof below.
                </span>
              </li>
            </ul>
          </Disclosure>

          <Disclosure
            title="The equation, for the curious"
            description="One line of maths describes every static linear solve; the size of it is what makes real FEA expensive."
          >
            <div className="space-y-3 text-xs leading-relaxed text-ink-muted">
              <p className="font-mono text-xs text-ink">
                [K] · &#123;u&#125; = &#123;f&#125;
              </p>
              <p>
                [K] is the stiffness of the whole part — assembled from every
                element. &#123;f&#125; is the applied force at every node.
                &#123;u&#125; is the unknown movement at every node; solving
                means finding the &#123;u&#125; that balances the force.
              </p>
              <p>
                Every node may move in three directions, so a mesh of{" "}
                {nodes !== null ? nodes.toLocaleString() : "a few thousand"}{" "}
                nodes means about{" "}
                {unknowns !== null ? unknowns.toLocaleString() : "tens of thousands of"}{" "}
                unknowns solved simultaneously. That number — not the physics —
                is why industrial analyses with millions of nodes take hours.
                This project keeps parts small and meshes purposeful, which is
                why a case finishes in seconds.
              </p>
            </div>
          </Disclosure>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Outputs"
          title="What comes out of a solve"
          description="Three headline numbers plus the full field. These are exactly the quantities the learned models were trained to reproduce."
        />
        <PanelBody className="space-y-4">
          <Table>
            <thead>
              <tr>
                <Th>Result</Th>
                <Th align="right">Unit</Th>
                <Th>What it means</Th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Max displacement</span>
                </Td>
                <Td align="right" mono>
                  mm
                </Td>
                <Td className="text-ink-muted">
                  How far the free end moves under the load.
                </Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">
                    Global max Von Mises stress
                  </span>
                </Td>
                <Td align="right" mono>
                  MPa
                </Td>
                <Td className="text-ink-muted">
                  The highest stress found anywhere in the part, with pulling,
                  pushing and twisting combined into one comparable number.
                </Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Weak-spot stress</span>
                </Td>
                <Td align="right" mono>
                  MPa
                </Td>
                <Td className="text-ink-muted">
                  The same number restricted to the hole or rounded corner,
                  where cracks usually start.
                </Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Full field</span>
                </Td>
                <Td align="right" mono>
                  every node
                </Td>
                <Td className="text-ink-muted">
                  Displacement and all stress components at every mesh point —
                  the raw material for the colour maps and the picture model.
                </Td>
              </tr>
            </tbody>
          </Table>
          <Callout tone="neutral" icon="info" title="MPa, quickly">
            1 MPa is one newton per square millimetre — about the pressure of a
            10 kg weight resting on a fingernail. A stress of 180 MPa means
            every square millimetre of material carries roughly that much
            internal force.
          </Callout>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Validation"
          title="Proof it is right"
          description="The solver was checked against textbook physics and against itself under mesh refinement. These numbers are why the dataset is allowed to be the ground truth."
        />
        <PanelBody className="space-y-5">
          <div>
            <div className="text-xs font-semibold text-ink">
              1. Against a textbook formula
            </div>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              An unperforated cantilever (120 × 40 × 6 mm, 500 N, steel) was
              compared with Euler–Bernoulli beam theory — the pencil-and-paper
              formula every mechanical engineer learns. The same case was run
              with two element types and several mesh sizes.
            </p>
            <div className="mt-2.5">
              <Table>
                <thead>
                  <tr>
                    <Th>Element</Th>
                    <Th align="right">Mesh</Th>
                    <Th align="right">Tip deflection vs theory</Th>
                    <Th align="right">Bending stress vs theory</Th>
                    <Th>Verdict</Th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <Td mono>C3D4</Td>
                    <Td align="right" mono>
                      1.5 mm
                    </Td>
                    <Td align="right" mono className="text-danger">
                      −19.3%
                    </Td>
                    <Td align="right" mono className="text-danger">
                      −11.1%
                    </Td>
                    <Td>
                      <Chip tone="danger">rejected</Chip>
                    </Td>
                  </tr>
                  <tr>
                    <Td mono>C3D10</Td>
                    <Td align="right" mono>
                      4.0 mm
                    </Td>
                    <Td align="right" mono>
                      −2.57%
                    </Td>
                    <Td align="right" mono>
                      +0.29%
                    </Td>
                    <Td className="text-ink-muted">production choice</Td>
                  </tr>
                  <tr>
                    <Td mono>C3D10</Td>
                    <Td align="right" mono>
                      2.0 mm
                    </Td>
                    <Td align="right" mono>
                      −2.39%
                    </Td>
                    <Td align="right" mono>
                      +0.24%
                    </Td>
                    <Td className="text-ink-muted">refinement check</Td>
                  </tr>
                  <tr>
                    <Td mono>C3D10</Td>
                    <Td align="right" mono>
                      1.5 mm
                    </Td>
                    <Td align="right" mono>
                      −2.35%
                    </Td>
                    <Td align="right" mono>
                      +0.64%
                    </Td>
                    <Td className="text-ink-muted">refinement check</Td>
                  </tr>
                </tbody>
              </Table>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-muted">
              Two lessons. First, the cheap 4-node element is unusable for
              bending — about 19% too stiff — which is why quadratic elements
              are mandatory. Second, the small remaining deflection gap (−2.35%)
              is understood, not a bug: a model whose base face is clamped
              rigidly is a little stiffer than ideal beam theory assumes. It
              shrinks to −1.37% for slimmer parts and does not improve with a
              finer mesh (the change from 2.0 mm to 1.5 mm is 0.03%), so it is a
              modelling effect with a known size, not a discretisation error.
            </p>
          </div>

          <div className="border-t border-line pt-4">
            <div className="text-xs font-semibold text-ink">
              2. Against itself: mesh convergence at the stress-riser
            </div>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              A peak stress at a hole edge is only trustworthy if it stops
              changing when the mesh gets finer. The production geometry (12 mm
              hole, mid-span) was solved with progressively finer meshes, with
              and without local refinement at the hole.
            </p>
            <div className="mt-2.5">
              <Table>
                <thead>
                  <tr>
                    <Th>Mesh policy</Th>
                    <Th align="right">4.0 mm</Th>
                    <Th align="right">3.0 mm</Th>
                    <Th align="right">2.0 mm</Th>
                    <Th align="right">1.5 mm</Th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <Td>Uniform</Td>
                    <Td align="right" mono>
                      259.1
                    </Td>
                    <Td align="right" mono>
                      265.9
                    </Td>
                    <Td align="right" mono>
                      269.3
                    </Td>
                    <Td align="right" mono>
                      267.0
                    </Td>
                  </tr>
                  <tr>
                    <Td>Hole-graded (production)</Td>
                    <Td align="right" mono>
                      —
                    </Td>
                    <Td align="right" mono>
                      269.8
                    </Td>
                    <Td align="right" mono>
                      270.5
                    </Td>
                    <Td align="right" mono>
                      270.8
                    </Td>
                  </tr>
                </tbody>
              </Table>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-muted">
              Uniform meshes leave the peak wobbling at the ±1% level because
              the hole surface is under-resolved. Grading the hole surface makes
              the number settle: the two finest meshes differ by 0.14%. That is
              the safety margin on the weak-spot labels. (Values in MPa.)
            </p>
          </div>

          <div className="border-t border-line pt-4">
            <div className="text-xs font-semibold text-ink">
              3. Against randomness: deterministic and gated
            </div>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">
              For this class of problem the solver is deterministic: the same
              design solved twice produces identical numbers, to the last digit.
              That is what makes cached results safe to reuse, and what makes
              the dataset reproducible. And no answer reaches a model without
              passing all six gates — in the current build, every planned case
              passed, which the{" "}
              <Link to="/dataset" className="text-link hover:underline">
                Dataset page
              </Link>{" "}
              confirms with live counts.
            </p>
          </div>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Scope"
          title="What the solver is not asked to do"
          description="The narrowness of the question is the reason the answer can be trusted at this speed."
        />
        <PanelBody className="space-y-3">
          <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              No plasticity, contact, buckling, vibration, fatigue, heat or
              time-dependent behaviour. Linear elasticity only.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              One load case family, one material, six cantilever shapes.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              A peak stress at a hole is a value at one node of a finite mesh.
              The refinement study bounds its sensitivity at about 0.15%, but it
              is not an exact mathematical peak.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              The solver computes; it does not decide. Choosing a design,
              applying safety factors and taking responsibility remain
              engineering work.
            </li>
          </ul>
          <p className="border-t border-line pt-3 text-2xs leading-relaxed text-ink-faint">
            Full boundaries live on the{" "}
            <Link to="/manual/limitations" className="text-link hover:underline">
              limits page
            </Link>
            ; the shapes and parameters are on{" "}
            <Link
              to="/manual/design-space"
              className="text-link hover:underline"
            >
              what can be designed here
            </Link>
            .
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Vocabulary"
          title="The words on this page, quickly"
          description="The full list lives in the glossary."
        />
        <PanelBody>
          <Terms
            items={[
              {
                term: "Node",
                body: "A point where mesh pieces meet; the solver computes movement and stress there.",
              },
              {
                term: "Element",
                body: "One small piece of the mesh; here a 10-node tetrahedron (C3D10).",
              },
              {
                term: "Mesh",
                body: "The net of nodes and elements that stands in for the smooth shape.",
              },
              {
                term: "Boundary condition",
                body: "A rule that fixes part of the model — here the clamped base.",
              },
              {
                term: "Degree of freedom",
                body: "One allowed direction of movement; every node has three (x, y, z).",
              },
              {
                term: "Linear elastic",
                body: "Twice the load, twice the movement — and full spring-back when unloaded.",
              },
              {
                term: "Von Mises stress",
                body: "One combined 'how hard is the material working' number, comparable to a single material limit.",
              },
              {
                term: "Convergence",
                body: "Shrinking mesh pieces until answers stop changing — the sign that the calculation is settled.",
              },
            ]}
          />
          <p className="mt-3 border-t border-line pt-3 text-2xs leading-relaxed text-ink-faint">
            More definitions in the{" "}
            <Link to="/manual/glossary" className="text-link hover:underline">
              plain-language glossary
            </Link>
            .
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Try it"
          title="Run this engine on your own design"
          description="FEA Verify runs exactly the pipeline described above on whichever design is loaded in the sidebar: production mesh, real CalculiX, streamed log, and a side-by-side comparison with the surrogate."
        />
        <PanelBody className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <Link to="/verify">
              <Button variant="primary" disabled={!calculixReady}>
                <Icon name="play" className="h-4 w-4" />
                Open FEA Verify
              </Button>
            </Link>
            <span className="text-2xs leading-relaxed text-ink-muted">
              Solved designs are cached — re-opening the same case is instant;
              "Force re-run" solves it from scratch.
            </span>
          </div>
          <Chain
            lines={[
              "design (sidebar)",
              "  └─ production mesh   quadratic tets, risers graded",
              "       └─ CalculiX solve   seconds on this machine",
              "            └─ extraction   displacement, stress, peak values",
              "                 └─ comparison   solver vs surrogate, error in %",
            ]}
          />
        </PanelBody>
      </Panel>

      <ManualFooterNav previous={previous} next={next} />
    </ManualLayout>
  );
}
