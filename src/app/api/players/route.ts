import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  try {
    const players = await prisma.player.findMany({
      where: { isActive: true },
      orderBy: { displayOrder: "asc" },
      include: {
        matchRecords: true,
        deposits: true,
      },
    });

    const enrichedPlayers = players.map((player) => {
      // Sum added deposits from matches
      const matchAddedDeposits = player.matchRecords.reduce(
        (sum, r) => sum + (r.addedDeposit || 0),
        0
      );
      // Sum additional off-match deposits
      const otherDeposits = player.deposits.reduce(
        (sum, d) => sum + (d.amount || 0),
        0
      );
      const totalPaid = player.initialDeposit + matchAddedDeposits + otherDeposits;

      // Sum fees charged across matches
      const totalUsed = player.matchRecords.reduce(
        (sum, r) => sum + (r.feeCharged || 0),
        0
      );

      const balance = totalPaid - totalUsed;

      // Map match records by matchId for O(1) lookups
      const recordsByMatch: Record<string, any> = {};
      player.matchRecords.forEach((r) => {
        recordsByMatch[r.matchId] = r;
      });

      return {
        ...player,
        totalAddedDeposit: matchAddedDeposits,
        totalPaid,
        totalUsed,
        balance,
        matchRecords: recordsByMatch,
      };
    });

    return NextResponse.json(enrichedPlayers);
  } catch (error: any) {
    console.error("GET /api/players error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { name, nickname, phoneNumber, initialDeposit } = body;

    if (!name || !name.trim()) {
      return NextResponse.json(
        { error: "Tên thành viên là bắt buộc" },
        { status: 400 }
      );
    }

    const count = await prisma.player.count();
    const player = await prisma.player.create({
      data: {
        name: name.trim(),
        nickname: nickname?.trim() || null,
        phoneNumber: phoneNumber?.trim() || null,
        initialDeposit: Number(initialDeposit) || 0,
        displayOrder: count + 1,
      },
    });

    // Automatically create empty record for all matches so player immediately appears in all matches
    const allMatches = await prisma.match.findMany({ select: { id: true } });
    for (const match of allMatches) {
      await prisma.matchPlayerRecord.create({
        data: {
          matchId: match.id,
          playerId: player.id,
          isPresent: false,
          hasDrinks: false,
          drinkAmount: 0,
          pitchShare: 0,
          feeCharged: 0,
          addedDeposit: 0,
        },
      });
    }

    return NextResponse.json(player, { status: 201 });
  } catch (error: any) {
    console.error("POST /api/players error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
