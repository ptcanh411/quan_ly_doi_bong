import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FC 6H Sáng Chủ Nhật - Quản Lý Quỹ & Điểm Danh",
  description: "Hệ thống quản lý quỹ, điểm danh, chia tiền sân & lập lịch trận đấu cho FC 6h Chủ Nhật",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="antialiased min-h-screen bg-slate-50 text-slate-900 pb-16 md:pb-0">
        {children}
      </body>
    </html>
  );
}
