import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { useNavigate } from "react-router-dom";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";

export function DataSetList() {
  const {dataSets, hasPermission, hasDataSetPermission} = useApplicationContext()!;
  const canCreateDataSets = hasPermission(PERMISSIONS.DATA_SET.ADD);
  const canEditDataSets = hasPermission(PERMISSIONS.DATA_SET.CHANGE);
  const canAssignRoles = hasPermission(PERMISSIONS.DATA_SET_ROLE.ASSIGN);
  const canViewSources = (dataSetId: number) => hasDataSetPermission(PERMISSIONS.INTEGRATION.VIEW, dataSetId);
  const navigate = useNavigate();

  return (
    <>
      {canCreateDataSets &&
        <div className="flex flex-row justify-end items-center space-x-4 mb-4">
          <Button variant="default" onClick={() => navigate('/data-sets/new') }>New Data Set</Button>
        </div>
      }
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {dataSets.map((item, index) => (
            <TableRow key={index}>
              <TableCell width="100%">
                {item.name}
              </TableCell>
              <TableCell className="flex space-x-4 whitespace-nowrap">
                {canAssignRoles &&
                  <Button onClick={() => {
                    navigate(`/data-sets/${item.id}/users`)
                  }} variant="secondary">Manage Access</Button>
                }
                {canViewSources(item.id!) &&
                  <Button onClick={() => {
                    navigate(`/data-sets/${item.id}/integrations`)
                  }} variant="secondary">Sources</Button>
                }
                <Button onClick={() => {
                  navigate(`/data-sets/${item.id}/edit`)
                }} variant="secondary">{canEditDataSets ? "Edit" : "View"}</Button>
              </TableCell>
             </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}
