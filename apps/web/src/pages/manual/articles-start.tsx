import { Link } from "react-router-dom";

import { Steps, Terms } from "../../components/content";
import { Callout, Panel, PanelBody, PanelHeader, Table, Td, Th } from "../../components/ui";
import type { ManualArticle } from "./model";

function DocLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link to={to} className="text-link hover:underline">
      {children}
    </Link>
  );
}

export const overview: ManualArticle = {
  id: "overview",
  to: "/manual/overview",
  group: "start",
  title: "The idea behind SurroSim",
  summary:
    "Why the project exists, what it borrowed from everyday engineering practice, and the loop that keeps it honest.",
  minutes: 5,
  body: (
    <>
      <Callout title="In plain words">
        SurroSim answers engineering questions about a part — how far it bends,
        where it is most stressed — in about a millisecond. It can do that
        because it does not calculate the physics on the spot. It studied
        thousands of examples that were calculated slowly and carefully with a
        real simulation engine, and it learned the pattern. This manual explains
        both halves of that sentence.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="Why bother"
          title="The problem: physics is accurate but slow"
          description="Predicting how a real part behaves means solving physics equations for every tiny piece of it, until the forces balance. Accuracy is bought with computing time."
        />
        <PanelBody className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <p>
            One design of one small part takes roughly ten seconds to solve on
            a normal computer. That sounds fast — until a study needs hundreds
            or thousands of variations. Exploring a design space becomes hours
            or days of pure computing, so it is usually done with experience
            and rules of thumb instead.
          </p>
          <p>
            SurroSim explores the middle ground. Keep the accurate simulation
            for the examples that matter, learn the pattern from them, and then
            answer instantly everywhere in between — while keeping the real
            simulation one click away whenever a decision matters.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="The core trick"
          title="Learn from solved examples"
          description="A surrogate model is the same idea as learning from worked exercises: see enough solved problems, and you can answer similar ones without re-deriving anything."
        />
        <PanelBody className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <p>
            The examples are not guesses or textbook approximations. Each one
            is a full three-dimensional simulation that was solved with
            CalculiX, a real finite-element program, then checked and stored.
            A solved case either passes every quality check or it is not allowed
            to teach the models.
          </p>
          <p>
            Because the examples are trustworthy, the fast answers are useful.
            Because the fast answers are approximations, the system is designed
            to say so: every prediction carries a confidence signal, and the
            real solver stays available for verification.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Two answers"
          title="The slow truth and the fast estimate"
          description="The app always tells you which kind of answer you are looking at."
        />
        <PanelBody>
          <Table>
            <thead>
              <tr>
                <Th>Question</Th>
                <Th>Real solver (CalculiX)</Th>
                <Th>Learned model (surrogate)</Th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <Td>What it is</Td>
                <Td>
                  Solves the physics equations for the actual part, piece by
                  piece, until forces balance.
                </Td>
                <Td>
                  Recognises the pattern in solved examples and returns the
                  closest matching answer.
                </Td>
              </tr>
              <tr>
                <Td>Trust</Td>
                <Td>
                  <strong className="text-ink">Ground truth</strong> — the
                  reference everything else is measured against.
                </Td>
                <Td>
                  <strong className="text-ink">Approximation</strong> — useful
                  for exploration, can be wrong at the edges of its experience.
                </Td>
              </tr>
              <tr>
                <Td>Speed</Td>
                <Td>About 10 seconds per design on the build machine.</Td>
                <Td>
                  About 10 microseconds for the three headline numbers; seconds
                  for a full colour map.
                </Td>
              </tr>
              <tr>
                <Td>Used for</Td>
                <Td>
                  Producing training data; checking important decisions and
                  optimisation finalists.
                </Td>
                <Td>
                  Interactive exploration, screening thousands of options,
                  confidence-aware estimates.
                </Td>
              </tr>
              <tr>
                <Td>Evidence</Td>
                <Td>
                  Validated against textbook beam theory and mesh studies (see
                  the <DocLink to="/solver">Solver page</DocLink>).
                </Td>
                <Td>
                  Measured against solved designs it never saw during training
                  (see the <DocLink to="/model">Model page</DocLink>).
                </Td>
              </tr>
            </tbody>
          </Table>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="The loop"
          title="How the whole system fits together"
          description="Seven stages, each one designed so the next can be trusted."
        />
        <PanelBody>
          <Steps
            items={[
              {
                title: "Pick the designs",
                body: "A sampling routine chooses parameter combinations that cover the whole allowed range, including deliberately awkward corner cases. The list is frozen before any solving starts.",
              },
              {
                title: "Solve every one for real",
                body: "Each design becomes a 3D shape, a mesh and a solver instruction file. CalculiX computes how far it bends and how stressed it gets. Nothing is estimated.",
              },
              {
                title: "Gate the answers",
                body: "A case becomes training material only if every quality check passes: clean solver finish, exact force balance, fine-enough mesh, complete result files, finite positive numbers.",
              },
              {
                title: "Learn the pattern",
                body: "Two kinds of model study the gated cases: one returns the three headline numbers, one predicts the full field across the part.",
              },
              {
                title: "Serve it with confidence",
                body: "The app returns a prediction together with how far the design sits from the training experience and how much the models disagree.",
              },
              {
                title: "Verify when it counts",
                body: "Whenever confidence is weak — or a decision is important — the real solver runs again from the app, for the exact design on screen.",
              },
              {
                title: "Keep the paper trail",
                body: "Every number can be followed back through model → dataset → solve → mesh. See the provenance page for the full chain.",
              },
            ]}
          />
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Honesty"
          title="What this is not"
          description="The system is deliberately explicit about its own boundaries."
        />
        <PanelBody className="space-y-3">
          <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              It is not a replacement for engineering judgement, safety factors
              or a validated commercial analysis tool.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              It covers six cantilever shape families, one steel material and
              one static load case — no more.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              Its confidence signals are honest heuristics, not guarantees. The
              full list is on the <DocLink to="/manual/limitations">limits page</DocLink>.
            </li>
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Next" title="Where to go from here" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            <DocLink to="/manual/design-space">What can be designed here</DocLink>{" "}
            introduces the six shapes and the numbers that describe them.
          </p>
          <p>
            <DocLink to="/solver">The Solver page</DocLink> opens the physics
            engine up and shows the evidence that its answers are right.
          </p>
          <p>
            <DocLink to="/manual/ground-truth">Where the answers come from</DocLink>{" "}
            walks through the factory that turns designs into trusted training
            data.
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};

export const glossary: ManualArticle = {
  id: "glossary",
  to: "/manual/glossary",
  group: "start",
  title: "Plain-language glossary",
  summary:
    "Every term and abbreviation the app and this manual use, explained without assuming an engineering or software background.",
  minutes: 6,
  body: (
    <>
      <Callout title="How to use this page" icon="book-open">
        Terms are grouped by where you meet them. If a page uses a word you do
        not recognise, come back here — the definition is one or two sentences,
        not a textbook chapter.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="Physics"
          title="The engineering words"
          description="What the simulation talks about."
        />
        <PanelBody>
          <Terms
            items={[
              {
                term: "FEA (finite-element analysis)",
                body: "A way of computing how a real part behaves by cutting it into many small pieces and solving the physics for all of them at once. The computer never sees the smooth shape — only the mesh.",
              },
              {
                term: "Cantilever",
                body: "A beam or plate held at one end with the load applied at the other. A shelf bracket is the everyday example, and every shape in SurroSim is a cantilever.",
              },
              {
                term: "Node",
                body: "A point in the mesh. The solver computes movement and stress at every node; the mesh is the net of nodes.",
              },
              {
                term: "Element",
                body: "One small piece of the mesh. Here each piece is a 10-node tetrahedron (a small pyramid-like solid), which bends accurately — unlike the cheaper 4-node version.",
              },
              {
                term: "Mesh",
                body: "The full net of nodes and elements that stands in for the smooth shape during calculation. Finer meshes are more accurate but slower.",
              },
              {
                term: "Boundary condition",
                body: "A rule that fixes part of the model. Here the clamped base cannot move at all, and the free end carries the load. Without boundary conditions the equations would have no unique answer.",
              },
              {
                term: "Degree of freedom",
                body: "One allowed direction of movement — sideways, vertical or through the thickness. Every node has three, so the solver must find three numbers per node.",
              },
              {
                term: "Stiffness",
                body: "How strongly a part resists bending. Thickness dominates: doubling a plate's thickness makes it roughly eight times harder to bend in this setup.",
              },
              {
                term: "Linear elastic",
                body: "The assumption that pushing twice as hard moves the part exactly twice as far, and that removing the load returns it to its original shape — like a spring, up to the point where real metal would permanently deform.",
              },
              {
                term: "Stress",
                body: "Internal force per area inside the material, measured in MPa. It is what a strength check compares against the material's limit.",
              },
              {
                term: "Von Mises stress",
                body: "A way of combining pulling, pushing and twisting from every direction into one 'how hard is this material being worked' number, so it can be compared against a single material limit.",
              },
              {
                term: "MPa (megapascal)",
                body: "One newton per square millimetre. For intuition: about the pressure of a 10 kg weight resting on a fingernail.",
              },
              {
                term: "Plasticity",
                body: "Permanent deformation after the material is stressed too far. Deliberately not modelled — everything here is elastic.",
              },
              {
                term: "Buckling",
                body: "A sudden sideways collapse of a part under compression. Not modelled here.",
              },
              {
                term: "ROI (region of interest)",
                body: "The weak spot — the edge of a hole or a rounded corner — where stress is tracked as its own number because that is where cracks usually start.",
              },
            ]}
          />
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Pipeline"
          title="The simulation words"
          description="The programs and files that produce the ground truth."
        />
        <PanelBody>
          <Terms
            items={[
              {
                term: "Gmsh",
                body: "The free program that builds the 3D shape from the design numbers and cuts it into a mesh.",
              },
              {
                term: "CalculiX (ccx)",
                body: "The free finite-element solver that computes the physics answers. 'ccx' is the name of its executable.",
              },
              {
                term: "C3D10 / C3D4",
                body: "CalculiX names for quadratic and linear tetrahedron elements. Quadratic (C3D10) bends accurately; linear (C3D4) measured about 19% too stiff at practical mesh sizes, so it is not used for data.",
              },
              {
                term: "Deck",
                body: "The instruction file handed to the solver: shape, material, support, load, and which results to write out.",
              },
              {
                term: "Convergence",
                body: "Shrinking the mesh pieces until the answers stop changing — the sign that a calculation is settled and not just a coarse guess.",
              },
              {
                term: "Deterministic",
                body: "Same instructions in, same numbers out, every time. This is why a solved case can be cached and reused safely.",
              },
              {
                term: "Gate",
                body: "An automatic quality check a solved case must pass before it may train a model. Failed cases are logged and excluded — never silently kept.",
              },
            ]}
          />
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Learning"
          title="The model words"
          description="What the fast estimates are and how their accuracy is described."
        />
        <PanelBody>
          <Terms
            items={[
              {
                term: "Surrogate",
                body: "A fast approximate model trained to imitate an expensive simulation. Also called the learned model.",
              },
              {
                term: "Dataset",
                body: "The collection of solved, gated cases — the answer key the models studied. Its contents and ranges are shown on the Dataset page.",
              },
              {
                term: "Label",
                body: "The known answer for one case in the dataset, produced by the real solver.",
              },
              {
                term: "Split",
                body: "How the dataset is divided. Training cases teach; validation cases choose between candidate models; test cases are the once-only final exam; challenge cases are the awkward corners of the range.",
              },
              {
                term: "Features",
                body: "The numbers a model is given to describe a design — the values you set, plus calculated ratios, plus a flag for the shape family.",
              },
              {
                term: "Ensemble",
                body: "Several models answering together. The app averages their answers and also measures how much they disagree — disagreement is a useful warning sign.",
              },
              {
                term: "Gaussian process (GP)",
                body: "A statistical curve fitter that also estimates how unsure it is about each answer.",
              },
              {
                term: "MLP (multilayer perceptron)",
                body: "A small neural network: a stack of simple maths layers trained on examples.",
              },
              {
                term: "GNN (graph neural network) / MeshGraphNet",
                body: "A model that learns by passing messages between neighbouring mesh points, so geometry itself informs the answer.",
              },
              {
                term: "Log space",
                body: "Training on the logarithm of the answers, so that a '10% wrong' counts the same for a tiny value and a huge one. It keeps errors proportional across very different cases.",
              },
              {
                term: "MAPE",
                body: "Mean absolute percentage error — the average miss, expressed as a percentage of the true value. '2% MAPE' means a typical prediction is about 2% away from the solver's answer.",
              },
              {
                term: "R²",
                body: "How much of the variation between cases a model captures. 1.000 is perfect; 0 means it learned nothing.",
              },
            ]}
          />
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Trust"
          title="The app words"
          description="The signals and plumbing you see in the interface."
        />
        <PanelBody>
          <Terms
            items={[
              {
                term: "Confidence",
                body: "A combined signal — bounds, distance from training designs, model disagreement — that leads to one of three recommendations: trust, caution, or run FEA.",
              },
              {
                term: "OOD (out-of-distribution)",
                body: "A design that sits far away from anything the models were trained on. Predictions there are extrapolation, and the app says so.",
              },
              {
                term: "Provenance",
                body: "The documented chain from a number back to the exact run, mesh and dataset that produced it.",
              },
              {
                term: "SHA-256",
                body: "A fingerprint of a file's contents. If even one byte changes, the fingerprint changes — that is what makes the provenance links checkable.",
              },
              {
                term: "Registry",
                body: "The folder holding a trained model plus its metadata and measured scores. The Model page shows which registry the app is currently serving.",
              },
              {
                term: "Job",
                body: "A longer server task (a real solve, a field prediction, an optimisation) that runs in the background while the app stays responsive. Jobs stream their log as they work.",
              },
              {
                term: "Cached",
                body: "A previous result reused instead of recomputed. Solved cases are cached per design, so re-opening a verification is instant unless you ask to re-run it.",
              },
            ]}
          />
        </PanelBody>
      </Panel>
    </>
  ),
};
