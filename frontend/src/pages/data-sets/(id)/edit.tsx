import { EditDataSetForm } from "@/components/data-sets/edit-data-set-form.tsx";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { PERMISSIONS } from "@/lib/permissions.ts";

export function EditDataSet() {
  const { hasPermission } = useApplicationContext()!;
  const canChangeDataSets = hasPermission(PERMISSIONS.DATASET.CHANGE);

  return (
    <PageMain>
      <PageHeading
        title={canChangeDataSets ? "Edit Data Set" : "Data Set"}
        description={canChangeDataSets
          ? "Update your data set configuration."
          : "Your data set's configuration."}
      />
      <EditDataSetForm />
    </PageMain>
  )
}
