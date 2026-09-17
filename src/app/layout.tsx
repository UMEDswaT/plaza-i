import type {Metadata} from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ПЛАЗА-И',
  description: 'Лоиҳакашӣ, дизайн ва назорати муаллифӣ дар Душанбе'
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tj">
      <body>{children}</body>
    </html>
  );
}