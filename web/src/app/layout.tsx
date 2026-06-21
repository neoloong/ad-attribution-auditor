import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Playfair_Display } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const playfairDisplay = Playfair_Display({
  variable: "--font-heading",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Ad Attribution Auditor — Don't let Big Tech grade their own homework",
  description:
    "Independent ad attribution auditing tool. Cross-reference Meta Ads & Google Ads against Shopify orders to calculate true incremental ROAS. De-duplication, cannibalization detection, and health alerts.",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "Ad Attribution Auditor",
    description:
      "Don't let Big Tech grade their own homework. Audit your ad platform attribution claims.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${playfairDisplay.variable} ${jetbrainsMono.variable} h-full antialiased scroll-smooth`}
    >
      <body className="min-h-full flex flex-col">
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
