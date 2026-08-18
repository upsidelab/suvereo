import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { useNavigate } from "react-router-dom";
import { PERMISSIONS } from "@/lib/permissions.ts";

export function DataSetList() {
  const {dataSets, hasPermission} = useApplicationContext()!;
  const canCreateDataSets = hasPermission(PERMISSIONS.DATASET.ADD);
  const canEditDataSets = hasPermission(PERMISSIONS.DATASET.CHANGE);
  const canAssignRoles = hasPermission(PERMISSIONS.DATASET_ROLE.ASSIGN);
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
              <TableCell width="75%">
                {item.name}
              </TableCell>
              <TableCell className="flex space-x-4" width="25%">
                {canAssignRoles &&
                  <Button onClick={() => {
                    navigate(`/data-sets/${item.id}/users`)
                  }} variant="secondary">Manage Access</Button>
                }
              </TableCell>
              <TableCell>
                <Button onClick={() => {
                  navigate(`/data-sets/${item.id}/integrations`)
                }} variant="secondary">Sources</Button>
              </TableCell>
              <TableCell>
                {canEditDataSets &&
                  <Button onClick={() => {
                    navigate(`/data-sets/${item.id}/edit`)
                  }} variant="secondary">Edit</Button>
                }
              </TableCell>
             </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}
