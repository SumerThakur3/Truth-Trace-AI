import { Shield } from "lucide-react";

export default function Loading() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4">
      <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-primary to-cyan-500 flex items-center justify-center animate-pulse">
        <Shield className="h-6 w-6 text-white" />
      </div>
      <p className="text-muted-foreground text-sm">Loading TruthTrace...</p>
    </div>
  );
}
