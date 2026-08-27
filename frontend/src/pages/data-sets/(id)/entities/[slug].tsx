import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { EntityTable } from "@/components/entities/entity-table.tsx";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { EntityType } from "@/lib/types.ts";
import { NotFound } from "@/pages/not-found.tsx";

const api = new ApiClient(authenticationProviderInstance);

export function EntityRecordsPage() {
  const { id, slug } = useParams<{ id: string; slug: string }>();
  const dataSetId = Number(id);
  const [entityType, setEntityType] = useState<EntityType | null>(null);
  const [isLoadingEntityType, setIsLoadingEntityType] = useState(true);

  useEffect(() => {
    api.entities().listTypes().then(types => {
      const found = types.find(t => t.slug === slug);
      setEntityType(found ?? null);
    }).catch(() => setEntityType(null)).finally(() => setIsLoadingEntityType(false));
  }, [slug]);

  if (isLoadingEntityType) {
    return null;
  }

  if (!entityType) {
    return <NotFound />;
  }

  return (
    <PageMain>
      <PageHeading title={entityType.label} description={`Browse ${entityType.label.toLowerCase()} in this data set.`} />
      <EntityTable dataSetId={dataSetId} entityType={entityType} />
    </PageMain>
  );
}
