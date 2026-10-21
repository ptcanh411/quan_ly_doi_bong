export interface Player {
  id: string;
  name: string;
  nickname: string | null;
  phoneNumber: string | null;
  initialDeposit: number;
  isActive: boolean;
  displayOrder: number;
  createdAt: string;
  updatedAt: string;

  // Computed fields
  totalAddedDeposit?: number;
  totalPaid?: number;
  totalUsed?: number;
  balance?: number;
  matchRecords?: Record<string, MatchPlayerRecord>;
}

export interface MatchPlayerRecord {
  id: string;
  matchId: string;
  playerId: string;
  isPresent: boolean;
  hasDrinks: boolean;
  drinkAmount: number;
  pitchShare: number;
  feeCharged: number;
  addedDeposit: number;
  note: string | null;
}

export interface Match {
  id: string;
  matchDate: string;
  title: string | null;
  timeSlot: string;
  stadiumName: string | null;
  pitchFee: number;
  drinksFee: number;
  defaultDrinkPerPerson: number;
  totalCost: number;
  status: string;
  notes: string | null;
  records?: MatchPlayerRecord[];
  
  // Computed aggregations
  attendingCount?: number;
  drinksCount?: number;
  totalFeeCharged?: number;
  totalAddedDeposit?: number;
}

export interface ClubConfig {
  id: string;
  clubName: string;
  bankCode: string;
  bankAccount: string;
  accountHolder: string;
  defaultTimeSlot: string;
}

export interface ClubSummary {
  totalPaid: number;
  totalUsed: number;
  balance: number;
  debtorCount: number;
  activePlayersCount: number;
  completedMatchesCount: number;
}
