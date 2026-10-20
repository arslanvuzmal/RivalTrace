"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

export default function SettingsPage() {
  const { data: session } = useSession();
  const [slackUrl, setSlackUrl] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);

  const handleSaveSlack = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await apiClient.put(`/api/v1/dashboard/slack`, { slack_webhook_url: slackUrl });
      alert("Slack Webhook URL saved successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to save Slack Webhook URL.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleManageBilling = async () => {
    setIsRedirecting(true);
    try {
      const res = await apiClient.post(`/api/v1/billing/checkout/${session?.user?.id}`);
      if (res.data && res.data.checkout_url) {
        window.location.href = res.data.checkout_url;
      }
    } catch (err) {
      console.error(err);
      alert("Failed to initialize billing session.");
      setIsRedirecting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings & Billing</h1>
        <p className="text-muted-foreground">Manage your account preferences and subscription.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Slack Delivery</CardTitle>
          <CardDescription>
            Receive your weekly competitive intelligence briefings directly in your Slack workspace.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSaveSlack}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="slackUrl">Slack Webhook URL</label>
              <Input
                id="slackUrl"
                type="url"
                placeholder="https://hooks.slack.com/services/..."
                value={slackUrl}
                onChange={(e) => setSlackUrl(e.target.value)}
              />
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : "Save Preferences"}
            </Button>
          </CardFooter>
        </form>
      </Card>

      <Separator />

      <Card>
        <CardHeader>
          <CardTitle>Billing & Subscription</CardTitle>
          <CardDescription>
            You are subscribed to the $300/mo automated intelligence plan. Manage your payment methods or download invoices.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Billing is handled securely by Stripe.
          </p>
        </CardContent>
        <CardFooter>
          <Button variant="outline" onClick={handleManageBilling} disabled={isRedirecting}>
            {isRedirecting ? "Redirecting to Stripe..." : "Manage Billing"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
