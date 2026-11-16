import { Link, useParams } from "react-router-dom";

import { Chip, Panel, PanelBody } from "../../components/ui";
import { ManualFooterNav, ManualLayout } from "./ManualLayout";
import { groupLabel } from "./model";
import { articleById, manualNeighbours } from "./registry";

export function ManualArticlePage() {
  const params = useParams();
  const slug = params.slug ?? "";
  const article = articleById(slug);

  if (!article) {
    return (
      <ManualLayout
        kicker="Documentation"
        title="That page does not exist"
        description="The manual address may be out of date."
      >
        <Panel>
          <PanelBody className="space-y-2">
            <p className="text-xs leading-relaxed text-ink-muted">
              No manual page matches "{slug}". Return to the{" "}
              <Link to="/manual" className="text-link hover:underline">
                documentation home
              </Link>{" "}
              to pick a topic.
            </p>
          </PanelBody>
        </Panel>
      </ManualLayout>
    );
  }

  const { previous, next } = manualNeighbours(article.id);

  return (
    <ManualLayout
      kicker={`Documentation · ${groupLabel(article.group)}`}
      title={article.title}
      description={article.summary}
      actions={<Chip tone="neutral">{article.minutes} min read</Chip>}
    >
      {article.body}
      <ManualFooterNav previous={previous} next={next} />
    </ManualLayout>
  );
}
