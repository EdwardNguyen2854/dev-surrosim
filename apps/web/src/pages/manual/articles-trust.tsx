import { Link } from "react-router-dom";

import { Chain, QA } from "../../components/content";
import { Callout, Panel, PanelBody, PanelHeader } from "../../components/ui";
import type { ManualArticle } from "./model";

function DocLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link to={to} className="text-link hover:underline">
      {children}
    </Link>
  );
}

export const provenance: ManualArticle = {
  id: "provenance",
  to: "/manual/provenance",
  group: "trust",
  title: "Every number has a paper trail",
  summary:
    "Fingerprints, commits and per-case records: how any prediction in the app can be walked back to the exact simulation that justified it.",
  minutes: 5,
  body: (
    <>
      <Callout title="In plain words">
        Provenance means being able to answer "where did this number come
        from?" — all the way down. Not as a promise, but as a chain of files
        that the system itself checks with content fingerprints.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="The chain"
          title="From a prediction back to a mesh"
          description="Each level names the one below it and records a fingerprint of its contents."
        />
        <PanelBody className="space-y-3">
          <Chain
            lines={[
              "prediction (app / API)",
              "  └─ model metadata       models/*/metadata.json   (config, seed, metrics)",
              "       └─ dataset sha256   data/dataset_*/manifest.json",
              "            └─ designs sha256   data/designs_*.csv",
              "                 └─ per-case run.json   (mesh policy, deck summary, solver log)",
              "                      └─ geometry metadata   (element order, refinement, quality)",
            ]}
          />
          <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                The <strong className="text-ink">model metadata</strong> records
                the training configuration, the random seed, the measured
                scores, and the fingerprint of the dataset it learned from.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                The <strong className="text-ink">dataset manifest</strong>{" "}
                records the design table it was built from, the gates applied,
                the solver version, and the git commit of the build.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              <span>
                The <strong className="text-ink">per-case run record</strong>{" "}
                keeps the mesh policy, the deck summary and the solver's own
                log, together with the full-field results.
              </span>
            </li>
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Why it matters" title="Three everyday consequences" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            <strong className="text-ink">Mistakes cannot hide.</strong> If a
            dataset changes, its fingerprint changes, and every model claiming
            to have learned from it fails the check. Retraining becomes forced,
            not assumed.
          </p>
          <p>
            <strong className="text-ink">Numbers can be audited.</strong> A
            surprising prediction can be traced to the exact mesh and solver
            output that produced its training examples.
          </p>
          <p>
            <strong className="text-ink">Runs are reproducible.</strong> Seeds,
            splits and configurations are explicit. Rebuilding the same release
            on the same data produces the same artifacts.
          </p>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="In the app" title="Where to see the trail" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            The sidebar always shows the registry being served, the dataset
            fingerprint, and the git commit of the build. The{" "}
            <DocLink to="/model">Model page</DocLink> and{" "}
            <DocLink to="/dataset">Dataset page</DocLink> print the same
            identifiers next to their evidence, and every prediction response
            carries them too — shown on the Explorer under "Model provenance".
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};

export const limitations: ManualArticle = {
  id: "limitations",
  to: "/manual/limitations",
  group: "trust",
  title: "What this is not",
  summary:
    "The explicit boundary of the evidence: physics, design space, model behaviour, validation and operation.",
  minutes: 6,
  body: (
    <>
      <Callout tone="warning" title="Read this before using a number">
        Predictions are surrogate approximations. They require independent
        engineering verification before any safety-relevant use; the app
        provides that verification but does not replace an engineer.
      </Callout>

      <Panel>
        <PanelHeader
          kicker="Physics"
          title="One kind of physics, deliberately"
          description="The simulation assumes linear elasticity. That narrowness is what makes it mathematically reliable — and it is also the first limit."
        />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              Linear elasticity only: no plasticity, contact, buckling,
              vibration, fatigue, thermal or time-dependent behaviour.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              Labels above the yield strength of steel are simulation outputs
              under the elasticity assumption — not a prediction of what a
              physical part would do.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              One load case family: a total transverse force at the free end of
              a cantilever, fully clamped at the base.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              One material: steel at 210,000 MPa and 0.30 Poisson ratio. Other
              metals and plastics were never trained on.
            </li>
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Design space"
          title="A closed world"
          description="Six shape families, sampled ranges, and nothing beyond."
        />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              A design outside the trained parameter box is a guess, not a
              prediction. The app flags it and recommends a real solve.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              Even inside the box, the challenge corners measure 5–9% typical
              error with individual cases worse. The extreme corners are exactly
              where you should verify.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              Sharp re-entrant corners are out of scope by design; shapes with
              them are filleted, and the model only knows the filleted versions.
            </li>
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Models" title="How the models can mislead" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              Average accuracy hides tail cases. A typical miss of a few percent
              does not bound the worst case.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              The field model predicts on a coarse mesh: good for seeing
              where stress gathers, not for reading peak values.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              Confidence signals are heuristics, not calibrated probabilities.
              A prediction marked "trust" is still an approximation.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              No safety factor is included anywhere. A predicted stress at the
              limit is a cue to analyse carefully, not a pass.
            </li>
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader
          kicker="Validation"
          title="What was checked, and what was never checked"
        />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <ul className="space-y-2">
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              The solver was validated against textbook beam theory, mesh
              refinement studies and its own determinism. That evidence is on
              the <DocLink to="/solver">Solver page</DocLink>.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              There is no experimental correlation: no physical part was ever
              tested and compared. All validation is theoretical and internal.
            </li>
            <li className="flex gap-2">
              <span className="text-ink-faint">—</span>
              The field model is validated on its coarse mesh profile only.
            </li>
          </ul>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader kicker="Operation" title="A local engineering demo" />
        <PanelBody className="space-y-2 text-xs leading-relaxed text-ink-muted">
          <p>
            The app has no authentication and no multi-user persistence. It is
            meant to run locally, on the machine that owns the repository. Do
            not expose it publicly as it is.
          </p>
          <p className="text-2xs text-ink-faint">
            See also the frequently-asked questions in the{" "}
            <DocLink to="/manual/faq">FAQ</DocLink>.
          </p>
        </PanelBody>
      </Panel>
    </>
  ),
};

export const faq: ManualArticle = {
  id: "faq",
  to: "/manual/faq",
  group: "trust",
  title: "Questions people ask",
  summary: "Practical answers, in the order people usually ask them.",
  minutes: 5,
  body: (
    <>
      <Panel>
        <PanelHeader
          kicker="FAQ"
          title="The questions, with straight answers"
          description="If a question is missing, the answer is usually in the glossary or the limits page."
        />
        <PanelBody>
          <QA
            items={[
              {
                q: "Can I analyse a shape that is not one of the six families?",
                a: (
                  <>
                    No — and the app will tell you so rather than guess. The
                    models are trained on six cantilever families only. For
                    anything else the honest path is a full simulation in a CAE
                    tool. Extending the family set is possible but means new
                    geometry, new sampling, new solves all the way through the
                    pipeline.
                  </>
                ),
              },
              {
                q: "Why can the predicted stress be higher than the yield strength of steel?",
                a: (
                  <>
                    Because the physics model is linear elastic: it keeps
                    doubling the stress as you double the load, which real steel
                    does not. Dataset cases that exceed yield are still valid
                    solver outputs{" "}
                    <em>under that assumption</em>; they are not a claim that
                    the physical part would survive. Treat them as
                    "what-if the material behaved perfectly elastically" numbers.
                  </>
                ),
              },
              {
                q: "How accurate is 'a few percent', really?",
                a: (
                  <>
                    A typical prediction is about 1–3% away from the solver in
                    the middle of the trained range, and about 5–9% at the
                    awkward corners — with individual worst cases larger. In
                    engineering terms that is useful for screening and
                    exploration, not enough to sign off a safety-relevant
                    design. Verify before decisions.
                  </>
                ),
              },
              {
                q: "Why does a solve take ten seconds here when FEA usually takes hours?",
                a: (
                  <>
                    Because the problem is deliberately small and simple: one
                    part, one material, one static load case, linear elasticity,
                    and a mesh of a few thousand nodes. No contact, no
                    nonlinearity, no long transient. The workflow pieces are the
                    same as a large analysis — just a much smaller problem.
                  </>
                ),
              },
              {
                q: "What does 'run FEA' mean when the app shows it?",
                a: (
                  <>
                    It means the model's confidence signals failed: the design is
                    outside the trained bounds, or far from the training data.
                    The recommendation is literal — open the{" "}
                    <DocLink to="/verify">FEA Verify page</DocLink> and solve the
                    real case. The fast answer there is not supported.
                  </>
                ),
              },
              {
                q: "Why is the picture model less accurate at the peak than the numbers model?",
                a: (
                  <>
                    The picture model works on a deliberately coarse mesh —
                    needed to keep its training affordable — and peak stresses
                    live at the finest geometric detail (a hole edge, a fillet).
                    So it is the right tool to see the pattern and the wrong tool
                    for the extreme value. The scalar ensemble is trained
                    directly on the peaks.
                  </>
                ),
              },
              {
                q: "Can I trust an optimization result?",
                a: (
                  <>
                    The finalist designs are only as good as the limits you set
                    and the surrogate accuracy. When verification is enabled,
                    every finalist is solved with the real solver, which turns
                    the result from "predicted feasible" into "verified
                    feasible". Always add your own safety margin on top of a
                    limit.
                  </>
                ),
              },
              {
                q: "What happens if I change the design after verifying it?",
                a: (
                  <>
                    The app notices and warns you that the comparison belongs to
                    the previous geometry. Re-run to verify the current design
                    — nothing silently carries over.
                  </>
                ),
              },
              {
                q: "Does the app need the internet?",
                a: (
                  <>
                    No. The web app, the API, the models and the bundled
                    CalculiX solver all run locally. The desktop build opens the
                    same app in a native window.
                  </>
                ),
              },
              {
                q: "Is this ready to use at work?",
                a: (
                  <>
                    It is a demonstration of a trustworthy engineering-AI
                    workflow, not a certified analysis product. Read the{" "}
                    <DocLink to="/manual/limitations">limits page</DocLink>{" "}
                    first; every prediction it shows is designed to be verified
                    with the real solver before any safety-relevant use.
                  </>
                ),
              },
            ]}
          />
        </PanelBody>
      </Panel>
    </>
  ),
};
