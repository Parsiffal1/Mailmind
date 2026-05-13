import "./globals.css";

export const metadata = {
  title: "MailMind",
  description: "Local-first Gmail task intelligence dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
