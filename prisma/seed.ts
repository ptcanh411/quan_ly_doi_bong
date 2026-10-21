import { PrismaClient } from "@prisma/client";
import fs from "fs";
import path from "path";

const prisma = new PrismaClient();

async function main() {
  console.log("Seeding database...");

  // 1. Club Config
  await prisma.clubConfig.upsert({
    where: { id: "default" },
    update: {},
    create: {
      id: "default",
      clubName: "FC 6H SÁNG CHỦ NHẬT",
      bankCode: "MB",
      bankAccount: "0987654321",
      accountHolder: "NGUYEN VAN THU QUY",
      defaultTimeSlot: "06:00 - 07:30",
    },
  });

  // Read seed_data.json
  const seedDataPath = path.join(process.cwd(), "seed_data.json");
  const rawData = fs.readFileSync(seedDataPath, "utf-8");
  const playersData = JSON.parse(rawData);

  // 2. Define historical matches
  const matchConfigs = [
    { key: "19/9", date: new Date("2024-09-19T06:00:00Z"), title: "Trận CN 19/9", pitchFee: 308000, totalCost: 308000 },
    { key: "27/9", date: new Date("2024-09-27T06:00:00Z"), title: "Trận CN 27/9", pitchFee: 170000, totalCost: 170000 },
    { key: "4/10", date: new Date("2024-10-04T06:00:00Z"), title: "Trận CN 4/10", pitchFee: 254000, totalCost: 254000 },
    { key: "11/10", date: new Date("2024-10-11T06:00:00Z"), title: "Trận CN 11/10", pitchFee: 330000, totalCost: 330000 },
    { key: "18/10", date: new Date("2024-10-18T06:00:00Z"), title: "Trận CN 18/10", pitchFee: 260000, totalCost: 260000 },
  ];

  // Clear existing records to ensure idempotent clean seed
  await prisma.matchPlayerRecord.deleteMany({});
  await prisma.match.deleteMany({});
  await prisma.depositTransaction.deleteMany({});
  await prisma.player.deleteMany({});

  const createdMatches: Record<string, string> = {};
  for (const m of matchConfigs) {
    const created = await prisma.match.create({
      data: {
        matchDate: m.date,
        title: m.title,
        timeSlot: "06:00 - 07:30",
        stadiumName: "Sân bóng 6h50",
        pitchFee: m.pitchFee,
        drinksFee: 0,
        defaultDrinkPerPerson: 10000,
        totalCost: m.totalCost,
        status: "COMPLETED",
        notes: "Trận đấu lịch sử từ bảng tính",
      },
    });
    createdMatches[m.key] = created.id;
  }

  // Next Sunday upcoming match
  const nextSunday = new Date();
  const day = nextSunday.getDay();
  const diff = (7 - day) % 7 || 7;
  nextSunday.setDate(nextSunday.getDate() + diff);
  nextSunday.setHours(6, 0, 0, 0);

  const upcomingMatch = await prisma.match.create({
    data: {
      matchDate: nextSunday,
      title: `Trận CN ${nextSunday.getDate()}/${nextSunday.getMonth() + 1}`,
      timeSlot: "06:00 - 07:30",
      stadiumName: "Sân bóng 6h50",
      pitchFee: 300000,
      drinksFee: 0,
      defaultDrinkPerPerson: 10000,
      totalCost: 300000,
      status: "SCHEDULED",
      notes: "Trận sắp tới - Chủ Nhật tuần này",
    },
  });

  // 3. Create Players & Match records
  let order = 0;
  for (const p of playersData) {
    order++;
    const player = await prisma.player.create({
      data: {
        name: p.name,
        nickname: p.name.includes(" ") ? p.name.split(" ").slice(1).join(" ") : null,
        initialDeposit: p.deposit,
        displayOrder: order,
        isActive: true,
      },
    });

    // Create records for completed matches
    for (const [matchKey, fee] of Object.entries(p.matches)) {
      const matchId = createdMatches[matchKey];
      if (matchId) {
        await prisma.matchPlayerRecord.create({
          data: {
            matchId: matchId,
            playerId: player.id,
            isPresent: true,
            hasDrinks: false,
            drinkAmount: 0,
            pitchShare: fee as number,
            feeCharged: fee as number,
            addedDeposit: 0,
          },
        });
      }
    }

    // Also link to upcoming match with default isPresent: false
    await prisma.matchPlayerRecord.create({
      data: {
        matchId: upcomingMatch.id,
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

  console.log("Seeding completed successfully!");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
