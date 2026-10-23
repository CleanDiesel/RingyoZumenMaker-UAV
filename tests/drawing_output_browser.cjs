// Run with Playwright available through NODE_PATH; args: generated index.html.
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const executablePath = process.env.PDF_BROWSER || path.join(
    process.env['PROGRAMFILES(X86)'], 'Microsoft/Edge/Application/msedge.exe');
  const browser = await chromium.launch({executablePath, headless: true});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(process.argv[2])).href);
    await page.emulateMedia({media: 'print'});
    await page.evaluate(() => document.body.dataset.printAll = '1');
    const result = await page.evaluate(() => {
      const tables = [...document.querySelectorAll('.attribute-table')];
      const mm = 96 / 25.4;
      return {
        rows: tables.reduce((total, table) => total + table.tBodies[0].rows.length, 0),
        pages: document.querySelectorAll('.attribute-continuation').length,
        tables: tables.map(table => ({
          headers: table.tHead.rows.length,
          fits: table.getBoundingClientRect().height <=
            (table.closest('.attribute-continuation') ? 158 : 40) * mm + 1,
          fullWidth: Math.abs(table.getBoundingClientRect().width -
            table.parentElement.clientWidth) < 2,
        })),
        noTableOnThirdDrawing: !document.querySelector('[data-drawing="3"] .attribute-table'),
        columns: tables[0].tHead.textContent,
      };
    });
    assert.deepEqual(errors, []);
    assert.equal(result.rows, 17);
    assert(result.pages > 0);
    assert(result.tables.every(table => table.headers === 1 && table.fits && table.fullWidth));
    assert(result.noTableOnThirdDrawing);
    assert(!result.columns.includes('枝番'));
    assert(result.columns.includes('No'));
    console.log('PASS: browser pagination, all 17 rows preserved, one header per page, full-width tables, per-drawing visibility');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
