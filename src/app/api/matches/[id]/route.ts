import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    const match = await prisma.match.findUnique({
      where: { id },
      include: {
        records: {
          include: {
            player: true,
          },
        },
      },
    });

    if (!match) {
      return NextResponse.json({ error: "Không tìm thấy trận đấu" }, { status: 404 });
    }

    return NextResponse.json(match);
  } catch (error: any) {
    console.error("GET /api/matches/[id] error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    const body = await req.json();
    const {
      title,
      matchDate,
      timeSlot,
      stadiumName,
      pitchFee,
      drinksFee,
      defaultDrinkPerPerson,
      status,
      notes,
      playerRecords, // Array of { playerId, isPresent, hasDrinks, drinkAmount, pitchShare, feeCharged, addedDeposit, note }
    } = body;

    const updatedMatch = await prisma.match.update({
      where: { id },
      data: {
        ...(title !== undefined && { title }),
        ...(matchDate !== undefined && { matchDate: new Date(matchDate) }),
        ...(timeSlot !== undefined && { timeSlot }),
        ...(stadiumName !== undefined && { stadiumName }),
        ...(pitchFee !== undefined && { pitchFee: Number(pitchFee) }),
        ...(drinksFee !== undefined && { drinksFee: Number(drinksFee) }),
        ...(defaultDrinkPerPerson !== undefined && { defaultDrinkPerPerson: Number(defaultDrinkPerPerson) }),
        totalCost: (Number(pitchFee) || 0) + (Number(drinksFee) || 0),
        ...(status !== undefined && { status }),
        ...(notes !== undefined && { notes }),
      },
    });

    if (Array.isArray(playerRecords)) {
      for (const rec of playerRecords) {
        await prisma.matchPlayerRecord.upsert({
          where: {
            matchId_playerId: {
              matchId: id,
              playerId: rec.playerId,
            },
          },
          update: {
            isPresent: Boolean(rec.isPresent),
            hasDrinks: Boolean(rec.hasDrinks),
            drinkAmount: Number(rec.drinkAmount) || 0,
            pitchShare: Number(rec.pitchShare) || 0,
            feeCharged: Number(rec.feeCharged) || 0,
            addedDeposit: Number(rec.addedDeposit) || 0,
            note: rec.note || null,
          },
          create: {
            matchId: id,
            playerId: rec.playerId,
            isPresent: Boolean(rec.isPresent),
            hasDrinks: Boolean(rec.hasDrinks),
            drinkAmount: Number(rec.drinkAmount) || 0,
            pitchShare: Number(rec.pitchShare) || 0,
            feeCharged: Number(rec.feeCharged) || 0,
            addedDeposit: Number(rec.addedDeposit) || 0,
            note: rec.note || null,
          },
        });
      }
    }

    return NextResponse.json({ success: true, match: updatedMatch });
  } catch (error: any) {
    console.error("PUT /api/matches/[id] error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    await prisma.match.delete({
      where: { id },
    });
    return NextResponse.json({ success: true, message: "Đã xóa trận đấu thành công" });
  } catch (error: any) {
    console.error("DELETE /api/matches/[id] error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
