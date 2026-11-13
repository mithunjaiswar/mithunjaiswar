Generators for the 4 dashboard tabs of "Zero & Low Deposit Monitoring Dashboard"
(1_Eye_View, 2_Daily_Trend, 3_Zero_Deposit, 4_Pilot_Journey) and the raw helper columns (CN:DC).
Output = Sheets API batchUpdate JSON. Formulas reference raw!$X$2:$X open ranges (tab renamed raw_pilot_week -> raw).
Extra raw formulas added by hand: DD:DG per-tab filter flags, DH:DU critical per day with the MasterTab rule,
CS/CT = latest-day pick of DH:DN / DO:DU.

daily6.py (Daily_Trend v6, manager review): Rent vs Paid uses only money paid after Weekly OS is cleared;
Collection = Weekly OS + New OS this week = Total OS; Critical split by call disposition (dispo tab, from
../dispo_daily.sql, collections_queries row 73); Car Recovery pending buckets 0-2/3-5/6-7/8-14/15+, TAT, and
Deposit Used Up merged in; 0 Deposit Cut and 0 Deposit join funnel removed; non-funnel rows in Join Funnel;
new Bad Debt section (active / joined-and-left / weekly-collection-left). Raw helpers EA:ED (first active day,
last live OS, owed above deposit, week|ID key). Layout: dates row 9, data from row 10, city wildcard $Z$1.
