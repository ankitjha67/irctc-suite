import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "TrainPool — Group train booking, without the WhatsApp chaos",
    template: "%s · TrainPool",
  },
  description:
    "Collect passenger details from your group in one link. Paste the final block into IRCTC in one go. Not affiliated with IRCTC.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"),
  openGraph: {
    title: "TrainPool",
    description: "Group train booking coordination without the WhatsApp chaos.",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
