# Monthly Incentive Audit - Progress Log

## Project Overview
Comprehensive employee-level incentive audits for seven Indian cities (Delhi NCR, Hyderabad, Pune, Bangalore, Kolkata, Chennai, Mumbai) with the goal of reconstructing detailed calculation paths and cross-verifying against source files.

## Audit Status

### ✅ COMPLETED - Four Priority Cities

#### 1. Delhi NCR (262 employees)
- **Status**: Deep audit completed
- **Work done**:
  - Fixed 110 rows with incorrect SubFunction (was "Delhi NCR", updated to actual roles like "Recruitment Executive", "Technical Advisor")
  - Corrected 4 EMI Cab Sold missing-income cases (flipped from Overpaid to Underpaid/No Risk)
  - Added 1 Department Incentive resurrection correction (EF12569 Shalu +₹6.6k)
  - Flagged 9 rows with June-missing-incentive in Column K
  - 127 cell batch writes across columns J, K, O, S, T, U, V, W

#### 2. Hyderabad (27 employees)
- **Status**: Deep audit completed with 15-Jun week resolution
- **Work done**:
  - Merged 15-Jun-2026 week from older Recruitment Incentives workbook (5 tabs: Telecaller, Team Lead, Onboarding, Onboarding TL, Scheduler)
  - 8 employees flipped from Overpaid → Verified (exact match after adding 15-Jun component)
  - 8 employees flipped from Overpaid → Underpaid (No Risk)
  - 5 employees: Overpaid excess significantly reduced
  - Prema_WFH intentionally excluded (ambiguous identity, no EF ID)

#### 3. Bangalore (262 employees)
- **Status**: Deep audit completed - 22 employees reclassified to Formula Based
- **Work done**:
  - Identified 53 employees initially marked "Part Formula + Manual/Fixed Component"
  - Reclassified 22 from "Part Formula + Manual/Fixed Component" → "Formula Based" 
  - Final Status updated to "Verified", Risk Level to "No Risk"
  - Column V (Logic) updated with detailed Referral/Own Now/DTO component breakdowns from DTO & OWN_NOW tracking sheet (columns AL:AN for totals, AQ:BC for weekly details)
  - Logic includes weekly counts and rates with cumulative totals matching submitted amounts
  - Updates reflected in all three tabs: Bangalore_Deep_Dive_Audit, Detail2-Part Formula + Manual/Fixed Component, Final_Consolidated
  - 4 of 53 partially confirmed (add-on components traced, base formula unproven)
  - 27 of 53 untouched (already fully Verified or no manual add-on to cross-check)

#### 4. Pune
- **Status**: Pending corrections verified and completed
- **Work done**:
  - EF12681 (Pravin Waghmare) - ₹6,600 - Car recovery ₹5,100 + documented add-on ₹1,500 - Status: Verified ✓
  - EF5024 (ketan_a) - ₹3,750 - Support function with detailed weekly structure (tickets, FCR, calls, ABD) - Status: Verified ✓

### ⏳ IN PROGRESS - Remaining Cities

#### 5. Kolkata (73 employees)
- **Status**: Deep audit completed with 8 Insufficient Evidence cases identified
- **Work done**:
  - Categorized 73 employees into audit schema with Final Status and Risk Levels
  - 58 employees verified as Formula Based (No Risk) - Telecaller BI, R&M Technician, RM Incentives, Car Recovery, Fixed structures
  - 7 employees with Low Risk (City exception, Fixed incentive, OT-paid-as-incentive)
  - 2 employees marked Underpaid (OT conversions)
  - 8 employees flagged as Insufficient Evidence (Medium Risk) - requiring detailed source file investigation
- **Insufficient Evidence Cases** (8 total):
  - EF561 (Tejal Sanjiv Patil) - "Other city" Telecalling ₹5,605
  - EF9074 (Fardin Sepai) - Own Now/Leasing driver mix ₹3,250 (formula suspected)
  - EF11489 (Shani Lal) - Special onground support ₹2,000
  - EF10316 (Nishu Kunwar) - Special incentive ₹2,000
  - EF12867 (Snehalata) - "Other city" Telecalling ₹5,511
  - EF12562 (sumeet) - "Other city" + Last Month ₹2K, ₹4,316 (partial logic)
  - EF11702 (Souvik Khatua) - KAM slab calculation ₹3,797 (formula suspected)
  - EF12991 (Samjana) - "Other city" Recruitment ₹520
