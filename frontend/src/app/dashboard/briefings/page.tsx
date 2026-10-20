"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { BriefingHistory } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";

export default function BriefingsList() {
  const { data: briefings, isLoading } = useQuery<BriefingHistory[]>({
    queryKey: ["briefings"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/dashboard/briefings");
      return res.data;
    },
  });

  const getThreatColor = (level: string) => {
    switch (level) {
      case "HIGH": return "bg-red-500 hover:bg-red-600";
      case "MEDIUM": return "bg-orange-500 hover:bg-orange-600";
      default: return "bg-green-500 hover:bg-green-600";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Briefings History</h1>
        <p className="text-muted-foreground">Review your past automated competitive intelligence reports.</p>
      </div>

      <div className="grid gap-4">
        {isLoading ? (
          [1, 2, 3].map((i) => <Skeleton key={i} className="h-32 w-full" />)
        ) : briefings?.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-10">
              <p className="text-muted-foreground">No briefings have been generated yet.</p>
            </CardContent>
          </Card>
        ) : (
          briefings?.map((b) => (
            <Link key={b.id} href={`/dashboard/briefings/${b.id}`}>
              <Card className="transition-all hover:bg-muted/50">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">{(b as any).competitor_name || "Competitor Insight"}</CardTitle>
                    <CardDescription>
                      Generated on {format(new Date(b.scrape_date), "PPP")}
                    </CardDescription>
                  </div>
                  <Badge className={getThreatColor(b.insight_json.threat_level)}>
                    {b.insight_json.threat_level} THREAT
                  </Badge>
                </CardHeader>
                <CardContent>
                  <p className="line-clamp-2 text-sm text-muted-foreground">
                    {b.insight_json.executive_summary}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
