// Zero sheet > raw_v2  ->  city Agent Tracking sheet > Calling_Masterlist
// 19-Nov: source changed from Agent_action (deleted) to raw_v2.
//   - raw_v2: header in row 2, data from row 4, 2 weeks of rows -> only the current (latest) week is printed.
//   - Columns are picked by raw_v2 header NAME (row 2), so a column move in raw_v2 does not break the sync.
//     If a header is not found the script stops with the missing names (nothing is written).
//   - Destination layout is NOT changed: A:BS data (C = agent_username, never written), BT:CD agent remarks.
//     Destination header rows 1-2 are kept as they are (not overwritten).
//   - target_trips (BF) and min_remaining_trips (BG) are not in raw_v2 -> left blank.
// Runs every time it is called (manual or trigger): re-prints raw_v2 and matches the BT:CD remarks by ID.
//   Skips only while the SQL query Automation is still writing raw_v2 (status not "GSHEET: SUCCESS" or
//   row count mismatch), so half-written data never wipes rows / remarks.
function syncHyderabadCallingMasterlist() {
  const SOURCE_ID = '1zsGMzqah8XCVfDM7f7R-BeNmK5DU5MxqTJ89xPJ25Sw';
  const SOURCE_TAB = 'raw_v2';
  const DEST_ID = '1AcbZbEU7UBPOgqNDIchN026w8CesbQlWKn61lrMy_ow';
  const CITY = 'hyderabad';

  const source = SpreadsheetApp.openById(SOURCE_ID).getSheetByName(SOURCE_TAB);
  const dest = SpreadsheetApp.openById(DEST_ID).getSheetByName('Calling_Masterlist');
  if (!source || !dest) throw new Error('Source ya destination tab nahi mila.');

  const clean = value => String(value ?? '').trim();

  // ---------- Destination column -> raw_v2 header ----------
  // Index 0 = A. null = left blank. 'C' (agent_username) is never written.
  const DEST_MAP = [
    /* A  week                          */ 'Week (Mon)',
    /* B  date                          */ '__REFRESH_DATE__',
    /* C  agent_username                */ null,
    /* D  partner_et_id                 */ 'Employee ID',
    /* E  lead_id                       */ 'Lead ID',
    /* F  partner_name                  */ 'Pilot Name',
    /* G  city                          */ 'City',
    /* H  product_type                  */ 'Product',
    /* I  elc_filter                    */ 'ELC / Non-ELC',
    /* J  car_numbers                   */ 'Car Numbers (now)',
    /* K  OS_Bucket                     */ 'OS Bucket',
    /* L  DP_Bucket                     */ 'Deposit Bucket Now',
    /* M  negative_os                   */ 'Weekly OS to Collect (Rs)',
    /* N  total_recovery                */ 'Collected This Week (Rs)',
    /* O  net_os                        */ 'Weekly OS Left (Rs)',
    /* P  recovery_pct                  */ 'Collection %',
    /* Q  razorpay_recovery             */ 'Razorpay (Rs)',
    /* R  other_recovery                */ 'Other Payment (Rs)',
    /* S  phonepe_recovery              */ 'PhonePe (Rs)',
    /* T  adjustments                   */ 'Positive Adjustment (Rs)',
    /* U  dp_to_os                      */ 'Deposit to OS (Rs)',
    /* V  current_deposit               */ 'Deposit Now (Rs)',
    /* W  active / inactive             */ 'Has Car Now',
    /* X  last_payment_habit            */ 'Payment Habit',
    /* Y  Last Week OS                  */ 'Last Week Closing OS (Rs)',
    /* Z  Car Count                     */ 'Cars Held This Week',
    /* AA Current Week Rented Days      */ 'Days Rented This Week',
    /* AB Current Week Lease Rent       */ 'Rent This Week (Rs)',
    /* AC Current Week fare_total       */ 'Uber Earnings (Rs)',
    /* AD Current Week Cash Collected   */ 'Cash Collected (Rs)',
    /* AE Current Week subscription     */ 'Uber Subscription (Rs)',
    /* AF Total Current OS              */ 'Live OS Now (Rs)',
    /* AG Current OS Surpass SD         */ 'Live OS + Deposit (Rs)',
    /* AH Is_in Car Recovery            */ 'In Car Recovery',
    /* AI Critical - Now (EOD)          */ '__CRITICAL_EOD__',
    /* AJ last_week_active_days         */ 'Days With Car (last week)',
    /* AK last_week_nd_days             */ 'Not-Driven Days (last week)',
    /* AL current_week_active_days      */ 'Days With Car',
    /* AM current_week_nd_days          */ 'Not-Driven Days',
    /* AN current_week_gps_kms          */ 'GPS km',
    /* AO current_week_uber_kms         */ 'Uber km',
    /* AP current_week_dead_kms         */ 'Dead km',
    /* AQ current_week_uber_trips       */ 'Uber Trips',
    /* AR last_paid_date                */ 'Last Paid Date',
    /* AS last_jama_date                */ 'Last Jama Date (4 weeks)',
    /* AT att_total                     */ 'Calls Attempted (week)',
    /* AU conn_total                    */ 'Calls Connected (week)',
    /* AV last_attempt_time             */ 'Last Attempt Time',
    /* AW last_connect_time             */ 'Last Connect Time',
    /* AX last_disposition              */ 'Last Disposition',
    /* AY att_today                     */ 'Calls Attempted Today',
    /* AZ conn_today                    */ 'Calls Connected Today',
    /* BA GPS_Tag                       */ 'GPS Yesterday',
    /* BB allocation_type               */ 'Allocation Type (D2O)',
    /* BC actioning_type                */ 'Actioning Type',
    /* BD acceptance_rate               */ 'Acceptance Rate',
    /* BE trip_tier                     */ 'Trip Tier',
    /* BF target_trips                  */ null,   // not in raw_v2
    /* BG min_remaining_trips           */ null,   // not in raw_v2
    /* BH Collections Tag               */ 'Collection Status',
    /* BI Critical - Morning List       */ 'Morning List Status',
    /* BJ ND Tag                        */ 'Not Driven Yesterday',
    /* BK RANK                          */ 'Rank in City',
    /* BL Car_Recovery Pending TAT      */ 'Recovery Pending Days',
    /* BM L2W 1% to 80%                 */ 'L2W Payment Tag',
    /* BN last_jama_date (1w)           */ 'Last Jama Date (this + last week)',
    /* BO Last Week OS + Recovery       */ 'Last Week OS + Recovery (Rs)',
    /* BP car_model                     */ 'Car Model (now)',
    /* BQ Stage Today                   */ 'Stage Today',
    /* BR Action Tag                    */ 'Action To Take',
    /* BS allocation_date (last join)   */ 'Last Join Date',
  ];

  const HEADER_ROW = 2;          // raw_v2 header row
  const SRC_FIRST_ROW = 4;       // raw_v2 data starts here
  const FIRST_DATA_ROW = 3;      // Calling_Masterlist data starts here
  const DEST_DATA_COLS = 71;     // A:BS
  const REMARK_START_COL = 72;   // BT
  const REMARK_COLS = 11;        // BT:CD
  const LAST_OUTPUT_COL = 82;    // CD
  const DEST_D_TO_LAST = DEST_DATA_COLS - 3;                 // D:BS = 68 cols
  const DEST_D_TO_REMARK_END = DEST_D_TO_LAST + REMARK_COLS; // D:CD = 79 cols
  if (DEST_MAP.length !== DEST_DATA_COLS) throw new Error(`DEST_MAP me ${DEST_MAP.length} cols, ${DEST_DATA_COLS} chahiye.`);

  // ---------- Source ready check (SQL query Automation status) ----------
  // Row in collections_queries is found by sheet id (D) + tab (E), not by row number (rows move).
  // Manual pgAdmin paste does not update that status -> run once with FORCE = true.
  const FORCE = false;
  const AUTO_ID = '1uKeBnDSiKO1Lyei-vadU66P3nUFfCL_pUemyKq4r7QE';
  const readAutoStatus = () => {
    const auto = SpreadsheetApp.openById(AUTO_ID).getSheetByName('collections_queries');
    const av = auto.getRange(1, 1, auto.getLastRow(), 10).getValues(); // A:J
    const ar = av.find(r => clean(r[3]) === SOURCE_ID && clean(r[4]) === SOURCE_TAB);
    return ar ? clean(ar[9]) : '';                                    // J = status
  };
  let expectedRows = null;
  let runText = '';
  if (!FORCE) {
    runText = readAutoStatus();
    const m = runText.match(/GSHEET: SUCCESS \((\d+) rows/);
    if (!m) {
      Logger.log(`Automation ne abhi likhna khatam nahi kiya (${runText || 'row nahi mili'}). Skip - next run me try hoga.`);
      return;
    }
    expectedRows = parseInt(m[1], 10);
  }
  const refreshTime = clean(source.getRange(SRC_FIRST_ROW, 2).getDisplayValue()); // raw_v2!B4
  // 20-Nov: no "same refresh -> skip" any more. Every run re-prints the latest raw_v2 data and
  // re-attaches the BT:CD remarks by partner_et_id. Only skips while the automation is still writing raw_v2.

  // ---------- raw_v2 header -> column index ----------
  const lastSrcCol = source.getLastColumn();
  const headers = source.getRange(HEADER_ROW, 1, 1, lastSrcCol).getValues()[0].map(clean);
  const idx = {};
  headers.forEach((h, i) => { if (h && !(h in idx)) idx[h] = i; });
  const missing = DEST_MAP.filter(n => n && !n.startsWith('__') && !(n in idx));
  ['Week (Mon)', 'Employee ID', 'City', 'Risk - That Day (EOD)'].forEach(n => { if (!(n in idx)) missing.push(n); });
  if (missing.length) throw new Error('raw_v2 me ye columns nahi mile: ' + [...new Set(missing)].join(', '));

  // Read only up to the last column we need.
  const neededCols = Math.max(...DEST_MAP.filter(n => n && !n.startsWith('__')).map(n => idx[n]),
                              idx['Risk - That Day (EOD)']) + 1;   // raw_v2 A:CL today
  const srcCount = Math.max(0, source.getLastRow() - SRC_FIRST_ROW + 1);
  const sourceRows = srcCount > 0
    ? source.getRange(SRC_FIRST_ROW, 1, srcCount, neededCols).getValues()
    : [];

  // Second check: rows read must equal the automation row count, and the status must not have changed while reading.
  const iId = idx['Employee ID'], iWeek = idx['Week (Mon)'], iCity = idx['City'];
  const readIds = sourceRows.filter(r => clean(r[iId]) !== '').length;
  if (!FORCE && (readIds !== expectedRows || readAutoStatus() !== runText)) {
    Logger.log(`Read ke time source badal gaya / rows match nahi (automation ${expectedRows}, read ${readIds}). Skip - next run me try hoga.`);
    return;
  }
  if (readIds === 0) { Logger.log('raw_v2 khaali hai. Skip.'); return; }

  // Current (latest) week only.
  const wkKey = v => (v instanceof Date) ? Utilities.formatDate(v, 'Asia/Kolkata', 'yyyy-MM-dd') : clean(v);
  const curWeek = sourceRows.map(r => wkKey(r[iWeek])).filter(Boolean).sort().pop();
  const refreshDate = refreshTime.slice(0, 10);

  function mapSourceRow(row) {
    return DEST_MAP.map(name => {
      if (name === null) return '';
      if (name === '__REFRESH_DATE__') return refreshDate;
      if (name === '__CRITICAL_EOD__') return clean(row[idx['Risk - That Day (EOD)']]) === 'Yes' ? 'Critical_Risk' : '';
      const v = row[idx[name]];
      return (v === 'NaN' || v === 'NaT') ? '' : v;
    });
  }

  // ---------- Existing destination IDs + BT:CD remarks ----------
  const oldCount = Math.max(0, dest.getLastRow() - FIRST_DATA_ROW + 1);
  const remarksById = new Map();
  if (oldCount > 0) {
    const ids = dest.getRange(FIRST_DATA_ROW, 4, oldCount, 1).getValues(); // D
    const remarks = dest.getRange(FIRST_DATA_ROW, REMARK_START_COL, oldCount, REMARK_COLS).getValues();
    ids.forEach((row, rowIndex) => {
      const id = clean(row[0]);
      if (!id) return;
      // Duplicate ID: combine remarks, lower non-blank value wins per column.
      const combined = remarksById.get(id) || Array(REMARK_COLS).fill('');
      for (let col = 0; col < REMARK_COLS; col++) {
        if (clean(remarks[rowIndex][col]) !== '') combined[col] = remarks[rowIndex][col];
      }
      remarksById.set(id, combined);
    });
  }

  // ---------- Build output (Hyderabad, current week, sorted by Rank in City) ----------
  const iRank = idx['Rank in City'];
  const picked = sourceRows
    .filter(r => wkKey(r[iWeek]) === curWeek && clean(r[iCity]).toLowerCase() === CITY && clean(r[iId]) !== '')
    .sort((a, b) => (Number(a[iRank]) || 0) - (Number(b[iRank]) || 0));

  const dataAB = [];
  const dataDToCD = [];
  const seen = new Set();
  picked.forEach(row => {
    const id = clean(row[iId]);
    if (seen.has(id)) return;   // duplicate ID in source -> first row
    seen.add(id);
    const mapped = mapSourceRow(row);
    const savedRemarks = remarksById.get(id) || Array(REMARK_COLS).fill('');
    dataAB.push(mapped.slice(0, 2));                    // A:B
    dataDToCD.push([...mapped.slice(3), ...savedRemarks]); // D:BS + BT:CD
  });

  const rowsToWrite = Math.max(oldCount, dataAB.length);
  const neededRows = FIRST_DATA_ROW + rowsToWrite - 1;
  if (dest.getMaxRows() < neededRows) dest.insertRowsAfter(dest.getMaxRows(), neededRows - dest.getMaxRows());
  if (dest.getMaxColumns() < LAST_OUTPUT_COL) dest.insertColumnsAfter(dest.getMaxColumns(), LAST_OUTPUT_COL - dest.getMaxColumns());

  if (rowsToWrite > 0) {
    // Old extra rows become blank; C stays untouched.
    while (dataAB.length < rowsToWrite) {
      dataAB.push(['', '']);
      dataDToCD.push(Array(DEST_D_TO_REMARK_END).fill(''));
    }
    dest.getRange(FIRST_DATA_ROW, 1, rowsToWrite, 2).setValues(dataAB);
    dest.getRange(FIRST_DATA_ROW, 4, rowsToWrite, DEST_D_TO_REMARK_END).setValues(dataDToCD);
  }

  Logger.log(`${seen.size} Hyderabad IDs print hui (week ${curWeek}, source refresh ${refreshTime}).`);
}
