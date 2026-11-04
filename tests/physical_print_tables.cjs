const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {PDFDocument}=require('pdf-lib');
const sharp=require('sharp');
const manifest=path.resolve(process.argv[2]);
const fixtures=JSON.parse(fs.readFileSync(manifest,'utf8'));
const root=path.dirname(manifest);
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 try{
  const page=await browser.newPage({viewport:{width:1800,height:1300}});
  const results=[];
  for(const [i,item] of fixtures.entries()){
   let errors=[];page.removeAllListeners('pageerror');page.on('pageerror',e=>errors.push(e.message));
   await page.goto(pathToFileURL(item.html).href);
   await page.evaluate(()=>document.fonts.ready);
   if(item.plugin==='uav')await page.waitForFunction(()=>document.documentElement.dataset.layoutReady==='1');
   await page.emulateMedia({media:'print'});
   if(item.plugin==='uav')await page.evaluate(()=>document.body.dataset.printAll='1');
   const state=await page.evaluate(plugin=>{
    const image=document.querySelector('.main_map');
    const bounds=image.getBoundingClientRect();
    const tables=[...document.querySelectorAll('.attribute-table')];
    return {image:{left:bounds.left,top:bounds.top,width:bounds.width,height:bounds.height},
     sheets:plugin==='uav'?document.querySelectorAll('.drawing-sheet').length:1,
     placement:document.querySelector('.drawing-sheet')?.dataset.tablePlacement,
     tables:tables.map(table=>{
      const box=table.getBoundingClientRect(),frame=table.parentElement;
      const rect=frame.getBoundingClientRect(), style=getComputedStyle(frame);
      return{bottomDelta:Math.abs(box.bottom-(rect.bottom-parseFloat(style.borderBottomWidth))),
       fits:box.top>=rect.top+parseFloat(style.borderTopWidth)-.2,
       left:getComputedStyle(table.rows[0].cells[0]).borderLeftWidth,
       right:getComputedStyle(table.rows[0].cells[table.rows[0].cells.length-1]).borderRightWidth,
       bottom:getComputedStyle(table.tBodies[0].rows[table.tBodies[0].rows.length-1].cells[0]).borderBottomWidth};
     })};
   },item.plugin);
   assert.deepEqual(errors,[]);
   const expectedPages=item.plugin==='uav'&&item.table&&item.kind==='tall'?2:1;
   assert.equal(state.sheets,expectedPages,JSON.stringify(item));
   if(item.table)assert.equal(state.placement,item.kind==='tall'?'continuation':'bottom');
   for(const table of state.tables){assert(table.fits);assert(table.bottomDelta<.6);assert.equal(table.left,'0px');assert.equal(table.right,'0px');assert.equal(table.bottom,'0px');}
   const pdfPath=path.join(root,`print-${i}.pdf`);
   const pdfBuffer=await page.pdf({preferCSSPageSize:true,printBackground:true});fs.writeFileSync(pdfPath,pdfBuffer);
   const pdf=await PDFDocument.load(pdfBuffer);
   assert.equal(pdf.getPageCount(),expectedPages,`${item.plugin}/${item.paper}/${item.kind}: no extra or clipped printed pages`);
   assert(Math.abs(pdf.getPage(0).getWidth()-(item.paper==='A3'?420:297)*72/25.4)<1);
   const prefix=path.join(root,`print-${i}`);
   execFileSync('pdftoppm',['-f','1','-singlefile','-r','300','-png',pdfPath,prefix],{windowsHide:true});
   const {data,info}=await sharp(prefix+'.png').removeAlpha().raw().toBuffer({resolveWithObject:true});
   const r=state.image,k=300/96;
   const x0=Math.max(0,Math.floor(r.left*k)),y0=Math.max(0,Math.floor(r.top*k));
   const x1=Math.min(info.width,Math.ceil((r.left+r.width)*k)),y1=Math.min(info.height,Math.ceil((r.top+r.height)*k));
   let minX=info.width,maxX=-1,minY=info.height,maxY=-1;
   for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++){
    const p=(y*info.width+x)*info.channels;
    if(data[p]>170&&data[p+1]<110&&data[p+2]<110){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
   }
   assert(maxX>=minX,'Known red survey line must be printed');
   const physical=(item.kind==='tall'?maxY-minY+1:maxX-minX+1)*25.4/300;
   const expected=item.kind==='tall'?(item.paper==='A3'?200:140):100;
   assert(Math.abs(physical-expected)<.6,`${item.plugin}/${item.paper}: ${expected}m at 1:1000 must print as ${expected}mm, got ${physical}`);
   results.push({...item,pdf:pdfPath,pages:pdf.getPageCount(),measured_mm:physical});
   await page.emulateMedia({media:'screen'});
   if(item.plugin==='uav')await page.evaluate(()=>delete document.body.dataset.printAll);
   await page.screenshot({path:path.join(root,`screen-${i}.png`),fullPage:true});
   console.log(item.plugin,item.paper,item.kind,item.table?'table':'no table',`${physical.toFixed(2)}mm`,expectedPages+' page(s): PASS');
  }
  // A single unusually long row must flow across multiple continuation pages.
  const source=fixtures.find(f=>f.plugin==='uav'&&f.paper==='A4'&&f.kind==='short'&&f.table);
  await page.goto(pathToFileURL(source.html).href);
  await page.waitForFunction(()=>document.documentElement.dataset.layoutReady==='1');
  const text='長い所有者名称'.repeat(300);
  const modified=await page.evaluate(({text,base})=>{
   document.querySelectorAll('.drawing-navigation').forEach(e=>e.remove());
   delete document.documentElement.dataset.layoutReady;
   const cell=document.querySelector('.attribute-table tbody tr').cells[7];cell.textContent=text;
   const baseElement=document.createElement('base');baseElement.href=base;document.head.prepend(baseElement);
   return '<!DOCTYPE html>'+document.documentElement.outerHTML;
  },{text,base:pathToFileURL(path.dirname(source.html)+path.sep).href});
  const longFile=path.join(root,'long-row.html');fs.writeFileSync(longFile,modified);
  await page.goto(pathToFileURL(longFile).href);
  await page.waitForFunction(()=>document.documentElement.dataset.layoutReady==='1');
  await page.emulateMedia({media:'print'});await page.evaluate(()=>document.body.dataset.printAll='1');
  const long=await page.evaluate(()=>({sheets:document.querySelectorAll('.drawing-sheet').length,
   text:[...document.querySelectorAll('.attribute-table tbody tr')].map(row=>row.cells[7].textContent).join(''),
   fits:[...document.querySelectorAll('.attribute-table')].every(table=>table.getBoundingClientRect().height<=table.parentElement.clientHeight+.2)}));
  assert(long.sheets>2);assert.equal(long.text,text);assert(long.fits);
  const longPdf=await PDFDocument.load(await page.pdf({preferCSSPageSize:true,printBackground:true}));
  assert.equal(longPdf.getPageCount(),long.sheets);
  console.log('Long single row: all text retained, no clipped pages: PASS');
  fs.writeFileSync(path.join(root,'print-validation.json'),JSON.stringify({results,long_row_pages:long.sheets},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
