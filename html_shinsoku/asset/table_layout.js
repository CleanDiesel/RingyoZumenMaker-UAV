/* Attribute tables never resize the map or cover its rendered content. */
(() => {
  const removeIds = element => {
    element.removeAttribute("id");
    element.querySelectorAll("[id]").forEach(child => child.removeAttribute("id"));
  };
  function paginateTables() {
    const factor = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--paper-factor")) || 1;
    const gap = 2 * 96 / 25.4 * factor;
    for (const sheet of [...document.querySelectorAll(".drawing-sheet:not(.attribute-continuation)")]) {
      const table = sheet.querySelector(".attribute-table");
      if (!table) continue;
      sheet.style.display = "block";
      const frame = sheet.querySelector(".map_container");
      const map = frame.querySelector(".map");
      const mapBox = map.getBoundingClientRect();
      const tableBox = table.getBoundingClientRect();
      const bottom = Number(map.dataset.contentBottom ?? 1);
      const occupied = mapBox.top + bottom * mapBox.height;
      if (occupied + gap <= tableBox.top && tableBox.height <= frame.clientHeight) {
        sheet.dataset.tablePlacement = "bottom";
        sheet.style.display = "";
        continue;
      }
      sheet.dataset.tablePlacement = "continuation";
      sheet.classList.remove("has-attribute-table");
      const rows = [...table.tBodies[0].rows];
      rows.forEach(row => row.remove());
      table.remove();
      let after = sheet, current, continuationFrame, pageNumber = 0;
      function newPage() {
        pageNumber++;
        const next = document.createElement("div");
        next.className = "drawing-sheet main_container attribute-continuation";
        next.dataset.drawing = sheet.dataset.drawing;
        next.dataset.printTitle = sheet.dataset.printTitle || sheet.dataset.title;
        next.dataset.title = sheet.dataset.title + "（属性表" + (pageNumber > 1 ? " " + pageNumber : "") + "）";
        next.append(sheet.querySelector("h1").cloneNode(true));
        const header = sheet.querySelector(".info_container").cloneNode(true);
        removeIds(header);
        next.append(header);
        const area = document.createElement("div");
        area.className = "sub_container";
        continuationFrame = document.createElement("div");
        continuationFrame.className = "map_container attribute-frame";
        current = table.cloneNode(false);
        const columns = table.querySelector("colgroup");
        if (columns) current.append(columns.cloneNode(true));
        current.append(table.tHead.cloneNode(true), document.createElement("tbody"));
        continuationFrame.append(current);
        const calculationColumn = sheet.querySelector('.xy_container').cloneNode(true);
        removeIds(calculationColumn);
        area.append(calculationColumn, continuationFrame);
        next.append(area);
        after.after(next);
        next.style.display = "block";
        after = next;
      }
      const fits = () => current.getBoundingClientRect().height <= continuationFrame.clientHeight + .1;
      newPage();
      for (const row of rows) {
        current.tBodies[0].append(row);
        if (fits()) continue;
        row.remove();
        if (current.tBodies[0].rows.length) newPage();
        current.tBodies[0].append(row);
        if (fits()) continue;
        // A single very long feature must also fit, without truncating text.
        const remaining = [...row.cells].map(cell => Array.from(cell.textContent));
        row.remove();
        while (remaining.some(text => text.length)) {
          const part = row.cloneNode(true);
          [...part.cells].forEach(cell => cell.textContent = "");
          current.tBodies[0].append(part);
          for (let i = 0; i < part.cells.length; i++) {
            let low = 0, high = remaining[i].length;
            while (low < high) {
              const middle = Math.ceil((low + high) / 2);
              part.cells[i].textContent = remaining[i].slice(0, middle).join("");
              if (fits()) low = middle; else high = middle - 1;
            }
            part.cells[i].textContent = remaining[i].splice(0, low).join("");
          }
          if (![...part.cells].some(cell => cell.textContent)) throw new Error("属性表の見出しが用紙に収まりません。");
          if (remaining.some(text => text.length)) newPage();
        }
      }
      sheet.style.display = "";
    }
    document.querySelectorAll(".attribute-continuation").forEach(sheet => sheet.style.display = "");
  }
  function paginateCalculations() {
    for (const sheet of [...document.querySelectorAll('.drawing-sheet:not(.attribute-continuation):not(.calculation-continuation)')]) {
      const column = sheet.querySelector('.xy_container');
      const map = sheet.querySelector('.map_container');
      const calculation = sheet.querySelector('.calc');
      if (!column || !map || !calculation) continue;
      sheet.style.display = 'block';
      const fitsColumn = () => column.getBoundingClientRect().height <= map.getBoundingClientRect().height + .5;
      if (!fitsColumn()) column.classList.add('calculations-compact');
      if (fitsColumn()) {
        for (const page of document.querySelectorAll('.attribute-continuation')) {
          if (page.dataset.drawing !== sheet.dataset.drawing) continue;
          const copy = column.cloneNode(true);
          removeIds(copy);
          page.querySelector('.xy_container').replaceWith(copy);
        }
        sheet.style.display = '';
        continue;
      }
      const units = [];
      for (const row of calculation.querySelector('.calc_area').children) {
        const deductions = row.querySelector('.calc-deduction');
        if (deductions) {
          units.push(row.querySelector('.calc-label').cloneNode(true));
          units.push(...[...deductions.children].map(child => child.cloneNode(true)));
        } else units.push(row.cloneNode(true));
      }
      // Fill the first page, then pair both continuation streams by page index.
      // Attribute pages already exist at this point and can host calculations.
      const attributePages = [...document.querySelectorAll('.attribute-continuation')]
        .filter(page => page.dataset.drawing === sheet.dataset.drawing);
      const columnTemplate = column.cloneNode(true);
      removeIds(columnTemplate);
      const mapTemplate = map.cloneNode(true);
      removeIds(mapTemplate);
      const area = calculation.querySelector('.calc_area');
      area.replaceChildren();
      area.classList.add('calculation-units');
      let after = sheet, frame = column, contents = area, number = 0;
      const height = map.getBoundingClientRect().height;
      frame.style.height = height + 'px';
      function newPage() {
        number++;
        let next = attributePages[number - 1];
        if (!next) {
          next = document.createElement('div');
          next.className = 'drawing-sheet main_container calculation-continuation';
          next.dataset.drawing = sheet.dataset.drawing;
          next.dataset.printTitle = sheet.dataset.printTitle || sheet.dataset.title;
          next.dataset.title = sheet.dataset.title + '（続き ' + (number + 1) + '）';
          next.append(sheet.querySelector('h1').cloneNode(true));
          const header = sheet.querySelector('.info_container').cloneNode(true);
          removeIds(header);
          next.append(header);
          const area = document.createElement('div');
          area.className = 'sub_container';
          area.append(columnTemplate.cloneNode(true), mapTemplate.cloneNode(true));
          next.append(area);
          after.after(next);
        }
        next.classList.add('calculation-continuation');
        next.dataset.title = sheet.dataset.title + '（続き ' + (number + 1) + '）';
        next.dataset.calculationContinuation = '1';
        const oldColumn = next.querySelector('.xy_container');
        frame = columnTemplate.cloneNode(true);
        frame.style.height = height + 'px';
        oldColumn.replaceWith(frame);
        frame.querySelector('.calc-heading').textContent += '（続き）';
        contents = frame.querySelector('.calc_area');
        contents.replaceChildren();
        contents.classList.add('calculation-units');
        next.style.display = 'block';
        after = next;
      }
      for (const unit of units) {
        contents.append(unit);
        if (frame.scrollHeight <= frame.clientHeight + 1) continue;
        unit.remove();
        newPage();
        contents.append(unit);
      }
      // Extra table pages repeat the calculation block of the first page.
      for (const page of attributePages.slice(number)) {
        const copy = column.cloneNode(true);
        removeIds(copy);
        page.querySelector('.xy_container').replaceWith(copy);
      }
      sheet.style.display = '';
    }
    document.querySelectorAll('.calculation-continuation').forEach(sheet => sheet.style.display = '');
  }
  window.RingyoLayout = {paginateTables, paginateCalculations};
})();
