import { DataSetAccessList } from "@/components/data-sets/data-set-access-list.tsx";
import { useParams } from "react-router-dom";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";

export function IndexDataSetUsers() {
  const {id} = useParams();
  const dataSetId = Number(id);

  return (
    <PageMain>
      <PageHeading title="Manage Data Set Access"
                   description="Control access to this data set by granting a role to individual users or whole groups."/>
      <DataSetAccessList dataSetId={dataSetId}/>
    </PageMain>
  )
}
