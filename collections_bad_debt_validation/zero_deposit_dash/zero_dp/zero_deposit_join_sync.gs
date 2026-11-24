/**
 * Zero sheet > 0_raw  ->  7 city Agent Tracking sheets > tab "0_Deposit_Join"
 *
 * Paste ONCE in the Zero & Low Deposit Monitoring Dashboard (Extensions -> Apps Script).
 * No SQL here: it only reads the 0_raw tab (filled hourly by SQL Automation row 78) and copies each city's rows.
 * 0_raw = ONLY 0 deposit pilots, pilot x week, last 3 weeks (header in row 2, data from row 4).
 *
 * City tab = every pilot of the city who joined at 0 deposit (latest week row), newest join first:
 *   Join Date | Join Type | Employee ID | Pilot Name | Product | Joined at 0 Deposit | Deposit Now | Deposit Bucket Now |
 *   Active (latest day) | Live OS | Weekly OS | Collected This Week | Collection % | Bad Debt | Bad Debt Type | In Car Recovery
 *
 * First time: run setupHourlyTrigger() once (allow permissions). It runs syncZeroDepositJoins now and then every hour.
 */
const SRC_ID = '1zsGMzqah8XCVfDM7f7R-BeNmK5DU5MxqTJ89xPJ25Sw';
const SRC_TAB = '0dp_raw';   // 24-Nov: renamed from 0_raw (automation shard 1)
const HEADER_ROW = 2, DATA_ROW = 4;
const DEST_TAB = '0_Deposit_Join';
const CITY_SHEETS = {
  'Bangalore': '1cqtYRXzgrfT9C32oPo50JY0jUDbd0j2LGIHgXAaDv3g',
  'Chennai':   '192b4gADIm3KfvshyjeuEvP0DGgVgIPzGehe_uChnE4I',
  'Delhi NCR': '1EgvSmWCBriuIhZWg3XNI5_Smz-U3YwIS4xZ5ohtZIDc',
  'Hyderabad': '1GLzLpDT8enQgXEjmxkuRAypxbToBY8UYiMxnocERGjE',
  'Kolkata':   '1vPodl3Ds77tyFT7FAk4F7fYAu9A5RSdC8NRF5Y2MmZI',
  'Mumbai':    '1sGaKUCpf1JCqgvoBulZ21oZ8mKWnKbHpJwRGvyfeQGw',
  'Pune':      '1YLqE7H-itBtb76LRTOKCAmR28ttQwzu_pNkplAweiso'
};
const MIN_DATA_ROWS = 100;   // fewer = automation is mid-write -> skip this run

const OUT = [   // [header in the city tab, 0_raw column name]
  ['Join Date', 'Join Date'], ['Join Type', 'Join Type'], ['Employee ID', 'Employee ID'], ['Pilot Name', 'Pilot Name'],
  ['Product', 'Product'], ['Joined at 0 Deposit', null], ['Deposit Now (Rs)', 'Deposit Now (Rs)'],
  ['Deposit Bucket Now', 'Deposit Bucket Now'], ['Active (latest day)', 'Active at Week End'],
  ['Live OS (Rs)', 'Live OS at Week End (Rs)'], ['Weekly OS - hisaab (Rs)', 'Weekly OS (hisaab) (Rs)'],
  ['Collected This Week (Rs)', 'Collected This Week (Rs)'], ['Collection %', 'Collection %'],
  ['Bad Debt (Rs)', 'Bad Debt at Week End (Rs)'], ['Bad Debt Type', 'Bad Debt Type at Week End'],
  ['In Car Recovery', 'In Car Recovery at Week End']
];

function syncZeroDepositJoins() {
  const src = SpreadsheetApp.openById(SRC_ID).getSheetByName(SRC_TAB);
  const last = src.getLastRow();
  if (last - DATA_ROW + 1 < MIN_DATA_ROWS) { Logger.log('0_raw has only ' + (last - DATA_ROW + 1) + ' data rows (automation writing?) - skipped'); return; }
  const width = src.getLastColumn();
  const h = src.getRange(HEADER_ROW, 1, 1, width).getValues()[0];
  const data = src.getRange(DATA_ROW, 1, last - DATA_ROW + 1, width).getValues();
  const ix = name => { const i = h.indexOf(name); if (i < 0) throw new Error('0_raw column missing: ' + name); return i; };
  const iWeek = ix('Week (Mon)'), iEtm = ix('Employee ID'), iCity = ix('City'), iRef = ix('Data Refreshed At');
  const cols = OUT.map(o => (o[1] ? ix(o[1]) : -1));

  // latest week row per pilot
  const latest = {};
  data.forEach(r => {
    const k = r[iEtm];
    if (k && (!latest[k] || toKey(r[iWeek]) > toKey(latest[k][iWeek]))) latest[k] = r;
  });

  const byCity = {};
  Object.keys(CITY_SHEETS).forEach(c => byCity[c] = []);
  Object.keys(latest).forEach(k => {
    const r = latest[k];
    if (!byCity[r[iCity]]) return;
    byCity[r[iCity]].push(cols.map((ci, j) => {
      if (ci < 0) return 'Yes';
      const v = r[ci];
      if (OUT[j][0] === 'Active (latest day)') return v == 1 ? 'Active' : 'Inactive';
      if (OUT[j][0] === 'In Car Recovery') return v == 1 ? 'Yes' : 'No';
      return v;
    }));
  });
  const refreshed = data.length ? data[0][iRef] : '';
  const header = OUT.map(o => o[0]);

  Object.keys(CITY_SHEETS).forEach(city => {
    const rows = byCity[city].sort((a, b) => toKey(b[0]) - toKey(a[0]));
    const ss = SpreadsheetApp.openById(CITY_SHEETS[city]);
    let sh = ss.getSheetByName(DEST_TAB);
    if (!sh) sh = ss.insertSheet(DEST_TAB);
    sh.clearContents();
    const out = [header].concat(rows);
    if (sh.getMaxRows() < out.length + 1) sh.insertRowsAfter(sh.getMaxRows(), out.length + 1 - sh.getMaxRows());
    sh.getRange(1, 1, out.length, header.length).setValues(out);
    sh.getRange(1, header.length + 2).setValue('Updated: ' + refreshed + '  |  source: Zero & Low Deposit dashboard > 0_raw (0 deposit pilots, last 3 weeks)');
    sh.getRange(1, 1, 1, header.length).setFontWeight('bold').setBackground('#1f3b66').setFontColor('#ffffff');
    if (rows.length) {
      sh.getRange(2, 1, rows.length, 1).setNumberFormat('dd-mmm-yyyy');
      sh.getRange(2, 7, rows.length, 1).setNumberFormat('#,##0');
      sh.getRange(2, 10, rows.length, 3).setNumberFormat('#,##0');
      sh.getRange(2, 13, rows.length, 1).setNumberFormat('0.0%');
      sh.getRange(2, 14, rows.length, 1).setNumberFormat('#,##0');
    }
    sh.setFrozenRows(1);
    Logger.log(city + ': ' + rows.length + ' pilots joined at 0 deposit');
  });
}

function toKey(v) {
  if (v instanceof Date) return v.getTime();
  const t = new Date(v).getTime();
  return isNaN(t) ? 0 : t;
}

/** Run once: hourly trigger (removes an older trigger of this function first) + one run now. */
function setupHourlyTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'syncZeroDepositJoins')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('syncZeroDepositJoins').timeBased().everyHours(1).create();
  syncZeroDepositJoins();
}
