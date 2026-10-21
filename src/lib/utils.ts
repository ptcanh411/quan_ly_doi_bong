import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatCompact(amount: number, showSign = false): string {
  if (amount === 0) return "0k";
  const inK = Math.round(amount / 1000);
  const sign = showSign && inK > 0 ? "+" : "";
  return `${sign}${inK}k`;
}

export function getNextSunday(fromDate = new Date()): Date {
  const date = new Date(fromDate);
  const day = date.getDay(); // 0 is Sunday
  const diff = (7 - day) % 7 || 7;
  date.setDate(date.getDate() + diff);
  date.setHours(6, 0, 0, 0);
  return date;
}

export function formatDateVi(dateInput: string | Date): string {
  const d = new Date(dateInput);
  const daysOfWeek = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
  const dayName = daysOfWeek[d.getDay()];
  const day = d.getDate();
  const month = d.getMonth() + 1;
  return `${dayName} ${day}/${month}`;
}

export function generateVietQRUrl(
  bankCode: string,
  accountNo: string,
  accountHolder: string,
  amount: number,
  description: string
): string {
  const sanitizedAmount = Math.max(0, Math.round(amount));
  const encodedDesc = encodeURIComponent(description);
  const encodedHolder = encodeURIComponent(accountHolder);
  return `https://img.vietqr.io/image/${bankCode}-${accountNo}-compact2.png?amount=${sanitizedAmount}&addInfo=${encodedDesc}&accountName=${encodedHolder}`;
}
