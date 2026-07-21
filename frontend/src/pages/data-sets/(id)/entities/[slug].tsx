import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { EntityTable } from "@/components/entities/entity-table.tsx";
import { ApiClient } from "@/lib/api.ts";
import { EntityType } from "@/lib/types.ts";

const api = new ApiClient();

export function EntityRecordsPage() {
  const { id, slug } = useParams<{ id: string; slug: string }>();
  const dataSetId = Number(id);
  const [entityType, setEntityType] = useState<EntityType | null>(null);

  useEffect(() => {
    api.entities().listTypes().then(types => {
      const found = types.find(t => t.slug === slug);
      setEntityType(found ?? null);
    });
  }, [slug]);

  if (!entityType) {
    return null;
  }

  return (
    <PageMain>
      <PageHeading title={entityType.label} description={`Browse ${entityType.label.toLowerCase()} in this dataset.`} />
      <EntityTable dataSetId={dataSetId} entityType={entityType} />
    </PageMain>
  );
}
