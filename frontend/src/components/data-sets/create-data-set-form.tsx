import { useNavigate } from "react-router-dom";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { DataSetForm } from "./data-set-form.tsx";
import { DataSetFormSchema } from "./data-set-form-schema.ts";
import { PERMISSIONS } from "@/lib/permissions.ts";

const api = new ApiClient(authenticationProviderInstance);

export interface CreateDataSetFormProps {
  isOnboarding?: boolean;
}

export function CreateDataSetForm({ isOnboarding = false }: CreateDataSetFormProps) {
  const {setDataSetId, hasPermission} = useApplicationContext()!;
  const navigate = useNavigate();

  const submitLabel = isOnboarding ? "Continue" : "Create"

  const handleSubmit = async (values: DataSetFormSchema) => {
    const createdDataSetId = await api.dataSets().createDataSet({ ...values }, values.preconfigureAgents);
    setDataSetId(createdDataSetId);
    navigate(hasPermission(PERMISSIONS.INTEGRATION.VIEW)
      ? `/data-sets/${createdDataSetId}/integrations`
      : '/data-sets');
  };

  return (
    <DataSetForm
      onSubmit={handleSubmit}
      isOnboarding={isOnboarding}
      submitButtonText={submitLabel}
    />
  );
}
