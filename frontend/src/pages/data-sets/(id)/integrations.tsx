import { useParams } from "react-router-dom";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { IntegrationList } from "@/components/integrations/integration-list.tsx";

export function IndexDataSetIntegrations() {
  const { id } = useParams();
  const dataSetId = Number(id);

  return (
    <PageMain>
      <PageHeading title="Integrations" description="Add and configure integrations to import data." />
      <IntegrationList dataSetId={dataSetId} />
    </PageMain>
  )
}
