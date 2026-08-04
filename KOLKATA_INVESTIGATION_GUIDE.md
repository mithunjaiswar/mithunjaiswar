# Kolkata Deep Audit - Investigation Guide

## Executive Summary
- **Total Employees**: 73
- **Verified (No Risk)**: 58
- **Low Risk**: 7
- **Medium Risk (Insufficient Evidence)**: 8
- **Underpaid**: 2

## Insufficient Evidence Cases - Requiring Investigation

All 8 cases below need cross-verification against source files (Recruitment Incentives, Department Incentives, DTO & OWN_NOW tracking, City-specific working files).

### 1. EF561 - Tejal Sanjiv Patil
- **Amount**: ₹5,605
- **Department**: Driver Acquisition | **Function**: Performance Marketing > Telecalling
- **Current Logic**: "Other city"
- **Investigation Required**:
  - Verify if this is a valid city exception or standard Telecaller calculation
  - Cross-check against Central Telecaller Incentive BI if applicable
  - Review Department budget allocation
- **Owner**: vishal.kumar@everestfleet.com

### 2. EF9074 - Fardin Sepai
- **Amount**: ₹3,250
- **Department**: Driver Operations | **Function**: Cash Collections and Performance > Telecalling
- **Current Logic**: "Majority Own Now Drivers mapped to him due to which the incentive is calculated less. For leasing his collection % is more so the final amount is give"
- **Investigation Required**:
  - Verify Own Now Driver count vs Leasing driver count
  - Cross-check against DTO & OWN_NOW tracking sheet (columns AL:AN for totals)
  - Verify collection % calculation basis
  - Reconcile actual amount with formula: (Own Now drivers × X% + Leasing drivers × Y%)
- **Owner**: vishal.kumar@everestfleet.com
- **Notes**: This appears to have a clear formula but needs detailed breakdown verification

### 3. EF11489 - Shani Lal
- **Amount**: ₹2,000
- **Department**: Driver Operations | **Function**: Onboarding > Allocation
- **Current Logic**: "Special incentive for onground support"
- **Investigation Required**:
  - Clarify what "onground support" means
  - Check if this is a fixed incentive or formula-based
  - Verify against Department Incentives file
  - Determine if this should be "Fixed" category
- **Owner**: vishal.kumar@everestfleet.com

### 4. EF10316 - Nishu Kunwar
- **Amount**: ₹2,000
- **Department**: Driver Operations | **Function**: EV > Operations
- **Current Logic**: "Special incentive"
- **Investigation Required**:
  - Identify specific basis of special incentive
  - Cross-check against Department Incentives or City-specific working files
  - Verify if this is recurring or one-time
  - Determine if there's a formula or if this is discretionary
- **Owner**: vishal.kumar@everestfleet.com

### 5. EF12867 - Snehalata_12867
- **Amount**: ₹5,511
- **Department**: Driver Acquisition | **Function**: Performance Marketing > Telecalling
- **Current Logic**: "Other city"
- **Investigation Required**:
  - Same as EF561 - verify "Other city" classification
  - Cross-check against Telecaller BI Central calculations
  - Determine if Kolkata Telecaller rates differ from other cities
- **Owner**: vishal.kumar@everestfleet.com

### 6. EF12562 - sumeet_12562
- **Amount**: ₹4,316
- **Department**: Driver Acquisition | **Function**: Performance Marketing > Telecalling
- **Current Logic**: "Other city Last Month 2K"
- **Investigation Required**:
  - Verify if this is "Other city" classification with additional ₹2K from last month
  - Cross-check against Telecaller BI Central for base amount
  - Verify date of last month addition and justification
- **Owner**: vishal.kumar@everestfleet.com
- **Notes**: Appears to have partial traceable logic (base + 2K add-on)

### 7. EF11702 - Souvik Khatua
- **Amount**: ₹3,797
- **Department**: Driver Acquisition | **Function**: Offline growth > Vendor Acquisition
- **Current Logic**: "KAM New slab Wise Calculation"
- **Investigation Required**:
  - Obtain KAM (Key Account Manager) slab definition
  - Get "New slab" rates and multipliers
  - Verify calculation: Amount broken down by slab × rate
  - Cross-check against Recruitment Incentives or City-specific working files
  - Determine if KAM has different commission structure
- **Owner**: vishal.kumar@everestfleet.com
- **Notes**: Logic mentions specific slab calculation - needs slab definition lookup

### 8. EF12991 - Samjana_12991
- **Amount**: ₹520
- **Department**: Recruitment | **Function**: Recruitment > Recruitment
- **Current Logic**: "Other city"
- **Investigation Required**:
  - Verify Recruitment incentive structure for Kolkata
  - Cross-check against Recruitment Incentives workbook
  - Determine if there's a standard Recruitment slab or fixed structure
  - Low amount suggests fixed payment or partial period calculation
- **Owner**: vishal.kumar@everestfleet.com

## Investigation Methodology

### Priority Sequence
1. **High Priority** (Traceable logic suspected):
   - EF9074 (Fardin Sepai) - Own Now/Leasing mix
   - EF11702 (Souvik Khatua) - KAM Slab calculation

2. **Medium Priority** (Source file lookup needed):
   - EF561, EF12867, EF12562 (Tejal, Snehalata, sumeet) - Telecaller/Other city
   - EF12991 (Samjana) - Recruitment

3. **Low Priority** (May remain as discretionary/insufficient):
   - EF11489 (Shani Lal) - Onground support
   - EF10316 (Nishu Kunwar) - Special incentive

### Source Files to Reference
- **Recruitment Incentives** (Jun 22–Jul 19): For Telecaller BI, Recruitment slab rates
- **Department Incentive Files**: For special/discretionary allowances
- **DTO & OWN_NOW Tracking**: Columns AL:AN for Referral/Own Now/DTO totals
- **City-specific Working Files**: Kolkata department/function-wise calculations
- **R&M Technician Incentive**: For any R&M related verification

### Documentation Format (for Column V - Detailed Logic)
Once verified, update Column V with:
```
[Category] — [Component]: [Calculation details]
Example: "Own Now Drivers — 45 drivers × collection%; Leasing drivers — 12 drivers × collection% = cumulative total ₹3,250"
```

## Notes
- All "Other city" entries need clarification on whether this represents a valid city exception or missing logic
- "Special incentive" entries require manager review to confirm discretionary nature or trace to source formula
- Two entries (EF9074, EF11702) appear to have partial formula logic but need detailed component breakdown
- Once verified, consider reclassifying to "Formula Based - [Type]" with corresponding "No Risk" or "Low Risk" status

---
**Date**: 2026-08-04  
**Auditor**: Claude  
**Status**: Investigation Guide for Kolkata Deep Audit Phase 2
