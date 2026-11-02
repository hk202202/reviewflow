import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ReviewFlow — AI-Powered Review Management for E-Commerce",
  description: "Manage reviews across Amazon, Flipkart, Myntra, Google Business with AI-powered replies. Save time, improve ratings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body className={inter.className}>{children}</body></html>;
}
