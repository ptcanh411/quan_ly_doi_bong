import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getNextSunday, formatDateVi } from "@/lib/utils";

export async function GET() {
  try {
    const matches = await prisma.match.findMany({
      orderBy: { matchDate: "asc" },
      include: {
        records: {
          include: {
            player: {
              select: {
                id: true,
                name: true,
                nickname: true,
                isActive: true,
              },
            },
          },
        },
      },
    });

    const enrichedMatches = matches.map((match) => {
      const attendingCount = match.records.filter((r) => r.isPresent).length;
      const drinksCount = match.records.filter((r) => r.hasDrinks).length;
      const totalFeeCharged = match.records.reduce((sum, r) => sum + (r.feeCharged || 0), 0);
      const totalAddedDeposit = match.records.reduce((sum, r) => sum + (r.addedDeposit || 0), 0);

      return {
        ...match,
        attendingCount,
        drinksCount,
        totalFeeCharged,
        totalAddedDeposit,
      };
    });

    return NextResponse.json(enrichedMatches);
  } catch (error: any) {
    console.error("GET /api/matches error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    let { matchDate, title, timeSlot, stadiumName, pitchFee, drinksFee, defaultDrinkPerPerson, autoNextSunday } = body;

    let targetDate: Date;

    if (autoNextSunday) {
      // Find latest existing match date
      const latestMatch = await prisma.match.findFirst({
        orderBy: { matchDate: "desc" },
      });
      const baseDate = latestMatch ? new Date(latestMatch.matchDate) : new Date();
      targetDate = getNextSunday(baseDate);
    } else if (matchDate) {
      targetDate = new Date(matchDate);
    } else {
      targetDate = getNextSunday(new Date());
    }

    if (!title) {
      title = `Trận ${formatDateVi(targetDate)}`;
    }

    const match = await prisma.match.create({
      data: {
        matchDate: targetDate,
        title,
        timeSlot: timeSlot || "06:00 - 07:30",
        stadiumName: stadiumName || "Sân bóng 6h50",
        pitchFee: Number(pitchFee) || 0,
        drinksFee: Number(drinksFee) || 0,
        defaultDrinkPerPerson: Number(defaultDrinkPerPerson) || 10000,
        totalCost: (Number(pitchFee) || 0) + (Number(drinksFee) || 0),
        status: "SCHEDULED",
      },
    });

    // Populate empty records for all active players
    const players = await prisma.player.findMany({
      where: { isActive: true },
      select: { id: true },
    });

    for (const player of players) {
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

    return NextResponse.json(match, { status: 201 });
  } catch (error: any) {
    console.error("POST /api/matches error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
