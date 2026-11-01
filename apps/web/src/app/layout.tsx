import './globals.css';

export const metadata = {
  title: 'DocFlow | Djinn Wish Pack',
  description: 'Precision Instrument on Paper - B2B Lending Document Platform',
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
