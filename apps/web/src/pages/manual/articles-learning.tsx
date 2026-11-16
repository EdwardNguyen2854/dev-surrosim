import { Link } from "react-router-dom";

import { Callout, Chip, Panel, PanelBody, PanelHeader, Table, Td, Th } from "../../components/ui";
import type { ManualArticle } from "./model";

function DocLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link to={to} className="text-link hover:underline">
      {children}
    </Link>
  );
}

export const surrogates: ManualArticle = {
  id: "surrogates",
  to: "/manual/surrogates",
  group: "learning",
  title: "How the fast models learn",
  summary:
    "Two kinds of model: one that answers with three numbers, one that draws the whole picture — and what their measured accuracy really means.",
  minutes: 6,
  body: (
    <>
      <Callout title="In plain words">
        The models are pattern-finders, not calculators. Someone (the dataset
        pipeline) has already worked out the answers to thousands of exercises.
        Training means showing those exercises to a mathematical function until
        it can produce the same answers for new, unseen designs. It never
        learns the physics as rules — it learns the pattern in the numbers.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="How learning works"
          title="Examples in, pattern out"
          description="This approach is called supervised learning: the dataset provides inputs (the design) and the correct outputs (the solved answers)."
        />
        <PanelBody className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <p>
            Training adjusts a model's internal numbers until its predictions
            match the solved examples as closely as possible. The model is then
            frozen. It is judged only on designs it has never seen — the test
            and challenge piles from the{" "}
            <DocLink to="/manual/ground-truth">ground-truth page</DocLink> —
            because measuring it on the study material would prove nothing.
          </p>
          <p>
            One important detail: the answers are learned in log space. In plain
            words, a 10% miss counts the same on a tiny part and a huge one, so
            accuracy stays proportional across a range that spans orders of
            magnitude.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="The numbers model"
          title="Three answers, each with its own trained model"
          description="The scalar ensemble takes the design numbers and returns the three headline values. Different targets are allowed to prefer different algorithms."
        />
        <PanelBody className="space-y-4">
          <Table>
            <thead>
              <tr>
                <Th>Target</Th>
                <Th>In plain words</Th>
                <Th align="right">Typical miss</Th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Max displacement</span>
                </Td>
                <Td className="text-ink-muted">How far the free end bends.</Td>
                <Td align="right" mono>
                  ~1.9%
                </Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Global max stress</span>
                </Td>
                <Td className="text-ink-muted">
                  The highest stress anywhere in the part.
                </Td>
                <Td align="right" mono>
                  ~2.3%
                </Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Weak-spot stress</span>
                </Td>
                <Td className="text-ink-muted">
                  The stress at the hole or rounded corner.
                </Td>
                <Td align="right" mono>
                  ~1.7%
                </Td>
              </tr>
            </tbody>
          </Table>
          <p className="text-2xs leading-relaxed text-ink-faint">
            Typical misses on unseen designs at the centre of the range. On the
            deliberately awkward challenge corners the typical miss rises to
            roughly 5–7%, and individual cases can be worse — the{" "}
            <DocLink to="/model">Model page</DocLink> shows the live tables,
            worst cases included.
          </p>
          <div className="space-y-3 border-t border-line pt-4">
            <p className="text-xs leading-relaxed text-ink-muted">
              Several candidate algorithms are trained and compared — a
              straight-line fit, a Gaussian process (a curve fitter that also
              reports uncertainty), a small neural network (MLP), and forests of
              decision trees. The winners are combined into an{" "}
              <strong className="text-ink">ensemble</strong>: several models
              answering together. Their average is usually better than any one
              of them, and — just as useful — how much they disagree becomes a
              warning signal.
            </p>
            <p className="text-xs leading-relaxed text-ink-muted">
              For reference: on the plate family, the classical textbook beam
              formula measured about 3.6% typical error — a good sanity check,
              but clearly behind the learned ensemble, and it cannot account for
              holes or shape changes at all.
            </p>
          </div>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="The picture model"
          title="Predicting the whole field, not just three numbers"
          description="The graph neural network (GNN) predicts displacement and stress at every point of a coarse mesh, so the app can draw colour maps for a design it has never solved."
        />
        <PanelBody className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <p>
            Think of the mesh as a net of points covering the part. Each point
            sends short messages to its neighbours about where it sits and what
            is happening around it. After several rounds of this, every point
            knows enough about the whole part to say how much it moves and how
            stressed it is. Training taught the message rules from real solved
            examples.
          </p>
          <p>
            On unseen test designs the picture model reduces to about{" "}
            <strong className="text-ink">2.6% error</strong> on the global peak
            stress, with a typical point error of 0.8% of the part's peak value.
            An identical network without the message passing measured 10.5% —
            evidence that looking at geometry, not just coordinates, is what
            makes it work.
          </p>
          <Callout tone="warning" title="Use the picture, not the peak">
            The field model was trained on a deliberately coarse mesh and is
            meant for seeing the pattern — where stress concentrates, how the
            part bends. For final peak values, read the numbers model and verify
            with a real solve before an engineering decision.
          </Callout>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="What it sees"
          title="A design is described by numbers, not a drawing"
          description="Features are the model's only view of the part. They fall into three groups."
        />
        <PanelBody className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                <strong className="text-ink">Direct inputs</strong> — the values
                you set on the sliders.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                <strong className="text-ink">Derived ratios</strong> — calculated
                combinations such as slenderness and diameter-to-width, the same
                dimensionless habits an engineer uses to make comparisons fair
                across sizes.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                <strong className="text-ink">Shape flags</strong> — one per
                family, so the model knows which geometry it is looking at.
              </span>
            </li>
          </ul>
          <p className="border-t border-line pt-3">
            The exact feature list for the live registry is listed on the{" "}
            <DocLink to="/model">Model page</DocLink>, under "Behind the
            scenes".
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Speed"
          title="Why it is a thousand times faster"
          description="No mesh, no equations, no iteration — just one pass through a trained function."
        />
        <PanelBody className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <p>
            A real solve builds a mesh, assembles and solves a giant system of
            equations, and reads the results back: about ten seconds here. A
            scalar prediction evaluates a handful of trained functions: about
            ten microseconds — roughly a million times faster per evaluation.
          </p>
          <p>
            The price is approximation. The speed is what makes thousands of
            what-if evaluations, live sliders and optimisation searches
            practical at all.
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};

export const trust: ManualArticle = {
  id: "trust",
  to: "/manual/trust",
  group: "learning",
  title: "When to trust a prediction",
  summary:
    "Bounds, distance and disagreement — the three honest signals behind the trust / caution / run-FEA recommendation.",
  minutes: 5,
  body: (
    <>
      <Callout title="In plain words">
        A prediction without a confidence signal is just a number pretending to
        be an answer. SurroSim checks three independent things about every
        design you ask about, combines them into one recommendation, and shows
        its reasoning instead of hiding it.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="The three signals"
          title="What gets checked before you read the numbers"
          description="They are heuristics designed to catch extrapolation, not calibrated probabilities — honest warning lights, not statistics."
        />
        <PanelBody>
          <Table>
            <thead>
              <tr>
                <Th>Signal</Th>
                <Th>How it is computed, in plain words</Th>
                <Th>What it catches</Th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Hard bounds</span>
                </Td>
                <Td className="text-ink-muted">
                  Every parameter is compared against the allowed design range.
                </Td>
                <Td className="text-ink-muted">
                  Requests outside the trained box. Any violation forces "run
                  FEA".
                </Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Distance to training designs</span>
                </Td>
                <Td className="text-ink-muted">
                  How far the design sits, in standardised units, from the fifth
                  nearest solved design — divided by what "far" usually means
                  inside the training data.
                </Td>
                <Td className="text-ink-muted">
                  Designs inside the box but in a sparsely populated region.
                  Ratio above 1.5 → caution; above 2.5 → out of domain.
                </Td>
              </tr>
              <tr>
                <Td>
                  <span className="font-medium text-ink">Model disagreement</span>
                </Td>
                <Td className="text-ink-muted">
                  The worst spread between ensemble members, as a percentage.
                </Td>
                <Td className="text-ink-muted">
                  Places where the models have not settled on one story. Above
                  15% → caution.
                </Td>
              </tr>
            </tbody>
          </Table>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="The recommendation"
          title="Three answers to 'can I use this?'"
          description="The worst signal wins: a bounds violation or a very distant design outranks agreement between models."
        />
        <PanelBody className="space-y-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="rounded border border-line p-3">
              <Chip tone="success">Trust</Chip>
              <p className="mt-2 text-xs leading-relaxed text-ink-muted">
                Inside the parameter box, close to training data, models agree.
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-ink">
                Use it to explore. It is still an approximation — not a
                safety-case answer.
              </p>
            </div>
            <div className="rounded border border-line p-3">
              <Chip tone="warning">Caution</Chip>
              <p className="mt-2 text-xs leading-relaxed text-ink-muted">
                OOD ratio above 1.5, or ensemble disagreement above 15%.
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-ink">
                Treat it as indicative. Verify with the real solver before any
                decision.
              </p>
            </div>
            <div className="rounded border border-line p-3">
              <Chip tone="danger">Run FEA</Chip>
              <p className="mt-2 text-xs leading-relaxed text-ink-muted">
                A design-space bound is violated, or the OOD ratio exceeds 2.5.
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-ink">
                The model has no experience here. Solve the real case.
              </p>
            </div>
          </div>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="In practice"
          title="How to act on each signal"
          description="The recommendation is advice, not a barrier — every analysis page keeps the real solver one click away."
        />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            <strong className="text-ink">Trust</strong> means the fast answer is
            safe to reason with while you explore. It does not mean it has a
            safety factor built in.
          </p>
          <p>
            <strong className="text-ink">Caution</strong> is the most useful
            state: the design is probably close to correct but is in thin
            evidence. Run the{" "}
            <DocLink to="/manual/app-verify">FEA verification</DocLink> for the
            exact design and compare — the app shows both numbers side by side.
          </p>
          <p>
            <strong className="text-ink">Run FEA</strong> is a refusal dressed
            as advice: the model is not supported here. The{" "}
            <DocLink to="/verify">FEA Verify page</DocLink> solves the real
            case in a few seconds and becomes the reference.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Honesty" title="The limits of the confidence logic itself" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            The signals are measured in feature space, not in geometry space —
            an unusual shape inside the parameter box can still be mis-scored.
            They flag extrapolation; they cannot prove correctness.
          </p>
          <p>
            That is why verification stays one click away on every page, and why
            no predicted stress is presented as a pass/fail against a material
            limit. The{" "}
            <DocLink to="/manual/limitations">limits page</DocLink> carries the
            full list.
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};