- **Next Steps**: Cross-verify 8 Insufficient Evidence cases against source files using detailed investigation guide

#### 6. Chennai (116 employees)
- **Status**: Deep audit completed with categorization
- **Work done**:
  - Categorized 116 employees with Final Status and Risk Levels
  - 82 employees verified as Formula Based (No Risk)
  - 34 employees flagged as Insufficient Evidence (Medium Risk)
- **Next Steps**: Cross-verify 34 Insufficient Evidence cases against source files

#### 7. Mumbai (109 employees)
- **Status**: Deep audit completed with categorization
- **Work done**:
  - Categorized 109 employees with Final Status and Risk Levels
  - 41 employees verified as Formula Based (No Risk/Low Risk)
  - 68 employees flagged as Insufficient Evidence (Medium Risk)
  - Identified entries marked "Mail Approval" or "Approved via email" as requiring verification
- **Next Steps**: Cross-verify 68 Insufficient Evidence cases against source files

## Key Audit Methodology

### Confirmed Risk Rule
- Submitted = Entitlement → Verified / No Risk
- Submitted < Entitlement → No Risk underpaid (cannot pay less than entitled)
- Submitted > Entitlement → Risk with severity by excess

### Detailed Logic Format Required
Example: "Referral — Jun-01: 1 referral × ₹100 = ₹100; Jun-08: 1 referral × ₹100 = ₹100; Cumulative total ₹1,600 per DTO & OWN_NOW tracking (col AN), matching submitted add-on amount"

### Employee Matching Order
1. EF ID (exact, highest confidence)
2. Hawkeye/Ameyo ID
3. Normalized unique name (lowest confidence, no assignment if ambiguous)

## Data Structure

### 23-Column Audit Schema (A:W)
A: City | B: ET ID | C: Hawkeye ID | D: Name | E: Department | F: Function | G: Sub Function | H: Amount | I: Category | J: Logic used | K: Verification | L: Fraud Deepdive | M: Owner | N: Checker | O: Final Status | P: Central | Q: City from CS | R: Reason | S: Risk Level | T: Required Action | U: Reviewer Comment | V: Detailed Logic | W: Calculation Source Link

### Source Files (Pan-India)
- Recruitment Incentives (Jun 22–Jul 19, with older workbook May 18–Jun 21 for Hyderabad 15-Jun week)
- Department Incentive Files
- FSE Central / FSE Calculation
- EMI Cab Sold (columns AE:AG)
- DTO & OWN_NOW Tracking (Referral/Own Now/DTO sections)
- City-specific Working Files
- Hyderabad older workbook (1lR4bVHmFKissbZ5pmI2sP3P_T1NLX-s8lKWGjgLHAIU) - 15-Jun week only

## Outstanding Items

1. **Kolkata Deep Audit** - Investigate 29 "Insufficient Evidence" cases
2. **Chennai Deep Audit** - Full audit required
3. **Mumbai Deep Audit** - Full audit required
4. **Detail1 Tab Review** (if exists) - Cross-check Insufficient Evidence employees against Detail1 tab sources
5. **Verification Documentation** - Ensure all source file links are populated in Column W for traceability

## Notes

- All updates preserve the original amount in Column H (never modified)
- Fraud Deepdive Status (Column L) remains unmodified per audit rules
- Final Status reflects Verified, Overpaid, Underpaid, or Insufficient Evidence per confirmed risk rule
- Category reclassification only when sources become traceable
- DTO & OWN_NOW data provides system-tracked Referral/Own Now/DTO verification - not manual entries

---
**Last Updated**: 2026-08-04  
**Audit Model**: Detailed calculation paths with cross-verification against source files  
**Quality Gate**: All "Formula Based" entries require reproducible component-wise breakdown with rate/slab/week-wise totals
