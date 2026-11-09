// Run with an exported, single-page UAV HTML containing deduction terms.
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const {PDFDocument} = require('pdf-lib');
const source = path.resolve(process.argv[2]);
const root = path.resolve(process.argv[3]);
fs.mkdirSync(root, {recursive:true});
(async()=>{
 const browser = await chromium.launch({headless:true, executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 try {
  const page = await browser.newPage({viewport:{width:1400,height:1000}});
  for (const mode of ['calculation','table','both','long-row']) {
   let html = fs.readFileSync(source,'utf8');
   html = html.replace('<head>', '<head><base href="'+pathToFileURL(path.dirname(source)+path.sep).href+'">');
   const setup = `
    const mode = ${JSON.stringify(mode)};
    const deductions = document.querySelector('.calc-deduction');
    const table = document.querySelector('.attribute-table');
    if (mode === 'calculation' || mode === 'both') {
      const term = deductions.querySelector('.deduction-term');
      for (let n=0;n<40;n++) deductions.insertBefore(term.cloneNode(true), deductions.lastElementChild);
    }
    if (mode === 'calculation') table.remove();
    else {
      document.querySelector('.map').dataset.contentBottom = '1';
      const row = table.tBodies[0].rows[0];
      if (mode === 'long-row') row.cells[7].textContent = '長い所有者名称'.repeat(300);
      else for (let n=0;n<100;n++) table.tBodies[0].append(row.cloneNode(true));
    }
    window.expectedTerms = deductions.querySelectorAll('.deduction-term').length;
    window.expectedRows = table.isConnected ? table.tBodies[0].rows.length : 0;
   `;
   html = html.replace('if (window.RingyoLayout) {', setup+'\nif (window.RingyoLayout) {');
   const file = path.join(root,mode+'.html'); fs.writeFileSync(file,html);
   await page.goto(pathToFileURL(file).href);
   await page.waitForFunction(()=>document.documentElement.dataset.layoutReady==='1');
   await page.emulateMedia({media:'print'});
   await page.evaluate(()=>document.body.dataset.printAll='1');
   const state = await page.evaluate(()=>{
    const sheets=[...document.querySelectorAll('.drawing-sheet')];
    const original=sheets[0];
    const columns=sheets.map(s=>s.querySelector('.xy_container'));
    const maps=sheets.map(s=>s.querySelector('.map_container'));
    const termSheets=sheets.filter((s,i)=>!i || s.dataset.calculationContinuation==='1');
    return {
     pages:sheets.length, expectedTerms:window.expectedTerms, expectedRows:window.expectedRows,
     terms:termSheets.reduce((n,s)=>n+s.querySelectorAll('.deduction-term').length,0),
     rows:sheets.reduce((n,s)=>n+s.querySelectorAll('.attribute-table tbody tr').length,0),
     text:[...document.querySelectorAll('.attribute-table tbody tr')].map(r=>r.cells[7].textContent).join(''),
     firstTerms:original.querySelectorAll('.deduction-term').length,
     columnsFit:columns.every(c=>c.scrollHeight<=c.clientHeight+1),
     tablesFit:[...document.querySelectorAll('.attribute-table')].every(t=>t.getBoundingClientRect().height<=t.parentElement.clientHeight+.2),
     blocks:sheets.every(s=>s.querySelector('.info_container') && s.querySelector('.sub_container').children.length===2 && s.querySelector('.xy_container') && s.querySelector('.map_container')),
     sameSizes:maps.every(m=>Math.abs(m.getBoundingClientRect().width-maps[0].getBoundingClientRect().width)<.2 && Math.abs(m.getBoundingClientRect().height-maps[0].getBoundingClientRect().height)<.2),
     mapReprint:sheets.filter(s=>s.classList.contains('calculation-continuation') && !s.classList.contains('attribute-continuation')).every(s=>s.querySelector('.main_map')?.getAttribute('src')===original.querySelector('.main_map').getAttribute('src')),
     paired:sheets.some(s=>s.classList.contains('calculation-continuation') && s.classList.contains('attribute-continuation'))
    };
   });
   assert(state.pages>1,mode);
   assert(state.blocks && state.sameSizes && state.columnsFit && state.tablesFit && state.mapReprint,JSON.stringify(state));
   assert.equal(state.terms,state.expectedTerms,mode);
   assert(state.firstTerms>0,mode);
   if (mode==='long-row') assert.equal(state.text,'長い所有者名称'.repeat(300));
   else assert.equal(state.rows,state.expectedRows,mode);
   if (mode==='both') assert(state.paired,'both continuations share a page');
   const pdf=await page.pdf({path:path.join(root,mode+'.pdf'),preferCSSPageSize:true,printBackground:true});
   assert.equal((await PDFDocument.load(pdf)).getPageCount(),state.pages,mode);
   await page.emulateMedia({media:'screen'});
   await page.locator('select[aria-label="表示する図面"]').selectOption({index:1});
   await page.screenshot({path:path.join(root,mode+'-page2.png'),fullPage:true});
   console.log(mode,JSON.stringify({...state,textLength:state.text.length,text:undefined}));
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
