import { Claim, Provider, Cluster } from './types';

export const providers: Provider[] = [
  { id: 'PRV-1029', name: 'Vision Center Excellence', specialty: 'Optometry', riskScore: 89, claimCount: 450, highRiskRatio: 0.28, totalAllowedAmount: 145000, city: 'Miami', state: 'FL' },
  { id: 'PRV-8834', name: 'ClearSight Associates', specialty: 'Ophthalmology', riskScore: 94, claimCount: 320, highRiskRatio: 0.35, totalAllowedAmount: 210500, city: 'Las Vegas', state: 'NV' },
  { id: 'PRV-5102', name: 'Downtown Eye Care', specialty: 'Optometry', riskScore: 24, claimCount: 890, highRiskRatio: 0.02, totalAllowedAmount: 89000, city: 'Chicago', state: 'IL' },
  { id: 'PRV-3391', name: 'Advanced Glaucoma Group', specialty: 'Ophthalmology', riskScore: 78, claimCount: 156, highRiskRatio: 0.19, totalAllowedAmount: 180200, city: 'New York', state: 'NY' },
  { id: 'PRV-7721', name: 'Family Vision Clinic', specialty: 'Optometry', riskScore: 45, claimCount: 650, highRiskRatio: 0.08, totalAllowedAmount: 72000, city: 'Austin', state: 'TX' },
];

export const clusters: Cluster[] = [
  { 
    id: 'CL-01', 
    name: 'Phantom Billing - Premium Frames', 
    description: 'Claims exhibiting patterns of billing for premium frames or designer lenses that were never dispensed to the patient.',
    claimCount: 142, 
    avgFraudScore: 88, 
    avgAllowedAmount: 450.50, 
    commonProcedures: ['V2118', 'V2784'],
    avgMemberAge: 42,
    commonFraudIndicators: ['High velocity billing', 'Out of state members', 'Zero follow-up visits'],
    riskCharacteristics: 'High concentration of codes V2118, V2784 combined with maximum benefit utilization. Often associated with newly registered providers.'
  },
  { 
    id: 'CL-02', 
    name: 'Upcoding - Comprehensive Exams', 
    description: 'Routine vision checks systematically upcoded to comprehensive medical eye exams to maximize reimbursement.',
    claimCount: 315, 
    avgFraudScore: 76, 
    avgAllowedAmount: 210.00, 
    commonProcedures: ['92004', '92014'],
    avgMemberAge: 35,
    commonFraudIndicators: ['Code clustering', 'Improbable diagnosis combos', 'High volume per day'],
    riskCharacteristics: 'Statistically improbable number of 92004/92014 codes compared to peer group averages. Often billed without corresponding complex diagnosis.'
  },
  { 
    id: 'CL-03', 
    name: 'Unbundling - Glaucoma Screening', 
    description: 'Separating bundled screening procedures into individual components to bypass maximum allowable charges.',
    claimCount: 85, 
    avgFraudScore: 92, 
    avgAllowedAmount: 380.25, 
    commonProcedures: ['92250', '92134'],
    avgMemberAge: 68,
    commonFraudIndicators: ['Sequential billing', 'Repeat unbundling', 'Modifier abuse'],
    riskCharacteristics: 'Same-day billing of multiple distinct structural imaging codes that should typically be bundled or mutually exclusive for the same patient encounter.'
  }
];

export const claims: Claim[] = [
  { id: 'CLM-9092831', providerId: 'PRV-8834', providerName: 'ClearSight Associates', memberId: 'MEM-44910', procedureCode: '92004', procedureDesc: 'Comprehensive Eye Exam', allowedAmount: 220.00, fraudScore: 96, riskLevel: 'Critical', fraudType: 'Upcoding', clusterId: 'CL-02', date: '2026-05-28', status: 'Flagged' },
  { id: 'CLM-7718290', providerId: 'PRV-1029', providerName: 'Vision Center Excellence', memberId: 'MEM-88212', procedureCode: 'V2784', procedureDesc: 'Premium Lens Addition', allowedAmount: 495.00, fraudScore: 89, riskLevel: 'High', fraudType: 'Phantom Billing', clusterId: 'CL-01', date: '2026-06-01', status: 'Investigating' },
  { id: 'CLM-3310928', providerId: 'PRV-3391', providerName: 'Advanced Glaucoma Group', memberId: 'MEM-11029', procedureCode: '92250', procedureDesc: 'Fundus Photography', allowedAmount: 185.00, fraudScore: 91, riskLevel: 'Critical', fraudType: 'Unbundling', clusterId: 'CL-03', date: '2026-06-03', status: 'Flagged' },
  { id: 'CLM-1092834', providerId: 'PRV-5102', providerName: 'Downtown Eye Care', memberId: 'MEM-55102', procedureCode: '92012', procedureDesc: 'Intermediate Eye Exam', allowedAmount: 85.00, fraudScore: 12, riskLevel: 'Low', fraudType: null, clusterId: 'CL-00', date: '2026-06-02', status: 'Cleared' },
  { id: 'CLM-8819237', providerId: 'PRV-1029', providerName: 'Vision Center Excellence', memberId: 'MEM-77382', procedureCode: 'V2118', procedureDesc: 'Designer Frame', allowedAmount: 380.00, fraudScore: 82, riskLevel: 'High', fraudType: 'Phantom Billing', clusterId: 'CL-01', date: '2026-06-01', status: 'Pending' },
  { id: 'CLM-6629108', providerId: 'PRV-7721', providerName: 'Family Vision Clinic', memberId: 'MEM-33019', procedureCode: '92014', procedureDesc: 'Comprehensive Est Exam', allowedAmount: 155.00, fraudScore: 68, riskLevel: 'Medium', fraudType: 'Upcoding', clusterId: 'CL-02', date: '2026-05-30', status: 'Pending' },
  { id: 'CLM-5510293', providerId: 'PRV-8834', providerName: 'ClearSight Associates', memberId: 'MEM-99201', procedureCode: '92134', procedureDesc: 'Retina OCT', allowedAmount: 195.00, fraudScore: 94, riskLevel: 'Critical', fraudType: 'Unbundling', clusterId: 'CL-03', date: '2026-06-02', status: 'Flagged' },
  { id: 'CLM-4418293', providerId: 'PRV-5102', providerName: 'Downtown Eye Care', memberId: 'MEM-11293', procedureCode: 'V2020', procedureDesc: 'Standard Frame', allowedAmount: 55.00, fraudScore: 8, riskLevel: 'Low', fraudType: null, clusterId: 'CL-00', date: '2026-06-03', status: 'Cleared' },
];

export const fraudTrendData = [
  { month: 'Jan', fraudAmount: 12000, claims: 450 },
  { month: 'Feb', fraudAmount: 15000, claims: 520 },
  { month: 'Mar', fraudAmount: 18000, claims: 610 },
  { month: 'Apr', fraudAmount: 24000, claims: 750 },
  { month: 'May', fraudAmount: 22000, claims: 720 },
  { month: 'Jun', fraudAmount: 35000, claims: 980 },
];
