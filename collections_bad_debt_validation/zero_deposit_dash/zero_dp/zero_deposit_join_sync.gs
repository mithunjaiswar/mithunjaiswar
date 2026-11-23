/**
 * Zero sheet > 0_raw (JOIN + DAY rows)  ->  7 city Agent Tracking sheets > tab "0_Deposit_Join"
 *
 * Paste ONCE in the Zero & Low Deposit Monitoring Dashboard (Extensions -> Apps Script).
 * No SQL here: it only reads the 0_raw tab (filled hourly by SQL Automation row 78) and copies each city's rows.
 *
 * Tab per city (last 8 weeks, newest join first):
 *   Join Date | Join Week | Employee ID | Pilot Name | Join Type | Product | Deposit at Join (Rs) | Joined at 0 Deposit (Yes/No)
 *   + for 0 deposit joins, status on the latest day: Active Now | Deposit Now (Rs) | Live OS Now (Rs) | Bad Debt Now (Rs) | In Car Recovery Now
 *
 * First time: run setupHourlyTrigger() once (allow permissions). It runs syncZeroDepositJoins now and then every hour.
 */
const SRC_ID = '1zsGMzqah8XCVfDM7f7R-BeNmK5DU5MxqTJ89xPJ25Sw';
const SRC_TAB = '0_raw';
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
const MIN_SRC_ROWS = 1000;   // 0_raw has ~20K rows; fewer = automation is mid-write -> skip this run

const HEADER = ['Join Date', 'Join Week', 'Employee ID', 'Pilot Name', 'Join Type', 'Product',
                'Deposit at Join (Rs)', 'Joined at 0 Deposit', 'Active Now', 'Deposit Now (Rs)',
                'Live OS Now (Rs)', 'Bad Debt Now (Rs)', 'In Car Recovery Now', 'Status Date'];

function syncZeroDepositJoins() {
  const src = SpreadsheetApp.openById(SRC_ID).getSheetByName(SRC_TAB);
  const last = src.getLastRow();
  if (last < MIN_SRC_ROWS) { Logger.log('0_raw has only ' + last + ' rows (automation writing?) - skipped'); return; }
  const data = src.getRange(1, 1, last, 32).getValues();
  const h = data[0];
  const ix = name => { const i = h.indexOf(name); if (i < 0) throw new Error('0_raw column missing: ' + name); return i; };
  const C = {
    type: ix('Row Type'), date: ix('Date'), city: ix('City'), product: ix('Product'), etm: ix('Employee ID'),
    name: ix('Pilot Name'), jdate: ix('Join Date'), jtype: ix('Join Type'), jweek: ix('Join Week'),
    depJoin: ix('Deposit at Join (Rs)'), zero: ix('Joined at 0 Deposit'), active: ix('Active (Live OS)'),
    dep: ix('Deposit That Day (Rs)'), lo: ix('Live OS (Rs)'), bda: ix('Active Bad Debt (Rs)'),
    bdl: ix('Left Bad Debt (Rs)'), inrc: ix('In Car Recovery'), refreshed: ix('Data Refreshed At')
  };

  // latest DAY row per pilot + join date (status of the 0 deposit pilot now)
  const latest = {};
  for (let r = 1; r < data.length; r++) {
    const row = data[r];
    if (row[C.type] !== 'DAY') continue;
    const key = row[C.etm] + '|' + toKey(row[C.jdate]);
    if (!latest[key] || toKey(row[C.date]) > toKey(latest[key][C.date])) latest[key] = row;
  }

  // JOIN rows per city
  const byCity = {};
  Object.keys(CITY_SHEETS).forEach(c => byCity[c] = []);
  for (let r = 1; r < data.length; r++) {
    const row = data[r];
    if (row[C.type] !== 'JOIN' || !byCity[row[C.city]]) continue;
    const s = latest[row[C.etm] + '|' + toKey(row[C.jdate])];
    byCity[row[C.city]].push([
      row[C.jdate], row[C.jweek], row[C.etm], row[C.name], row[C.jtype], row[C.product],
      row[C.depJoin], row[C.zero],
      s ? (s[C.active] == 1 ? 'Active' : 'Inactive') : '',
      s ? s[C.dep] : '', s ? s[C.lo] : '',
      s ? (Number(s[C.bda]) || 0) + (Number(s[C.bdl]) || 0) : '',
      s ? (s[C.inrc] == 1 ? 'Yes' : 'No') : '',
      s ? s[C.date] : ''
    ]);
  }
  const refreshed = data.length > 1 ? data[1][C.refreshed] : '';

  Object.keys(CITY_SHEETS).forEach(city => {
    const rows = byCity[city];
    rows.sort((a, b) => (toKey(b[0]) - toKey(a[0])) || (a[7] === b[7] ? 0 : (a[7] === 'Yes' ? -1 : 1)));
    const ss = SpreadsheetApp.openById(CITY_SHEETS[city]);
    let sh = ss.getSheetByName(DEST_TAB);
    if (!sh) sh = ss.insertSheet(DEST_TAB);
    sh.clearContents();
    const out = [HEADER].concat(rows);
    if (sh.getMaxRows() < out.length + 1) sh.insertRowsAfter(sh.getMaxRows(), out.length + 1 - sh.getMaxRows());
    sh.getRange(1, 1, out.length, HEADER.length).setValues(out);
    sh.getRange(1, 16).setValue('Updated: ' + refreshed + '  |  source: Zero & Low Deposit dashboard > 0_raw');
    sh.getRange(1, 1, 1, HEADER.length).setFontWeight('bold').setBackground('#1f3b66').setFontColor('#ffffff');
    if (rows.length) {
      sh.getRange(2, 1, rows.length, 2).setNumberFormat('dd-mmm-yyyy');
      sh.getRange(2, 14, rows.length, 1).setNumberFormat('dd-mmm-yyyy');
      sh.getRange(2, 7, rows.length, 1).setNumberFormat('#,##0');
      sh.getRange(2, 10, rows.length, 3).setNumberFormat('#,##0');
    }
    sh.setFrozenRows(1);
    Logger.log(city + ': ' + rows.length + ' joins, ' + rows.filter(x => x[7] === 'Yes').length + ' at 0 deposit');
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
