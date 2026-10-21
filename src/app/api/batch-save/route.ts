import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { updates } = body; // Array of { matchId, playerId, addedDeposit, feeCharged }

    if (!Array.isArray(updates)) {
      return NextResponse.json({ error: "Dữ liệu cập nhật không hợp lệ" }, { status: 400 });
    }

    for (const item of updates) {
      await prisma.matchPlayerRecord.upsert({
        where: {
          matchId_playerId: {
            matchId: item.matchId,
            playerId: item.playerId,
          },
        },
        update: {
          ...(item.addedDeposit !== undefined && { addedDeposit: Number(item.addedDeposit) || 0 }),
          ...(item.feeCharged !== undefined && {
            feeCharged: Number(item.feeCharged) || 0,
            isPresent: Number(item.feeCharged) > 0,
          }),
        },
        create: {
          matchId: item.matchId,
          playerId: item.playerId,
          addedDeposit: Number(item.addedDeposit) || 0,
          feeCharged: Number(item.feeCharged) || 0,
          isPresent: Number(item.feeCharged) > 0,
        },
      });
    }

    return NextResponse.json({ success: true, count: updates.length });
  } catch (error: any) {
    console.error("POST /api/batch-save error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
