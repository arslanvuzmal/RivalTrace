"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Competitor } from "@/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Trash2 } from "lucide-react";
import AddCompetitorModal from "@/components/competitors/add-competitor-modal";

export default function CompetitorsPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: competitors, isLoading } = useQuery<Competitor[]>({
    queryKey: ["competitors"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/dashboard/competitors");
      return res.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/api/v1/dashboard/competitors/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["competitors"] });
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Competitors</h1>
          <p className="text-muted-foreground">Manage the companies you are tracking.</p>
        </div>
        <Button onClick={() => setIsModalOpen(true)}>Add Competitor</Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Website</TableHead>
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center">
                  <Skeleton className="h-8 w-full" />
                </TableCell>
              </TableRow>
            ) : competitors?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-10 text-muted-foreground">
                  No competitors added yet. Click "Add Competitor" to start tracking.
                </TableCell>
              </TableRow>
            ) : (
              competitors?.map((comp) => (
                <TableRow key={comp.id}>
                  <TableCell className="font-medium">{comp.name}</TableCell>
                  <TableCell>
                    <a href={comp.website_url} target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">
                      {comp.website_url}
                    </a>
                  </TableCell>
                  <TableCell>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      onClick={() => {
                        if (confirm(`Stop tracking ${comp.name}?`)) {
                          deleteMutation.mutate(comp.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <AddCompetitorModal open={isModalOpen} onOpenChange={setIsModalOpen} />
    </div>
  );
}
