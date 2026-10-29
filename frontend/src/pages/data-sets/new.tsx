import { CreateDataSetForm } from "@/components/data-sets/create-data-set-form.tsx";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";

export function NewDataSet() {
  return (
    <PageMain>
      <PageHeading title="Create Data Set" description="Organize your content with data sets." />
      <CreateDataSetForm/>
    </PageMain>
  )
}
