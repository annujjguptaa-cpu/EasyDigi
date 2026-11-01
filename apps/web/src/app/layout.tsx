import './globals.css';

export const metadata = {
  title: 'EasyDigi',
  description: 'EasyDigi — AI-powered lending document platform. Paper-first design. DPDPA-aligned consent.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-paper text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
