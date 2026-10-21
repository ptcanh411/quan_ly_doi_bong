import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function PUT(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    const body = await req.json();
    const { name, nickname, phoneNumber, initialDeposit, isActive } = body;

    const updated = await prisma.player.update({
      where: { id },
      data: {
        ...(name !== undefined && { name: name.trim() }),
        ...(nickname !== undefined && { nickname: nickname?.trim() || null }),
        ...(phoneNumber !== undefined && { phoneNumber: phoneNumber?.trim() || null }),
        ...(initialDeposit !== undefined && { initialDeposit: Number(initialDeposit) }),
        ...(isActive !== undefined && { isActive: Boolean(isActive) }),
      },
    });

    return NextResponse.json(updated);
  } catch (error: any) {
    console.error("PUT /api/players/[id] error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(
  req: Request,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params;
    // Hard delete with cascade or soft delete
    await prisma.player.delete({
      where: { id },
    });
    return NextResponse.json({ success: true, message: "Đã xóa thành viên thành công" });
  } catch (error: any) {
    console.error("DELETE /api/players/[id] error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
