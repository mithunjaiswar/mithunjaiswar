// Zero sheet > Agent_action  ->  city Agent Tracking sheet > Calling_Masterlist
// 18-Nov: Agent_action got a new column BR "allocation_date (last join)", so
//   source  = A:BU (73 cols): BR allocation_date, BS SD Bucket (at allocation, not printed), BT agent_username, BU actioning_type
//   dest    = A:BS (new BS = allocation_date), remarks BS:CC -> BT:CD
// BEFORE the first run in each city sheet: insert 1 column to the LEFT of BS in Calling_Masterlist,
// so the old remarks (BS:CC) move to BT:CD. Otherwise the remarks are read from the wrong columns.
// 18-Nov: runs only when the SQL query Automation status for Agent_action says GSHEET: SUCCESS with the same row count,
//   and the source refresh (B3) is new for this city; else skips and the next trigger retries.
function syncHyderabadCallingMasterlist() {
  const SOURCE_ID = '1zsGMzqah8XCVfDM7f7R-BeNmK5DU5MxqTJ89xPJ25Sw';
  const DEST_ID = '1AcbZbEU7UBPOgqNDIchN026w8CesbQlWKn61lrMy_ow';

  const source = SpreadsheetApp
    .openById(SOURCE_ID)
    .getSheetByName('Agent_action');

  const dest = SpreadsheetApp
    .openById(DEST_ID)
    .getSheetByName('Calling_Masterlist');

  if (!source || !dest) {
    throw new Error('Source ya destination tab nahi mila.');
  }

  const clean = value => String(value ?? '').trim();

  // ---------- Source ready check (SQL query Automation status) ----------
  // Run only when SQL query Automation > collections_queries (row with this sheet id + tab Agent_action)
  // says "GSHEET: SUCCESS (N rows" - i.e. the automation has finished writing - and the tab has exactly N rows.
  // RUNNING / FAILED / count mismatch -> skip; the next trigger run tries again.
  // (Rows in collections_queries move around, so the row is found by sheet id + tab name, not by row number.)
  // Manual pgAdmin paste does not update that status -> run once with FORCE = true.
  // Same refresh time (Agent_action!B3) as the last successful sync of this city -> nothing new, skip.
  const FORCE = false;
  const AUTO_ID = '1uKeBnDSiKO1Lyei-vadU66P3nUFfCL_pUemyKq4r7QE';
  const readAutoStatus = () => {
    const auto = SpreadsheetApp.openById(AUTO_ID).getSheetByName('collections_queries');
    const av = auto.getRange(1, 1, auto.getLastRow(), 10).getValues(); // A:J
    const ar = av.find(r => clean(r[3]) === SOURCE_ID && clean(r[4]) === 'Agent_action'); // D = sheet id, E = tab
    return ar ? clean(ar[9]) : '';                                                         // J = status
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
  const refreshTime = clean(source.getRange('B3').getDisplayValue()); // refresh time written by the query in every row

  const props = PropertiesService.getScriptProperties();
  const propKey = 'last_sync_' + DEST_ID;
  if (!FORCE && props.getProperty(propKey) === refreshTime) {
    Logger.log(`Source me naya data nahi hai (last refresh ${refreshTime} pehle hi print ho chuka). Skip.`);
    return;
  }

  const FIRST_DATA_ROW = 3;
  const SOURCE_COLS = 73;       // A:BU   (18-Nov: + BS SD Bucket; agent BT, actioning BU)
  const REMARK_START_COL = 72;  // BT     (was 71 = BS)
  const REMARK_COLS = 11;       // BT:CD  (was BS:CC)
  const LAST_OUTPUT_COL = 82;   // CD     (was 81 = CC)
  const DEST_DATA_COLS = 71;    // A:BS   (was 70 = A:BR)
  const DEST_D_TO_LAST = DEST_DATA_COLS - 3;          // D:BS = 68 cols (was 67)
  const DEST_D_TO_REMARK_END = DEST_D_TO_LAST + REMARK_COLS; // D:CD = 79 cols (was 78)

  // Source row ko destination A:BS ki mapping mein convert karo.
  // Destination C blank rakha jaata hai; script kabhi C mein write nahi karega.
  function mapSourceRow(row) {
    const result = Array(DEST_DATA_COLS).fill(''); // A:BS

    result[0] = row[0]; // A→A
    result[1] = row[1]; // B→B

    // Source C:BA → destination D:BB
    for (let sourceCol = 3; sourceCol <= 53; sourceCol++) {
      result[sourceCol] = row[sourceCol - 1];
    }

    result[54] = row[72]; // Source BU (actioning_type) → destination BC

    // Source BB:BI → destination BD:BK
    for (let sourceCol = 54; sourceCol <= 61; sourceCol++) {
      result[sourceCol + 1] = row[sourceCol - 1];
    }

    // Source BK:BQ → destination BL:BR
    for (let sourceCol = 63; sourceCol <= 69; sourceCol++) {
      result[sourceCol] = row[sourceCol - 1];
    }

    result[70] = row[69]; // NEW: Source BR (allocation_date (last join)) → destination BS

    return result;
  }

  // Existing destination IDs aur BT:CD remarks padho.
  const oldCount = Math.max(
    0,
    dest.getLastRow() - FIRST_DATA_ROW + 1
  );

  const remarksById = new Map();

  if (oldCount > 0) {
    const ids = dest
      .getRange(FIRST_DATA_ROW, 4, oldCount, 1) // D
      .getValues();

    const remarks = dest
      .getRange(
        FIRST_DATA_ROW,
        REMARK_START_COL,
        oldCount,
        REMARK_COLS
      )
      .getValues();

    ids.forEach((row, rowIndex) => {
      const id = clean(row[0]);
      if (!id) return;

      // Duplicate ID ke remarks combine karo.
      // Same column mein neeche wali non-blank value priority legi.
      const combined =
        remarksById.get(id) || Array(REMARK_COLS).fill('');

      for (let col = 0; col < REMARK_COLS; col++) {
        if (clean(remarks[rowIndex][col]) !== '') {
          combined[col] = remarks[rowIndex][col];
        }
      }

      remarksById.set(id, combined);
    });
  }

  // Headers aur source data padho.
  const sourceHeaders = source
    .getRange(1, 1, 2, SOURCE_COLS)
    .getValues();

  const sourceCount = Math.max(
    0,
    source.getLastRow() - FIRST_DATA_ROW + 1
  );

  const sourceRows = sourceCount > 0
    ? source
        .getRange(FIRST_DATA_ROW, 1, sourceCount, SOURCE_COLS)
        .getValues()
    : [];

  // Second check: rows read must equal the automation row count, and the status must not have changed
  // while we were reading (a new refresh could have started).
  const readIds = sourceRows.filter(r => clean(r[2]) !== '').length;
  if (!FORCE && (readIds !== expectedRows || readAutoStatus() !== runText)) {
    Logger.log(`Read ke time source badal gaya / rows match nahi (automation ${expectedRows}, read ${readIds}). Skip - next run me try hoga.`);
    return;
  }
  if (readIds === 0) {
    Logger.log('Agent_action khaali hai. Skip.');
    return;
  }

  const dataAB = [];
  const dataDToCD = [];
  const seenSourceIds = new Set();

  sourceRows.forEach(row => {
    // Source F = city
    if (clean(row[5]).toLowerCase() !== 'hyderabad') return;

    // Source C = ID; destination D = ID
    const id = clean(row[2]);
    if (!id) return;

    // Source mein duplicate ID aaye to pehli row print karo.
    if (seenSourceIds.has(id)) return;
    seenSourceIds.add(id);

    const mapped = mapSourceRow(row);
    const savedRemarks =
      remarksById.get(id) || Array(REMARK_COLS).fill('');

    dataAB.push(mapped.slice(0, 2)); // Destination A:B
    dataDToCD.push([
      ...mapped.slice(3), // Destination D:BS
      ...savedRemarks      // Destination BT:CD
    ]);
  });

  const rowsToWrite = Math.max(oldCount, dataAB.length);
  const neededRows = FIRST_DATA_ROW + rowsToWrite - 1;

  if (dest.getMaxRows() < neededRows) {
    dest.insertRowsAfter(
      dest.getMaxRows(),
      neededRows - dest.getMaxRows()
    );
  }

  if (dest.getMaxColumns() < LAST_OUTPUT_COL) {
    dest.insertColumnsAfter(
      dest.getMaxColumns(),
      LAST_OUTPUT_COL - dest.getMaxColumns()
    );
  }

  // Header rows 1–2: A:B aur D:BS print karo. C untouched.
  const mappedHeaders = sourceHeaders.map(mapSourceRow);

  dest.getRange(1, 1, 2, 2).setValues(
    mappedHeaders.map(row => row.slice(0, 2))
  );

  dest.getRange(1, 4, 2, DEST_D_TO_LAST).setValues(
    mappedHeaders.map(row => row.slice(3))
  );

  if (rowsToWrite > 0) {
    // Purani extra data rows blank hongi; C phir bhi untouched rahega.
    while (dataAB.length < rowsToWrite) {
      dataAB.push(['', '']);
      dataDToCD.push(Array(DEST_D_TO_REMARK_END).fill('')); // D:CD
    }

    dest
      .getRange(FIRST_DATA_ROW, 1, rowsToWrite, 2)
      .setValues(dataAB);

    dest
      .getRange(FIRST_DATA_ROW, 4, rowsToWrite, DEST_D_TO_REMARK_END)
      .setValues(dataDToCD);
  }

  props.setProperty(propKey, refreshTime);   // remember which refresh this city already has
  Logger.log(`${seenSourceIds.size} Hyderabad IDs print hui (source refresh ${refreshTime}).`);
}
