import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  try {
    let config = await prisma.clubConfig.findUnique({
      where: { id: "default" },
    });

    if (!config) {
      config = await prisma.clubConfig.create({
        data: {
          id: "default",
          clubName: "FC 6H SÁNG CHỦ NHẬT",
          bankCode: "MB",
          bankAccount: "0987654321",
          accountHolder: "NGUYEN VAN THU QUY",
          defaultTimeSlot: "06:00 - 07:30",
        },
      });
    }

    return NextResponse.json(config);
  } catch (error: any) {
    console.error("GET /api/config error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function PUT(req: Request) {
  try {
    const body = await req.json();
    const { clubName, bankCode, bankAccount, accountHolder, defaultTimeSlot } = body;

    const updated = await prisma.clubConfig.upsert({
      where: { id: "default" },
      update: {
        ...(clubName !== undefined && { clubName }),
        ...(bankCode !== undefined && { bankCode }),
        ...(bankAccount !== undefined && { bankAccount }),
        ...(accountHolder !== undefined && { accountHolder }),
        ...(defaultTimeSlot !== undefined && { defaultTimeSlot }),
      },
      create: {
        id: "default",
        clubName: clubName || "FC 6H SÁNG CHỦ NHẬT",
        bankCode: bankCode || "MB",
        bankAccount: bankAccount || "0987654321",
        accountHolder: accountHolder || "NGUYEN VAN THU QUY",
        defaultTimeSlot: defaultTimeSlot || "06:00 - 07:30",
      },
    });

    return NextResponse.json(updated);
  } catch (error: any) {
    console.error("PUT /api/config error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
