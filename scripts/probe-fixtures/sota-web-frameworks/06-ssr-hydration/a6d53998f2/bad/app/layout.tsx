export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><div suppressHydrationWarning>{children}</div></body></html>
}
