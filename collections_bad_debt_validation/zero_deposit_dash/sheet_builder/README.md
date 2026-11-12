Generators for the 4 dashboard tabs of "Zero & Low Deposit Monitoring Dashboard"
(1_Eye_View, 2_Daily_Trend, 3_Zero_Deposit, 4_Pilot_Journey) and the raw helper columns (CN:DC).
Output = Sheets API batchUpdate JSON. Formulas reference raw!$X$2:$X open ranges (tab renamed raw_pilot_week -> raw).
Extra raw formulas added by hand: DD:DG per-tab filter flags, DH:DU critical per day with the MasterTab rule,
CS/CT = latest-day pick of DH:DN / DO:DU.
