export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';

export interface Claim {
  id: string;
  providerId: string;
  providerName: string;
  memberId: string;
  procedureCode: string;
  procedureDesc: string;
  allowedAmount: number;
  fraudScore: number;
  riskLevel: RiskLevel;
  fraudType: string | null;
  clusterId: string;
  date: string;
  status: 'Pending' | 'Flagged' | 'Cleared' | 'Investigating';
}

export interface Provider {
  id: string;
  name: string;
  specialty: string;
  riskScore: number;
  claimCount: number;
  highRiskRatio: number;
  totalAllowedAmount: number;
  city: string;
  state: string;
}

export interface Cluster {
  id: string;
  name: string;
  description: string;
  claimCount: number;
  avgFraudScore: number;
  avgAllowedAmount: number;
  commonProcedures: string[];
  avgMemberAge: number;
  commonFraudIndicators: string[];
  riskCharacteristics: string;
}
