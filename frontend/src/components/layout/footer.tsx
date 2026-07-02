import Link from "next/link";
import { Shield, Github, Twitter, Linkedin } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-12 md:grid-cols-4">
          <div className="md:col-span-2">
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-cyan-500">
                <Shield className="h-4 w-4 text-white" />
              </div>
              <span className="text-lg font-bold">
                Truth<span className="text-primary">Trace</span> AI
              </span>
            </Link>
            <p className="text-muted-foreground max-w-md text-sm leading-relaxed">
              Every answer with proof. AI-powered fact verification and trust
              analysis platform for the next generation of informed decisions.
            </p>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Product</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link href="/chat" className="hover:text-foreground transition-colors">Verify Facts</Link></li>
              <li><Link href="/dashboard" className="hover:text-foreground transition-colors">Dashboard</Link></li>
              <li><Link href="/#features" className="hover:text-foreground transition-colors">Features</Link></li>
              <li><Link href="/#how-it-works" className="hover:text-foreground transition-colors">How It Works</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold mb-4">Connect</h4>
            <div className="flex gap-3">
              {[Github, Linkedin].map((Icon, i) => (
                <a
                  key={i}
                 href={
                       i === 0
                       ? "https://github.com/SumerThakur3"
                       : "https://www.linkedin.com/in/sumer-thakur-2486b62a7/"
                       }
                  className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted hover:bg-primary hover:text-white transition-all"
                >
                  <Icon className="h-4 w-4" />
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t flex flex-col sm:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} TruthTrace AI. All rights reserved.</p>
          <p>Built with precision. Verified with proof.</p>
        </div>
      </div>
    </footer>
  );
}
