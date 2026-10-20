"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, AlertTriangle, Calendar } from "lucide-react";

export default function DashboardHome() {
  const { data: competitors, isLoading: isLoadingComp } = useQuery({
    queryKey: ["competitors"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/dashboard/competitors");
      return res.data;
    },
  });

  const { data: briefings, isLoading: isLoadingBrief } = useQuery({
    queryKey: ["briefings"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/dashboard/briefings");
      return res.data;
    },
  });

  const activeCount = competitors?.length || 0;
  
  // Calculate highest threat from recent briefings
  let overallThreat = "LOW";
  let threatColor = "text-green-500";
  if (briefings && briefings.length > 0) {
    const recent = briefings.slice(0, 5);
    if (recent.some((b: any) => b.insight_json?.threat_level === "HIGH")) {
      overallThreat = "HIGH";
      threatColor = "text-red-500";
    } else if (recent.some((b: any) => b.insight_json?.threat_level === "MEDIUM")) {
      overallThreat = "MEDIUM";
      threatColor = "text-orange-500";
    }
  }

  // Nothing in the repository schedules the run (n8n or another scheduler calls the webhook), so
  // show when the last briefing was made rather than guessing the next one.
  const lastBriefing = briefings && briefings.length > 0
    ? new Date(briefings[0].scrape_date).toLocaleDateString()
    : "None yet";

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
      
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Competitors</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoadingComp ? "-" : activeCount}</div>
            <p className="text-xs text-muted-foreground">Tracking {activeCount} competitors</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overall Threat Level</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${threatColor}`}>
              {isLoadingBrief ? "-" : overallThreat}
            </div>
            <p className="text-xs text-muted-foreground">Based on latest briefings</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Last Briefing</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoadingBrief ? "-" : lastBriefing}</div>
            <p className="text-xs text-muted-foreground">{briefings?.length || 0} competitor briefings so far</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
